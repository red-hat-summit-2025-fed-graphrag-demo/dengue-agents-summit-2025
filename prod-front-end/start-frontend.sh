#!/bin/bash

# Navigate to the directory containing this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd $SCRIPT_DIR

# Start the Next.js development server
echo "Starting Next.js chat frontend for WebSocket testing..."
echo "Connect to http://localhost:3000 in your browser once the server is running."
npm run dev -- --port 3000
