"""
tests/test_asset_provenance.py — Task 5.3: provenance asset.

Mỗi asset sinh/tải về phải có sidecar `<asset>.meta.json` đúng schema;
storyboard nhúng `asset_meta` khi có; export ZIP kèm provenance.
"""

import json
import sys
import zipfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.media_engine import asset_provenance as prov  # noqa: E402

REQUIRED_KEYS = {"source", "source_url", "author", "license", "prompt", "created_at"}


def test_write_read_copy_meta_roundtrip(tmp_path):
    asset = tmp_path / "scene_000.png"
    asset.write_bytes(b"fake-image")

    meta = prov.write_asset_meta(
        asset,
        source="pexels",
        source_url="https://www.pexels.com/photo/123",
        author="Jane Doe",
        license="Pexels License",
        prompt=None,
    )
    assert meta is not None
    assert REQUIRED_KEYS <= set(meta.keys())
    sidecar = tmp_path / "scene_000.png.meta.json"
    assert sidecar.exists()

    loaded = prov.read_asset_meta(asset)
    assert loaded["source"] == "pexels"
    assert loaded["author"] == "Jane Doe"

    dest = tmp_path / "scene_001.png"
    dest.write_bytes(b"fake-image-2")
    copied = prov.copy_asset_meta(asset, dest)
    assert copied["source"] == "pexels"
    assert (tmp_path / "scene_001.png.meta.json").exists()

    # asset chưa có sidecar -> None (tương thích ngược job cũ)
    assert prov.read_asset_meta(tmp_path / "khong-co.png") is None


def test_provenance_from_cascade_metadata_mapping():
    imagen = prov.provenance_from_cascade_metadata(
        {"tier_used": "tier1_imagen", "source": "imagen-3.0-generate-002"}, prompt="p1"
    )
    assert imagen["source"] == "imagen"
    assert imagen["prompt"] == "p1"

    flux = prov.provenance_from_cascade_metadata(
        {"tier_used": "tier2_flux", "source": "pollinations_flux"}, prompt="p2"
    )
    assert flux["source"] == "flux"

    proc = prov.provenance_from_cascade_metadata(
        {"tier_used": "tier4_procedural", "source": "procedural_asset_synthesizer"}
    )
    assert proc["source"] == "procedural"

    stock = prov.provenance_from_cascade_metadata(
        {"tier_used": "tier3_stock", "source": "curated_or_wikimedia"},
        provenance_url="https://commons.wikimedia.org/wiki/File:X.jpg",
        provenance_provider="wikimedia",
    )
    assert stock["source"] == "wikimedia"
    assert stock["source_url"].startswith("https://commons.wikimedia.org/")


def _fake_download(self, url, output_path):
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"downloaded-bytes")
    return str(out.absolute())


def test_pexels_download_writes_meta(tmp_path, monkeypatch):
    from core.media_engine.pexels_client import PexelsClient

    monkeypatch.setenv("PEXELS_API_KEY", "test-key")
    client = PexelsClient()
    monkeypatch.setattr(PexelsClient, "_download_file", _fake_download)
    out = tmp_path / "img.png"
    saved = client.download_image(
        {
            "download_url": "https://images.pexels.com/photo.jpg",
            "url": "https://www.pexels.com/photo/999",
            "author": "John Photographer",
        },
        str(out),
    )
    meta = prov.read_asset_meta(saved)
    assert meta["source"] == "pexels"
    assert meta["source_url"] == "https://www.pexels.com/photo/999"
    assert meta["author"] == "John Photographer"
    assert "Pexels License" in meta["license"]


def test_pixabay_download_writes_meta(tmp_path, monkeypatch):
    from core.media_engine.pixabay_client import PixabayClient

    monkeypatch.setenv("PIXABAY_API_KEY", "test-key")
    client = PixabayClient()
    monkeypatch.setattr(PixabayClient, "_download_file", _fake_download)
    out = tmp_path / "img2.png"
    saved = client.download_image(
        {
            "download_url": "https://cdn.pixabay.com/photo.jpg",
            "url": "https://pixabay.com/photos/777",
            "author": "pixabay_user",
        },
        str(out),
    )
    meta = prov.read_asset_meta(saved)
    assert meta["source"] == "pixabay"
    assert meta["source_url"] == "https://pixabay.com/photos/777"
    assert meta["author"] == "pixabay_user"


