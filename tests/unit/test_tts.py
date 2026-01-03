import pytest
from app.tts.kokoro import KokoroTTSService, TTSError

@pytest.mark.asyncio
async def test_tts_success(mocker):
    tts = KokoroTTSService()
    mocker.patch.object(tts, "_synthesize_blocking", return_value=b"dummybytes")
    out = await tts.synthesize("Hello world")
    assert out != ""

@pytest.mark.asyncio
async def test_tts_empty_text():
    tts = KokoroTTSService()
    result = await tts.synthesize("")
    assert result == ""

@pytest.mark.asyncio
async def test_tts_error_wrapping(mocker):
    tts = KokoroTTSService()
    mocker.patch.object(tts, "_synthesize_blocking", side_effect=Exception("kokoro died"))
    with pytest.raises(TTSError):
        await tts.synthesize("Hello")
