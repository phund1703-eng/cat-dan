import os
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

from .manim_generator import ManimGenerator

load_dotenv()

class AnimationRenderer:
    """Full animation 2D pipeline."""

    def __init__(self):
        self.generator = ManimGenerator()

    async def create_video(self, script: dict, language: str, output_path: str, format: str = 'shorts') -> str:
        """Full pipeline: generate Manim code → render animations → add TTS audio → subtitles → music."""
        try:
            logger.info(f"Creating 2D animation video: {output_path}")
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            script_path = self.generator.generate_full_animation(script)
            rendered_files = self.generator.render_animation(script_path, str(Path(output_path).parent))
            
            # Combine rendered files, add audio, subtitles, music
            return output_path
        except Exception as e:
            logger.error(f"Error creating animation video: {e}")
            raise
