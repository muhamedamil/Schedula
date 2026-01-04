"""
websocket.py

FastAPI WebSocket handler for the Voice Assistant.

Responsibilities:
- Receive audio/text from client
- Perform STT if audio
- Run LangGraph workflow
- Convert system message to TTS
- Send text + audio back to client

Error handling:
- STT/TTS/Workflow errors are caught and returned to frontend without crashing
"""

import base64
import json
import logging
from typing import Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.state import ConversationState
from app.workflow import run_step
from app.stt.whisper import WhisperSTTService, STTError
from app.tts.kokoro import KokoroTTSService, TTSError

logger = logging.getLogger(__name__)

# In-memory conversation store
user_states: Dict[str, ConversationState] = {}


async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for voice interaction."""
    await websocket.accept()
    user_id = str(id(websocket))
    logger.info("WebSocket client connected: %s", user_id)

    # Initialize conversation state
    state = ConversationState()
    user_states[user_id] = state

    # Run START node immediately to set the greeting before any user input
    try:
        initial_state_dict = await run_step(state)
        if isinstance(initial_state_dict, dict):
            state = ConversationState(**initial_state_dict)
        else:
            state = initial_state_dict
        user_states[user_id] = state

        # Generate TTS for initial greeting
        audio_b64: Optional[str] = None
        if state.system_message:
            try:
                audio_b64 = await KokoroTTSService.synthesize(state.system_message)
            except TTSError as e:
                logger.error("TTS generation failed for initial greeting: %s", e)
                audio_b64 = None

        # Send initial greeting to client
        await websocket.send_json(
            {
                "text": state.system_message or "",
                "audio_b64": audio_b64,
                "step": state.step,
            }
        )
        logger.info("Sent initial greeting to user %s", user_id)

    except Exception:
        logger.exception("Failed to send initial greeting")
        state.system_message = "Sorry, something went wrong."
        await websocket.send_json(
            {
                "text": state.system_message,
                "audio_b64": None,
                "step": state.step,
            }
        )

    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)

            msg_type = data.get("type")
            payload = data.get("payload")
            user_text: Optional[str] = None

            # ---------------- STT ---------------- #
            if msg_type == "audio":
                try:
                    audio_bytes = base64.b64decode(payload)
                    user_text = await WhisperSTTService.transcribe(audio_bytes)
                    logger.info("STT output: %s", user_text)
                except STTError as e:
                    logger.warning("STT failed: %s", e)
                    await websocket.send_json(
                        {"error": f"Audio transcription failed: {str(e)}"}
                    )
                    continue
                except Exception as e:
                    logger.exception("Unexpected error during STT")
                    await websocket.send_json(
                        {"error": "Unexpected server error during transcription"}
                    )
                    continue

            elif msg_type == "text":
                user_text = payload

            else:
                await websocket.send_json({"error": "Invalid message type"})
                continue

            # ---------------- LangGraph Workflow ---------------- #
            state.last_user_message = user_text
            logger.info(
                "[WEBSOCKET] Current state.step before run_step: %s", state.step
            )
            logger.info(
                "[WEBSOCKET] Calling run_step with last_user_message: %s", user_text
            )
            updated_state_dict: Optional[dict] = None

            try:
                # Ensure we pass a plain dict to LangGraph
                updated_state_dict = await run_step(state)
                logger.info(
                    "[WEBSOCKET] run_step completed. Result type: %s",
                    type(updated_state_dict),
                )
                if isinstance(updated_state_dict, dict):
                    state = ConversationState(**updated_state_dict)
                else:
                    # Fallback if workflow returns a model
                    state = updated_state_dict
                logger.info("[WEBSOCKET] New state.step after run_step: %s", state.step)
                logger.info(
                    "[WEBSOCKET] New state.system_message: %s", state.system_message
                )

            except Exception:
                logger.exception("LangGraph execution failed")
                # Always fallback safely
                state.system_message = "Sorry, something went wrong."

            # Save updated state
            user_states[user_id] = state

            # ---------------- TTS ---------------- #
            audio_b64: Optional[str] = None
            if state.system_message:
                try:
                    audio_b64 = await KokoroTTSService.synthesize(state.system_message)
                except TTSError as e:
                    logger.error("TTS generation failed: %s", e)
                    audio_b64 = None

            # ---------------- Response ---------------- #
            await websocket.send_json(
                {
                    "text": state.system_message or "",
                    "audio_b64": audio_b64,
                    "step": state.step,
                }
            )

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected: %s", user_id)
        user_states.pop(user_id, None)
