"""VieNeu-TTS Client for Vietnamese On-Device CPU speech synthesis."""
import asyncio
import os
import threading
from pathlib import Path
from typing import Optional, Union, List, Tuple
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# Task 5.5: Singleton cache for VieNeu-TTS models across requests and instances
_SHARED_TTS_ENGINES: dict = {}
_CLASS_LOCK = threading.Lock()


class VieNeuClient:
    """Client for generating Vietnamese speech on-device CPU using VieNeu-TTS (ONNX int8)."""

    def __init__(
        self,
        precision: str = "int8",
        voice_dir: Optional[Union[str, Path]] = None
    ):
        """
        Initializes the VieNeu TTS Client.

        Args:
            precision (str): Model quantization precision ('int8' or 'fp32'). Defaults to 'int8'.
            voice_dir (Union[str, Path], optional): Directory containing sample voices for cloning.
                                                    Defaults to 'assets/voices'.
        """
        self.precision = precision
        self.voice_dir = Path(voice_dir).resolve() if voice_dir else Path("assets/voices").resolve()
        self._tts = None
        self._init_lock = threading.Lock()

    def _get_tts(self):
        """Lazy initialization of Vieneu engine on-device CPU with process-wide singleton cache."""
        key = self.precision
        if key not in _SHARED_TTS_ENGINES:
            with _CLASS_LOCK:
                if key not in _SHARED_TTS_ENGINES:
                    try:
                        from vieneu import Vieneu
                        logger.info(f"Initializing VieNeu-TTS engine (precision={self.precision}, device=CPU)...")
                        _SHARED_TTS_ENGINES[key] = Vieneu(precision=self.precision)
                        logger.success("VieNeu-TTS engine initialized successfully (cached in singleton).")
                    except ImportError as ie:
                        logger.error("vieneu package is not installed. Please run: pip install vieneu soundfile")
                        raise RuntimeError(f"VieNeu package missing: {ie}") from ie
                    except Exception as e:
                        logger.error(f"Failed to initialize VieNeu-TTS: {e}")
                        raise RuntimeError(f"VieNeu initialization failed: {e}") from e
        self._tts = _SHARED_TTS_ENGINES[key]
        return self._tts

    def detect_voice_sample(self) -> Optional[str]:
        """
        Scans voice directory (assets/voices/) for reference audio samples (.wav or .mp3)
        to enable natural voice cloning.

        Returns:
            Optional[str]: Absolute path to the first valid voice sample, or None if none found.
        """
        if not self.voice_dir.exists() or not self.voice_dir.is_dir():
            return None

        # Search for .wav and .mp3 files
        for ext in ("*.wav", "*.mp3", "*.WAV", "*.MP3"):
            samples = list(self.voice_dir.glob(ext))
            if samples:
                sample_path = str(samples[0].resolve())
                logger.info(f"VieNeu: Detected reference voice sample for cloning: {sample_path}")
                return sample_path

        return None

    def _sync_synthesize(
        self,
        text: str,
        output_path: str,
        ref_audio: Optional[str] = None,
        voice: Optional[str] = None
    ) -> str:
        """
        Synchronous CPU inference worker.

        Args:
            text (str): Vietnamese text to synthesize.
            output_path (str): Destination audio path.
            ref_audio (Optional[str]): Reference audio path for voice cloning.
            voice (Optional[str]): Built-in preset voice name (e.g. 'Thiện Minh', 'Trúc Ly').

        Returns:
            str: Absolute path of written audio file.
        """
        tts = self._get_tts()
        out_path = Path(output_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"VieNeu: Starting on-device CPU synthesis for '{text[:40]}...' (ref={ref_audio}, voice={voice})")

        audio_data = None
        if ref_audio and os.path.exists(ref_audio):
            # Voice cloning mode with reference audio
            logger.info(f"VieNeu: Synthesizing with reference voice cloning: {ref_audio}")
            try:
                audio_data = tts.infer(text=text, ref_audio=ref_audio, denoise=True)
            except TypeError:
                audio_data = tts.infer(text=text, ref_audio=ref_audio)
        else:
            # Preset voice (defaults to Minh Quân if unspecified)
            preset = voice if voice and voice != "default" else "Minh Quân"
            logger.info(f"VieNeu: Synthesizing with preset voice '{preset}'")
            try:
                audio_data = tts.infer(text=text, voice=preset)
            except TypeError:
                try:
                    audio_data = tts.infer(text=text, voice="Minh Quân")
                except TypeError:
                    audio_data = tts.infer(text=text)

        # Save audio output with resilient fallbacks
        saved = False

        # 1. Try built-in tts.save()
        if hasattr(tts, "save"):
            try:
                tts.save(audio_data, str(out_path))
                saved = True
            except Exception as e_save:
                logger.debug(f"tts.save() encountered: {e_save}, trying soundfile...")

        # 2. Try soundfile
        if not saved:
            try:
                import soundfile as sf
                samplerate = getattr(tts, "sample_rate", 24000)
                sf.write(str(out_path), audio_data, samplerate=samplerate)
                saved = True
            except Exception as e_sf:
                logger.debug(f"soundfile write failed: {e_sf}, trying scipy...")

        # 3. Try scipy.io.wavfile
        if not saved:
            try:
                from scipy.io import wavfile
                import numpy as np
                samplerate = getattr(tts, "sample_rate", 24000)
                if hasattr(audio_data, "numpy"):
                    data = audio_data.numpy()
                else:
                    data = np.asarray(audio_data)
                wavfile.write(str(out_path), samplerate, data)
                saved = True
            except Exception as e_scipy:
                raise RuntimeError(f"Could not save generated audio to {out_path}: {e_scipy}")

        logger.success(f"VieNeu: Generated audio successfully at: {out_path}")
        return str(out_path)

    async def synthesize(
        self,
        text: str,
        language: str = "vi",
        output_path: str = "",
        ref_audio: Optional[str] = None,
        voice: Optional[str] = None
    ) -> str:
        """
        Synthesizes Vietnamese speech asynchronously using thread executor
        to keep the asyncio event loop responsive.

        Args:
            text (str): Vietnamese text to synthesize.
            language (str): Language code (default 'vi').
            output_path (str): File destination path for generated audio.
            ref_audio (Optional[str]): Explicit reference audio for voice cloning.
                                       If None, automatically checks assets/voices/.
            voice (Optional[str]): Built-in preset voice name.

        Returns:
            str: Path to the generated audio file.
        """
        if not output_path:
            clean_hash = abs(hash(text))
            output_path = f"output/tts_vieneu_{clean_hash}.wav"

        out_path = Path(output_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        target_ref = ref_audio or (self.detect_voice_sample() if not voice or voice == "default" else None)
        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(
            None,
            self._sync_synthesize,
            text,
            str(out_path),
            target_ref,
            voice
        )

    def list_preset_voices(self) -> List[Tuple[str, str]]:
        """Returns list of built-in preset voices (display_name, voice_id)."""
        try:
            tts = self._get_tts()
            if hasattr(tts, "list_preset_voices"):
                return tts.list_preset_voices()
        except Exception as e:
            logger.warning(f"Could not retrieve preset voices from vieneu: {e}")
        return [
            ("Minh Quân (Chuẩn)", "Minh Quân"),
            ("⭐ Thiện Minh — Nam · Bắc · Kể chuyện", "Thiện Minh"),
            ("⭐ Trúc Ly — Nữ · Bắc · Tự nhiên", "Trúc Ly"),
            ("⭐ Mai Anh — Nữ · Bắc · Tin tức", "Mai Anh"),
            ("⭐ Thái Sơn — Nam · Nam · Kể chuyện", "Thái Sơn"),
            ("⭐ Thùy Dung — Nữ · Nam · Tin tức", "Thùy Dung"),
            ("⭐ Quang Sơn — Nam · Trung · Tự nhiên", "Quang Sơn")
        ]

    def is_available(self) -> bool:
        """Checks if the vieneu library is installed and importable."""
        try:
            import vieneu
            return True
        except ImportError:
            return False
