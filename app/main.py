"""
main.py

FastAPI entry point for the Voice Assistant.
Serves frontend, handles WebSocket, and applies middleware.
"""

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import asyncio

from app.websocket import websocket_endpoint
from app.utils.logger import setup_logging
from app.tts.kokoro import KokoroTTSService
from app.stt.whisper import WhisperSTTService

# Logging
setup_logging()

app = FastAPI(title="Voice Scheduling Assistant")


# Startup: Preload Models
@app.on_event("startup")
async def startup_event():
    """Preload heavy models on server startup to speed up first requests."""
    import logging

    logger = logging.getLogger(__name__)

    logger.info("Preloading TTS model (Kokoro)...")
    KokoroTTSService._init_pipeline()

    logger.info("Preloading STT model (Whisper)...")
    WhisperSTTService._load_model()

    logger.info("All models preloaded successfully")


# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Frontend
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


from app.config import settings


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """
    Serve the main frontend HTML page.
    Injects configuration from settings (e.g. Google Client ID) into the HTML.
    """
    html_content = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")

    # Inject Google Client ID if present
    if settings.GOOGLE_CLIENT_ID:
        html_content = html_content.replace(
            "YOUR_GOOGLE_CLIENT_ID_HERE", settings.GOOGLE_CLIENT_ID
        )

    return html_content


# WebSocket Route
@app.websocket("/ws")
async def ws_route(websocket: WebSocket, token: str = None):
    """Forward WebSocket connections to websocket.py handler."""
    await websocket_endpoint(websocket, token)
