import asyncio
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger
from dotenv import load_dotenv

from core.config import get_settings

from .edge_tts_client import EdgeTTSClient
from .fish_audio_client import FishAudioClient
from .vieneu_client import VieNeuClient

load_dotenv()

class TTSManager:
    """Unified TTS interface managing multiple TTS engines."""

    def __init__(self):
        """Initializes the TTS Manager and loads config."""
        self.edge_client = EdgeTTSClient()
        self.fish_client = FishAudioClient()
        self.vieneu_client = VieNeuClient()
        self.config = self._load_config()
        self.primary_engine = self.config.get("tts", {}).get("primary_engine", "auto")

    def _load_config(self) -> Dict[str, Any]:
        """Nạp cấu hình từ nguồn duy nhất core.config.get_settings()
        (config/settings.yaml, resolve theo thư mục gốc repo)."""
        return get_settings()

    async def synthesize(
        self,
        text: str,
        language: str = "vi",
        output_path: str = None,
        engine: str = 'auto',
        voice_preset: str = None
    ) -> str:
        """
        Synthesizes speech using the requested engine or fallback logic.
        Prioritizes VieNeu-TTS (on-device CPU) for Vietnamese with automatic failover to Edge TTS.

        Args:
            text (str): The text to synthesize.
            language (str): Language ('vi' or 'en'). Defaults to 'vi'.
            output_path (str, optional): File output path.
            engine (str, optional): 'auto', 'vieneu', 'fish', or 'edge'. Defaults to 'auto'.
            voice_preset (str, optional): Built-in voice preset name or voice sample reference.

        Returns:
            str: Path to the generated audio file.
        """
        target_engine = self.primary_engine if engine == 'auto' else engine

        # 1. Prioritize VieNeu-TTS for Vietnamese or explicit 'vieneu' engine
        if target_engine == 'vieneu' or (engine == 'auto' and language == 'vi'):
            try:
                logger.info(f"TTSManager: Attempting synthesis with VieNeu TTS (On-Device CPU, voice={voice_preset})")
                return await self.vieneu_client.synthesize(
                    text=text,
                    language=language,
                    output_path=output_path,
                    voice=voice_preset
                )
            except Exception as e:
                logger.warning(f"TTSManager: VieNeu TTS failed ({e}), falling back to Edge TTS")
                return await self.edge_client.synthesize(
                    text=text,
                    language=language,
                    output_path=output_path
                )

        # 2. Fish Audio engine
        if target_engine == 'fish':
            try:
                logger.info("TTSManager: Attempting synthesis with Fish Audio")
                return await self.fish_client.synthesize(text, language, output_path)
            except Exception as e:
                logger.error(f"TTSManager: Fish Audio failed ({e}), falling back to Edge TTS")
                return await self.edge_client.synthesize(text, language, output_path)

        # 3. Default Edge TTS
        try:
            logger.info("TTSManager: Attempting synthesis with Edge TTS")
            return await self.edge_client.synthesize(text, language, output_path)
        except Exception as e:
            logger.error(f"TTSManager: Edge TTS failed: {e}")
            raise

    async def synthesize_scenes(
        self,
        scenes: List[Dict[str, Any]],
        language: str,
        output_dir: str,
        voice_preset: str = None
    ) -> List[str]:
        """
        Synthesizes narration for a list of scenes.

        Args:
            scenes (list): List of scene dictionaries containing 'narration'.
            language (str): Language for TTS.
            output_dir (str): Directory to save scene audios.
            voice_preset (str, optional): Preset voice name or voice sample reference.

        Returns:
            list: List of absolute paths to generated audio files.
        """
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        
        audio_paths = []
        
        for i, scene in enumerate(scenes):
            narration = scene.get("narration", "").strip()
            if not narration:
                logger.warning(f"Scene {i} has no narration, skipping TTS.")
                audio_paths.append("")
                continue
                
            filename = f"scene_{i:03d}.wav"
            output_path = str(out_dir / filename)
            
            try:
                path = await self.synthesize(narration, language, output_path, voice_preset=voice_preset)
                audio_paths.append(path)
            except Exception as e:
                logger.error(f"Failed to synthesize scene {i}: {e}")
                audio_paths.append("")
                
        return audio_paths
