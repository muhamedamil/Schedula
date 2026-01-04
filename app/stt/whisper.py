import asyncio
import io
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

from app.config import settings
from app.utils.logger import setup_logging  

logger = setup_logging(__name__)



class STTError(Exception):
    pass


class WhisperSTTService:
    """
    Production-grade Speech-to-Text (STT) service built on FasterWhisper.

    This service provides asynchronous, non-blocking transcription of
    short to medium-length audio inputs using a locally hosted Whisper model.
    
    Responsibilities:
    - Validate audio input format.
    - Perform speech-to-text transcription.
    - Surface clear, domain-specific errors.

    Non-goals:
    - Audio capture (handled by browser/client).
    - Streaming or partial transcription (can be added later).
    - Audio preprocessing or resampling.

    Intended usage:
        stt = WhisperSTTService()
        text = await stt.transcribe(audio_bytes)
    """

    _model: Optional[WhisperModel] = None
    _executor = ThreadPoolExecutor(max_workers=2)

    def __init__(self):
        if WhisperSTTService._model is None:
            logger.info("Loading Whisper model: %s", settings.WHISPER_MODEL)
            WhisperSTTService._model = WhisperModel(
                settings.WHISPER_MODEL,
                device="auto",
                compute_type="int8",
            )

        self.model = WhisperSTTService._model

    async def transcribe(self, audio_bytes: bytes) -> str:
        """
        Transcribe WAV audio bytes to text.
        """
        if not audio_bytes:
            raise STTError("Empty audio input")

        loop = asyncio.get_running_loop()

        try:
            text = await loop.run_in_executor(
                self._executor,
                self._sync_transcribe,
                audio_bytes,
            )
            return text
        except Exception as e:
            logger.exception("STT transcription failed")
            raise STTError(str(e)) from e

    def _sync_transcribe(self, audio_bytes: bytes) -> str:
        """
        Blocking whisper call (runs in thread).
        """
        audio_np, sr = sf.read(io.BytesIO(audio_bytes))
        if sr != 16000:
            raise STTError(f"Expected 16kHz audio, got {sr}")

        segments, _ = self.model.transcribe(
            audio_np,
            language=settings.WHISPER_LANGUAGE,
            vad_filter=True,
        )

        text = " ".join(seg.text.strip() for seg in segments)
        if not text:
            raise STTError("Empty transcription result")

        return text
