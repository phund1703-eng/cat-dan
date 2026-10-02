"""
AutoVideoFactory — Test The 8 Universal Kinetic Engines: test_all_8_engines.py
Kiểm thử tự động trọn vẹn 8 Động Cơ Chuyển Động Vật Lý Hoàn Chỉnh (1080x1920, 12fps, stop-motion):
1. ENGINE_COMPRESS_SQUASH : Máy dập ép bẹp quả cam (Piston & Orange)
2. ENGINE_SEVER_SHATTER   : Dao bếp chém đứt đôi bánh mì baguette (Trường hợp A)
2b.ENGINE_SEVER_SHATTER_B : Lưỡi rìu bổ đôi khúc gỗ rừng già (Trường hợp B)
3. ENGINE_EMIT_SLIDE      : Máy ảnh xổ liên tiếp dải photobooth (Vintage Camera & Polaroid Portraits)
4. ENGINE_CONVERGE_WRAP   : Dải băng quấn bay vào hội tụ bao bọc xác ướp (Pharaoh & Real Linen Papyrus)
5. ENGINE_ABSORB_DISSOLVE : Bạch cầu nuốt chửng vi khuẩn thu nhỏ tiêu biến (Real WBC & Bacterium)
6. ENGINE_TRANSLATE_NAV   : Tàu ngầm lặn sâu nghiêng lướt sóng hải lưu (Submarine & Gauge)
7. ENGINE_SWEEP_OSCILLATE : Kính hiển vi dao động quét qua quét lại soi mẫu (Real Microscope & Petri Dish)
8. ENGINE_REVOLVE_VORTEX  : Hành tinh quay quanh quỹ đạo tâm elip (Planet & Orbiter)
"""

import os
import sys
import subprocess
from pathlib import Path
from loguru import logger
from PIL import Image, ImageDraw, ImageOps

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.media_engine.kinetic_layout_bridge import KineticLayoutBridge
from styles.collage_broll.gbro_adapter import GbroAdapter

OUT_DIR = PROJECT_ROOT / "data" / "test_8_engines"
OUT_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR = OUT_DIR / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def create_linen_strip_from_papyrus(papyrus_path: Path, output_path: Path, crop_box=(30, 160, 480, 260), angle_tilt: int = -10):
    """Tạo dải băng quấn ướp xác từ ảnh texture vải papyrus thật."""
    if not papyrus_path.exists():
        # Fallback tạo nền giấy cổ nếu file không tồn tại
        img = Image.new("RGBA", (380, 90), (235, 220, 195, 255))
    else:
        with Image.open(papyrus_path) as pap:
            pap_rgba = pap.convert("RGBA")
            img = pap_rgba.crop(crop_box)

    if angle_tilt != 0:
        img = img.rotate(angle_tilt, expand=True, resample=Image.Resampling.BICUBIC)
    img.save(str(output_path), format="PNG")
    return str(output_path)


def create_polaroid_card(character_path: Path, output_path: Path, caption: str = ""):
    """Tạo tấm ảnh Polaroid / photobooth chuẩn phong cách collage với nhân vật thật."""
    card_w, card_h = 360, 440
    card = Image.new("RGBA", (card_w, card_h), (252, 250, 244, 255))
    draw = ImageDraw.Draw(card)
    # Khung viền ảnh thẻ giấy cổ
    draw.rectangle([6, 6, card_w - 6, card_h - 6], outline=(215, 210, 195, 255), width=2)

    box_w, box_h = 310, 310
    box_x, box_y = 25, 25
    draw.rectangle([box_x, box_y, box_x + box_w, box_y + box_h], fill=(32, 38, 48, 255))

    if character_path.exists():
        char = Image.open(character_path).convert("RGBA")
        scale = min(box_w / char.width, box_h / char.height) * 0.92
        rw, rh = int(char.width * scale), int(char.height * scale)
        r_char = char.resize((rw, rh), Image.Resampling.LANCZOS)
        # Căn chỉnh nhân vật ở đáy khung ảnh
        char_x = box_x + (box_w - rw) // 2
        char_y = box_y + (box_h - rh)
        card.paste(r_char, (char_x, char_y), mask=r_char)

    # Vạch ghi chú vintage ở đáy ảnh
    draw.rectangle([35, 365, card_w - 35, 370], fill=(200, 195, 180, 255))
    draw.rectangle([65, 385, card_w - 65, 389], fill=(220, 215, 205, 255))

    card.save(str(output_path), format="PNG")
    return str(output_path)


