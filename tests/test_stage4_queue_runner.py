"""
Task 4.1 — Hàng đợi bền: worker poll DB (dashboard.worker.runner) thay
Celery/Redis. Test dispatch resume, tôn trọng điểm dừng duyệt, FIFO +
giới hạn đồng thời, và đọc config queue.max_concurrent_jobs.
"""

import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import dashboard.api.database as db_mod
import dashboard.worker.runner as runner_mod
import dashboard.worker.video_tasks as worker_mod
from dashboard.api.models import JobStatus


@pytest.fixture()
def runner_env(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path}/stage4.db", connect_args={"check_same_thread": False}
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_mod.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(db_mod, "SessionLocal", TestingSession)
    monkeypatch.setattr(worker_mod, "SessionLocal", TestingSession)
    return TestingSession


def _make_job(db, job_id, stage="pending", status=JobStatus.pending, mode="auto",
              created_at=None):
    job = db_mod.VideoJob(
        id=job_id,
        topic="Vì sao bạch cầu tiêu diệt vi khuẩn",
        style="collage_broll",
        language="vi",
        status=status,
        stage=stage,
        mode=mode,
    )
    db.add(job)
    db.commit()
    if created_at is not None:
        job.created_at = created_at
        db.commit()
    return job


def _stub_dispatch(monkeypatch):
    """Thay các hàm stage thật bằng recorder; trả dict ghi lại lời gọi."""
    calls = {"full": [], "stages23": [], "stages45": [], "gate_resume": []}

    monkeypatch.setattr(worker_mod, "run_video_pipeline",
                        lambda job_id: calls["full"].append(job_id))
    monkeypatch.setattr(worker_mod, "continue_video_pipeline",
                        lambda job_id: calls["stages45"].append(job_id))

    async def fake_stages_2_and_3(job_id):
        calls["stages23"].append(job_id)

    monkeypatch.setattr(worker_mod, "_async_execute_stages_2_and_3", fake_stages_2_and_3)
    monkeypatch.setattr(
        worker_mod, "continue_after_source_review",
        lambda job_id: calls["gate_resume"].append(job_id) or {"status": "resumed"},
    )
    return calls


# ---------------------------------------------------------------------------
# resume_video_pipeline — bảng dispatch theo stage
# ---------------------------------------------------------------------------

def test_resume_pending_runs_full_pipeline(runner_env, monkeypatch):
    TestingSession = runner_env
    db = TestingSession()
    try:
        _make_job(db, "job-new")
    finally:
        db.close()
    calls = _stub_dispatch(monkeypatch)

    result = worker_mod.resume_video_pipeline("job-new")

    assert result["action"] == "ran"
    assert calls["full"] == ["job-new"]


def test_resume_script_ready_auto_rechecks_source_gate(runner_env, monkeypatch):
    TestingSession = runner_env
    db = TestingSession()
    try:
        _make_job(db, "job-script", stage="script_ready", status=JobStatus.processing)
    finally:
        db.close()
    calls = _stub_dispatch(monkeypatch)

    result = worker_mod.resume_video_pipeline("job-script")

    assert result["action"] == "ran"
    assert calls["gate_resume"] == ["job-script"]


def test_resume_voice_ready_runs_stages_2_and_3(runner_env, monkeypatch):
    TestingSession = runner_env
    db = TestingSession()
    try:
        _make_job(db, "job-voice", stage="voice_ready", status=JobStatus.processing)
    finally:
        db.close()
    calls = _stub_dispatch(monkeypatch)

    result = worker_mod.resume_video_pipeline("job-voice")

    assert result["action"] == "ran"
    assert calls["stages23"] == ["job-voice"]


@pytest.mark.parametrize("stage", ["assets_ready", "rendering"])
def test_resume_render_stages_run_stages_4_and_5(runner_env, monkeypatch, stage):
    TestingSession = runner_env
    db = TestingSession()
    try:
        _make_job(db, f"job-{stage}", stage=stage, status=JobStatus.processing)
    finally:
        db.close()
    calls = _stub_dispatch(monkeypatch)

    result = worker_mod.resume_video_pipeline(f"job-{stage}")

    assert result["action"] == "ran"
    assert calls["stages45"] == [f"job-{stage}"]


def test_resume_waits_at_source_review(runner_env, monkeypatch):
    TestingSession = runner_env
    db = TestingSession()
    try:
        _make_job(db, "job-gate", stage="source_review", status=JobStatus.processing)
    finally:
        db.close()
    calls = _stub_dispatch(monkeypatch)

    result = worker_mod.resume_video_pipeline("job-gate")

    assert result["action"] == "waiting"
    assert calls == {"full": [], "stages23": [], "stages45": [], "gate_resume": []}


def test_resume_waits_at_step_by_step_assets_ready(runner_env, monkeypatch):
    TestingSession = runner_env
    db = TestingSession()
    try:
        _make_job(db, "job-step", stage="assets_ready",
                  status=JobStatus.processing, mode="step_by_step")
    finally:
        db.close()
    calls = _stub_dispatch(monkeypatch)

    result = worker_mod.resume_video_pipeline("job-step")

    assert result["action"] == "waiting"
    assert calls == {"full": [], "stages23": [], "stages45": [], "gate_resume": []}


