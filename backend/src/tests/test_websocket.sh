#!/bin/bash
# Test script for the agent WebSocket API using websocat

# Check if websocat is installed
if ! command -v websocat &> /dev/null; then
    echo "Error: websocat is not installed. Please install it to run this test."
    exit 1
fi

# Configuration
AGENT_ID="simple_test_agent"
WS_URL="ws://localhost:8000/ws/agent/$AGENT_ID"
TEST_MESSAGE="Hello, can you introduce yourself and explain how the agent system works?"

# Display test info
echo "Testing WebSocket connection to $WS_URL"
echo "Agent ID: $AGENT_ID"
echo "Test message: $TEST_MESSAGE"
echo ""
echo "Press Ctrl+C to exit after receiving the response"
echo "======================================================="
echo ""

# Run websocat
echo $TEST_MESSAGE | websocat $WS_URL