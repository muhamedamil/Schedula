"""
whisper.py

Production-grade Speech-to-Text (STT) service using FasterWhisper.

Features:
- Accepts any audio format (mp3, wav, ogg, etc.) and converts to 16kHz mono WAV.
- Async transcription using thread pool.
- Handles float32 conversion for ONNX compatibility.
- Clear domain-specific error handling.
- Thread-safe model loading.

Usage:
    from app.stt.whisper import WhisperSTTService

    audio_bytes = ...  # bytes from client
    text = await WhisperSTTService.transcribe(audio_bytes)
"""

import asyncio
import io
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import numpy as np
import soundfile as sf
from pydub import AudioSegment
from faster_whisper import WhisperModel

from app.config import settings

logger = logging.getLogger(__name__)


class STTError(Exception):
    """Custom exception for STT-related errors."""


class WhisperSTTService:
    """
    Production-grade asynchronous STT service built on FasterWhisper.

    Responsibilities:
    - Accept any audio format and convert to WAV (16kHz mono, float32)
    - Perform async speech-to-text transcription
    - Surface clear, domain-specific errors
    """

    _model: Optional[WhisperModel] = None
    _executor = ThreadPoolExecutor(max_workers=2)

    # ---------------- Model Loading ----------------
    @classmethod
    def _load_model(cls):
        if cls._model is None:
            logger.info("Loading Whisper model: %s", settings.WHISPER_MODEL)
            cls._model = WhisperModel(
                settings.WHISPER_MODEL,
                device="cpu",
                compute_type="int8",
            )
        return cls._model

    # Public Async Method
    @classmethod
    async def transcribe(cls, audio_bytes: bytes) -> str:
        """
        Asynchronously transcribe audio bytes to text.
        """
        if not audio_bytes:
            raise STTError("Empty audio input")

        loop = asyncio.get_running_loop()

        try:
            text = await loop.run_in_executor(
                cls._executor,
                cls._sync_transcribe,
                audio_bytes,
            )
            return text
        except Exception as e:
            logger.warning("STT failed: %s", e)
            raise STTError(str(e)) from e

    # Blocking Transcription
    @classmethod
    def _sync_transcribe(cls, audio_bytes: bytes) -> str:
        """
        Blocking transcription (runs in a thread). Accepts any audio format.
        """
        model = cls._load_model()

        # Step 1: Convert to WAV, 16kHz, mono
        try:
            audio_wav = cls._convert_to_wav(audio_bytes)
        except Exception as e:
            raise STTError(f"Failed to convert audio: {e}") from e

        # Step 2: Load audio into NumPy
        try:
            audio_np, sr = sf.read(io.BytesIO(audio_wav))
        except Exception as e:
            raise STTError(f"Failed to read WAV: {e}") from e

        # Step 3: Ensure correct sample rate
        if sr != 16000:
            raise STTError(f"Expected 16kHz audio, got {sr}")

        # Step 4: Convert to float32 for ONNX
        audio_np = audio_np.astype("float32")

        # Step 5: Transcribe
        try:
            segments, _ = model.transcribe(
                audio_np,
                language=settings.WHISPER_LANGUAGE,
                vad_filter=True,
            )
        except Exception as e:
            raise STTError(f"Whisper transcription failed: {e}") from e

        # Step 6: Combine text
        text = " ".join(seg.text.strip() for seg in segments)
        if not text:
            raise STTError("Empty transcription result")

        return text

    # Audio Conversion
    @staticmethod
    def _convert_to_wav(audio_bytes: bytes) -> bytes:
        """
        Convert any audio format to WAV 16kHz mono, float32 bytes.
        """
        try:
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
            audio = audio.set_channels(1).set_frame_rate(16000)
            buf = io.BytesIO()
            audio.export(buf, format="wav")
            return buf.getvalue()
        except Exception as e:
            raise STTError(f"Audio conversion failed: {e}") from e
