"""
scripts/audit_and_migrate_asset_cache.py
Kiểm tra, thanh lọc và di chuyển asset từ cache cũ (data/cache/cutouts)
sang thư viện trung tâm đã kiểm duyệt (data/asset_library/global_cutouts).
Loại bỏ và cô lập triệt để các file rác thuộc danh sách đen (Requirement R5).
"""

import os
import shutil
from pathlib import Path
from typing import Set, List, Dict, Any, Tuple
from PIL import Image
from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OLD_CACHE = PROJECT_ROOT / "data" / "cache" / "cutouts"
NEW_LIBRARY = PROJECT_ROOT / "data" / "asset_library" / "global_cutouts"
QUARANTINE_DIR = PROJECT_ROOT / "data" / "cache" / "quarantine"
HUMAN_BODY_CACHE = PROJECT_ROOT / "data" / "cache" / "human_body_assets"

# Đảm bảo thư mục đích tồn tại
NEW_LIBRARY.mkdir(parents=True, exist_ok=True)
QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

try:
    from core.media_engine.asset_content_validator import AssetContentValidator
    validator = AssetContentValidator()
except Exception:
    validator = None

try:
    from prepare_human_body_assets import draw_procedural_golden_scale
except Exception:
    draw_procedural_golden_scale = None

APPROVED_ASSET_NAMES: Set[str] = {
    # Sinh học & Vi sinh vật
    "biology_microscope", "biology_bacterium", "biology_dna",
    "biology_white_blood_cell", "biology_white_blood_cell_cutout",
    
    # Địa lý & Hàng hải
    "geography_anchor", "geography_anglerfish", "geography_compass",
    "geography_pressure_gauge", "geography_submarine",
    
    # Lịch sử & Khảo cổ
    "history_ankh", "history_canopic_jar", "history_papyrus",
    "history_pharaoh", "history_pyramid", "history_sarcophagus",
    
    # Đạo cụ thực tế
    "real_axe", "real_axe_cutout", "real_kitchen_knife", "real_kitchen_knife_cutout",
    "real_baguette", "real_baguette_cutout", "real_wood_log", "real_wood_log_cutout",
    "vintage_camera",
    
    # Thiên văn & Vũ trụ
    "planet", "clock", "compass", "brain", "galaxy", "black_hole",
    
    # Asset chuyên đề cơ thể người
    "human_silhouette", "bryson_book", "elements_59_chart",
    "flask_oxygen", "flask_hydrogen", "carbon_crystal", "money_stack_44k",
    "bill_receipt_3ty", "dna_helix", "glowing_brain", "cosmic_atoms",
    "heart_empathy", "microscope_brass", "cash_register", "petri_chemicals",
    "golden_scale",
}

REJECTED_ASSET_NAMES: Set[str] = {
    "scale",            # Con chim! Không phải cân tiểu ly
    "scale.png",
    "test_art_cutout", "test_art_cutout.png",
    "test_axe_flip_v", "test_axe_flip_v.png",
    "test_axe_rot_180", "test_axe_rot_180.png",
    "test_knife_dl", "test_knife_dl.png",
    "test_knife_flip_v", "test_knife_flip_v.png",
    "temp_raw_real_kitchen_knife", "temp_raw_real_kitchen_knife.png",
}


def is_blacklisted(file_path: Path) -> Tuple[bool, str]:
    """Kiểm tra xem file có thuộc blacklist hay các dạng file rác trung gian không."""
    stem = file_path.stem.lower()
    name = file_path.name.lower()

    if stem in REJECTED_ASSET_NAMES or name in REJECTED_ASSET_NAMES:
        return True, "in REJECTED_ASSET_NAMES blacklist"

    if stem.startswith("test_") or stem.startswith("temp_"):
        return True, "temporary/test prefix junk"

    if "_raw_try" in stem or stem.endswith("_raw"):
        return True, "intermediate raw attempt file"

    return False, ""


