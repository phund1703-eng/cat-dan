"""
core/media_engine/asset_provenance.py — Truy vết nguồn gốc asset (Task 5.3).

Mỗi asset được sinh ra hoặc tải về đều có một file sidecar đi kèm:

    <asset_file>.meta.json        (vd: scene_000.png.meta.json)

với schema:

    {
      "source": "imagen|flux|pexels|pixabay|procedural|user_upload",
      "source_url": "https://... (trang nguồn, nếu có)",
      "author": "tác giả / công cụ tạo",
      "license": "giấy phép sử dụng",
      "prompt": "prompt đã dùng để sinh (nếu có)",
      "created_at": "2026-10-03T12:34:56+00:00"
    }

Ngoài 6 nguồn chuẩn trên, pipeline còn ghi đúng tên nhà cung cấp thật cho
ảnh stock ngoài danh mục đó — "wikimedia", "unsplash" (ảnh curated),
"template" (ảnh mẫu có sẵn trong repo) — thà ghi đúng nguồn còn hơn gán
nhầm sang pexels/pixabay. Hàm đọc luôn trả None khi asset chưa có sidecar
(job cũ) để mọi luồng tương thích ngược.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger(__name__)

#: Sáu nguồn chuẩn theo đặc tả Giai đoạn 5.3 (cộng thêm tên provider thật
#: như wikimedia/unsplash/template khi asset đến từ các kho đó).
KNOWN_SOURCES = (
    "imagen",
    "flux",
    "pexels",
    "pixabay",
    "procedural",
    "user_upload",
)

PathLike = Union[str, Path]


def meta_path_for(asset_path: PathLike) -> Path:
    """Đường dẫn sidecar của một asset: `<asset>.meta.json`."""
    p = Path(asset_path)
    return p.with_name(p.name + ".meta.json")


def build_asset_meta(
    source: str,
    source_url: Optional[str] = None,
    author: Optional[str] = None,
    license: Optional[str] = None,
    prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """Dựng dict metadata đúng schema provenance (chưa ghi đĩa)."""
    return {
        "source": source,
        "source_url": source_url,
        "author": author,
        "license": license,
        "prompt": prompt,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def write_asset_meta(asset_path: PathLike, **kwargs: Any) -> Optional[Dict[str, Any]]:
    """
    Ghi `<asset>.meta.json` cho asset tại `asset_path`.

    Trả dict metadata đã ghi; lỗi ghi đĩa chỉ log cảnh báo và trả None —
    provenance không bao giờ được làm hỏng pipeline sinh asset.
    """
    meta = build_asset_meta(**kwargs)
    try:
        target = meta_path_for(asset_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return meta
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Không ghi được provenance cho {asset_path}: {exc}")
        return None


def read_asset_meta(asset_path: PathLike) -> Optional[Dict[str, Any]]:
    """Đọc sidecar của asset; None khi chưa có hoặc file hỏng (job cũ)."""
    try:
        target = meta_path_for(asset_path)
        if not target.exists():
            return None
        data = json.loads(target.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Không đọc được provenance của {asset_path}: {exc}")
        return None


def copy_asset_meta(source_asset: PathLike, dest_asset: PathLike) -> Optional[Dict[str, Any]]:
    """
    Chép provenance từ asset gốc sang asset đích (vd asset cascade →
    scene_XXX.png sau _ensure_scene_composite). Không sửa nội dung meta.
    """
    meta = read_asset_meta(source_asset)
    if meta is None:
        return None
    try:
        target = meta_path_for(dest_asset)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return meta
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Không chép được provenance {source_asset} → {dest_asset}: {exc}")
        return None


def provenance_from_cascade_metadata(
    metadata: Dict[str, Any],
    prompt: Optional[str] = None,
    provenance_url: Optional[str] = None,
    provenance_provider: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Chuyển metadata nội bộ của CascadeAssetOrchestrator
    (tier_used/source dạng 'imagen-3.0-generate-002', 'pollinations_flux',
    'curated_or_wikimedia', 'procedural_asset_synthesizer') sang kwargs
    cho write_asset_meta() đúng schema provenance.
    """
    raw_source = str(metadata.get("source", ""))
    tier = str(metadata.get("tier_used", ""))

    if "imagen" in raw_source or tier.startswith("tier1"):
        return {
            "source": "imagen",
            "source_url": None,
            "author": "Google Imagen 3 (imagen-3.0-generate-002)",
            "license": "AI-generated content",
            "prompt": prompt,
        }
    if "flux" in raw_source or tier.startswith("tier2"):
        return {
            "source": "flux",
            "source_url": provenance_url,
            "author": "Pollinations FLUX.1",
            "license": "AI-generated content",
            "prompt": prompt,
        }
    if tier.startswith("tier4") or "procedural" in raw_source:
        return {
            "source": "procedural",
            "source_url": None,
            "author": "AutoVideoFactory ProceduralAssetSynthesizer",
            "license": "Generated in-repo (project LICENSE)",
            "prompt": prompt,
        }
    # Tier 3: ảnh stock curated/Wikimedia — ghi đúng provider thật.
    provider = provenance_provider or "wikimedia"
    license_by_provider = {
        "wikimedia": "Wikimedia Commons (see source file page for exact license)",
        "unsplash": "Unsplash License",
    }
    return {
        "source": provider,
        "source_url": provenance_url,
        "author": None,
        "license": license_by_provider.get(provider, "See source_url"),
        "prompt": prompt,
    }


__all__ = [
    "KNOWN_SOURCES",
    "meta_path_for",
    "build_asset_meta",
    "write_asset_meta",
    "read_asset_meta",
    "copy_asset_meta",
    "provenance_from_cascade_metadata",
]
