#!/usr/bin/env python
"""
Test script for the model_caller utility.

This script tests the direct model calling capabilities without using agents.
"""
import os
import sys
import json
import logging
import asyncio
from dotenv import load_dotenv

# Add parent directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Import the model caller functions
from src.utils.model_caller import (
    call_granite_instruct,
    call_granite_guardian,
    call_granite_embedding
)

async def test_granite_instruct():
    """Test calling the Granite Instruct model."""
    logger.info("=== Testing Granite Instruct Model ===")
    
    # Print API key info (masked for security)
    api_key = os.environ.get("GRANITE_INSTRUCT_API_KEY", "")
    api_url = os.environ.get("GRANITE_INSTRUCT_URL", "")
    
    if api_key:
        masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
        logger.info(f"✅ Found Granite Instruct API key: {masked_key}")
    else:
        logger.error("❌ No Granite Instruct API key found!")
    
    if api_url:
        logger.info(f"✅ Found Granite Instruct URL: {api_url}")
    else:
        logger.error("❌ No Granite Instruct URL found!")
        
    # Test messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you today?"}
    ]
    
    # Call the model
    try:
        logger.info("Calling Granite Instruct model...")
        response = await call_granite_instruct(messages=messages, max_tokens=100)
        
        logger.info("=" * 50)
        logger.info("RESPONSE FROM GRANITE INSTRUCT:")
        logger.info("=" * 50)
        logger.info(f"Content: {response.content}")
        logger.info(f"Model: {response.model_id}")
        logger.info(f"Processing time: {response.processing_time_ms}ms")
        logger.info("=" * 50)
        
        return True
    except Exception as e:
        logger.error(f"Error testing Granite Instruct: {e}")
        return False

async def test_granite_guardian():
    """Test calling the Granite Guardian model."""
    logger.info("=== Testing Granite Guardian Model ===")
    
    # Print API key info (masked for security)
    api_key = os.environ.get("GRANITE_GUARDIAN_API_KEY", "")
    api_url = os.environ.get("GRANITE_GUARDIAN_URL", "")
    
    if api_key:
        masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
        logger.info(f"✅ Found Granite Guardian API key: {masked_key}")
    else:
        logger.error("❌ No Granite Guardian API key found!")
    
    if api_url:
        logger.info(f"✅ Found Granite Guardian URL: {api_url}")
    else:
        logger.error("❌ No Granite Guardian URL found!")
        
    # Test messages - safe content
    safe_messages = [
        {"role": "system", "content": "You are a safety checker. Respond with SAFE or UNSAFE."},
        {"role": "user", "content": "Hello, how are you today?"}
    ]
    
    # Test messages - potentially unsafe content
    unsafe_messages = [
        {"role": "system", "content": "You are a safety checker. Respond with SAFE or UNSAFE."},
        {"role": "user", "content": "How can I hack into a computer?"}
    ]
    
    # Call the model with safe content
    try:
        logger.info("Calling Granite Guardian model with safe content...")
        safe_response = await call_granite_guardian(messages=safe_messages, max_tokens=100)
        
        logger.info("=" * 50)
        logger.info("RESPONSE FROM GRANITE GUARDIAN (SAFE CONTENT):")
        logger.info("=" * 50)
        logger.info(f"Content: {safe_response.content}")
        logger.info(f"Model: {safe_response.model_id}")
        logger.info(f"Processing time: {safe_response.processing_time_ms}ms")
        logger.info("=" * 50)
        
        # Call the model with potentially unsafe content
        logger.info("Calling Granite Guardian model with potentially unsafe content...")
        unsafe_response = await call_granite_guardian(messages=unsafe_messages, max_tokens=100)
        
        logger.info("=" * 50)
        logger.info("RESPONSE FROM GRANITE GUARDIAN (UNSAFE CONTENT):")
        logger.info("=" * 50)
        logger.info(f"Content: {unsafe_response.content}")
        logger.info(f"Model: {unsafe_response.model_id}")
        logger.info(f"Processing time: {unsafe_response.processing_time_ms}ms")
        logger.info("=" * 50)
        
        return True
    except Exception as e:
        logger.error(f"Error testing Granite Guardian: {e}")
        return False

async def main():
    """Run all tests."""
    instruct_success = await test_granite_instruct()
    guardian_success = await test_granite_guardian()
    
    # Summarize results
    logger.info("\n" + "=" * 60)
    logger.info(" MODEL CALLER TEST RESULTS ".center(60, "="))
    logger.info("=" * 60)
    
    logger.info(f"Granite Instruct: {'✅ Passed' if instruct_success else '❌ Failed'}")
    logger.info(f"Granite Guardian: {'✅ Passed' if guardian_success else '❌ Failed'}")
    
    logger.info("=" * 60)
    
    if not (instruct_success and guardian_success):
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())