@pytest.mark.parametrize("status", [JobStatus.done, JobStatus.failed,
                                    JobStatus.published, JobStatus.scheduled])
def test_resume_skips_terminal_statuses(runner_env, monkeypatch, status):
    TestingSession = runner_env
    db = TestingSession()
    try:
        _make_job(db, "job-term", stage="done", status=status)
    finally:
        db.close()
    calls = _stub_dispatch(monkeypatch)

    result = worker_mod.resume_video_pipeline("job-term")

    assert result["action"] == "skipped"
    assert calls == {"full": [], "stages23": [], "stages45": [], "gate_resume": []}


# ---------------------------------------------------------------------------
# WorkerRunner — claim, FIFO, concurrency, recovery
# ---------------------------------------------------------------------------

def _fake_resume_factory(TestingSession, calls, sleep_s=0.0):
    def fake_resume(job_id):
        calls.append(job_id)
        if sleep_s:
            time.sleep(sleep_s)
        db = TestingSession()
        try:
            worker_mod.update_job_stage(db, job_id, "done", status=JobStatus.done)
        finally:
            db.close()
        return {"job_id": job_id, "action": "ran"}

    return fake_resume


def test_runner_processes_pending_and_recovers_stuck_jobs(runner_env, monkeypatch):
    """Job mới (pending) + job kẹt stage trung gian đều được chạy tiếp."""
    TestingSession = runner_env
    db = TestingSession()
    try:
        _make_job(db, "job-fresh")
        _make_job(db, "job-stuck-voice", stage="voice_ready", status=JobStatus.processing)
        _make_job(db, "job-stuck-render", stage="rendering", status=JobStatus.processing)
    finally:
        db.close()

    calls = []
    monkeypatch.setattr(worker_mod, "resume_video_pipeline",
                        _fake_resume_factory(TestingSession, calls))

    runner = runner_mod.WorkerRunner(max_concurrent_jobs=2, poll_interval=0.05, once=True)
    processed = runner.run()

    assert processed == 3
    assert set(calls) == {"job-fresh", "job-stuck-voice", "job-stuck-render"}


def test_runner_never_touches_waiting_or_terminal_jobs(runner_env, monkeypatch):
    TestingSession = runner_env
    db = TestingSession()
    try:
        _make_job(db, "job-gate", stage="source_review", status=JobStatus.processing)
        _make_job(db, "job-review", stage="assets_ready",
                  status=JobStatus.processing, mode="step_by_step")
        _make_job(db, "job-done", stage="done", status=JobStatus.done)
        _make_job(db, "job-failed", stage="failed", status=JobStatus.failed)
    finally:
        db.close()

    calls = []
    monkeypatch.setattr(worker_mod, "resume_video_pipeline",
                        _fake_resume_factory(TestingSession, calls))

    runner = runner_mod.WorkerRunner(max_concurrent_jobs=2, poll_interval=0.05, once=True)
    processed = runner.run()

    assert processed == 0
    assert calls == []


def test_runner_fifo_and_concurrency_limit(runner_env, monkeypatch):
    """5 job cùng lúc -> tối đa 2 chạy song song, bắt đầu theo FIFO."""
    TestingSession = runner_env
    db = TestingSession()
    try:
        base = datetime(2026, 1, 1, 0, 0, 0)
        for i in range(5):
            _make_job(db, f"job-{i}", created_at=base + timedelta(seconds=i))
    finally:
        db.close()

    lock = threading.Lock()
    state = {"active": 0, "max_active": 0, "starts": []}

    def fake_resume(job_id):
        with lock:
            state["active"] += 1
            state["max_active"] = max(state["max_active"], state["active"])
            state["starts"].append(job_id)
        time.sleep(0.25)
        with lock:
            state["active"] -= 1
        db2 = TestingSession()
        try:
            worker_mod.update_job_stage(db2, job_id, "done", status=JobStatus.done)
        finally:
            db2.close()
        return {"job_id": job_id, "action": "ran"}

    monkeypatch.setattr(worker_mod, "resume_video_pipeline", fake_resume)

    runner = runner_mod.WorkerRunner(max_concurrent_jobs=2, poll_interval=0.05, once=True)
    processed = runner.run()

    assert processed == 5
    assert state["max_active"] <= 2
    assert state["starts"][:2] == ["job-0", "job-1"]
    assert set(state["starts"]) == {f"job-{i}" for i in range(5)}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_load_max_concurrent_jobs(tmp_path, monkeypatch):
    cfg = tmp_path / "settings.yaml"
    cfg.write_text("queue:\n  max_concurrent_jobs: 3\n", encoding="utf-8")

    monkeypatch.delenv("CATDAN_MAX_CONCURRENT_JOBS", raising=False)
    assert runner_mod.load_max_concurrent_jobs(cfg) == 3

    monkeypatch.setenv("CATDAN_MAX_CONCURRENT_JOBS", "5")
    assert runner_mod.load_max_concurrent_jobs(cfg) == 5

    monkeypatch.delenv("CATDAN_MAX_CONCURRENT_JOBS", raising=False)
    assert runner_mod.load_max_concurrent_jobs(tmp_path / "khong-co.yaml") == 2
