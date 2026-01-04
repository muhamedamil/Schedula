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
import urllib.request
import asyncio
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import WebSocket, WebSocketDisconnect, Query

from app.state import ConversationState
from app.workflow import run_step
from app.stt.whisper import WhisperSTTService, STTError
from app.tts.kokoro import KokoroTTSService, TTSError

logger = logging.getLogger(__name__)

# In-memory conversation store
user_states: Dict[str, ConversationState] = {}
_executor = ThreadPoolExecutor(max_workers=2)


def _fetch_google_user_info(access_token: str) -> Optional[dict]:
    """Fetch user info from Google API."""
    try:
        logger.info(f"Validating token starting with: {access_token[:10]}...")
        url = "https://www.googleapis.com/oauth2/v3/userinfo"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "VoiceSchedulingAgent/1.0",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        logger.error(f"Google API Error {e.code}: {e.reason} - Body: {error_body}")
        return None
    except Exception as e:
        logger.error(f"Failed to fetch Google user info: {e}")
        return None


async def websocket_endpoint(
    websocket: WebSocket, token: Optional[str] = Query(None)  # Receive token from URL
):
    """Main WebSocket endpoint for voice interaction."""
    await websocket.accept()
    user_id = str(id(websocket))
    logger.info("WebSocket client connected: %s", user_id)

    # Initialize conversation state
    state = ConversationState()

    # Handle initial authentication
    if token:
        logger.info("Found token in connection params")

        # Validate token by fetching user info
        loop = asyncio.get_running_loop()
        user_info = await loop.run_in_executor(
            _executor, _fetch_google_user_info, token
        )

        if user_info:
            # Token is valid
            state.google_access_token = token
            if user_info.get("given_name"):
                state.name = user_info.get("given_name")
                logger.info("Authenticated as: %s", state.name)
                # We don't change step to ASK_DATETIME here, we let start_node handle it
                # But the state now has the name!
        else:
            logger.warning("Provided token was invalid or expired - ignoring")
            try:
                await websocket.send_json({"type": "auth_error"})
            except Exception:
                logger.warning("Could not send auth_error (client likely disconnected)")

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

    except (WebSocketDisconnect, RuntimeError):
        logger.info("Client disconnected during startup")
        return
    except Exception:
        logger.exception("Failed to send initial greeting")
        # Try to send error if possible, but ignore failure
        try:
            state.system_message = "Sorry, something went wrong."
            await websocket.send_json(
                {
                    "text": state.system_message,
                    "audio_b64": None,
                    "step": state.step,
                }
            )
        except Exception:
            pass

    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)

            msg_type = data.get("type")
            payload = data.get("payload")
            user_text: Optional[str] = None

            # ---------------- Authentication ---------------- #
            if msg_type == "auth":
                # Frontend sends Google OAuth token
                google_token = (
                    payload.get("google_token") if isinstance(payload, dict) else None
                )
                if google_token:
                    state.google_access_token = google_token
                    user_states[user_id] = state
                    logger.info(
                        "Google access token received and stored for user %s", user_id
                    )
                    await websocket.send_json({"status": "authenticated"})
                else:
                    logger.warning("Auth message received but no google_token found")
                    await websocket.send_json({"error": "No token provided"})
                continue

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
