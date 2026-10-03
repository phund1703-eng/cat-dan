"""
tests/test_stage3_publish.py — Giai đoạn 3: đăng bài khép kín.

Mọi HTTP/Postiz đều là client giả; không gọi mạng thật.
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
import dashboard.api.routes.jobs as jobs_mod
import dashboard.worker.video_tasks as worker_mod
from dashboard.api.models import JobStatus


@pytest.fixture()
def publish_env(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path}/stage3.db", connect_args={"check_same_thread": False}
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_mod.Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(db_mod, "SessionLocal", TestingSession)
    monkeypatch.setattr(jobs_mod, "SessionLocal", TestingSession)
    monkeypatch.setattr(worker_mod, "SessionLocal", TestingSession)

    video_path = tmp_path / "final_video.mp4"
    video_path.write_bytes(b"fake-but-present-video")
    thumbnail_path = tmp_path / "thumbnail.jpg"
    thumbnail_path.write_bytes(b"thumbnail")

    db = TestingSession()
    try:
        job = db_mod.VideoJob(
            id="job-stage3",
            topic="Vì sao bạch cầu tiêu diệt vi khuẩn",
            style="collage_broll",
            language="vi",
            status=JobStatus.done,
            stage="done",
            mode="auto",
        )
        db.add(job)
        db.commit()
        worker_mod.update_job_stage(
            db,
            "job-stage3",
            "done",
            status=JobStatus.done,
            pipeline_data={
                "script": {
                    "title": "Bạch cầu làm gì?",
                    "description": "Giải thích ngắn",
                    "hashtags": ["#khoahoc"],
                    "scenes": [],
                },
                "metadata": {
                    "title": "Bạch cầu làm gì?",
                    "description": "Giải thích ngắn",
                    "hashtags": ["#khoahoc"],
                    "thumbnail_text": "BẠCH CẦU",
                },
                "thumbnail_path": str(thumbnail_path),
            },
        )
        job = worker_mod.get_job(db, "job-stage3")
        job.output_path = str(video_path)
        db.commit()
    finally:
        db.close()

    return TestingSession, video_path


def _get_job(TestingSession):
    db = TestingSession()
    try:
        return worker_mod.get_job(db, "job-stage3")
    finally:
        db.close()


def test_publish_success_records_postiz_id(publish_env, monkeypatch):
    TestingSession, video_path = publish_env
    calls = []

    class SuccessfulPostiz:
        async def schedule_post(self, **kwargs):
            calls.append(kwargs)
            return {"id": "post-123", "status": "scheduled"}

    monkeypatch.setattr(worker_mod, "PostizClient", SuccessfulPostiz)

    result = worker_mod.publish_video("job-stage3", ["youtube", "tiktok"])

    assert result["status"] == "published"
    assert result["postiz_post_id"] == "post-123"
    assert calls[0]["video_path"] == str(video_path)
    assert calls[0]["title"] == "Bạch cầu làm gì?"
    assert calls[0]["platforms"] == ["youtube", "tiktok"]
    assert calls[0]["thumbnail_path"].endswith("thumbnail.jpg")

    job = _get_job(TestingSession)
    assert job.status == JobStatus.published
    assert job.pipeline_data["publish"]["postiz_post_id"] == "post-123"
    assert job.pipeline_data["publish"]["status"] == "published"
    assert job.output_path == str(video_path)


def test_publish_failure_keeps_done_video_and_uses_publish_failed(publish_env, monkeypatch):
    TestingSession, video_path = publish_env

    class BrokenPostiz:
        async def schedule_post(self, **kwargs):
            raise RuntimeError("Postiz offline")

    monkeypatch.setattr(worker_mod, "PostizClient", BrokenPostiz)

    result = worker_mod.publish_video("job-stage3", ["youtube"])

    assert result["status"] == "publish_failed"
    job = _get_job(TestingSession)
    assert job.status == JobStatus.publish_failed
    assert job.status != JobStatus.failed
    assert job.stage == "done"
    assert job.output_path == str(video_path)
    assert video_path.exists()
    publish = job.pipeline_data["publish"]
    assert publish["status"] == "publish_failed"
    assert "Postiz offline" in publish["error"]
    assert publish["error_type"] == "RuntimeError"


def test_publish_response_without_post_id_is_failure(publish_env, monkeypatch):
    TestingSession, _video_path = publish_env

    class EmptyPostiz:
        async def schedule_post(self, **kwargs):
            return {"status": "queued"}

    monkeypatch.setattr(worker_mod, "PostizClient", EmptyPostiz)

    result = worker_mod.publish_video("job-stage3", ["youtube"])

    assert result["status"] == "publish_failed"
    job = _get_job(TestingSession)
    assert job.status == JobStatus.publish_failed
    assert "did not include a post id" in job.pipeline_data["publish"]["error"]

# ---------------------------------------------------------------------------
# Task 3.2 — Thumbnail
# ---------------------------------------------------------------------------
def test_thumbnail_dimensions_and_vietnamese_text_fit(tmp_path):
    from PIL import Image, ImageDraw

    from core.render_engine.thumbnail_generator import (
        LANDSCAPE_SIZE,
        PORTRAIT_SIZE,
        create_thumbnail_image,
        generate_job_thumbnails,
        wrap_thumbnail_text,
        _text_bbox,
    )

    source = tmp_path / "hook.png"
    Image.new("RGB", (640, 360), (44, 92, 145)).save(source)

    result = generate_job_thumbnails(
        tmp_path / "job-output",
        "CƠ THỂ NGƯỜI KỲ DIỆU",
        source_image_path=source,
        video_format="landscape",
    )

    with Image.open(result["thumbnail_path"]) as portrait:
        assert portrait.size == PORTRAIT_SIZE
    with Image.open(result["thumbnail_landscape_path"]) as landscape:
        assert landscape.size == LANDSCAPE_SIZE

    text = "CƠ THỂ NGƯỜI KỲ DIỆU"
    assert len(text) == 20
    _normalized, lines, font, _font_size = wrap_thumbnail_text(text, size=PORTRAIT_SIZE)
    probe_draw = ImageDraw.Draw(Image.new("RGB", PORTRAIT_SIZE))
    usable_width = int(int(PORTRAIT_SIZE[0] * 0.88) * 0.90)
    assert lines
    assert all(_text_bbox(probe_draw, line, font)[0] <= usable_width for line in lines)

    one = create_thumbnail_image(
        tmp_path / "single.jpg", text, source_image_path=source, size=PORTRAIT_SIZE
    )
    with Image.open(one) as image:
        assert image.size == PORTRAIT_SIZE
        assert image.format == "JPEG"


def test_worker_ensures_thumbnail_next_to_master(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from PIL import Image

    monkeypatch.chdir(tmp_path)
    job_dir = tmp_path / "data" / "output" / "job-thumb"
    job_dir.mkdir(parents=True)
    source = job_dir / "snapshot.jpg"
    Image.new("RGB", (540, 960), (120, 80, 40)).save(source)
    video = job_dir / "final_video.mp4"
    video.write_bytes(b"video")

    job = SimpleNamespace(
        id="job-thumb",
        topic="Cơ thể người",
        language="vi",
        style="collage_broll",
        output_path=str(video),
        script={"title": "Cơ thể kỳ diệu", "scenes": []},
        extra_metadata={},
    )
    pipeline_data = {
        "script": job.script,
        "metadata": {"thumbnail_text": "CƠ THỂ KỲ DIỆU"},
        "scenes": [],
    }

    result = worker_mod._ensure_job_thumbnail(job, pipeline_data)

    assert Path(result["thumbnail_path"]).exists()
    with Image.open(result["thumbnail_path"]) as image:
        assert image.size == (1080, 1920)
    assert pipeline_data["thumbnail_text"] == "CƠ THỂ KỲ DIỆU"


# ---------------------------------------------------------------------------
# Task 3.3 — Channels config + scheduling
# ---------------------------------------------------------------------------
def test_channels_config_reads_config_directory():
    from dashboard.api.routes.channels import (
        CHANNELS_CONFIG_PATH,
        get_channel,
        get_channel_schedule,
        load_channels_config,
    )

    assert CHANNELS_CONFIG_PATH.name == "channels.yaml"
    assert CHANNELS_CONFIG_PATH.parent.name == "config"
    config = load_channels_config()
    assert "collage_broll" in config
    assert get_channel("collage_broll")["style"] == "collage_broll"
    assert get_channel_schedule("collage_broll")["schedule"]["max_per_day"] == 3


def test_scheduler_feature_flag_can_be_disabled(monkeypatch):
    from dashboard.api.publish_scheduler import scheduler_enabled

    monkeypatch.setenv("CATDAN_PUBLISH_SCHEDULER_ENABLED", "0")
    assert scheduler_enabled() is False
    monkeypatch.setenv("CATDAN_PUBLISH_SCHEDULER_ENABLED", "1")
    assert scheduler_enabled() is True


@pytest.fixture()
def schedule_env(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path}/stage3-schedule.db", connect_args={"check_same_thread": False}
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_mod.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(db_mod, "SessionLocal", TestingSession)
    monkeypatch.setattr(jobs_mod, "SessionLocal", TestingSession)
    monkeypatch.setattr(worker_mod, "SessionLocal", TestingSession)

    db = TestingSession()
    try:
        for idx in range(3):
            job = db_mod.VideoJob(
                id=f"job-schedule-{idx}",
                topic=f"Chủ đề {idx}",
                style="collage_broll",
                language="vi",
                status=JobStatus.done,
                stage="done",
                mode="auto",
            )
            db.add(job)
        db.commit()
    finally:
        db.close()
    return TestingSession


def test_approve_three_jobs_with_max_per_day_two_rolls_third_to_next_day(
    schedule_env, monkeypatch
):
    from datetime import datetime, timezone

    TestingSession = schedule_env

    fake_schedule = {
        "enabled": True,
        "timezone": "UTC",
        "posting_times": ["07:00", "12:00", "20:00"],
        "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "max_per_day": 2,
    }
    monkeypatch.setattr(jobs_mod, "get_schedule_for_style", lambda style: fake_schedule)

    class FakeDateTime(datetime):
        fixed = datetime(2026, 10, 3, 6, 0, tzinfo=timezone.utc)

        @classmethod
        def now(cls, tz=None):
            return cls.fixed.astimezone(tz) if tz else cls.fixed

    monkeypatch.setattr(jobs_mod, "datetime", FakeDateTime)

    from fastapi.testclient import TestClient
    from dashboard.api.main import app

    with TestClient(app) as client:
        scheduled = []
        for idx in range(3):
            response = client.put(
                f"/jobs/job-schedule-{idx}/approve",
                json={"platforms": ["youtube"]},
            )
            assert response.status_code == 200, response.text
            payload = response.json()
            assert payload["status"] == "scheduled"
            scheduled.append(payload["scheduled_at"])

    assert scheduled[0].startswith("2026-10-03T07:00")
    assert scheduled[1].startswith("2026-10-03T12:00")
    assert scheduled[2].startswith("2026-10-04T07:00")

    db = TestingSession()
    try:
        for idx in range(3):
            job = worker_mod.get_job(db, f"job-schedule-{idx}")
            assert job.status == JobStatus.scheduled
            assert job.stage == "scheduled"
            assert job.pipeline_data["publish"]["status"] == "scheduled"
            assert job.pipeline_data["publish"]["scheduled_at"] == scheduled[idx]
    finally:
        db.close()


def test_run_due_publish_jobs_calls_publisher_only_when_due(schedule_env, monkeypatch):
    from datetime import datetime, timezone

    TestingSession = schedule_env
    db = TestingSession()
    try:
        job = worker_mod.get_job(db, "job-schedule-0")
        worker_mod.update_job_stage(
            db,
            job.id,
            "scheduled",
            status=JobStatus.scheduled,
            pipeline_data={
                "publish": {
                    "status": "scheduled",
                    "platforms": ["youtube"],
                    "scheduled_at": "2026-10-03T07:00:00+00:00",
                }
            },
        )
    finally:
        db.close()

    calls = []

    def fake_publish(job_id, platforms, schedule_time=None):
        calls.append((job_id, platforms, schedule_time))
        return {"status": "published", "job_id": job_id}

    monkeypatch.setattr(worker_mod, "publish_video", fake_publish)

    assert worker_mod.run_due_publish_jobs(datetime(2026, 10, 3, 6, 59, tzinfo=timezone.utc)) == []
    results = worker_mod.run_due_publish_jobs(datetime(2026, 10, 3, 7, 0, tzinfo=timezone.utc))
    assert results == [{"status": "published", "job_id": "job-schedule-0"}]
    assert calls == [("job-schedule-0", ["youtube"], None)]
