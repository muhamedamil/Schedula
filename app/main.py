"""
main.py

Entry point for the Voice Assistant application.
Serves frontend and runs existing WebSocket server.
"""

import asyncio
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.websocket import main as websocket_main  
from app.utils.logger import setup_logging  


logger = setup_logging(__name__)

# ---------------- FastAPI Setup ---------------- #
app = FastAPI(title="Voice Assistant")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Serve Frontend ---------------- #
FRONTEND_PATH = Path(__file__).parent.parent / "frontend" / "index.html"

@app.get("/")
async def serve_index():
    return FileResponse(FRONTEND_PATH)

# ---------------- Startup & Shutdown Events ---------------- #
@app.on_event("startup")
async def startup_event():
    logger.info("Voice Assistant FastAPI server starting up...")
    # Start WebSocket server in background
    asyncio.create_task(websocket_main())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Voice Assistant FastAPI server shutting down...")

# ---------------- Run via Uvicorn ---------------- #
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Voice Assistant server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
