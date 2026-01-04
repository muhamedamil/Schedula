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

# ---------------- Logging ---------------- #
setup_logging()

app = FastAPI(title="Voice Scheduling Assistant")

# ---------------- Middleware ---------------- #
# Allow all origins (for dev purposes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Frontend ---------------- #
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the main frontend HTML page."""
    return (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")

# ---------------- WebSocket Route ---------------- #
@app.websocket("/ws")
async def ws_route(websocket: WebSocket):
    """Forward WebSocket connections to websocket.py handler."""
    await websocket_endpoint(websocket)
