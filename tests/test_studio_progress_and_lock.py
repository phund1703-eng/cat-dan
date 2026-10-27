"""
Tests for Studio Real-time Progress, Manual Studio Lock, and TTS Singleton Cache.
"""
import sys
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
from core.tts_engine.vieneu_client import VieNeuClient, _SHARED_TTS_ENGINES


@pytest.fixture()
def test_db_session(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path}/test_lock.db", connect_args={"check_same_thread": False}
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_mod.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(db_mod, "SessionLocal", TestingSession)
    monkeypatch.setattr(worker_mod, "SessionLocal", TestingSession)
    return TestingSession


def test_update_job_progress(test_db_session):
    db = test_db_session()
    try:
        job = db_mod.VideoJob(
            id="job-prog-1",
            topic="Kiểm tra tiến độ",
            style="collage_broll",
            language="vi",
            status=JobStatus.processing,
            stage="script_ready",
            pipeline_data={}
        )
        db.add(job)
        db.commit()

        # Update progress
        worker_mod.update_job_progress(
            db, "job-prog-1",
            percent=35,
            current_step="Đang thu âm Cảnh 2/5",
            scene_current=2,
            scene_total=5,
            log_line="Đã tạo âm thanh Cảnh 2"
        )

        job_updated = db_mod.get_job(db, "job-prog-1")
        prog = job_updated.pipeline_data.get("progress", {})
        assert prog["percent"] == 35
        assert prog["current_step"] == "Đang thu âm Cảnh 2/5"
        assert prog["scene_current"] == 2
        assert prog["scene_total"] == 5
        assert len(prog["logs"]) >= 1
        assert "Đã tạo âm thanh Cảnh 2" in prog["logs"][-1]
    finally:
        db.close()


def test_manual_studio_lock_prevents_worker_claim(test_db_session):
    db = test_db_session()
    try:
        job = db_mod.VideoJob(
            id="job-lock-1",
            topic="Khóa studio",
            status=JobStatus.processing,
            stage="script_ready",
            mode="auto",
            pipeline_data={"manual_studio_lock": True}
        )
        db.add(job)
        db.commit()

        # Runner must NOT claim this job because manual_studio_lock is True
        assert runner_mod.is_claimable(job, in_flight_ids=set()) is False

        # resume_video_pipeline must return action="waiting"
        res = worker_mod.resume_video_pipeline("job-lock-1")
        assert res["action"] == "waiting"
        assert res["reason"] == "manual_studio_lock"
    finally:
        db.close()


def test_vieneu_singleton_engine_cache():
    # Verify _SHARED_TTS_ENGINES is present
    client1 = VieNeuClient(precision="int8")
    client2 = VieNeuClient(precision="int8")
    assert client1.precision == client2.precision
    # Dummy mock test to verify singleton behavior
    dummy_model = object()
    _SHARED_TTS_ENGINES["mock_prec"] = dummy_model
    client_mock = VieNeuClient(precision="mock_prec")
    assert client_mock._get_tts() is dummy_model
    del _SHARED_TTS_ENGINES["mock_prec"]
