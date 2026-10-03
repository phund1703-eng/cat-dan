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
