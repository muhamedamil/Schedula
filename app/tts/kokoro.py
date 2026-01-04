"""
Kokoro Text-to-Speech Service
"""

import asyncio
import base64
from io import BytesIO
from typing import Optional

import numpy as np
import soundfile as sf
from kokoro import KPipeline

from app.config import settings
from app.utils.logger import setup_logging  

logger = setup_logging(__name__)

class TTSError(Exception):
    """
    Base exception for TTS-related failures.
    Raised when speech synthesis fails or times out.
    """
    pass


class KokoroTTSService:
    """
    This service:
    - Converts text → speech
    - Returns base64 WAV audio
    - Does NOT perform playback
    """

    def __init__(self):
        self.voice = settings.TTS_VOICE
        self.sample_rate = 24000

        # Kokoro pipeline is heavy → load once
        self._pipeline = KPipeline(lang_code="a")

    # ---------------- Internal blocking call ---------------- #

    def _synthesize_blocking(self, text: str) -> bytes:
        """
        Blocking Kokoro synthesis.
        Must run in executor.
        """
        audio_chunks = []

        generator = self._pipeline(text, voice=self.voice)
        for _, _, chunk in generator:
            if chunk is not None:
                audio_chunks.append(chunk)

        if not audio_chunks:
            raise TTSError("Kokoro returned empty audio")

        full_audio = np.concatenate(audio_chunks)

        with BytesIO() as buf:
            sf.write(buf, full_audio, self.sample_rate, format="WAV")
            return buf.getvalue()

    # ---------------- Public async API ---------------- #

    async def synthesize(
        self,
        text: str,
        timeout: float = 8.0,
        retries: int = 2,
    ) -> str:
        """
        Convert text to base64-encoded WAV audio.

        Returns:
            base64 string
        """
        if not text or not text.strip():
            return ""

        loop = asyncio.get_running_loop()

        for attempt in range(1, retries + 1):
            try:
                wav_bytes = await asyncio.wait_for(
                    loop.run_in_executor(
                        None, self._synthesize_blocking, text
                    ),
                    timeout=timeout,
                )

                return base64.b64encode(wav_bytes).decode("utf-8")

            except asyncio.TimeoutError:
                logger.warning("TTS timeout (attempt %s)", attempt)

            except Exception as e:
                logger.exception("TTS failed (attempt %s): %s", attempt, e)

        raise TTSError("TTS synthesis failed after retries")
