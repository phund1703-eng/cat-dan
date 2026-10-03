"""
tests/test_sources_on_product.py — Task 2.4 (nguồn lên sản phẩm cuối).

- Mô tả metadata có mục "Nguồn tham khảo:" (dedupe theo URL).
- Export ZIP chứa sources.json + sources.md khớp nội dung scene.
"""

import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from publish.metadata_generator import (
    MetadataGenerator,
    append_sources_to_description,
    build_sources_markdown,
    build_sources_payload,
    collect_sources,
)

SCRIPT = {
    "title": "Bạch cầu",
    "description": "Mô tả gốc.",
    "scenes": [
        {
            "scene_index": 0,
            "fact": "Bạch cầu tiêu diệt vi khuẩn",
            "sources": [
                {"title": "Bạch cầu – Wikipedia", "url": "https://vi.wikipedia.org/wiki/Bach_cau", "publisher": "Wikipedia", "accessed_date": "2026-10-03"},
                {"title": "WHO Fact", "url": "https://www.who.int/example", "publisher": "WHO", "accessed_date": ""},
            ],
        },
        {
            "scene_index": 1,
            "fact": "Tế bào mới được tạo liên tục",
            "sources": [
                {"title": "Bạch cầu – Wikipedia", "url": "https://vi.wikipedia.org/wiki/Bach_cau", "publisher": "Wikipedia", "accessed_date": "2026-10-03"},
            ],
        },
        {"scene_index": 2, "fact": "", "sources": []},
    ],
}


def test_collect_sources_dedupes_by_url():
    sources = collect_sources(SCRIPT)
    assert [s["url"] for s in sources] == [
        "https://vi.wikipedia.org/wiki/Bach_cau",
        "https://www.who.int/example",
    ]


def test_description_gets_sources_section():
    desc = append_sources_to_description(SCRIPT["description"], SCRIPT, "vi")
    assert desc.startswith("Mô tả gốc.")
    assert "Nguồn tham khảo:" in desc
    assert "https://vi.wikipedia.org/wiki/Bach_cau" in desc
    assert desc.count("Bach_cau") == 1  # dedupe
    # idempotent
    assert append_sources_to_description(desc, SCRIPT, "vi") == desc


def test_fallback_metadata_includes_sources():
    meta = MetadataGenerator.__new__(MetadataGenerator)  # tránh khởi tạo GeminiClient
    out = MetadataGenerator._fallback_metadata(meta, SCRIPT, "vi")
    out = MetadataGenerator._with_sources_section(out, SCRIPT, "vi")
    assert "Nguồn tham khảo:" in out["description"]
    assert len(out["sources"]) == 2


def test_build_sources_payload_and_markdown():
    payload = build_sources_payload(SCRIPT["scenes"])
    assert len(payload["sources"]) == 2
    assert len(payload["scenes"]) == 3
    md = build_sources_markdown(SCRIPT["scenes"])
    assert md.startswith("# Nguồn tham khảo")
    assert "Bạch cầu – Wikipedia" in md
    assert "https://www.who.int/example" in md


@pytest.fixture()
def zip_env(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import dashboard.api.database as db_mod
    import dashboard.api.routes.jobs as jobs_mod

    engine = create_engine(f"sqlite:///{tmp_path}/t.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_mod.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(db_mod, "SessionLocal", TestingSession)
    monkeypatch.setattr(jobs_mod, "SessionLocal", TestingSession)
    return TestingSession


def test_export_zip_contains_sources_files(zip_env):
    TestingSession = zip_env
    from dashboard.api.database import VideoJob
    from dashboard.api.models import JobStatus

    job_id = "job-zip-1"
    db = TestingSession()
    try:
        db.add(VideoJob(
            id=job_id, topic="Bạch cầu", style="collage_broll", language="vi",
            status=JobStatus.done, stage="done", mode="auto",
            pipeline_data_json=json.dumps({"scenes": SCRIPT["scenes"], "script": {"scenes": SCRIPT["scenes"]}}, ensure_ascii=False),
        ))
        db.commit()
    finally:
        db.close()

    from fastapi.testclient import TestClient
    from dashboard.api.main import app

    with TestClient(app) as client:
        r = client.get(f"/jobs/{job_id}/export-zip")
        assert r.status_code == 200, r.text

    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    assert "sources.json" in names
    assert "sources.md" in names
    payload = json.loads(zf.read("sources.json").decode("utf-8"))
    assert len(payload["sources"]) == 2
    md = zf.read("sources.md").decode("utf-8")
    assert "Bach_cau" in md

    # dọn file zip test sinh ra ở data/output
    zip_path = Path("data/output") / f"{job_id}.zip"
    zip_path.unlink(missing_ok=True)
