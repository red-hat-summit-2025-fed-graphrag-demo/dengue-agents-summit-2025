#!/bin/bash

# Configuration
BACKEND_PORT=8000

# Get the directory of the script itself
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
# Go up one level to the project root
PROJECT_ROOT=$( cd -- "$SCRIPT_DIR/.." &> /dev/null && pwd )

# Define path to venv python
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python"

# Adjust this command if your backend starts differently
# Run uvicorn specifying the app location relative to the project root
BACKEND_CMD="$VENV_PYTHON -m uvicorn api.main:app --port $BACKEND_PORT"
FRONTEND_CMD="streamlit run app.py"

# Define relative paths from script location
BACKEND_DIR_RELATIVE="../api" # Still useful for display message
FRONTEND_DIR_RELATIVE="."

# --- Check and Start Backend ---
echo "Checking if backend port $BACKEND_PORT is in use..."
if lsof -Pi :$BACKEND_PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "Backend appears to be running on port $BACKEND_PORT."
else
    # Navigate to the backend directory relative to the script
    BACKEND_ABS_PATH="$(cd "$SCRIPT_DIR/$BACKEND_DIR_RELATIVE" && pwd)"
    echo "Backend not running. Starting backend server from project root targeting '$BACKEND_ABS_PATH/main.py'..."
    # Change to PROJECT ROOT before running uvicorn
    cd "$PROJECT_ROOT" || { echo "Failed to cd into project root '$PROJECT_ROOT'"; exit 1; }
    
    # Start backend in the background using the venv python
    echo "Running command in $PWD: $BACKEND_CMD"
    $BACKEND_CMD &    
    BACKEND_PID=$!
    echo "Backend started with PID $BACKEND_PID. Waiting a few seconds for it to initialize..."
    sleep 5 # Give the server a moment to start up

    # Optional: Check again if it actually started listening
    if ! lsof -Pi :$BACKEND_PORT -sTCP:LISTEN -t >/dev/null ; then
        echo "Error: Backend failed to start listening on port $BACKEND_PORT."
        # Optionally kill the process we tried to start
        # kill $BACKEND_PID
        exit 1
    fi
    echo "Backend is now listening on port $BACKEND_PORT."
fi