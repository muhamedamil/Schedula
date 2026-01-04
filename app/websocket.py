"""
websocket.py

WebSocket server for Voice Assistant.

Responsibilities:
- Accept user audio/text input from client
- Convert audio to text (STT)
- Run LangGraph workflow for conversation state
- Convert system messages to speech (TTS)
- Send back text + audio to client
"""

import asyncio
import base64
import json
from websockets import serve, WebSocketServerProtocol
from typing import Dict

from app.state import ConversationState
from app.workflow import run_step
from app.tts.kokoro import KokoroTTSService
from app.stt.whisper import WhisperSTTService
from app.utils.logger import setup_logging  


logger = setup_logging(__name__)


# ---------------- In-Memory State Store ---------------- #
# For this assignment, simple dict keyed by websocket object
user_states: Dict[str, ConversationState] = {}

# ---------------- WebSocket Handler ---------------- #
async def handle_client(websocket: WebSocketServerProtocol):
    user_id = str(websocket.remote_address)
    logger.info("Client connected: %s", user_id)

    # Initialize user state
    if user_id not in user_states:
        user_states[user_id] = ConversationState()

    try:
        async for message in websocket:
            """
            Expecting message as JSON:
            {
                "type": "text" | "audio",
                "payload": "..."  # text or base64 audio
            }
            """
            try:
                data = json.loads(message)
                msg_type = data.get("type")
                payload = data.get("payload")
            except Exception as e:
                logger.warning("Invalid message format: %s", e)
                continue

            # ---------------- Speech-to-Text ---------------- #
            user_text = ""
            if msg_type == "audio":
                try:
                    audio_bytes = base64.b64decode(payload)
                    user_text = await WhisperSTTService.transcribe(audio_bytes)
                    logger.info("STT recognized: %s", user_text)
                except Exception as e:
                    logger.exception("STT failed: %s", e)
                    await websocket.send(
                        json.dumps({"error": "STT failed"})
                    )
                    continue
            elif msg_type == "text":
                user_text = payload
            else:
                await websocket.send(
                    json.dumps({"error": "Unknown message type"})
                )
                continue

            # ---------------- Update Conversation State ---------------- #
            state = user_states[user_id]
            state.last_user_message = user_text

            # Run workflow node
            try:
                state = await run_step(state)
            except Exception as e:
                logger.exception("Workflow error: %s", e)
                state.system_message = "Oops! Something went wrong."
                state.step = "START"

            user_states[user_id] = state

            # ---------------- Text-to-Speech ---------------- #
            audio_b64 = None
            if state.system_message:
                try:
                    audio_bytes = await KokoroTTSService.synthesize(state.system_message)
                    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                except Exception as e:
                    logger.exception("TTS failed: %s", e)

            # ---------------- Send Response ---------------- #
            response = {
                "text": state.system_message,
                "audio_b64": audio_b64,
                "step": state.step,
            }
            await websocket.send(json.dumps(response))

    except Exception as e:
        logger.exception("WebSocket error for %s: %s", user_id, e)
    finally:
        logger.info("Client disconnected: %s", user_id)
        if user_id in user_states:
            del user_states[user_id]

# ---------------- Server Entry Point ---------------- #
async def main():
    async with serve(handle_client, "0.0.0.0", 8765):
        logger.info("WebSocket server started on port 8765")
        await asyncio.Future()  # run forever

