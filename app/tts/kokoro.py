import logging
import asyncio
import base64
from io import BytesIO
from typing import Optional

import numpy as np
import soundfile as sf
from kokoro import KPipeline

from app.config import settings

logger = logging.getLogger(__name__)


class TTSError(Exception):
    """Base exception for TTS-related failures."""

    pass


class KokoroTTSService:
    """
    Class-level TTS service:
    - Converts text → speech
    - Returns base64 WAV audio
    - Does NOT perform playback
    """

    _pipeline: Optional[KPipeline] = None
    _voice: Optional[str] = None
    _sample_rate: int = 24000

    # ---------------- Initialization ---------------- #
    @classmethod
    def _init_pipeline(cls):
        """Lazy-load the heavy Kokoro pipeline once."""
        if cls._pipeline is None:
            cls._voice = settings.TTS_VOICE
            cls._pipeline = KPipeline(lang_code="a")
            logger.info("Kokoro TTS pipeline loaded with voice '%s'", cls._voice)
        return cls._pipeline

    # ---------------- Internal blocking call ---------------- #
    @classmethod
    def _synthesize_blocking(cls, text: str) -> bytes:
        """
        Blocking Kokoro synthesis.
        Must run in executor.
        """
        if not text.strip():
            raise TTSError("Empty text for TTS")

        cls._init_pipeline()

        audio_chunks = []
        generator = cls._pipeline(text, voice=cls._voice)

        for _, _, chunk in generator:
            if chunk is not None:
                audio_chunks.append(chunk)

        if not audio_chunks:
            raise TTSError("Kokoro returned empty audio")

        full_audio = np.concatenate(audio_chunks)

        with BytesIO() as buf:
            sf.write(buf, full_audio, cls._sample_rate, format="WAV")
            return buf.getvalue()

    # ---------------- Public async API ---------------- #
    @classmethod
    async def synthesize(
        cls,
        text: str,
        timeout: float = 25.0,
        retries: int = 2,
    ) -> str:
        """
        Convert text to base64-encoded WAV audio asynchronously.

        Returns:
            base64 string
        """
        if not text or not text.strip():
            return ""

        loop = asyncio.get_running_loop()

        for attempt in range(1, retries + 1):
            try:
                wav_bytes = await asyncio.wait_for(
                    loop.run_in_executor(None, cls._synthesize_blocking, text),
                    timeout=timeout,
                )
                return base64.b64encode(wav_bytes).decode("utf-8")

            except asyncio.TimeoutError:
                logger.warning("TTS timeout (attempt %s)", attempt)

            except Exception as e:
                logger.exception("TTS failed (attempt %s): %s", attempt, e)

        raise TTSError("TTS synthesis failed after retries")
