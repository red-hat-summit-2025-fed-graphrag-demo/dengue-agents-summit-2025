#!/usr/bin/env python
"""
Test script for the agent WebSocket API.

This script sends a message to the agent WebSocket endpoint and prints the response.
It uses the websocat command-line tool to establish a WebSocket connection.
"""
import os
import sys
import json
import asyncio
import logging
import subprocess
from dotenv import load_dotenv

# Add parent directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("test_websocket")

# Load environment variables
load_dotenv()

async def test_websocket_agent():
    """Test the agent WebSocket API using websocat."""
    # Configure websocat command
    agent_id = "simple_test_agent"
    ws_url = f"ws://localhost:8000/ws/agent/{agent_id}"
    test_message = "Hello, can you discuss the variety of house cat breeds?"
    
    # Check if websocat is installed
    try:
        subprocess.run(["which", "websocat"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        logger.error("websocat is not installed. Please install it to run this test.")
        return False
    
    logger.info(f"Testing WebSocket connection to {ws_url}")
    logger.info(f"Agent ID: {agent_id}")
    logger.info(f"Test message: {test_message}")
    
    # Run websocat command
    try:
        # Command to connect and send a message, then disconnect after receiving a response
        websocat_cmd = [
            "websocat", 
            # "-n1",  # Removed: This caused exit after first message (connection confirmation)
            "--text",
            ws_url
        ]
        
        # Start websocat process
        logger.info("Starting websocat process...")
        process = subprocess.Popen(
            websocat_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send the test message
        logger.info("Sending test message...")
        process.stdin.write(test_message + "\n")
        process.stdin.flush()
        
        # Read responses until we receive the actual agent response
        logger.info("Waiting for response...")
        while True:
            response = process.stdout.readline().strip()
            if not response:
                break
                
            # Parse the response
            try:
                response_data = json.loads(response)
                
                # Print connection message
                if response_data.get("type") == "connected":
                    logger.info(f"Connected: {response_data.get('message')}")
                
                # Print agent status updates
                elif response_data.get("type") == "agent_stream":
                    message_type = response_data.get("message_type")
                    if message_type == "agent_update":
                        logger.info(f"Agent update: {response_data.get('content')} - {response_data.get('data', {}).get('message', '')}")
                    elif message_type == "logs":
                        logger.info(f"Agent thinking: {str(response_data.get('data', ''))[:100]}...")
                
                # Print the final response
                elif response_data.get("type") == "response":
                    logger.info("\n" + "=" * 60)
                    logger.info(" AGENT RESPONSE FROM WEBSOCKET ".center(60, "="))
                    logger.info("=" * 60)
                    # Log the full response data, formatted as JSON
                    logger.info(json.dumps(response_data, indent=2))
                    logger.info("=" * 60 + "\n")
                    break
                
                # Handle errors
                elif response_data.get("type") == "error":
                    logger.error(f"Error: {response_data.get('message')}")
                    break
                    
            except json.JSONDecodeError:
                # Just print raw response if it's not valid JSON
                logger.info(f"Raw response: {response}")
        
        # Close the process
        process.stdin.close()
        process.terminate()
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing WebSocket: {str(e)}")
        return False

async def main():
    """Main test function."""
    logger.info("Testing WebSocket agent API...")
    success = await test_websocket_agent()
    
    if success:
        logger.info("WebSocket test completed successfully")
    else:
        logger.error("WebSocket test failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())