"""
tests/test_source_gate.py — Task 2.2 Source Gate.

Phạm vi:
- Phát hiện khẳng định định lượng (số/năm/đơn vị/tỉ lệ) -> needs_source.
- Audit verified/unreachable bằng fetcher mock (không mạng thật).
- Job dừng ở source_review và tiếp tục sau khi bổ sung nguồn (resume qua API + worker).
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.script_engine.source_gate import (
    STATUS_NEEDS_SOURCE,
    STATUS_UNREACHABLE,
    STATUS_VERIFIED,
    contains_numeric_claim,
    evaluate_gate,
    validate_source_url,
)


def _ok_fetcher(url):
    return {"reachable": True, "http_status": 200, "text": "Bạch cầu tiêu diệt vi khuẩn xâm nhập.", "error": ""}


def _dead_fetcher(url):
    return {"reachable": False, "http_status": 404, "text": "", "error": "HTTP 404"}


# ---------------------------------------------------------------------------
# Phát hiện số liệu
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("text", [
    "Mỗi giây cơ thể tạo ra 2 triệu tế bào mới.",
    "Chiều dài DNA khoảng 100 tỷ km.",
    "Năm 1969 con người đặt chân lên Mặt Trăng.",
    "San hô nuôi dưỡng 25% sinh vật biển.",
    "Nhiệt độ bề mặt đạt 5.500 độ C.",
    "Có hàng nghìn loài vi khuẩn.",
    "More than 3 billion people are affected.",
])
def test_numeric_claim_detected(text):
    assert contains_numeric_claim(text) is True


@pytest.mark.parametrize("text", [
    "Bạch cầu là những chiến binh bảo vệ cơ thể.",
    "Trái Đất là hành tinh xanh kỳ diệu.",
    "",
])
def test_qualitative_claim_not_numeric(text):
    assert contains_numeric_claim(text) is False


# ---------------------------------------------------------------------------
# Audit từng trạng thái
# ---------------------------------------------------------------------------
def test_scene_with_numbers_but_no_sources_is_blocked():
    scenes = [{"scene_index": 0, "narration": "Cơ thể có 37 nghìn tỷ tế bào.", "fact": "", "sources": []}]
    gate = evaluate_gate(scenes, fetcher=_ok_fetcher, use_cache=False)
    assert gate["has_blocking"] is True
    assert gate["blocking"] == [0]
    assert gate["audit"][0]["status"] == STATUS_NEEDS_SOURCE


def test_scene_with_reachable_source_is_verified():
    scenes = [{
        "scene_index": 0,
        "narration": "Bạch cầu tiêu diệt vi khuẩn xâm nhập.",
        "fact": "Bạch cầu tiêu diệt vi khuẩn",
        "sources": [{"title": "Wiki", "url": "https://vi.wikipedia.org/wiki/Bach_cau", "publisher": "Wikipedia", "accessed_date": "2026-10-03"}],
    }]
    gate = evaluate_gate(scenes, fetcher=_ok_fetcher, use_cache=False)
    assert gate["has_blocking"] is False
    assert gate["audit"][0]["status"] == STATUS_VERIFIED
    assert "tiêu diệt vi khuẩn" in gate["audit"][0]["excerpt"]


def test_scene_with_unreachable_source():
    scenes = [{
        "scene_index": 0,
        "narration": "Trái Đất cách Mặt Trời 150 triệu km.",
        "fact": "",
        "sources": [{"title": "X", "url": "https://example.org/dead", "publisher": "", "accessed_date": ""}],
    }]
    gate = evaluate_gate(scenes, fetcher=_dead_fetcher, use_cache=False)
    assert gate["audit"][0]["status"] == STATUS_UNREACHABLE
    # unreachable không thuộc nhóm chặn cứng (chỉ needs_source mới chặn Auto)
    assert gate["has_blocking"] is False


def test_malformed_source_url_is_unreachable():
    scenes = [{
        "scene_index": 0,
        "narration": "Có 8 hành tinh trong Hệ Mặt Trời.",
        "fact": "",
        "sources": [{"title": "X", "url": "khong-phai-url", "publisher": "", "accessed_date": ""}],
    }]
    gate = evaluate_gate(scenes, fetcher=_ok_fetcher, use_cache=False)
    assert gate["audit"][0]["status"] == STATUS_UNREACHABLE


@pytest.mark.parametrize("url,ok", [
    ("https://www.who.int/news-room", True),
    ("http://example.com/page", True),
    ("www.who.int/news", False),
    ("ftp://example.com/x", False),
    ("http://localhost:8000/x", False),
    ("https://127.0.0.1/x", False),
    ("", False),
])
def test_validate_source_url(url, ok):
    assert validate_source_url(url)[0] is ok


# ---------------------------------------------------------------------------
# Dừng ở source_review + bổ sung nguồn + tiếp tục (DB + API)
# ---------------------------------------------------------------------------
@pytest.fixture()
def job_env(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import dashboard.api.database as db_mod
    import dashboard.api.routes.jobs as jobs_mod
    import dashboard.worker.video_tasks as worker_mod
    import core.script_engine.source_gate as gate_mod

    engine = create_engine(f"sqlite:///{tmp_path}/t.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_mod.Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(db_mod, "SessionLocal", TestingSession)
    monkeypatch.setattr(jobs_mod, "SessionLocal", TestingSession)
    monkeypatch.setattr(worker_mod, "SessionLocal", TestingSession)
    monkeypatch.setattr(gate_mod, "_default_fetcher", _ok_fetcher)

    resumed = []

    async def fake_stages_2_and_3(job_id):
        resumed.append(job_id)
        db = TestingSession()
        try:
            worker_mod.update_job_stage(db, job_id, "assets_ready", pipeline_data=(worker_mod.get_job(db, job_id).pipeline_data or {}))
        finally:
            db.close()

    monkeypatch.setattr(worker_mod, "_async_execute_stages_2_and_3", fake_stages_2_and_3)
    return TestingSession, resumed


def _create_blocked_job(TestingSession):
    import dashboard.worker.video_tasks as worker_mod
    from dashboard.api.models import JobStatus

    db = TestingSession()
    try:
        job = worker_mod.get_job(db, "job-test-1")
        if job is None:
            from dashboard.api.database import VideoJob
            job = VideoJob(
                id="job-test-1", topic="Vì sao bạch cầu tiêu diệt vi khuẩn",
                style="collage_broll", language="vi", status=JobStatus.processing,
                stage="source_review", mode="auto",
            )
            db.add(job)
            db.commit()
        scenes = [{
            "scene_index": 0, "index": 0,
            "narration": "Mỗi giây cơ thể tạo ra hàng triệu tế bào mới.",
            "fact": "", "sources": [], "duration": 4.0,
        }]
        p_data = {"script": {"title": "t", "scenes": [dict(scenes[0])]}, "scenes": scenes}
        worker_mod.update_job_stage(db, "job-test-1", "source_review", status=JobStatus.processing, pipeline_data=p_data)
        return "job-test-1"
    finally:
        db.close()


def test_resume_blocked_then_resumed_after_sources_added(job_env):
    TestingSession, resumed = job_env
    import dashboard.worker.video_tasks as worker_mod

    job_id = _create_blocked_job(TestingSession)

    # Chưa có nguồn -> vẫn chặn
    result = worker_mod.continue_after_source_review(job_id)
    assert result["status"] == "blocked"
    assert resumed == []
    db = TestingSession()
    try:
        assert worker_mod.get_job(db, job_id).stage == "source_review"
    finally:
        db.close()

    # Bổ sung nguồn qua API endpoint (TestClient)
    from fastapi.testclient import TestClient
    from dashboard.api.main import app

    with TestClient(app) as client:
        r = client.post(f"/jobs/{job_id}/step/sources", json={
            "scenes": [{
                "scene_index": 0,
                "fact": "Cơ thể liên tục tạo tế bào mới",
                "sources": [{"title": "Wikipedia", "url": "https://vi.wikipedia.org/wiki/Te_bao", "publisher": "Wikipedia", "accessed_date": "2026-10-03"}],
            }]
        })
        assert r.status_code == 200, r.text
        assert r.json()["stage"] == "source_review"

        # Job không ở source_review thì continue-source-review phải 400
        r_bad = client.post("/jobs/khong-ton-tai/continue-source-review")
        assert r_bad.status_code == 404

        r2 = client.post(f"/jobs/{job_id}/continue-source-review")
        assert r2.status_code == 200, r2.text

    # Background task đã chạy (TestClient chạy nền đồng bộ) -> stages 2-3 được gọi
    assert resumed == [job_id]
    db = TestingSession()
    try:
        job = worker_mod.get_job(db, job_id)
        assert job.stage == "assets_ready"
        audit = (job.pipeline_data or {}).get("source_audit") or []
        assert audit and audit[0]["status"] == STATUS_VERIFIED
    finally:
        db.close()
