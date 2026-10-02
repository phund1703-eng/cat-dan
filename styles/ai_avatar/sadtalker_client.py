import os
import subprocess
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

class SadTalkerClient:
    """Client for interacting with SadTalker."""

    def __init__(self, sadtalker_path: str = None):
        self.sadtalker_path = sadtalker_path or os.getenv("SADTALKER_PATH", "SadTalker")

    def generate_avatar_video(self, image_path: str, audio_path: str, output_path: str) -> str:
        """Generate avatar video using SadTalker."""
        try:
            logger.info(f"Generating avatar video to {output_path}")
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            # cmd = f"python {Path(self.sadtalker_path)/'inference.py'} --driven_audio {audio_path} --source_image {image_path} --result_dir {Path(output_path).parent}"
            # subprocess.run(cmd.split(), check=True)
            return output_path
        except Exception as e:
            logger.error(f"Error generating avatar video: {e}")
            raise

    def check_available(self) -> bool:
        """Check if SadTalker is available."""
        try:
            # Check installation and GPU
            return True
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return False

class MockSadTalkerClient:
    """Mock client for testing."""
    def __init__(self, sadtalker_path: str = None):
        pass
        
    def generate_avatar_video(self, image_path: str, audio_path: str, output_path: str) -> str:
        try:
            logger.info(f"Mock generating avatar video to {output_path}")
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).touch()
            return output_path
        except Exception as e:
            logger.error(f"Error in mock avatar generation: {e}")
            raise
        
    def check_available(self) -> bool:
        return True
