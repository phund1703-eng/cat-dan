"""
AutoVideoFactory — Universal Collage B-Roll Production Script (v3)
Sản xuất 3 video Shorts (9:16, 1080x1920) theo tiêu chuẩn Universal Collage B-Roll Framework:
Gate 1: TextVisualAnalyzer (4 Archetypes, Bộ 3 Thành phần Chức năng)
Gate 2: UniversalImageGenerator (FLUX.1 Pollinations)
Gate 3: SemanticVerifier (Gemini Vision / Semantic Evaluation Quality Gate)
Gate 4: GbroAdapter.render_universal_artwork_clip (Stop-Motion 12 FPS Assemble-from-empty)
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path
from loguru import logger
from PIL import Image

ROOT_DIR = Path(__file__).parent.parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.script_engine.text_visual_analyzer import TextVisualAnalyzer
from core.media_engine.universal_image_generator import UniversalImageGenerator
from core.media_engine.semantic_verifier import SemanticVerifier
from core.tts_engine.tts_manager import TTSManager
from core.render_engine.ffmpeg_utils import get_video_info, concat_videos
from core.render_engine.subtitle_generator import SubtitleGenerator
from styles.collage_broll.gbro_adapter import GbroAdapter


TARGET_VIDEOS = [
    {
        "id": "video_biology_v3",
        "topic": "Hành trình tế bào bạch cầu tiêu diệt vi khuẩn",
        "title": "Bạch Cầu Tiêu Diệt Vi Khuẩn",
        "topic_domain": "biology",
        "scenes": [
            {
                "narration": "Mỗi giây trôi qua, cơ thể chúng ta là một bãi chiến trường khốc liệt chống lại hàng triệu vi khuẩn xâm nhập.",
                "has_hand": False,
                "has_camera": False,
                "seed": 1101
            },
            {
                "narration": "Ngay khi phát hiện mầm bệnh, các tế bào bạch cầu đại thực bào lập tức vươn xúc tu bao vây kẻ thù.",
                "has_hand": False,
                "has_camera": False,
                "seed": 1102
            },
            {
                "narration": "Quá trình thực bào diễn ra chớp nhoáng, nuốt chửng và phân giải hoàn toàn vi khuẩn để bảo vệ sự sống.",
                "has_hand": False,
                "has_camera": False,
                "seed": 1103
            }
        ]
    },
    {
        "id": "video_geography_v3",
        "topic": "Bí mật rãnh Mariana - Vực sâu tăm tối nhất hành tinh",
        "title": "Bí Mật Rãnh Mariana",
        "topic_domain": "geography",
        "scenes": [
            {
                "narration": "Rãnh Mariana sâu gần mười một nghìn mét, nơi bóng tối vĩnh cửu bao trùm đáy đại dương.",
                "has_hand": False,
                "has_camera": False,
                "seed": 2201
            },
            {
                "narration": "Áp suất nơi đây gấp hơn một nghìn lần mặt biển, đủ sức nghiền nát mọi tàu ngầm thông thường.",
                "has_hand": False,
                "has_camera": False,
                "seed": 2202
            },
            {
                "narration": "Dù vậy, các sinh vật kỳ dị phát quang vẫn phát triển mạnh mẽ, mở ra cánh cửa tiến hóa chưa từng biết.",
                "has_hand": False,
                "has_camera": True,
                "seed": 2203
            }
        ]
    },
    {
        "id": "video_history_v3",
        "topic": "Bí mật kỹ thuật ướp xác của các Pharaoh Ai Cập",
        "title": "Bí Mật Kỹ Thuật Ướp Xác Pharaoh",
        "topic_domain": "history",
        "scenes": [
            {
                "narration": "Người Ai Cập cổ đại tin rằng thể xác phải nguyên vẹn thì linh hồn mới có thể bước vào cõi vĩnh hằng.",
                "has_hand": False,
                "has_camera": False,
                "seed": 3301
            },
            {
                "narration": "Họ tỉ mỉ loại bỏ nội tạng và bảo quản riêng biệt trong bốn chiếc bình canopic bằng đá alabaster.",
                "has_hand": True,
                "has_camera": False,
                "seed": 3302
            },
            {
                "narration": "Sau bảy mươi ngày ướp muối natron và bọc vải lanh, thi hài được an táng trong cỗ quan tài vàng lộng lẫy.",
                "has_hand": False,
                "has_camera": False,
                "seed": 3303
            }
        ]
    }
]


async def produce_universal_videos():
    output_dir = Path("output").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = Path("data/temp_universal_v3").resolve()
    temp_dir.mkdir(parents=True, exist_ok=True)

    analyzer = TextVisualAnalyzer()
    img_gen = UniversalImageGenerator()
    verifier = SemanticVerifier()
    tts_manager = TTSManager()
    adapter = GbroAdapter()
    sub_generator = SubtitleGenerator(model_size="base")

    width, height = 1080, 1920
    summary_report = []

    for vid_idx, vid_cfg in enumerate(TARGET_VIDEOS, start=1):
        vid_id = vid_cfg["id"]
        topic = vid_cfg["topic"]
        domain = vid_cfg["topic_domain"]
        logger.info(f"\n=========================================================================")
        logger.info(f"🚀 BẮT ĐẦU SẢN XUẤT VIDEO V3 ({vid_idx}/3): [{vid_id}] - {topic}")
        logger.info(f"=========================================================================")

        vid_work_dir = temp_dir / vid_id
        vid_work_dir.mkdir(parents=True, exist_ok=True)

        # 1. Sinh âm thanh TTS bằng EdgeTTS chuẩn tiếng Việt
        logger.info("🎙️ Sinh giọng đọc EdgeTTS tiếng Việt cho từng cảnh...")
        audio_dir = vid_work_dir / "tts"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_files = await tts_manager.synthesize_scenes(
            scenes=vid_cfg["scenes"],
            language="vi",
            output_dir=str(audio_dir)
        )

        scene_clips = []
        scene_durations = []
        scene_metadata = []

        for sc_idx, sc_cfg in enumerate(vid_cfg["scenes"]):
            sentence = sc_cfg["narration"]
            seed = sc_cfg.get("seed", 1000 + sc_idx)
            has_hand = sc_cfg.get("has_hand", False)
            has_camera = sc_cfg.get("has_camera", False)

            logger.info(f"\n--- [Cảnh {sc_idx + 1}/{len(vid_cfg['scenes'])}] ---")
            logger.info(f"📝 Lời thoại: {sentence}")

            # Gate 1: TextVisualAnalyzer
            logger.info("🧠 [Gate 1] Phân tích ngữ nghĩa thị giác & Visual Archetype...")
            vis_data = await analyzer.analyze_sentence(sentence, topic_context=topic, scene_idx=sc_idx)
            archetype = vis_data["archetype"]
            hero = vis_data["hero_concept"]
            dynamics = vis_data["dynamics"]
            grounding = vis_data["grounding"]
            color_field = vis_data["color_field"]
            color_hex = vis_data["color_hex"]
            flux_prompt = vis_data["flux_prompt"]

            logger.info(f"🏛️ Archetype: [{archetype}] | Nền: {color_field} (#{color_hex})")
            logger.info(f"✨ Hero: {hero[:40]}... | Dynamics: {dynamics[:40]}...")

            # Gate 2: UniversalImageGenerator (FLUX.1)
            raw_art_path = str(vid_work_dir / f"art_raw_{sc_idx}.png")
            logger.info("🎨 [Gate 2] Sinh tranh tĩnh 9:16 FLUX hoàn chỉnh...")
            generated_art = await img_gen.generate_artwork(
                prompt=flux_prompt,
                output_path=raw_art_path,
                seed=seed,
                width=720,
                height=1280
            )

            # Gate 3: SemanticVerifier (Quality Gate)
            logger.info("🔍 [Gate 3] Kiểm duyệt ngữ nghĩa (Vision/Semantic Quality Gate)...")
            final_art, verify_res = await verifier.verify_and_refine(
                sentence=sentence,
                image_path=generated_art,
                initial_prompt=flux_prompt,
                image_gen=img_gen
            )
            logger.info(f"✅ Đã duyệt tác phẩm: Confidence={verify_res.get('confidence', 0.85):.2f}")

            # Tính thời lượng cảnh từ âm thanh TTS
            audio_f = audio_files[sc_idx] if sc_idx < len(audio_files) and os.path.exists(audio_files[sc_idx]) else None
            if audio_f:
                info = get_video_info(audio_f)
                dur = max(4.0, (info.get("duration", 0.0) or 4.5) + 0.5)
            else:
                dur = 5.0
            scene_durations.append(dur)

            # Gate 4: Stop-Motion 12 FPS Assemble-from-empty
            logger.info(f"🎬 [Gate 4] Lắp ráp Stop-Motion 12 FPS từ rỗng ({dur:.1f}s)...")
            raw_clip_path = str(vid_work_dir / f"clip_raw_{sc_idx}.mp4")
            adapter.render_universal_artwork_clip(
                artwork_path=final_art,
                color_hex=color_hex,
                color_field=color_field,
                topic_domain=domain,
                output_path=raw_clip_path,
                has_hand=has_hand,
                has_camera=has_camera,
                duration=dur,
                work_dir=vid_work_dir / f"frames_{sc_idx}",
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
                    "-filter_complex", f"[1:a]apad=whole_dur={dur:.2f}[a]",
                    "-map", "0:v",
                    "-map", "[a]",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-t", f"{dur:.2f}",
                    scene_clip_path
                ]
                subprocess.run(merge_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            else:
                import shutil
                shutil.copyfile(raw_clip_path, scene_clip_path)

            scene_clips.append(scene_clip_path)
            scene_metadata.append({
                "scene_idx": sc_idx + 1,
                "narration": sentence,
                "archetype": archetype,
                "hero": hero,
                "dynamics": dynamics,
                "grounding": grounding,
                "color_field": color_field,
                "color_hex": color_hex,
                "has_hand": has_hand,
                "artwork": final_art,
                "confidence": verify_res.get("confidence", 0.85)
            })

        # Nối các cảnh thành video chính
        logger.info(f"🔗 Ghép nối {len(scene_clips)} cảnh thành video chính...")
        concat_raw = str(vid_work_dir / "concat_raw.mp4")
        concat_videos(scene_clips, concat_raw)

        # Tạo phụ đề TikTok ASS chuẩn 100% tiếng Việt
        logger.info("📝 Tạo phụ đề TikTok ASS...")
        ass_path = str(vid_work_dir / "subtitles.ass")
        script_payload = {
            "title": vid_cfg["title"],
            "scenes": vid_cfg["scenes"]
        }
        sub_generator.generate_tiktok_ass(
            script=script_payload,
            scene_durations=scene_durations,
            output_path=ass_path,
            format="shorts"
        )

        # Burn phụ đề vào video cuối cùng
        final_video_out = str(output_dir / f"{vid_id}.mp4")
        logger.info(f"🔥 Xuất bản video hoàn chỉnh: {final_video_out}")
        sub_generator.burn_subtitles(
            video_path=concat_raw,
            sub_path=ass_path,
            output_path=final_video_out
        )

        # Trích xuất ít nhất 3 khung hình đại diện
        logger.info("📸 Trích xuất khung hình đại diện...")
        extracted_frames = []
        frame_times = [1.8, 6.8, 11.5]
        for f_i, f_time in enumerate(frame_times, start=1):
            frame_out = str(output_dir / f"{vid_id}_frame_{f_i}.jpg")
            extract_cmd = [
                "ffmpeg", "-y",
                "-ss", str(f_time),
                "-i", final_video_out,
                "-vframes", "1",
                "-q:v", "2",
                frame_out
            ]
            subprocess.run(extract_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            extracted_frames.append(frame_out)

        summary_report.append({
            "video_id": vid_id,
            "title": vid_cfg["title"],
            "domain": domain,
            "output_path": final_video_out,
            "frames": extracted_frames,
            "scenes": scene_metadata
        })
        logger.success(f"🎉 Hoàn thành xuất sắc: {final_video_out}")

    return summary_report


if __name__ == "__main__":
    results = asyncio.run(produce_universal_videos())
    logger.success(f"\n✅ ĐÃ HOÀN THÀNH TẤT CẢ {len(results)} VIDEO UNIVERSAL COLLAGE B-ROLL!")
