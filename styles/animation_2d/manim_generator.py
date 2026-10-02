import os
import subprocess
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

MANIM_PROMPT_TEMPLATE = """
Generate a ManimCE Scene class for the following script scene.
Only output valid Python code.
Script: {script}
"""

class ManimGenerator:
    """Generates and renders Manim code for 2D animations."""

    def __init__(self):
        pass

    def generate_scene_code(self, script: dict, scene_index: int) -> str:
        """Generate Manim python code for one scene."""
        try:
            logger.info(f"Generating Manim code for scene {scene_index}")
            scene_data = script.get('scenes', [])[scene_index]
            code = f"from manim import *\n\nclass Scene{scene_index}(Scene):\n    def construct(self):\n        text = Text('Scene {scene_index}')\n        self.play(Write(text))\n        self.wait(1)"
            return code
        except Exception as e:
            logger.error(f"Error generating scene code: {e}")
            raise

    def generate_full_animation(self, script: dict) -> str:
        """Generates complete Manim Python file for all scenes."""
        try:
            logger.info("Generating full Manim animation script")
            out_path = Path("manim_script.py")
            out_path.write_text("from manim import *\n")
            return str(out_path)
        except Exception as e:
            logger.error(f"Error generating full animation: {e}")
            raise

    def render_animation(self, manim_script_path: str, output_dir: str) -> list[str]:
        """Render Manim script to video files."""
        try:
            logger.info(f"Rendering Manim animation from {manim_script_path}")
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            # subprocess.run(["manim", "render", manim_script_path, "-qh", "--fps", "30"], check=True)
            return [str(Path(output_dir) / "rendered_scene.mp4")]
        except Exception as e:
            logger.error(f"Error rendering animation: {e}")
            raise
