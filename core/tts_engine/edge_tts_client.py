import asyncio
from pathlib import Path
import edge_tts
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

class EdgeTTSClient:
    """Client for generating speech using Microsoft Edge TTS (Free fallback)."""

    def __init__(self):
        """Initializes the Edge TTS client."""
        self.default_voices = {
            "vi": "vi-VN-NamMinhNeural",
            "en": "en-US-JennyNeural"
        }
        self.rate = "-5%"
        self.pitch = "-2Hz"

    async def synthesize(
        self,
        text: str,
        language: str = "vi",
        output_path: str = "",
        rate: str = None,
        pitch: str = None
    ) -> str:
        """
        Synthesizes speech from text and saves to an audio file.

        Args:
            text (str): The text to synthesize.
            language (str): Language code ('vi' or 'en').
            output_path (str): The path to save the audio file.
            rate (str, optional): Speed adjustment (e.g., '-5%'). Defaults to self.rate.
            pitch (str, optional): Pitch adjustment (e.g., '-2Hz'). Defaults to self.pitch.

        Returns:
            str: The absolute path to the generated audio file.
        """
        voice = self.default_voices.get(language, "en-US-JennyNeural")
        eff_rate = rate if rate is not None else self.rate
        eff_pitch = pitch if pitch is not None else self.pitch

        logger.info(
            f"Synthesizing text with Edge TTS (Voice: {voice}, Rate: {eff_rate}, Pitch: {eff_pitch}) -> {output_path}"
        )
        
        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            communicate = edge_tts.Communicate(text, voice, rate=eff_rate, pitch=eff_pitch)
            await communicate.save(str(path.absolute()))
            
            logger.success(f"Successfully generated Edge TTS audio: {output_path}")
            return str(path.absolute())
        except Exception as e:
            logger.error(f"Failed to synthesize with Edge TTS: {e}")
            raise

    async def get_available_voices(self, language: str = None) -> list:
        """
        Gets available voices, optionally filtered by language.

        Args:
            language (str, optional): Language prefix (e.g., 'vi', 'en').

        Returns:
            list: A list of voice dictionaries.
        """
        try:
            voices = await edge_tts.list_voices()
            if language:
                return [v for v in voices if v["Locale"].startswith(language)]
            return voices
        except Exception as e:
            logger.error(f"Failed to list Edge TTS voices: {e}")
            return []
