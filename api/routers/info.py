import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Response
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

router = APIRouter()

# Determine the project root relative to this file's location
# Adjust depth as necessary if file structure changes
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOW_REGISTRY_PATH = PROJECT_ROOT / "backend" / "src" / "registries" / "workflows"

@router.options("/workflows/")
async def workflow_options(response: Response):
    """Handle OPTIONS preflight requests for CORS."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    return {"detail": "OK"}

@router.get("/workflows/", tags=["info"], summary="List available workflow IDs")
async def list_workflows(response: Response):
    """Reads the workflow registry directory and returns a list of available workflow IDs."""
    # Add CORS headers directly to the response
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    
    if not WORKFLOW_REGISTRY_PATH.is_dir():
        raise HTTPException(status_code=500, detail=f"Workflow registry directory not found: {WORKFLOW_REGISTRY_PATH}")

    try:
        workflow_files = WORKFLOW_REGISTRY_PATH.glob("*.json")
        workflow_ids = sorted([f.stem for f in workflow_files if f.is_file()])
        return {"workflows": workflow_ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading workflow registry: {e}")
