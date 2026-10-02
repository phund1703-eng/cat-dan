"""
AutoVideoFactory — Phase 3 (Giai đoạn 1) Verification Script: test_motion_engine.py
Kiểm thử bộ máy diễn hoạt cơ học từng nấc giật (MotionTimelineEngine & Compositor 12fps):
1. Clip 1: Cảnh Dập Nén Vật Lý (Piston Squash)
   - Trục ép kim loại (Hero) dập xuống 3 nấc giật mạnh (DISCRETE_TRANSLATE).
   - Quả cam tươi (Secondary) bị đè nén dẹp bẹp 35% chiều cao (SQUASH_AND_STRETCH).
   - Xuất: data/test_motion/clip_piston_squash.mp4.
2. Clip 2: Cảnh In Ảnh Trượt Liên Tiếp (Photo Strip Sequence)
   - Máy ảnh vintage (Hero) rơi vào vị trí.
   - Giây 1.8+: Tấm ảnh 1 trượt xuống từ đáy máy ảnh (SEQUENTIAL_SPAWN).
   - Giây 2.6+: Tấm ảnh 2 trượt nối tiếp bên dưới tấm ảnh 1.
   - Xuất: data/test_motion/clip_photo_strip.mp4.
3. Trích xuất 4 khung hình chuyển động (1.5s, 2.2s, 2.8s, 3.5s) của mỗi clip để nghiệm thu.
"""

import os
import sys
import subprocess
from pathlib import Path
from loguru import logger
from PIL import Image, ImageDraw, ImageOps, ImageFilter

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.media_engine.motion_timeline_engine import MotionTimelineEngine
from styles.collage_broll.gbro_adapter import GbroAdapter


def create_sample_photo_card(character_path: Path, output_path: Path, caption: str = "ARCHIVE 1954"):
    """Tạo tấm ảnh in Polaroid/vintage photobooth với viền kem cổ điển."""
    card_w, card_h = 360, 440
    card = Image.new("RGBA", (card_w, card_h), (252, 250, 242, 255))
    draw = ImageDraw.Draw(card)
    # Khung viền chỉ đen mỏng
    draw.rectangle([8, 8, card_w - 8, card_h - 8], outline=(220, 215, 200, 255), width=2)

    # Ảnh nhân vật ở trên
    photo_w, photo_h = 320, 340
    if character_path.exists():
        char_img = Image.open(character_path).convert("RGBA")
        # Grayscale halftone style
        char_gray = ImageOps.grayscale(char_img)
        char_tint = ImageOps.colorize(char_gray, black=(20, 25, 35), white=(245, 240, 230))
        char_tint.putalpha(char_img.getchannel("A"))

        # Fit vào ô ảnh
        scale = min(photo_w / char_img.width, photo_h / char_img.height) * 0.95
        rw = int(char_img.width * scale)
        rh = int(char_img.height * scale)
        char_resized = char_tint.resize((rw, rh), Image.Resampling.LANCZOS)

        # Ô ảnh màu xám đậm
        photo_box = Image.new("RGBA", (photo_w, photo_h), (35, 40, 50, 255))
        px = (photo_w - rw) // 2
        py = (photo_h - rh) // 2
        photo_box.paste(char_resized, (px, py), mask=char_resized)
        card.paste(photo_box, (20, 20), mask=photo_box)

    # Dải đục lỗ / vạch kỹ thuật photobooth ở đáy
    draw.rectangle([20, 380, card_w - 20, 384], fill=(180, 175, 160, 255))
    for dot_x in range(40, card_w - 40, 45):
        draw.ellipse([dot_x - 3, 405 - 3, dot_x + 3, 405 + 3], fill=(160, 155, 140, 255))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    card.save(str(output_path), format="PNG")
    return str(output_path)


