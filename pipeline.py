"""
AutoVideoFactory — Main Pipeline Orchestrator
Điều phối toàn bộ quy trình tạo video từ đầu đến cuối
"""

import sys
import asyncio
import uuid
from pathlib import Path
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

# Import các engine
from core.script_engine.script_generator import ScriptGenerator
from core.tts_engine.tts_manager import TTSManager
from core.media_engine.media_manager import MediaManager


class VideoFactory:
    """
    Pipeline chính tạo video tự động.
    
    Sử dụng:
        factory = VideoFactory()
        result = await factory.create_video(
            topic="5 mẹo học tiếng Anh hiệu quả",
            style="collage_broll",
            language="vi",
        )
    """
    
    def __init__(self):
        self.script_gen = ScriptGenerator()
        self.tts_manager = TTSManager()
        self.media_manager = MediaManager()
        self.output_dir = Path("data/output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_video(
        self,
        topic: str,
        style: str,
        language: str = "vi",
        video_format: str = "shorts",
        quality: str = "standard",
        job_id: str = None,
    ) -> dict:
        """
        Tạo video hoàn chỉnh từ chủ đề.
        
        Args:
            topic: Chủ đề video (ví dụ: "5 mẹo học tiếng Anh")
            style: Phong cách video: collage_broll | animation_2d | clip_overlay | whiteboard | ai_avatar
            language: Ngôn ngữ: vi | en | both
            video_format: Định dạng: shorts (9:16) | landscape (16:9)
            quality: standard | premium
            job_id: ID job (tự tạo nếu None)
            
        Returns:
            dict: {job_id, output_path, script, metadata, duration, style}
        """
        
        job_id = job_id or str(uuid.uuid4())[:8]
        job_output_dir = self.output_dir / job_id
        job_output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🎬 Bắt đầu tạo video [{job_id}]: '{topic}' | {style} | {language}")
        start_time = datetime.now()
        
        try:
            # === Bước 1: Tạo kịch bản ===
            logger.info(f"📝 [1/4] Đang viết kịch bản với Gemini...")
            
            if language == "both":
                scripts = await self.script_gen.generate_bilingual(topic, style)
                script_vi = scripts["vi"]
                script_en = scripts["en"]
                primary_script = script_vi
            else:
                primary_script = await self.script_gen.generate(
                    topic=topic, style=style, language=language, quality=quality
                )
                scripts = {language: primary_script}
            
            logger.success(f"✅ Kịch bản: {len(primary_script.get('scenes', []))} cảnh")
            
            # === Bước 2: Tạo giọng đọc ===
            logger.info(f"🎙️ [2/4] Đang tạo giọng đọc...")
            tts_dir = job_output_dir / "audio"
            tts_dir.mkdir(exist_ok=True)
            
            audio_files = {}
            for lang, script in scripts.items():
                lang_audio_dir = tts_dir / lang
                lang_audio_dir.mkdir(exist_ok=True)
                audio_files[lang] = await self.tts_manager.synthesize_scenes(
                    scenes=script["scenes"],
                    language=lang,
                    output_dir=str(lang_audio_dir),
                )
            
            logger.success(f"✅ Đã tạo audio cho {len(audio_files)} ngôn ngữ")
            
            # === Bước 3: Tải media ===
            logger.info(f"📸 [3/4] Đang tải media (stock footage/images)...")
            media_dir = job_output_dir / "media"
            media_dir.mkdir(exist_ok=True)
            
            scene_media = self.media_manager.download_scene_media(
                scenes=primary_script["scenes"],
                output_dir=str(media_dir),
            )
            
            logger.success(f"✅ Đã tải {len(scene_media)} file media")
            
            # === Bước 4: Render video ===
            logger.info(f"🎞️ [4/4] Đang render video [{style}]...")
            
            video_files = {}
            for lang, script in scripts.items():
                lang_output = str(job_output_dir / f"video_{lang}.mp4")
                video_path = await self._render_by_style(
                    style=style,
                    script=script,
                    language=lang,
                    audio_files=audio_files.get(lang, []),
                    media_files=scene_media,
                    output_path=lang_output,
                    video_format=video_format,
                )
                video_files[lang] = video_path
            
            # === Sinh metadata ===
            from publish.metadata_generator import MetadataGenerator
            meta_gen = MetadataGenerator()
            metadata = await meta_gen.generate(primary_script, language if language != "both" else "vi", style)
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.success(f"🎉 Video hoàn thành! [{job_id}] trong {duration:.1f}s")
            
            return {
                "job_id": job_id,
                "status": "done",
                "output_files": video_files,
                "output_path": video_files.get(language, list(video_files.values())[0]),
                "script": primary_script,
                "metadata": metadata,
                "duration_seconds": duration,
                "style": style,
                "language": language,
                "topic": topic,
            }
            
        except Exception as e:
            logger.error(f"❌ Lỗi tạo video [{job_id}]: {e}")
            raise
    
    async def _render_by_style(
        self,
        style: str,
        script: dict,
        language: str,
        audio_files: list,
        media_files: list,
        output_path: str,
        video_format: str,
    ) -> str:
        """Route đến engine phù hợp theo phong cách"""
        
        if style == "collage_broll":
            from styles.collage_broll.collage_engine import CollageEngine
            engine = CollageEngine()
            
        elif style == "animation_2d":
            from styles.animation_2d.animation_renderer import AnimationRenderer
            engine = AnimationRenderer()
            
        elif style == "clip_overlay":
            from styles.clip_overlay.clip_engine import ClipEngine
            engine = ClipEngine()
            
        elif style == "whiteboard":
            from styles.whiteboard.whiteboard_engine import WhiteboardEngine
            engine = WhiteboardEngine()
            
        elif style == "ai_avatar":
            from styles.ai_avatar.avatar_renderer import AvatarRenderer
            engine = AvatarRenderer()
            
        else:
            raise ValueError(f"Phong cách không hợp lệ: {style}")
        
        if style == "collage_broll":
            return await engine.create_video(
                script=script,
                language=language,
                output_path=output_path,
                format=video_format,
                audio_files=audio_files,
                media_files=media_files,
            )
        
        return await engine.create_video(
            script=script,
            language=language,
            output_path=output_path,
            format=video_format,
        )


# ===== CLI Interface =====
async def main():
    """Quick test: tạo 1 video từ command line"""
    import sys
    
    if len(sys.argv) < 3:
        print("Sử dụng: python pipeline.py <topic> <style> [language] [format]")
        print("Ví dụ: python pipeline.py '5 mẹo học tiếng Anh' collage_broll vi shorts")
        return
    
    topic = sys.argv[1]
    style = sys.argv[2]
    language = sys.argv[3] if len(sys.argv) > 3 else "vi"
    video_format = sys.argv[4] if len(sys.argv) > 4 else "shorts"
    
    factory = VideoFactory()
    result = await factory.create_video(
        topic=topic,
        style=style,
        language=language,
        video_format=video_format,
    )
    
    print(f"\n✅ Video đã tạo xong!")
    print(f"📁 File: {result['output_path']}")
    print(f"🎬 Job ID: {result['job_id']}")
    print(f"⏱️  Thời gian: {result['duration_seconds']:.1f}s")
    print(f"📝 Title: {result['metadata'].get('title', '')}")


if __name__ == "__main__":
    asyncio.run(main())
