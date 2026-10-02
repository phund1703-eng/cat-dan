"""
AutoVideoFactory — Phase 3 Production Pipeline (V5): run_pipeline_v5.py
Pipeline Tích Hợp Toàn Diện Thế Hệ 5 (Kinetic Stop-Motion 12fps):
Quy trình tự động hóa hoàn toàn từ Văn bản kịch bản -> Video YouTube Shorts / TikTok chuẩn phong cách Collage:
1. Script Engine: Phân tích câu thoại tiếng Việt -> VerbSemanticMatcher nhận diện Động từ & Ánh xạ về 1 trong 8 Động cơ Kinetic.
2. Bridge Engine: KineticLayoutBridge tự động đo đạc Alpha Bounding Box, tính toán tỷ lệ scale và điểm va chạm cơ học.
3. Media Generator / Cache: Định vị hoặc sinh Isolated Cutouts chất lượng cao (nền trong suốt 100%, không rỗng).
4. Compositor 12fps: GbroAdapter render hoạt cảnh stop-motion với viền kem 3px, bóng đổ 45° và nhịp giật Discrete Physical Steps.
5. TTS & Audio Sync: EdgeTTS lồng tiếng tự nhiên và SubtitleGenerator dán phụ đề động lực học chuẩn xác.
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from loguru import logger
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.script_engine.verb_semantic_matcher import VerbSemanticMatcher
from core.script_engine.ai_visual_director import AIVisualDirector
from core.media_engine.kinetic_layout_bridge import KineticLayoutBridge
from styles.collage_broll.gbro_adapter import GbroAdapter
from core.tts_engine.tts_manager import TTSManager
from core.render_engine.subtitle_generator import SubtitleGenerator


from core.render_engine.ffmpeg_utils import get_video_info

OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class PipelineV5:
    """
    Bộ điều phối toàn trình Video Collage V5 (Cinematic Collage Theatre 7 Tầng).
    """

    def __init__(self):
        self.matcher = VerbSemanticMatcher()
        self.director = AIVisualDirector()
        self.bridge = KineticLayoutBridge()
        self.adapter = GbroAdapter()
        self.tts = TTSManager()
        self.subtitle_gen = SubtitleGenerator()

    async def produce_single_scene_video(
        self,
        sentence: str,
        hero_asset_path: str,
        secondary_asset_path: Optional[str] = None,
        action_assets_paths: Optional[list] = None,
        output_filename: str = "video_v5_demo.mp4",
        custom_layout_params: Optional[dict] = None
    ) -> Path:
        """
        Sản xuất 1 clip video thành phẩm V5 hoàn chỉnh từ 1 câu thoại tiếng Việt theo kiến trúc 7 tầng.
        """
        logger.info(f"\n🚀 [PIPELINE V5] Bắt đầu sản xuất kịch bản: '{sentence}'")
        out_final_path = OUTPUT_DIR / output_filename
        temp_dir = OUTPUT_DIR / f"temp_{Path(output_filename).stem}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # 1. Thu âm Voice EdgeTTS & lấy duration thực tế
        audio_path = temp_dir / "voice.mp3"
        logger.info("🎙️ [Step 1] Sinh thuyết minh EdgeTTS tiếng Việt...")
        try:
            await self.tts.synthesize(text=sentence, language="vi", output_path=str(audio_path))
            probe_info = get_video_info(str(audio_path))
            actual_duration = float(probe_info.get("duration", 3.2))
        except Exception as e:
            logger.warning(f"⚠️ TTS Exception ({e}), sử dụng fallback duration 3.5s")
            actual_duration = 3.5
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                "-t", str(actual_duration), str(audio_path)
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        video_duration = max(3.0, actual_duration + 0.5)
        logger.info(f"⏱️ Thời lượng audio: {actual_duration:.2f}s -> Thời lượng video: {video_duration:.2f}s")

        # 2. Phân tích kịch bản bằng AIVisualDirector & sinh Scene Blueprint 7 Tầng
        logger.info("🧠 [Step 2] AIVisualDirector phân tích kịch bản & sinh Scene Blueprint 7 Tầng...")
        blueprint = await self.director.direct_scene(sentence)
        fx_cfg = blueprint.get("cause_and_effect_fx", {})
        kinetic_engine = fx_cfg.get("kinetic_engine", "ENGINE_SEVER_SHATTER")
        logger.info(f"🎯 Động cơ Kinetic: {kinetic_engine} | Archetype: {blueprint.get('spatial_context', {}).get('archetype')}")

        # 3. Xây dựng Scene Layout 7 tầng tối ưu tọa độ va chạm qua KineticLayoutBridge
        logger.info("📐 [Step 3] KineticLayoutBridge tự động hóa kích thước, va chạm & phân tầng 7 lớp...")
        params = dict(custom_layout_params or {})
        scene_layout = self.bridge.build_scene_layout(
            engine_name=kinetic_engine,
            hero_asset_path=hero_asset_path,
            secondary_asset_path=secondary_asset_path,
            action_assets_paths=action_assets_paths,
            custom_params=params,
            director_blueprint=blueprint
        )
        if not scene_layout.get("has_pointing_hand"):
            scene_layout["has_pointing_hand"] = params.get("has_pointing_hand", True)

        # 4. Render khung hình Stop-motion 12fps bằng GbroAdapter (Kiến trúc 7 Tầng)
        temp_video = temp_dir / "visual_no_audio.mp4"
        logger.info("🎨 [Step 4] GbroAdapter render stop-motion 12fps 7 tầng (1080x1920)...")
        self.adapter.render_multi_element_scene(
            scene_layout=scene_layout,
            hero_asset_path=hero_asset_path,
            secondary_asset_path=secondary_asset_path,
            output_video_path=str(temp_video),
            duration=video_duration,
            work_dir=temp_dir / "frames",
            width=1080,
            height=1920,
            fps=12
        )

        # 5. Tạo Subtitle ASS chuẩn TikTok Yellow và Ghép Video + Audio + Subtitles
        logger.info("🎬 [Step 5] Ghép muxing Video + Audio + Phụ đề ASS TikTok Yellow...")
        subtitle_ass = temp_dir / "subtitles.ass"
        # Tạo file phụ đề ASS chuẩn TikTok Yellow (&H0000FFFF) viền đen
        ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TikTokYellow,Arial,65,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,3,2,60,60,320,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.20,0:00:{actual_duration:05.2f},TikTokYellow,,0,0,0,,{sentence.upper()}
"""
        with open(subtitle_ass, "w", encoding="utf-8") as f:
            f.write(ass_content)

        # Ghép video bằng FFmpeg
        # Chuyển đường dẫn ASS sang định dạng an toàn cho ffmpeg filter trên Windows
        ass_filter_path = str(subtitle_ass).replace("\\", "/").replace(":", "\\:")
        mux_cmd = [
            "ffmpeg", "-y",
            "-i", str(temp_video),
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
            str(out_final_path)
        ]

        # Nếu subtitles filter bị lỗi do font, fallback sang ghép audio thường
        res = subprocess.run(mux_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if res.returncode != 0:
            logger.warning("⚠️ Subtitle filter không khả dụng, thực hiện ghép Video + Audio chuẩn.")
            fallback_cmd = [
                "ffmpeg", "-y",
                "-i", str(temp_video),
                "-i", str(audio_path),
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                str(out_final_path)
            ]
            subprocess.run(fallback_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)

        logger.info(f"✨ [PIPELINE V5 THÀNH CÔNG] Video hoàn chỉnh: {out_final_path} ({out_final_path.stat().st_size / 1024:.1f} KB)")
        return out_final_path


async def run_v5_verification():
    """Hàm chạy kiểm thử tích hợp đầu cuối cho kịch bản mẫu."""
    pipeline = PipelineV5()

    sentence = "Lưỡi rìu bổ đôi khúc gỗ rừng già"
    axe_asset = str(PROJECT_ROOT / "data" / "cache" / "cutouts" / "real_axe.png")
    woodlog_asset = str(PROJECT_ROOT / "data" / "cache" / "cutouts" / "real_wood_log.png")

    output_path = await pipeline.produce_single_scene_video(
        sentence=sentence,
        hero_asset_path=axe_asset,
        secondary_asset_path=woodlog_asset,
        output_filename="video_v5_sever_axe_woodlog.mp4",
        custom_layout_params={
            "hero_scale": 0.48,
            "sec_scale": 0.38,
            "split_axis": "vertical",
            "windup_tilt_deg": -35.0,
            "strike_tilt_deg": 6.0,
            "tilt_deg": 30.0,
            "drift_direction": [1.0, 0.2],
            "max_drift_px": 260.0,
            "has_pointing_hand": True
        }
    )

    # Trích xuất snapshot kiểm tra tại giây 2.4s
    snap_path = OUTPUT_DIR / "snapshot_v5_demo_axe_woodlog.jpg"
    subprocess.run([
        "ffmpeg", "-y",
        "-ss", "2.4",
        "-i", str(output_path),
        "-vframes", "1",
        "-q:v", "2",
        str(snap_path)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    print(f"🎉 Kiểm thử End-to-End V5 hoàn tất! Video: {output_path} | Snapshot: {snap_path}")


if __name__ == "__main__":
    asyncio.run(run_v5_verification())
