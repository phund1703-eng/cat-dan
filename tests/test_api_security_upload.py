"""
tests/test_api_security_upload.py — Task 5.4: an toàn API tối thiểu.

- SECRET_KEY đã đặt → endpoint ghi thiếu/sai X-API-Key bị 401, đúng key chạy.
- SECRET_KEY chưa đặt → API không khoá (dev localhost).
- Upload validate bằng magic bytes: file .exe đổi đuôi .png/.mp3 bị chặn;
  vượt giới hạn dung lượng bị 413.
"""

import io
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import dashboard.api.database as db_mod
from dashboard.api.upload_validation import (
    detect_audio_format,
    detect_image_format,
)

SECRET = "test-secret-key-123"
JOB_BODY = {
    "topic": "Kiểm tra bảo mật API",
    "style": "collage_broll",
    "language": "vi",
    "mode": "auto",
}
VALID_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02"
    b"\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
)
EXE_BYTES = b"MZ\x90\x00\x03\x00\x00\x00fake executable content"


@pytest.fixture()
def api_client(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path}/security.db", connect_args={"check_same_thread": False}
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_mod.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(db_mod, "SessionLocal", TestingSession)

    from fastapi.testclient import TestClient
    from dashboard.api.main import app

    with TestClient(app) as client:
        yield client


def _create_job(client, headers=None):
    return client.post("/jobs", json=JOB_BODY, headers=headers or {})


# ---------------------------------------------------------------------------
# X-API-Key
# ---------------------------------------------------------------------------

def test_write_endpoints_locked_when_secret_set(api_client, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", SECRET)

    # Thiếu key -> 401
    resp = _create_job(api_client)
    assert resp.status_code == 401

    # Sai key -> 401
    resp = _create_job(api_client, {"X-API-Key": "sai-key"})
    assert resp.status_code == 401

    # Đúng key -> chạy bình thường
    resp = _create_job(api_client, {"X-API-Key": SECRET})
    assert resp.status_code == 200, resp.text
    job_id = resp.json()["id"]

    # DELETE cũng bị khoá
    resp = api_client.delete(f"/jobs/{job_id}")
    assert resp.status_code == 401
    resp = api_client.delete(f"/jobs/{job_id}", headers={"X-API-Key": SECRET})
    assert resp.status_code == 200, resp.text

    # GET vẫn mở (chỉ endpoint ghi mới khoá)
    resp = api_client.get("/jobs")
    assert resp.status_code == 200


def test_write_endpoints_open_when_secret_unset(api_client, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "")
    resp = _create_job(api_client)
    assert resp.status_code == 200, resp.text


def test_placeholder_secret_counts_as_unset(api_client, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "change_this_to_random_secret_key_for_production")
    resp = _create_job(api_client)
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# Upload validation (magic bytes)
# ---------------------------------------------------------------------------

def test_detect_formats_by_magic_bytes():
    assert detect_image_format(VALID_PNG) == "png"
    assert detect_image_format(b"\xff\xd8\xff\xe0jpeg") == "jpg"
    assert detect_image_format(b"RIFF\x00\x00\x00\x00WEBP...") == "webp"
    assert detect_image_format(EXE_BYTES) is None
    assert detect_audio_format(b"RIFF$\x00\x00\x00WAVEfmt ") == "wav"
    assert detect_audio_format(b"ID3\x03\x00...") == "mp3"
    assert detect_audio_format(b"\xff\xfb\x90d...") == "mp3"
    assert detect_audio_format(EXE_BYTES) is None


def test_exe_disguised_as_png_rejected(api_client, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", SECRET)
    headers = {"X-API-Key": SECRET}
    job_id = _create_job(api_client, headers).json()["id"]

    resp = api_client.post(
        f"/jobs/{job_id}/upload-scene-image",
        data={"scene_index": 0},
        files={"file": ("evil.png", io.BytesIO(EXE_BYTES), "image/png")},
        headers=headers,
    )
    assert resp.status_code == 400, resp.text

    # Ảnh PNG thật thì qua
    resp = api_client.post(
        f"/jobs/{job_id}/upload-scene-image",
        data={"scene_index": 0},
        files={"file": ("real.png", io.BytesIO(VALID_PNG), "image/png")},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


def test_exe_disguised_as_mp3_rejected(api_client, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", SECRET)
    headers = {"X-API-Key": SECRET}
    resp = api_client.post(
        "/voices/upload",
        files={"file": ("malware.mp3", io.BytesIO(EXE_BYTES), "audio/mpeg")},
        headers=headers,
    )
    assert resp.status_code == 400, resp.text

    # Không key thì bị 401 trước cả validate
    resp = api_client.post(
        "/voices/upload",
        files={"file": ("malware.mp3", io.BytesIO(EXE_BYTES), "audio/mpeg")},
    )
    assert resp.status_code == 401


def test_oversize_image_upload_rejected(api_client, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", SECRET)
    headers = {"X-API-Key": SECRET}
    job_id = _create_job(api_client, headers).json()["id"]

    big = VALID_PNG + b"\x00" * (16 * 1024 * 1024)  # > 15 MB
    resp = api_client.post(
        f"/jobs/{job_id}/upload-scene-image",
        data={"scene_index": 0},
        files={"file": ("big.png", io.BytesIO(big), "image/png")},
        headers=headers,
    )
    assert resp.status_code == 413, resp.text


def test_empty_upload_rejected(api_client, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", SECRET)
    headers = {"X-API-Key": SECRET}
    job_id = _create_job(api_client, headers).json()["id"]
    resp = api_client.post(
        f"/jobs/{job_id}/upload-scene-image",
        data={"scene_index": 0},
        files={"file": ("empty.png", io.BytesIO(b""), "image/png")},
        headers=headers,
    )
    assert resp.status_code == 400, resp.text
