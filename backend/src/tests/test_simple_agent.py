#!/usr/bin/env python
"""
Test script for the SimpleTestAgent.

This script demonstrates how to use the SimpleTestAgent with the prompt registry.
"""
import asyncio
import logging
import sys
import os
from dotenv import load_dotenv

# Add parent directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import necessary components
from src.agent_system.core.message import Message, MessageRole
from src.registries.agent_registry import AgentRegistry
from src.registries.prompt_registry import PromptRegistry

async def test_simple_agent():
    """Test the SimpleTestAgent using the registry system."""
    logger.info("Starting SimpleTestAgent test")
    
    # Check if environment variables are available
    instruct_key = os.environ.get("GRANITE_INSTRUCT_API_KEY", "")
    instruct_url = os.environ.get("GRANITE_INSTRUCT_URL", "")
    
    if not instruct_key or not instruct_url:
        logger.error("❌ Missing Granite Instruct API key or URL. Please set these environment variables.")
        return False
    
    # Initialize registries
    agent_registry = AgentRegistry()
    prompt_registry = PromptRegistry()
    
    # Verify the prompt exists
    try:
        test_prompt = prompt_registry.get_prompt("test.simple_test", message="Test message")
        logger.info(f"Found test prompt. First 50 chars: {test_prompt[:50]}...")
    except ValueError as e:
        logger.error(f"Error loading test prompt: {e}")
        return False
    
    # Instantiate the test agent
    try:
        test_agent = agent_registry.instantiate_agent("simple_test_agent")
        logger.info(f"Instantiated agent: {test_agent.name} (ID: {test_agent.agent_id})")
    except ValueError as e:
        logger.error(f"Error instantiating agent: {e}")
        return False
    
    # Define a test message
    test_message = Message(
        role=MessageRole.USER,
        content="Hello, can you introduce yourself and explain how the agent system works?"
    )
    
    # Define a simple callback for streaming updates
    async def stream_callback(agent_id, message_type, content, data=None):
        if message_type == "agent_update":
            logger.info(f"Agent update: {content} - {data.get('message', '')}")
        elif message_type == "logs":
            logger.info(f"Agent thinking: {data[:100]}...")
    
    # Process the message
    logger.info("Processing test message")
    try:
        response_message, next_agent = await test_agent.process(
            message=test_message,
            session_id="test_session",
            stream_callback=stream_callback
        )
        
        # Log the response
        if response_message:
            logger.info("\n" + "=" * 60)
            logger.info(" SIMPLE AGENT RESPONSE ".center(60, "="))
            logger.info("=" * 60)
            logger.info(response_message.content)
            logger.info("=" * 60)
            logger.info("Test completed successfully")
            return True
        else:
            logger.error("No response received from agent")
            return False
            
    except Exception as e:
        logger.error(f"Error during agent processing: {e}")
        return False

async def main():
    """Main test function."""
    success = await test_simple_agent()
    
    if not success:
        logger.error("SimpleTestAgent test failed")
        sys.exit(1)
    else:
        logger.info("SimpleTestAgent test passed")

if __name__ == "__main__":
    asyncio.run(main())