def run_motion_tests():
    output_dir = PROJECT_ROOT / "data" / "test_motion"
    output_dir.mkdir(parents=True, exist_ok=True)

    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    adapter = GbroAdapter()
    width, height = 1080, 1920
    fps = 12
    duration = 5.0

    logger.info("=" * 70)
    logger.info("🚀 BẮT ĐẦU KIỂM THỬ GIAI ĐOẠN 1: MOTION TIMELINE ENGINE (12FPS)")
    logger.info("=" * 70)

    # =========================================================================
    # TEST 1: CẢNH DẬP NÉN VẬT LÝ (PISTON SQUASH)
    # =========================================================================
    logger.info("\n🎬 --- TEST 1: Cảnh Dập Nén Vật Lý (Piston Squash) ---")

    # Assets
    piston_path = PROJECT_ROOT / "data" / "cache" / "phase2_assets" / "hero_mechanicalm_cutout.png"
    if not piston_path.exists():
        piston_path = PROJECT_ROOT / "assets" / "fallback_library" / "industrial_social" / "press_machine.png"

    orange_path = PROJECT_ROOT / "data" / "cache" / "phase2_assets" / "sec_freshjuicy_cutout.png"
    if not orange_path.exists():
        orange_path = PROJECT_ROOT / "data" / "cache" / "phase2_assets" / "sec_freshcutora_cutout.png"

    scene_layout_1 = {
        "archetype": "industrial_social",
        "color_field": {"name": "Burnt Terracotta", "hex": "#D44D22"},
        "color_hex": "#D44D22",
        "environment_graphic": "ruler_scale",
        "has_pointing_hand": True,
        "hero_element": {
            "name": "mechanical press piston",
            "scale": 0.52,
            "position": [0.5, 0.30],
            "rotation_deg": 0
        },
        "secondary_element": {
            "name": "fresh orange half",
            "scale": 0.35,
            "position": [0.5, 0.68],
            "rotation_deg": 0
        }
    }

    # Timeline cơ học:
    # 1. Trục ép kim loại dập xuống 3 nấc giật mạnh từ Y=0.30 -> Y=0.52 (1.4s -> 2.4s)
    # 2. Quả cam ở dưới chạm phải trục ép bị nén dẹp bẹp xuống 35% chiều cao (2.3s -> 2.8s)
    timeline_1 = [
        {
            "target": "hero",
            "action": "DISCRETE_TRANSLATE",
            "time_range": [1.4, 2.4],
            "start_pos": [0.5, 0.30],
            "end_pos": [0.5, 0.52],
            "steps": 3
        },
        {
            "target": "secondary",
            "action": "SQUASH_AND_STRETCH",
            "time_range": [2.3, 2.8],
            "scale_x": 1.35,
            "scale_y": 0.65,
            "steps": 3
        }
    ]

    out_video_1 = output_dir / "clip_piston_squash.mp4"
    out_frame_1 = output_dir / "frame_piston_squash.png"

    logger.info("⚙️ Render Stop-Motion 12 FPS: clip_piston_squash.mp4...")
    adapter.render_multi_element_scene(
        scene_layout=scene_layout_1,
        hero_asset_path=str(piston_path),
        secondary_asset_path=str(orange_path),
        output_video_path=str(out_video_1),
        output_frame_path=str(out_frame_1),
        duration=duration,
        work_dir=output_dir / "frames_piston",
        width=width,
        height=height,
        fps=fps,
        timeline=timeline_1
    )

    # =========================================================================
    # TEST 2: CẢNH IN ẢNH TRƯỢT LIÊN TIẾP (PHOTO STRIP SEQUENCE)
    # =========================================================================
    logger.info("\n🎬 --- TEST 2: Cảnh In Ảnh Trượt Liên Tiếp (Photo Strip Sequence) ---")

    camera_path = PROJECT_ROOT / "assets" / "collage_assets" / "props" / "vintage_camera.png"
    char1_path = PROJECT_ROOT / "assets" / "collage_assets" / "characters" / "man_suit_chess.png"
    char2_path = PROJECT_ROOT / "assets" / "collage_assets" / "characters" / "woman_gown_chess.png"

    photo1_path = assets_dir / "photo_card_1.png"
    photo2_path = assets_dir / "photo_card_2.png"
    create_sample_photo_card(char1_path, photo1_path, caption="PHOTO #1")
    create_sample_photo_card(char2_path, photo2_path, caption="PHOTO #2")

    scene_layout_2 = {
        "archetype": "archive_documentary",
        "color_field": {"name": "Deep Cobalt", "hex": "#1D3557"},
        "color_hex": "#1D3557",
        "environment_graphic": "coordinate_grid",
        "has_pointing_hand": False,
        "hero_element": {
            "name": "vintage camera",
            "scale": 0.46,
            "position": [0.5, 0.32],
            "rotation_deg": 0
        },
        "secondary_element": {
            "name": "empty_anchor",
            "scale": 0.01,
            "position": [0.5, 0.95],
            "rotation_deg": 0
        }
    }

    action_assets_2 = [
        {
            "id": "action_asset_1",
            "path": str(photo1_path),
            "scale": 0.30,
            "layer_order": "below_hero"
        },
        {
            "id": "action_asset_2",
            "path": str(photo2_path),
            "scale": 0.30,
            "layer_order": "below_hero"
        }
    ]

    # Timeline in ảnh liên tiếp:
    # - Máy ảnh ở vị trí [0.5, 0.32] (đáy máy ảnh nằm ở khoảng Y=0.44 = 845px).
    # - Giây 1.8 -> 2.5: Tấm ảnh 1 trượt từ [0.5, 0.38] xuống distance = 360px (4 nấc giật).
    # - Giây 2.6 -> 3.3: Tấm ảnh 1 tiếp tục trượt xuống thêm 360px để nhường chỗ (từ Y=0.38+360 xuống Y=0.38+720).
    # - Giây 2.6 -> 3.3: Tấm ảnh 2 trượt ra từ đáy máy ảnh distance = 360px, nối tiếp ngay trên tấm ảnh 1!
    timeline_2 = [
        {
            "target": "action_asset_1",
            "action": "SEQUENTIAL_SPAWN",
            "spawn_time": 1.8,
            "slide_direction": [0.0, 1.0],
            "distance": 360,
            "duration": 0.7,
            "steps": 4,
            "base_pos": [0.5, 0.38]
        },
        {
            "target": "action_asset_1",
            "action": "DISCRETE_TRANSLATE",
            "time_range": [2.6, 3.3],
            "start_pos": [540, int(1920 * 0.38) + 360],
            "end_pos": [540, int(1920 * 0.38) + 720],
            "steps": 4
        },
        {
            "target": "action_asset_2",
            "action": "SEQUENTIAL_SPAWN",
            "spawn_time": 2.6,
            "slide_direction": [0.0, 1.0],
            "distance": 360,
            "duration": 0.7,
            "steps": 4,
            "base_pos": [0.5, 0.38]
        }
    ]

    out_video_2 = output_dir / "clip_photo_strip.mp4"
    out_frame_2 = output_dir / "frame_photo_strip.png"

    logger.info("⚙️ Render Stop-Motion 12 FPS: clip_photo_strip.mp4...")
    adapter.render_multi_element_scene(
        scene_layout=scene_layout_2,
        hero_asset_path=str(camera_path),
        secondary_asset_path=str(photo1_path),  # Dummy placeholder
        output_video_path=str(out_video_2),
        output_frame_path=str(out_frame_2),
        duration=duration,
        work_dir=output_dir / "frames_photo",
        width=width,
        height=height,
        fps=fps,
        timeline=timeline_2,
        action_assets=action_assets_2
    )

    # =========================================================================
    # TRÍCH XUẤT 4 KHUNG HÌNH CHUYỂN ĐỘNG LIÊN TIẾP (1.5s, 2.2s, 2.8s, 3.5s)
    # =========================================================================
    logger.info("\n📸 Trích xuất 4 khung hình tiến trình cử động vật lý (1.5s, 2.2s, 2.8s, 3.5s)...")
    sample_timestamps = [1.5, 2.2, 2.8, 3.5]
    extracted_records = {"piston": [], "photo": []}

    for clip_name, vid_p, key in [("Piston Squash", out_video_1, "piston"),
                                   ("Photo Strip", out_video_2, "photo")]:
        for ts in sample_timestamps:
            frame_name = f"{key}_t_{int(ts*10):02d}.jpg"
            frame_out = output_dir / frame_name
            extract_cmd = [
                "ffmpeg", "-y",
                "-ss", f"{ts:.2f}",
                "-i", str(vid_p),
                "-vframes", "1",
                "-q:v", "2",
                str(frame_out)
            ]
            subprocess.run(extract_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            extracted_records[key].append(str(frame_out))
            logger.info(f"   🖼️ [{clip_name}] Trích xuất t={ts:.1f}s -> {frame_name}")

    logger.info("\n" + "=" * 70)
    logger.info("🎉 HOÀN THÀNH KIỂM THỬ GIAI ĐOẠN 1!")
    logger.info("=" * 70)
    logger.info(f"1. Clip Piston Squash: {out_video_1} ({os.path.getsize(out_video_1)/1024:.1f} KB)")
    logger.info(f"2. Clip Photo Strip:   {out_video_2} ({os.path.getsize(out_video_2)/1024:.1f} KB)")


if __name__ == "__main__":
    run_motion_tests()
