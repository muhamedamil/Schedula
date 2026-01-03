import pytest
from app.stt.whisper import WhisperSTTService, STTError

@pytest.mark.asyncio
async def test_transcribe_success(mocker):
    stt = WhisperSTTService()
    dummy_audio = b"\x00" * 32000  # simulate 2 seconds of silence @16kHz
    mocker.patch.object(stt, "_sync_transcribe", return_value="hello world")
    text = await stt.transcribe(dummy_audio)
    assert text == "hello world"

@pytest.mark.asyncio
async def test_transcribe_empty_audio():
    stt = WhisperSTTService()
    with pytest.raises(STTError):
        await stt.transcribe(b"")

@pytest.mark.asyncio
async def test_transcribe_internal_error(mocker):
    stt = WhisperSTTService()
    mocker.patch.object(stt, "_sync_transcribe", side_effect=Exception("oops"))
    with pytest.raises(STTError):
        await stt.transcribe(b"\x00" * 32000)
