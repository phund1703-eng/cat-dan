import os
import httpx
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

class FishAudioClient:
    """Client for generating and cloning speech using Fish Audio API."""

    def __init__(self):
        """Initializes the Fish Audio client with environment variables."""
        self.api_key = os.getenv("FISH_AUDIO_API_KEY")
        self.vi_reference_id = os.getenv("FISH_AUDIO_VI_REFERENCE_ID")
        self.en_reference_id = os.getenv("FISH_AUDIO_EN_REFERENCE_ID")
        
        if not self.api_key:
            logger.warning("FISH_AUDIO_API_KEY not found in environment variables.")
            
        self.base_url = "https://api.fish.audio"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def synthesize(self, text: str, language: str, output_path: str) -> str:
        """
        Synthesizes speech from text using Fish Audio.

        Args:
            text (str): The text to synthesize.
            language (str): Language code ('vi' or 'en').
            output_path (str): The path to save the audio file.

        Returns:
            str: The absolute path to the generated audio file.
        """
        logger.info(f"Synthesizing text with Fish Audio ({language}) -> {output_path}")
        
        reference_id = self.vi_reference_id if language == 'vi' else self.en_reference_id
        
        payload = {
            "text": text,
            "format": "wav",
        }
        
        if reference_id:
            payload["reference_id"] = reference_id
            
        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1/tts",
                    headers=self.headers,
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                
                with open(path, "wb") as f:
                    f.write(response.content)
                    
            logger.success(f"Successfully generated Fish Audio: {output_path}")
            return str(path.absolute())
        except Exception as e:
            logger.error(f"Failed to synthesize with Fish Audio: {e}")
            raise

    async def clone_voice(self, audio_file_path: str, name: str, description: str = "") -> str:
        """
        Uploads an audio file to clone a voice.

        Args:
            audio_file_path (str): Path to the reference audio.
            name (str): Name for the cloned voice.
            description (str, optional): Description for the voice.

        Returns:
            str: The reference_id of the cloned voice.
        """
        logger.info(f"Cloning voice '{name}' from {audio_file_path}")
        
        try:
            path = Path(audio_file_path)
            if not path.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
                
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            async with httpx.AsyncClient() as client:
                with open(path, "rb") as f:
                    files = {"audio": (path.name, f, "audio/wav")}
                    data = {"name": name, "description": description}
                    
                    response = await client.post(
                        f"{self.base_url}/v1/models",
                        headers=headers,
                        data=data,
                        files=files,
                        timeout=120.0
                    )
                    response.raise_for_status()
                    
                    result = response.json()
                    reference_id = result.get("_id")
                    
                    logger.success(f"Voice cloned successfully. Reference ID: {reference_id}")
                    return reference_id
        except Exception as e:
            logger.error(f"Failed to clone voice: {e}")
            raise