def safe_quarantine(src: Path) -> bool:
    """Di chuyển an toàn file vào quarantine, ghi đè nếu đã tồn tại."""
    target = QUARANTINE_DIR / src.name
    try:
        if target.exists():
            target.unlink()
        shutil.move(str(src), str(target))
        logger.info(f"   ↳ Quarantined to: {target.name}")
        return True
    except Exception as e:
        logger.error(f"   ↳ Failed to quarantine {src.name}: {e}")
        return False


def audit_and_migrate() -> Dict[str, List[Path]]:
    """
    Thực hiện kiểm định và di chuyển asset:
    1. Quét data/cache/cutouts/.
    2. Chặn và loại bỏ các file trong blacklist REJECTED_ASSET_NAMES sang quarantine.
    3. Di chuyển/sao chép các file hợp lệ trong APPROVED_ASSET_NAMES sang data/asset_library/global_cutouts/.
    4. Bổ sung golden_scale hợp lệ nếu có trong human_body_assets.
    """
    results: Dict[str, List[Path]] = {
        "approved": [],
        "rejected": [],
        "suspicious": []
    }

    if not OLD_CACHE.exists():
        logger.warning(f"Cache cũ không tồn tại: {OLD_CACHE}")
        return results

    # 1. Quét toàn bộ PNG trong OLD_CACHE
    for f in sorted(OLD_CACHE.glob("*.png")):
        stem = f.stem.lower()

        # Kiểm tra blacklist
        blacklisted, reason = is_blacklisted(f)
        if blacklisted:
            results["rejected"].append(f)
            logger.warning(f"❌ REJECTED & PURGING: {f.name} ({reason})")
            safe_quarantine(f)
            continue

        # Kiểm tra tính toàn vẹn hình ảnh bằng AssetContentValidator hoặc PIL
        if validator is not None:
            v_res = validator.validate_cutout(f)
            if not v_res.is_valid:
                results["rejected"].append(f)
                logger.warning(f"❌ REJECTED (validator failed): {f.name} — {v_res.reason}")
                safe_quarantine(f)
                continue
        else:
            try:
                with Image.open(f) as img:
                    w, h = img.size
                    if w < 50 or h < 50:
                        results["rejected"].append(f)
                        logger.warning(f"❌ REJECTED (too small): {f.name}")
                        safe_quarantine(f)
                        continue
            except Exception as e:
                results["rejected"].append(f)
                logger.warning(f"❌ REJECTED (unreadable): {f.name} ({e})")
                safe_quarantine(f)
                continue

        # Di chuyển vào thư viện trung tâm nếu thuộc whitelist
        if stem in APPROVED_ASSET_NAMES:
            dest = NEW_LIBRARY / f.name
            shutil.copy2(str(f), str(dest))
            results["approved"].append(f)
            logger.success(f"✅ MIGRATED: {f.name} -> {NEW_LIBRARY.name}")
        else:
            results["suspicious"].append(f)
            logger.info(f"⚠️ SUSPICIOUS: {f.name} (not in whitelist)")

    # 2. Bổ sung golden_scale từ human_body_assets, đảm bảo sinh procedural bằng Pillow (R3)
    golden_scale_src = HUMAN_BODY_CACHE / "golden_scale.png"
    if draw_procedural_golden_scale is not None:
        draw_procedural_golden_scale(golden_scale_src)
    if golden_scale_src.exists():
        if validator is None or validator.validate_cutout(golden_scale_src).is_valid:
            dest = NEW_LIBRARY / "golden_scale.png"
            shutil.copy2(str(golden_scale_src), str(dest))
            results["approved"].append(golden_scale_src)
            logger.success(f"✅ MIGRATED: golden_scale.png (procedural) -> {NEW_LIBRARY.name}")

    logger.info(
        f"AUDIT DONE: {len(results['approved'])} approved, "
        f"{len(results['rejected'])} rejected, {len(results['suspicious'])} suspicious"
    )

    return results


if __name__ == "__main__":
    audit_and_migrate()