def run_all_8_engines():
    adapter = GbroAdapter()
    width, height = 1080, 1920
    fps = 12
    duration = 3.5

    # 1. Định vị các Real Cutouts chuẩn xác
    piston_path = PROJECT_ROOT / "data" / "cache" / "phase2_assets" / "hero_mechanicalm_cutout.png"
    orange_path = PROJECT_ROOT / "data" / "cache" / "phase2_assets" / "sec_freshjuicy_cutout.png"
    knife_path = PROJECT_ROOT / "data" / "cache" / "cutouts" / "real_kitchen_knife.png"
    baguette_path = PROJECT_ROOT / "data" / "cache" / "cutouts" / "real_baguette.png"
    axe_path = PROJECT_ROOT / "data" / "cache" / "cutouts" / "real_axe.png"
    woodlog_path = PROJECT_ROOT / "data" / "cache" / "cutouts" / "real_wood_log.png"
    camera_path = PROJECT_ROOT / "data" / "cache" / "cutouts" / "vintage_camera.png"
    pharaoh_path = PROJECT_ROOT / "data" / "cache" / "cutouts" / "history_pharaoh.png"
    wbc_path = PROJECT_ROOT / "data" / "cache" / "cutouts" / "biology_white_blood_cell.png"
    bacteria_path = PROJECT_ROOT / "data" / "cache" / "cutouts" / "biology_bacterium.png"
    submarine_path = PROJECT_ROOT / "data" / "cache" / "cutouts" / "geography_submarine.png"
    microscope_path = PROJECT_ROOT / "data" / "cache" / "cutouts" / "biology_microscope.png"
    petri_path = PROJECT_ROOT / "data" / "cache" / "phase2_assets" / "sec_glasspetri_cutout.png"
    planet_path = PROJECT_ROOT / "data" / "cache" / "cutouts" / "planet.png"
    clock_path = PROJECT_ROOT / "data" / "cache" / "cutouts" / "clock.png"

    # Assets phụ kiện thật (Polaroid cards với nhân vật & Vải Papyrus thật)
    char1_path = PROJECT_ROOT / "assets" / "collage_assets" / "characters" / "man_suit_chess.png"
    char2_path = PROJECT_ROOT / "assets" / "collage_assets" / "characters" / "woman_gown_chess.png"
    photo1_path = Path(create_polaroid_card(char1_path, ASSETS_DIR / "polaroid_man.png"))
    photo2_path = Path(create_polaroid_card(char2_path, ASSETS_DIR / "polaroid_woman.png"))

    papyrus_texture = PROJECT_ROOT / "assets" / "fallback_library" / "historical_relic" / "papyrus.png"
    linen1_path = Path(create_linen_strip_from_papyrus(papyrus_texture, ASSETS_DIR / "linen_strip_1.png", crop_box=(20, 150, 490, 250), angle_tilt=-12))
    linen2_path = Path(create_linen_strip_from_papyrus(papyrus_texture, ASSETS_DIR / "linen_strip_2.png", crop_box=(20, 260, 490, 360), angle_tilt=14))

    # 2. Xây dựng Scene Layouts 100% tự động qua KineticLayoutBridge
    ENGINES_CONFIG = [
        {
            "id": 1,
            "filename": "clip_01_compress_squash.mp4",
            "name": "ENGINE_COMPRESS_SQUASH",
            "desc": "Máy dập ép bẹp dẹp quả cam (Scale Y=0.32, X=1.70, Screen Shake +-8px)",
            "hero_path": str(piston_path),
            "sec_path": str(orange_path),
            "layout": KineticLayoutBridge.build_scene_layout(
                engine_name="ENGINE_COMPRESS_SQUASH",
                hero_asset_path=str(piston_path),
                secondary_asset_path=str(orange_path),
                custom_params={"hero_scale": 0.52, "sec_scale": 0.35, "scale_x": 1.70, "scale_y": 0.32}
            )
        },
        {
            "id": 2,
            "filename": "clip_02_sever_shatter.mp4",
            "name": "ENGINE_SEVER_SHATTER",
            "desc": "Trường hợp A: Dao bếp thật chém đứt đôi bánh mì baguette (Drift 260px, Tilt 30°)",
            "hero_path": str(knife_path),
            "sec_path": str(baguette_path),
            "layout": KineticLayoutBridge.build_scene_layout(
                engine_name="ENGINE_SEVER_SHATTER",
                hero_asset_path=str(knife_path),
                secondary_asset_path=str(baguette_path),
                custom_params={
                    "hero_scale": 0.45,
                    "sec_scale": 0.40,
                    "split_axis": "vertical",
                    "windup_tilt_deg": -35.0,
                    "strike_tilt_deg": 6.0,
                    "tilt_deg": 30.0,
                    "drift_direction": [1.0, 0.2],
                    "max_drift_px": 260.0
                }
            )
        },
        {
            "id": "2b",
            "filename": "clip_02b_sever_axe_woodlog.mp4",
            "name": "ENGINE_SEVER_SHATTER_CASE_B",
            "desc": "Trường hợp B: Chiếc rìu thật bổ đôi khúc gỗ rừng già (Drift 260px, Tilt 30°)",
            "hero_path": str(axe_path),
            "sec_path": str(woodlog_path),
            "layout": KineticLayoutBridge.build_scene_layout(
                engine_name="ENGINE_SEVER_SHATTER",
                hero_asset_path=str(axe_path),
                secondary_asset_path=str(woodlog_path),
                custom_params={
                    "hero_scale": 0.48,
                    "sec_scale": 0.38,
                    "split_axis": "vertical",
                    "windup_tilt_deg": -35.0,
                    "strike_tilt_deg": 6.0,
                    "tilt_deg": 30.0,
                    "drift_direction": [1.0, 0.2],
                    "max_drift_px": 260.0
                }
            )
        },
        {
            "id": 3,
            "filename": "clip_03_emit_slide.mp4",
            "name": "ENGINE_EMIT_SLIDE",
            "desc": "Máy ảnh xổ dải photobooth trượt xa 550px lượn chao đảo",
            "hero_path": str(camera_path),
            "sec_path": str(photo1_path),
            "layout": KineticLayoutBridge.build_scene_layout(
                engine_name="ENGINE_EMIT_SLIDE",
                hero_asset_path=str(camera_path),
                action_assets_paths=[str(photo1_path), str(photo2_path)],
                custom_params={"hero_scale": 0.48, "emit_asset_scale": 0.28, "hero_y": 0.36, "distance": 550.0}
            )
        },
        {
            "id": 4,
            "filename": "clip_04_converge_wrap.mp4",
            "name": "ENGINE_CONVERGE_WRAP",
            "desc": "Dải băng vải papyrus thật từ ngoài biên 750px+ bay vào hội tụ bao bọc xác ướp",
            "hero_path": str(pharaoh_path),
            "sec_path": str(linen1_path),
            "layout": KineticLayoutBridge.build_scene_layout(
                engine_name="ENGINE_CONVERGE_WRAP",
                hero_asset_path=str(pharaoh_path),
                action_assets_paths=[str(linen1_path), str(linen2_path)],
                custom_params={"hero_scale": 0.52, "wrap_strip_scale": 0.35, "hero_y": 0.50}
            )
        },
        {
            "id": 5,
            "filename": "clip_05_absorb_dissolve.mp4",
            "name": "ENGINE_ABSORB_DISSOLVE",
            "desc": "Bạch cầu thật nuốt chửng vi khuẩn từ đáy sâu y=0.85 & phình to 1.30x",
            "hero_path": str(wbc_path),
            "sec_path": str(bacteria_path),
            "layout": KineticLayoutBridge.build_scene_layout(
                engine_name="ENGINE_ABSORB_DISSOLVE",
                hero_asset_path=str(wbc_path),
                secondary_asset_path=str(bacteria_path),
                custom_params={"hero_scale": 0.52, "sec_scale": 0.32}
            )
        },
        {
            "id": 6,
            "filename": "clip_06_translate_nav.mp4",
            "name": "ENGINE_TRANSLATE_NAV",
            "desc": "Tàu ngầm lặn sâu lướt chéo toàn màn hình [0.12, 0.22] -> [0.88, 0.78]",
            "hero_path": str(submarine_path),
            "sec_path": str(clock_path),
            "layout": KineticLayoutBridge.build_scene_layout(
                engine_name="ENGINE_TRANSLATE_NAV",
                hero_asset_path=str(submarine_path),
                secondary_asset_path=str(clock_path),
                custom_params={"hero_scale": 0.48, "sec_scale": 0.28, "start_pos": [0.12, 0.22], "end_pos": [0.88, 0.78], "max_tilt_deg": 22.0, "wave_amplitude": 45.0}
            )
        },
        {
            "id": 7,
            "filename": "clip_07_sweep_oscillate.mp4",
            "name": "ENGINE_SWEEP_OSCILLATE",
            "desc": "Kính hiển vi quang học thật dao động quét rộng +-45° soi mẫu",
            "hero_path": str(microscope_path),
            "sec_path": str(petri_path),
            "layout": KineticLayoutBridge.build_scene_layout(
                engine_name="ENGINE_SWEEP_OSCILLATE",
                hero_asset_path=str(microscope_path),
                secondary_asset_path=str(petri_path),
                custom_params={"hero_scale": 0.52, "sec_scale": 0.34, "sweep_angle": 45.0, "cycles": 2}
            )
        },
        {
            "id": 8,
            "filename": "clip_08_revolve_vortex.mp4",
            "name": "ENGINE_REVOLVE_VORTEX",
            "desc": "Vật thể quay quanh tâm elip quỹ đạo R=420px (2.5D: 0.60x sau lưng / 1.40x trước mặt)",
            "hero_path": str(planet_path),
            "sec_path": str(clock_path),
            "layout": KineticLayoutBridge.build_scene_layout(
                engine_name="ENGINE_REVOLVE_VORTEX",
                hero_asset_path=str(planet_path),
                secondary_asset_path=str(clock_path),
                custom_params={"hero_scale": 0.45, "sec_scale": 0.25, "radius": 420.0, "time_range": [1.0, 3.4]}
            )
        }
    ]

    results = []
    print("=" * 110)
    print("🚀 [TEST 8 ENGINES] SẢN XUẤT 9 CLIPS VỚI UNIVERSAL KINETIC LAYOUT BRIDGE & AUTHENTIC ASSETS (12FPS)")
    print("=" * 110)

    for cfg in ENGINES_CONFIG:
        c_id = cfg["id"]
        c_name = cfg["name"]
        c_desc = cfg["desc"]
        out_vid = OUT_DIR / cfg["filename"]
        id_str = f"{c_id:02d}" if isinstance(c_id, int) else str(c_id)
        out_snap = OUT_DIR / f"snapshot_{id_str}_{c_name.lower()}.jpg"

        logger.info(f"\n🎬 [{id_str}] Render Clip: {c_name} — '{c_desc}'")

        adapter.render_multi_element_scene(
            scene_layout=cfg["layout"],
            hero_asset_path=cfg["hero_path"],
            secondary_asset_path=cfg["sec_path"],
            output_video_path=str(out_vid),
            duration=duration,
            work_dir=OUT_DIR / f"temp_frames_{c_id}",
            width=width,
            height=height,
            fps=fps
        )

        assert out_vid.exists() and out_vid.stat().st_size > 1000, f"❌ Không thể tạo video: {out_vid}"

        # Trích xuất snapshot tại 2.4s (thời điểm hành động rõ nhất)
        extract_cmd = [
            "ffmpeg", "-y",
            "-ss", "2.4",
            "-i", str(out_vid),
            "-vframes", "1",
            "-q:v", "2",
            str(out_snap)
        ]
        subprocess.run(extract_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)

        vid_kb = out_vid.stat().st_size / 1024
        print(f"✅ [{c_id}] {c_name:<30} | File: {cfg['filename']:<32} | {vid_kb:.1f} KB | Snapshot: {out_snap.name}")
        results.append({
            "id": c_id,
            "name": c_name,
            "desc": c_desc,
            "video_path": str(out_vid),
            "snapshot_path": str(out_snap)
        })

    print("=" * 110)
    print(f"🎉 TỔNG KẾT: ĐÃ HOÀN THÀNH XUẤT SẮC 9/9 CLIPS KIỂM THỬ KINETIC ENGINES VỚI BRIDGE & REAL ASSETS!")
    print("=" * 110)
    return results


if __name__ == "__main__":
    run_all_8_engines()
