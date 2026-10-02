"""
AutoVideoFactory — Production Script: produce_human_body_video.py
Sản xuất trọn vẹn Video hoàn chỉnh từ kịch bản:
"Giá trị nguyên liệu thô cấu tạo nên cơ thể người" (8 phân cảnh điện ảnh 7 tầng).
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from loguru import logger
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.script_engine.ai_visual_director import AIVisualDirector
from core.media_engine.kinetic_layout_bridge import KineticLayoutBridge
from styles.collage_broll.gbro_adapter import GbroAdapter
from core.tts_engine.tts_manager import TTSManager
from core.render_engine.ffmpeg_utils import get_video_info

OUTPUT_DIR = PROJECT_ROOT / "output" / "human_body_cost"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR = PROJECT_ROOT / "data" / "cache" / "human_body_assets"

SCENES = [
    {
        "id": 1,
        "title": "Scene 1: Sẽ tốn bao nhiêu tiền để mua nguyên liệu làm nên bạn?",
        "sentence": "Bạn đã bao giờ tự hỏi: Sẽ tốn bao nhiêu tiền để mua toàn bộ nguyên liệu thô cấu tạo nên một cơ thể người?",
        "hero_asset": "human_silhouette.png",
        "secondary_asset": "golden_scale.png",
        "engine": "ENGINE_REVOLVE_VORTEX",
        "archetype": "conceptual_duel",
        "color_field": "Plum & Gold",
        "color_hex": "4A235A",
        "environment_graphic": "coordinate_grid",
        "custom_params": {
            "hero_scale": 0.48,
            "sec_scale": 0.36,
            "radius": 360.0,
            "has_pointing_hand": True
        }
    },
    {
        "id": 2,
        "title": "Scene 2: Sách Bill Bryson & 59 nguyên tố",
        "sentence": "Theo cuốn sách \"Cơ thể người\" của Bill Bryson và dữ liệu từ Hiệp hội Hóa học Hoàng gia Anh, cần chính xác 59 nguyên tố để lắp ráp ra bạn.",
        "hero_asset": "bryson_book.png",
        "secondary_asset": "elements_59_chart.png",
        "engine": "ENGINE_EMIT_SLIDE",
        "archetype": "historical_relic",
        "color_field": "Warm Ochre",
        "color_hex": "B7950B",
        "environment_graphic": "papyrus_frame",
        "custom_params": {
            "hero_scale": 0.46,
            "sec_scale": 0.40,
            "distance": 480.0,
            "has_pointing_hand": True
        }
    },
    {
        "id": 3,
        "title": "Scene 3: Oxy 61% và Hydro 10% - Quá rẻ",
        "sentence": "Bạn tưởng sẽ đắt đỏ lắm sao? Thực ra 61% cơ thể bạn chỉ là Oxy – trị giá vỏn vẹn 9 Bảng Anh. Thêm 10% là Hydro, tốn thêm 16 Bảng nữa. Quá rẻ đúng không!",
        "hero_asset": "flask_oxygen.png",
        "secondary_asset": "flask_hydrogen.png",
        "engine": "ENGINE_SWEEP_OSCILLATE",
        "archetype": "specimen_scientific",
        "color_field": "Teal & Coral",
        "color_hex": "2A9D8F",
        "environment_graphic": "microscope_reticle",
        "custom_params": {
            "hero_scale": 0.42,
            "sec_scale": 0.38,
            "sweep_angle": 35.0,
            "has_pointing_hand": True
        }
    },
    {
        "id": 4,
        "title": "Scene 4: Carbon tinh khiết 13,6 kg - 44.300 Bảng Anh",
        "sentence": "Nhưng đây mới là thứ ngốn tiền nhất: Bạn cần 13,6 kg Carbon tinh khiết. Và khoản này sẽ tiêu tốn của bạn một con số khổng lồ: 44.300 Bảng Anh!",
        "hero_asset": "carbon_crystal.png",
        "secondary_asset": "money_stack_44k.png",
        "engine": "ENGINE_COMPRESS_SQUASH",
        "archetype": "industrial_social",
        "color_field": "Burnt Terracotta",
        "color_hex": "D44D22",
        "environment_graphic": "ruler_scale",
        "custom_params": {
            "hero_scale": 0.46,
            "sec_scale": 0.42,
            "scale_y": 0.35,
            "scale_x": 1.65,
            "has_pointing_hand": True
        }
    },
    {
        "id": 5,
        "title": "Scene 5: Tổng hóa đơn 96.546 Bảng Anh ~ 3 tỷ đồng",
        "sentence": "Cộng thêm các nguyên tố vi lượng khác, tổng hóa đơn để mua toàn bộ nguyên liệu làm ra bạn là chính xác 96.546 Bảng Anh 79 xu — tức là khoảng 3 tỷ đồng.",
        "hero_asset": "cash_register.png",
        "secondary_asset": "bill_receipt_3ty.png",
        "engine": "ENGINE_EMIT_SLIDE",
        "archetype": "conceptual_duel",
        "color_field": "Plum & Gold",
        "color_hex": "4A235A",
        "environment_graphic": "coordinate_grid",
        "custom_params": {
            "hero_scale": 0.45,
            "sec_scale": 0.42,
            "distance": 520.0,
            "has_pointing_hand": True
        }
    },
    {
        "id": 6,
        "title": "Scene 6: Các nhà khoa học bất lực",
        "sentence": "Nhưng đây mới là sự thật chấn động: Ngay cả khi bạn mua đủ số hóa chất đó, và gọi những nhà khoa học thiên tài nhất lịch sử đến phòng thí nghiệm... họ vẫn bất lực. Họ không thể lắp ráp đống hóa chất vô tri ấy thành dù chỉ một tế bào sống.",
        "hero_asset": "microscope_brass.png",
        "secondary_asset": "petri_chemicals.png",
        "engine": "ENGINE_SWEEP_OSCILLATE",
        "archetype": "specimen_scientific",
        "color_field": "Deep Cobalt",
        "color_hex": "1D3557",
        "environment_graphic": "microscope_reticle",
        "custom_params": {
            "hero_scale": 0.46,
            "sec_scale": 0.38,
            "sweep_angle": 42.0,
            "has_pointing_hand": True
        }
    },
    {
        "id": 7,
        "title": "Scene 7: Phép màu vũ trụ - Nguyên tử tự liên kết",
        "sentence": "Phép màu vĩ đại nhất của vũ trụ là: Bằng một cách nào đó, những nguyên tử chết hoàn toàn vô tri vô giác lại biết cách tự liên kết lại để trở thành chính bạn.",
        "hero_asset": "cosmic_atoms.png",
        "secondary_asset": "dna_helix.png",
        "engine": "ENGINE_CONVERGE_WRAP",
        "archetype": "specimen_scientific",
        "color_field": "Forest Sage",
        "color_hex": "2D6A4F",
        "environment_graphic": "depth_contours",
        "custom_params": {
            "hero_scale": 0.46,
            "sec_scale": 0.40,
            "has_pointing_hand": True
        }
    },
    {
        "id": 8,
        "title": "Scene 8: Một thực thể biết suy nghĩ và yêu thương",
        "sentence": "Một thực thể biết suy nghĩ, biết yêu thương và biết tò mò... Và chính điều kỳ diệu đó khiến bạn không thể không thắc mắc...",
        "hero_asset": "glowing_brain.png",
        "secondary_asset": "heart_empathy.png",
        "engine": "ENGINE_REVOLVE_VORTEX",
        "archetype": "conceptual_duel",
        "color_field": "Plum & Gold",
        "color_hex": "4A235A",
        "environment_graphic": "coordinate_grid",
        "custom_params": {
            "hero_scale": 0.48,
            "sec_scale": 0.38,
            "radius": 380.0,
            "has_pointing_hand": True
        }
    }
]


async def produce_human_body_video():
    logger.info("🎬 [PRODUCTION] Bắt đầu sản xuất trọn vẹn 8 cảnh kịch bản: 'Cơ Thể Người'")
    
    tts = TTSManager()
    director = AIVisualDirector()
    bridge = KineticLayoutBridge()
    adapter = GbroAdapter()
    
    scene_video_paths = []
    
    for sc in SCENES:
        sc_id = sc["id"]
        sentence = sc["sentence"]
        logger.info(f"\n=======================================================")
        logger.info(f"▶️ Đang sản xuất {sc['title']} (Scene {sc_id}/8)...")
        
        sc_dir = OUTPUT_DIR / f"scene_{sc_id}"
        sc_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. EdgeTTS Audio
        audio_path = sc_dir / "voice.mp3"
        try:
            await tts.synthesize(text=sentence, language="vi", output_path=str(audio_path))
            probe_info = get_video_info(str(audio_path))
            actual_duration = float(probe_info.get("duration", 4.0))
        except Exception as e:
            logger.warning(f"TTS fallback ({e})")
            actual_duration = 4.0
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                "-t", str(actual_duration), str(audio_path)
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        video_duration = max(3.5, actual_duration + 0.4)
        logger.info(f"⏱️ Audio: {actual_duration:.2f}s | Video Duration: {video_duration:.2f}s")
        
        # 2. Assets
        hero_p = str(ASSETS_DIR / sc["hero_asset"])
        sec_p = str(ASSETS_DIR / sc["secondary_asset"])
        
        # 3. Director Blueprint & Layout
        blueprint = await director.direct_scene(sentence)
        custom_params = dict(sc.get("custom_params", {}))
        custom_params["color_field"] = sc.get("color_field", "Plum & Gold")
        custom_params["color_hex"] = sc.get("color_hex", "4A235A")
        custom_params["environment_graphic"] = sc.get("environment_graphic", "coordinate_grid")
        
        scene_layout = bridge.build_scene_layout(
            engine_name=sc["engine"],
            hero_asset_path=hero_p,
            secondary_asset_path=sec_p,
            custom_params=custom_params,
            director_blueprint=blueprint
        )
        scene_layout["has_pointing_hand"] = True
        
        # 4. Render 7-layer stop-motion (12fps, 1080x1920)
        temp_visual = sc_dir / "visual_no_audio.mp4"
        adapter.render_multi_element_scene(
            scene_layout=scene_layout,
            hero_asset_path=hero_p,
            secondary_asset_path=sec_p,
            output_video_path=str(temp_visual),
            duration=video_duration,
            work_dir=sc_dir / "frames",
            width=1080,
            height=1920,
            fps=12
        )
        
        # 5. ASS Subtitle (TikTok Yellow)
        sub_ass = sc_dir / "subtitles.ass"
        ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TikTokYellow,Arial,60,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,3,2,60,60,320,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.15,0:00:{actual_duration:05.2f},TikTokYellow,,0,0,0,,{sentence.upper()}
"""
        with open(sub_ass, "w", encoding="utf-8") as f:
            f.write(ass_content)
            
        # 6. Mux Scene Video
        scene_final_mp4 = sc_dir / f"scene_{sc_id}.mp4"
        ass_filter_path = str(sub_ass).replace("\\", "/").replace(":", "\\:")
        mux_cmd = [
            "ffmpeg", "-y",
            "-i", str(temp_visual),
            "-i", str(audio_path),
            "-filter_complex", f"[0:v]subtitles='{ass_filter_path}'[v]",
            "-map", "[v]",
            "-map", "1:a",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(scene_final_mp4)
        ]
        res = subprocess.run(mux_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if res.returncode != 0:
            # fallback copy
            fallback_cmd = [
                "ffmpeg", "-y",
                "-i", str(temp_visual),
                "-i", str(audio_path),
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                str(scene_final_mp4)
            ]
            subprocess.run(fallback_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            
        # 7. Snapshot for inspection
        snap_jpg = sc_dir / f"snapshot_scene_{sc_id}.jpg"
        mid_time = f"{video_duration / 2.0:.2f}"
        subprocess.run([
            "ffmpeg", "-y",
            "-ss", mid_time,
            "-i", str(scene_final_mp4),
            "-vframes", "1",
            "-q:v", "2",
            str(snap_jpg)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        logger.success(f"✅ Hoàn thành Scene {sc_id}: {scene_final_mp4.name} ({scene_final_mp4.stat().st_size / 1024:.1f} KB)")
        scene_video_paths.append(scene_final_mp4)

    # ----------------------------------------------------
    # Concatenate all 8 scenes into final master video
    # ----------------------------------------------------
    logger.info("\n🎞️ [CONCATENATION] Đang ghép nối toàn bộ 8 phân cảnh thành Master Video...")
    concat_list_txt = OUTPUT_DIR / "concat_list.txt"
    with open(concat_list_txt, "w", encoding="utf-8") as f:
        for p in scene_video_paths:
            # ffmpeg concat format
            safe_p = str(p.resolve()).replace("\\", "/")
            f.write(f"file '{safe_p}'\n")
            
    master_video = PROJECT_ROOT / "output" / "video_human_body_cost_complete.mp4"
    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_txt),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        str(master_video)
    ]
    subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
    
    probe_master = get_video_info(str(master_video))
    master_dur = float(probe_master.get("duration", 0.0))
    master_size_mb = master_video.stat().st_size / (1024 * 1024)
    logger.success(f"\n🎉🎉🎉 [MASTER VIDEO HOÀN TẤT] 🎉🎉🎉")
    logger.success(f"📍 Đường dẫn: {master_video}")
    logger.success(f"⏱️ Thời lượng: {master_dur:.2f}s | Dung lượng: {master_size_mb:.2f} MB")
    
    # Snapshot master
    master_snap = PROJECT_ROOT / "output" / "snapshot_human_body_master.jpg"
    subprocess.run([
        "ffmpeg", "-y",
        "-ss", "12.0",
        "-i", str(master_video),
        "-vframes", "1",
        "-q:v", "2",
        str(master_snap)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print(f"DONE_MASTER:{master_video}:{master_dur}:{master_size_mb:.2f}")


if __name__ == "__main__":
    asyncio.run(produce_human_body_video())
