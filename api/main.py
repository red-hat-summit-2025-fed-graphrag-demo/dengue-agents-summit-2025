"""
Main FastAPI application for the Dengue Agents API.
"""
import os
import sys
import logging
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from typing import Dict, Any, List, Optional
import json
import uuid
from datetime import datetime
import traceback
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# --- Add backend directory to sys.path ---
# Calculate the project root directory (assuming api/main.py is one level down)
# Adjust if the file structure changes
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
    print(f"[SysPath] Added {BACKEND_DIR} to sys.path")
# -----------------------------------------

# Configure logging
log_level = logging.INFO
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# --- Basic Console Logging Setup (for general logs) ---
logging.basicConfig(level=log_level, format=log_format)

# --- File Handler for Structured Workflow Step Logs ---
# Reverted - removing file handler setup
# log_file = "workflow_trace.log"
# step_logger = logging.getLogger("workflow.step")
# step_logger.setLevel(log_level)
# step_logger.propagate = False
# file_handler = logging.FileHandler(log_file, mode='a')
# json_formatter = logging.Formatter('%(message)s')
# file_handler.setFormatter(json_formatter)
# step_logger.addHandler(file_handler)
# ----------------------------------------------------

logger = logging.getLogger("api") # Keep this for general API logging

# Import routers
from api.routers import ws, info

# Create FastAPI application
app = FastAPI(
    title="Dengue Agents API",
    description="""
    API for the Dengue Agents system
    
    ## ⚠️ IMPORTANT: WebSocket API Documentation
    
    **This API primarily uses WebSockets for real-time communication.**
    
    For complete WebSocket API documentation, please visit the [AsyncAPI Documentation](/asyncapi-docs) 
    which provides detailed information about the message formats and WebSocket endpoints.
    
    ## WebSocket Endpoints
    
    * `/ws/workflow/{workflow_name}`: WebSocket endpoint for executing a specific workflow
      * Receives: JSON with `{"message": "user prompt", "metadata": { ... }}`
      * Sends: Various message types including connected, stream updates, and final results
    
    * `/ws/agent/{agent_id}`: WebSocket endpoint for interacting with a specific agent
      * Receives: JSON with `{"message": "content"}` or plain text
      * Sends: Agent responses
    """,
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow requests from any origin
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Allow specific methods
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],  # Allow specific headers
    expose_headers=["Content-Length"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Include routers
app.include_router(ws.router)
app.include_router(info.router, prefix="/api/v1", tags=["info"])

# Mount static files directory
app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")

# Serve AsyncAPI YAML definition
@app.get("/asyncapi.yaml", tags=["docs"], summary="AsyncAPI specification")
async def get_asyncapi_spec():
    """Return the AsyncAPI specification YAML file."""
    return FileResponse(Path(__file__).resolve().parent / "asyncapi.yaml")

# Serve AsyncAPI documentation UI
@app.get("/asyncapi-docs", tags=["docs"], summary="AsyncAPI documentation UI")
async def get_asyncapi_docs():
    """Return the AsyncAPI documentation UI."""
    return FileResponse(Path(__file__).resolve().parent / "static" / "asyncapi.html")

@app.get("/", tags=["root"], summary="Root endpoint providing basic API info")
async def root():
    """Root endpoint that returns basic API information."""
    return {
        "name": "Dengue Agents API",
        "version": "0.1.0",
        "description": "API for the Dengue Agents system",
        "status": "running",
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )

# Run the application with uvicorn if executed directly
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    uvicorn.run("api.main:app", host=host, port=port, reload=True)