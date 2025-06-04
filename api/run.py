#!/usr/bin/env python
"""
Run script for the Dengue Agents API.

This script starts the FastAPI application using uvicorn.
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("api.run")

def main():
    """Run the FastAPI application."""
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    logger.info(f"Starting API server on {host}:{port}")
    
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
    )

if __name__ == "__main__":
    main()