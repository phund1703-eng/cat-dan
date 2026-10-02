"""
AutoVideoFactory — Phase 3 Production Pipeline (V4)
Triển khai sản xuất 3 video thành phẩm hoàn chỉnh theo tiêu chuẩn Collage B-Roll V4:
1. Sinh học: output/video_biology_v4.mp4
2. Địa lý / Biển sâu: output/video_geography_v4.mp4
3. Lịch sử / Khảo cổ: output/video_history_v4.mp4

Quy trình tự động tích hợp:
- Script tiếng Việt chuẩn ngữ nghĩa & cú pháp hành động.
- Voice EdgeTTS tiếng Việt tự nhiên, chuẩn nhịp.
- MultiElementSceneDesigner phân tích cú pháp câu -> layout đa vật thể.
- MultiAssetGenerator sinh song song Hero & Secondary cutouts trên nền trắng, bóc tách rembg, AlphaQAGate QA.
- GbroAdapter lắp ráp stop-motion 12fps với viền kem 3px, đổ bóng vật lý 45°, cự ly gần và va chạm đè ép.
- SubtitleGenerator sinh phụ đề TikTok ASS chữ vàng/trắng viền đen dày, đồng bộ từng cụm từ.
- Trích xuất 9 khung hình nghiệm thu vào output/v4_frames/.
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path
from loguru import logger
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.script_engine.text_visual_analyzer import MultiElementSceneDesigner
from core.media_engine.multi_asset_generator import MultiAssetGenerator
from core.tts_engine.tts_manager import TTSManager
from core.render_engine.ffmpeg_utils import get_video_info, concat_videos
from core.render_engine.subtitle_generator import SubtitleGenerator
from styles.collage_broll.gbro_adapter import GbroAdapter


TARGET_VIDEOS_V4 = [
    {
        "id": "biology",
        "video_filename": "video_biology_v4.mp4",
        "title": "Cơ Chế Bạch Cầu Tiêu Diệt Vi Khuẩn",
        "topic": "Cơ chế bạch cầu săn tìm và tiêu diệt vi khuẩn trong cơ thể",
        "archetype": "specimen_scientific",
        "scenes": [
            {
                "narration": "Khi vi khuẩn xâm nhập vào mô tế bào, cơ thể lập tức phát tín hiệu báo động khẩn cấp.",
                "has_hand": False,
                "layout_hint": {
                    "archetype": "specimen_scientific",
                    "color_field": {"name": "Deep Cobalt", "hex": "#1D3557"},
                    "interaction_type": "EXAMINING",
                    "environment_graphic": "microscope_reticle",
                    "hero_element": {
                        "name": "vintage brass microscope",
                        "prompt": "a vintage brass laboratory microscope",
                        "scale": 0.50
                    },
                    "secondary_element": {
                        "name": "glass petri dish with red bacteria culture colonies",
                        "prompt": "a glass petri dish with red bacteria culture colonies",
                        "scale": 0.35
                    },
                    "has_pointing_hand": False
                }
            },
            {
                "narration": "Các tế bào bạch cầu đại thực bào cơ động di chuyển thần tốc để bao vây toàn bộ ổ vi khuẩn.",
                "has_hand": True,
                "layout_hint": {
                    "archetype": "specimen_scientific",
                    "color_field": {"name": "Sage Green", "hex": "#588157"},
                    "interaction_type": "ENGULFING",
                    "environment_graphic": "depth_contours",
                    "hero_element": {
                        "name": "giant glowing white blood cell warrior",
                        "prompt": "a scientific glowing white blood cell macrophage warrior cell",
                        "scale": 0.52
                    },
                    "secondary_element": {
                        "name": "cluster of rod shaped green bacteria",
                        "prompt": "a cluster of microscopic rod shaped bacteria germs",
                        "scale": 0.32
                    },
                    "has_pointing_hand": True
                }
            },
            {
                "narration": "Quá trình thực bào diễn ra chớp nhoáng, nuốt trọn và phân giải hoàn toàn vi khuẩn để bảo vệ sự sống.",
                "has_hand": False,
                "layout_hint": {
                    "archetype": "specimen_scientific",
                    "color_field": {"name": "Teal & Coral", "hex": "#2A9D8F"},
                    "interaction_type": "ENGULFING",
                    "environment_graphic": "ruler_scale",
                    "hero_element": {
                        "name": "phagocyte white blood cell",
                        "prompt": "a large phagocyte white blood cell engulfing microbe",
                        "scale": 0.52
                    },
                    "secondary_element": {
                        "name": "dissolved bacteria debris",
                        "prompt": "microscopic dissolved bacteria colony fragments",
                        "scale": 0.30
                    },
                    "has_pointing_hand": False
                }
            }
        ]
    },
    {
        "id": "geography",
        "video_filename": "video_geography_v4.mp4",
        "title": "Bí Ẩn Vực Thẳm Mariana",
        "topic": "Bí ẩn vực thẳm Mariana và áp suất nghiền nát tàu ngầm",
        "archetype": "geography_ocean",
        "scenes": [
            {
                "narration": "Rãnh Mariana sâu gần mười một nghìn mét, nơi bóng tối vĩnh cửu bao trùm đáy đại dương.",
                "has_hand": False,
                "layout_hint": {
                    "archetype": "geography_ocean",
                    "color_field": {"name": "Deep Cobalt", "hex": "#1D3557"},
                    "interaction_type": "MEASURING",
                    "environment_graphic": "coordinate_grid",
                    "hero_element": {
                        "name": "yellow retro research submarine",
                        "prompt": "a yellow retro oceanic deep sea research submarine submersible",
                        "scale": 0.48
                    },
                    "secondary_element": {
                        "name": "heavy cast iron ship anchor",
                        "prompt": "a vintage heavy cast iron nautical ship anchor",
                        "scale": 0.32
                    },
                    "has_pointing_hand": False
                }
            },
            {
                "narration": "Áp suất nơi đây gấp hơn một nghìn lần mặt biển, đủ sức nghiền nát mọi lớp vỏ thép của tàu ngầm.",
                "has_hand": True,
                "layout_hint": {
                    "archetype": "geography_ocean",
                    "color_field": {"name": "Charcoal Kraft", "hex": "#264653"},
                    "interaction_type": "PRESSING",
                    "environment_graphic": "coordinate_grid",
                    "hero_element": {
                        "name": "vintage industrial pressure gauge manometer",
                        "prompt": "a vintage round metal pressure gauge manometer with dial and needle",
                        "scale": 0.52
                    },
                    "secondary_element": {
                        "name": "yellow retro research submarine",
                        "prompt": "a yellow retro oceanic deep sea research submarine submersible",
                        "scale": 0.34
                    },
                    "has_pointing_hand": True
                }
            },
            {
                "narration": "Dù vậy, các loài cá phát quang kỳ bí vẫn kiên cường thích nghi và phát triển mạnh mẽ.",
                "has_hand": False,
                "layout_hint": {
                    "archetype": "geography_ocean",
                    "color_field": {"name": "Teal & Coral", "hex": "#2A9D8F"},
                    "interaction_type": "EXAMINING",
                    "environment_graphic": "depth_contours",
                    "hero_element": {
                        "name": "bioluminescent deep sea anglerfish",
                        "prompt": "a glowing bioluminescent deep-sea anglerfish with lantern",
                        "scale": 0.50
                    },
                    "secondary_element": {
                        "name": "deep ocean scientific camera",
                        "prompt": "a vintage deep sea exploration camera lens underwater",
                        "scale": 0.32
                    },
                    "has_pointing_hand": False
                }
            }
        ]
    },
    {
        "id": "history",
        "video_filename": "video_history_v4.mp4",
        "title": "Bí Thuật Ướp Xác Ai Cập",
        "topic": "Bí thuật ướp xác Ai Cập cổ đại và 4 chiếc bình Canopic linh thiêng",
        "archetype": "historical_relic",
        "scenes": [
            {
                "narration": "Người Ai Cập cổ đại tin rằng thể xác phải nguyên vẹn thì linh hồn mới có thể bước vào cõi vĩnh hằng.",
                "has_hand": False,
                "layout_hint": {
                    "archetype": "historical_relic",
                    "color_field": {"name": "Mustard Cardstock", "hex": "#E9C46A"},
                    "interaction_type": "EXAMINING",
                    "environment_graphic": "papyrus_frame",
                    "hero_element": {
                        "name": "ornate gilded pharaoh sarcophagus",
                        "prompt": "an ornate gilded ancient Egyptian pharaoh sarcophagus funerary mask",
                        "scale": 0.52
                    },
                    "secondary_element": {
                        "name": "ancient Egyptian linen mummy wrapping scroll",
                        "prompt": "an antique linen mummy wrapping bundle with hieroglyphs",
                        "scale": 0.32
                    },
                    "has_pointing_hand": False
                }
            },
            {
                "narration": "Họ tỉ mỉ loại bỏ nội tạng và bảo quản riêng biệt trong bốn chiếc bình canopic bằng đá thạch cao.",
                "has_hand": True,
                "layout_hint": {
                    "archetype": "historical_relic",
                    "color_field": {"name": "Burnt Terracotta", "hex": "#D44D22"},
                    "interaction_type": "EXAMINING",
                    "environment_graphic": "papyrus_frame",
                    "hero_element": {
                        "name": "ancient Egyptian canopic jar",
                        "prompt": "an ancient Egyptian alabaster canopic jar with carved deity head lid",
                        "scale": 0.50
                    },
                    "secondary_element": {
                        "name": "ancient papyrus manuscript scroll",
                        "prompt": "an antique Egyptian papyrus scroll with sacred hieroglyphic symbols",
                        "scale": 0.32
                    },
                    "has_pointing_hand": True
                }
            },
            {
                "narration": "Bốn chiếc bình canopic được phong ấn nghiêm ngặt dưới sự bảo hộ linh thiêng của các vị thần.",
                "has_hand": False,
                "layout_hint": {
                    "archetype": "historical_relic",
                    "color_field": {"name": "Plum & Gold", "hex": "#4A235A"},
                    "interaction_type": "PRESSING",
                    "environment_graphic": "papyrus_frame",
                    "hero_element": {
                        "name": "ancient Egyptian canopic jar",
                        "prompt": "an ancient Egyptian alabaster canopic jar with carved deity head lid",
                        "scale": 0.50
                    },
                    "secondary_element": {
                        "name": "ornate gilded pharaoh sarcophagus",
                        "prompt": "an ornate gilded ancient Egyptian pharaoh sarcophagus funerary mask",
                        "scale": 0.36
                    },
                    "has_pointing_hand": False
                }
            }
        ]
    }
]


async def run_production_v4():
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    frames_dir = output_dir / "v4_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    work_base_dir = PROJECT_ROOT / "data" / "work_v4"
    work_base_dir.mkdir(parents=True, exist_ok=True)

    cache_assets_dir = PROJECT_ROOT / "data" / "cache" / "v4_assets"
    cache_assets_dir.mkdir(parents=True, exist_ok=True)

    # Khởi tạo các engines
    tts_manager = TTSManager()
    designer = MultiElementSceneDesigner()
    generator = MultiAssetGenerator(cache_dir=cache_assets_dir)
    adapter = GbroAdapter()
    sub_generator = SubtitleGenerator(model_size="base")

    width, height = 1080, 1920
    summary_report = []

    logger.info("=" * 70)
    logger.info("🚀 BẮT ĐẦU SẢN XUẤT 3 VIDEO V4 COLLAGE B-ROLL (PHASE 3 PIPELINE)")
    logger.info("=" * 70)

    for vid_idx, vid_cfg in enumerate(TARGET_VIDEOS_V4, start=1):
        vid_id = vid_cfg["id"]
        vid_title = vid_cfg["title"]
        vid_filename = vid_cfg["video_filename"]
        topic = vid_cfg["topic"]

        logger.info(f"\n🎬 [{vid_idx}/3] Đang sản xuất Video V4: {vid_title} ({vid_filename})")
        vid_work_dir = work_base_dir / vid_id
        vid_work_dir.mkdir(parents=True, exist_ok=True)

        # 1. Sinh âm thanh TTS bằng EdgeTTS tiếng Việt chuẩn
        logger.info(f"🎙️ [1/5] Sinh giọng đọc EdgeTTS tiếng Việt cho 3 cảnh...")
        audio_dir = vid_work_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_files = await tts_manager.synthesize_scenes(
            scenes=vid_cfg["scenes"],
            language="vi",
            output_dir=str(audio_dir)
        )

        scene_clips = []
        scene_durations = []
        scene_layouts = []

        # 2. Xử lý từng cảnh: Phân tích -> Sinh cutouts -> Render Stop-motion 12fps
        for sc_idx, sc_cfg in enumerate(vid_cfg["scenes"]):
            sentence = sc_cfg["narration"]
            logger.info(f"\n--- Cảnh {sc_idx + 1}/3 ---")
            logger.info(f"📝 Lời thoại: \"{sentence}\"")

            # Tính thời lượng cảnh từ file audio thực tế
            audio_f = audio_files[sc_idx] if sc_idx < len(audio_files) and os.path.exists(audio_files[sc_idx]) else None
            if audio_f:
                info = get_video_info(audio_f)
                audio_dur = info.get("duration", 0.0) or 4.5
                sc_dur = max(4.5, audio_dur + 0.6)
            else:
                sc_dur = 5.0
            scene_durations.append(sc_dur)

            # Phân tích cú pháp cảnh
            layout_hint = sc_cfg.get("layout_hint")
            if layout_hint:
                scene_layout = layout_hint
                logger.info(f"🎯 [Layout Config] Hero='{scene_layout['hero_element']['name']}', Sec='{scene_layout['secondary_element']['name']}', Inter='{scene_layout['interaction_type']}'")
            else:
                scene_layout = await designer.design_scene(sentence, topic_context=topic, scene_idx=sc_idx)
            scene_layouts.append(scene_layout)

            # Sinh song song các vật thể cho cảnh (hoặc lấy từ cache/fallback)
            sc_assets_dir = vid_work_dir / f"scene_{sc_idx}_assets"
            asset_res = await generator.generate_scene_assets(
                scene_layout=scene_layout,
                output_dir=sc_assets_dir
            )
            hero_path = asset_res["hero_path"]
            sec_path = asset_res["sec_path"]

            # Kết xuất Stop-Motion 12 FPS video clip cho cảnh
            raw_clip_path = str(vid_work_dir / f"clip_raw_{sc_idx}.mp4")
            last_frame_path = str(vid_work_dir / f"last_frame_{sc_idx}.png")
            logger.info(f"🎞️ [Stop-Motion 12fps] Render cảnh {sc_idx + 1} ({sc_dur:.2f}s)...")

            adapter.render_multi_element_scene(
                scene_layout=scene_layout,
                hero_asset_path=hero_path,
                secondary_asset_path=sec_path,
                output_video_path=raw_clip_path,
                output_frame_path=last_frame_path,
                duration=sc_dur,
                work_dir=vid_work_dir / f"frames_sc_{sc_idx}",
                width=width,
                height=height,
                fps=12
            )

            # Ghép audio vào clip từng cảnh
            scene_clip_path = str(vid_work_dir / f"clip_{sc_idx}.mp4")
            if audio_f and os.path.exists(audio_f):
                merge_cmd = [
                    "ffmpeg", "-y",
                    "-i", raw_clip_path,
                    "-i", audio_f,
                    "-filter_complex", f"[1:a]apad=whole_dur={sc_dur:.2f}[a]",
                    "-map", "0:v",
                    "-map", "[a]",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-t", f"{sc_dur:.2f}",
                    scene_clip_path
                ]
                subprocess.run(merge_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            else:
                import shutil
                shutil.copyfile(raw_clip_path, scene_clip_path)

            scene_clips.append(scene_clip_path)

        # 3. Nối các cảnh thành video chính
        logger.info(f"🔗 [3/5] Ghép nối 3 cảnh thành video tổng thể...")
        concat_raw = str(vid_work_dir / "concat_raw.mp4")
        concat_videos(scene_clips, concat_raw)

        # 4. Tạo phụ đề TikTok ASS và Burn vào video cuối
        logger.info(f"📝 [4/5] Sinh phụ đề TikTok ASS & Burn vào video...")
        ass_path = str(vid_work_dir / "subtitles.ass")
        script_payload = {
            "title": vid_title,
            "scenes": vid_cfg["scenes"]
        }
        sub_generator.generate_tiktok_ass(
            script=script_payload,
            scene_durations=scene_durations,
            output_path=ass_path,
            format="shorts"
        )

        final_video_out = str(output_dir / vid_filename)
        sub_generator.burn_subtitles(
            video_path=concat_raw,
            sub_path=ass_path,
            output_path=final_video_out
        )
        logger.success(f"🎬 [V4 Complete] Đã xuất video thành phẩm: {final_video_out}")

        # 5. Trích xuất 3 khung hình tiêu biểu (ở giây thứ 2 của mỗi cảnh)
        logger.info(f"📸 [5/5] Trích xuất 3 khung hình tiêu biểu vào output/v4_frames/...")
        extracted_frames = []
        accum_dur = 0.0
        for sc_i, sc_dur in enumerate(scene_durations, start=1):
            # Lấy mẫu tại thời điểm bố cục đã lắp ráp hoàn chỉnh đầy đủ 2-3 vật thể và phụ đề
            target_time = accum_dur + min(sc_dur - 0.6, 3.6)
            accum_dur += sc_dur
            frame_filename = f"{vid_id}_scene_{sc_i}.jpg"
            frame_out = str(frames_dir / frame_filename)

            extract_cmd = [
                "ffmpeg", "-y",
                "-ss", f"{target_time:.2f}",
                "-i", final_video_out,
                "-vframes", "1",
                "-q:v", "2",
                frame_out
            ]
            subprocess.run(extract_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            extracted_frames.append(frame_out)
            logger.info(f"   🖼️ Frame {sc_i}: {frame_filename} (t={target_time:.2f}s)")

        summary_report.append({
            "id": vid_id,
            "title": vid_title,
            "video_path": final_video_out,
            "frames": extracted_frames,
            "total_duration": sum(scene_durations)
        })

    logger.info("\n" + "=" * 70)
    logger.info("🎉 TỔNG KẾT NGHIỆM THU PHASE 3: 3 VIDEO V4 & 9 KHUNG HÌNH ĐẠT CHUẨN")
    logger.info("=" * 70)
    for rep in summary_report:
        v_size = os.path.getsize(rep["video_path"]) / (1024 * 1024)
        logger.info(f"✨ {rep['title']}:")
        logger.info(f"   - Video: {rep['video_path']} ({v_size:.2f} MB, {rep['total_duration']:.1f}s)")
        logger.info(f"   - Frames ({len(rep['frames'])}):")
        for f in rep["frames"]:
            logger.info(f"     * {f}")

    return summary_report


if __name__ == "__main__":
    asyncio.run(run_production_v4())