def test_image_generator_procedural_fallback_writes_meta(tmp_path):
    from core.media_engine.image_generator import ImageGenerator

    gen = ImageGenerator()
    out = tmp_path / "collage.png"
    gen._generate_artistic_collage_fallback({"narration": "Thiên hà rực rỡ"}, 0, str(out))
    assert out.exists()
    meta = prov.read_asset_meta(out)
    assert meta["source"] == "procedural"
    assert meta["prompt"] == "Thiên hà rực rỡ"


def test_cascade_tier4_post_process_writes_real_sidecar(tmp_path):
    import asyncio

    from core.media_engine.cascade_asset_orchestrator import CascadeAssetOrchestrator

    async def _run():
        orch = CascadeAssetOrchestrator(cache_dir=tmp_path / "cache")
        img = orch._generate_tier4_procedural("white blood cell", width=256, height=256)
        return await orch._post_process_and_validate(
            candidate_img=img,
            target_object="white blood cell",
            job_cache_dir=tmp_path / "job",
            metadata={
                "tier_used": "tier4_procedural",
                "source": "procedural_asset_synthesizer",
                "confidence": 1.0,
                "is_aligned": True,
                "prompt": None,
            },
            width=256,
            height=256,
        )

    path, metadata = asyncio.run(_run())
    meta = prov.read_asset_meta(path)
    assert meta is not None
    assert meta["source"] == "procedural"
    assert REQUIRED_KEYS <= set(meta.keys())
    assert metadata["asset_meta"] == meta


@pytest.fixture()
def prov_db(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import dashboard.api.database as db_mod
    from dashboard.api.models import JobStatus

    engine = create_engine(
        f"sqlite:///{tmp_path}/prov.db", connect_args={"check_same_thread": False}
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_mod.Base.metadata.create_all(bind=engine)
    db = TestingSession()
    job = db_mod.VideoJob(
        id="job-prov",
        topic="Bạch cầu",
        style="collage_broll",
        language="vi",
        status=JobStatus.processing,
        stage="assets_ready",
        mode="auto",
    )
    job.pipeline_data = {"storyboard": [], "scenes": []}
    db.add(job)
    db.commit()
    yield db, db_mod
    db.close()


def test_update_scene_image_embeds_user_upload_meta(prov_db, tmp_path):
    db, db_mod = prov_db
    img = tmp_path / "up.png"
    img.write_bytes(b"user-image")

    updated = db_mod.update_scene_image(db, "job-prov", 0, str(img))
    scene = updated.pipeline_data["storyboard"][0]
    assert scene["tier_used"] == "user_uploaded"
    assert scene["asset_meta"]["source"] == "user_upload"


def test_export_zip_includes_provenance(prov_db, tmp_path, monkeypatch):
    import dashboard.api.routes.jobs as jobs_mod

    db, db_mod = prov_db
    monkeypatch.chdir(tmp_path)
    job_dir = Path("data/output/job-prov/images")
    job_dir.mkdir(parents=True, exist_ok=True)
    asset = job_dir / "scene_000.png"
    asset.write_bytes(b"img")
    meta = prov.write_asset_meta(
        asset, source="imagen", author="Google Imagen 3", license="AI-generated content",
        prompt="white blood cell, vintage engraving",
    )

    import dashboard.api.database as db_module

    job = db_module.get_job(db, "job-prov")
    p_data = job.pipeline_data or {}
    p_data["storyboard"] = [
        {"scene_index": 0, "image_path": str(asset), "tier_used": "tier1_imagen", "asset_meta": meta}
    ]
    job.pipeline_data = p_data
    db.commit()

    response = jobs_mod.export_job_zip("job-prov", db)
    zip_path = Path(response.path)
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "asset_provenance.json" in names
        assert any(n.endswith("scene_000.png.meta.json") for n in names)
        payload = json.loads(zf.read("asset_provenance.json"))
    assert payload[0]["provenance"]["source"] == "imagen"
