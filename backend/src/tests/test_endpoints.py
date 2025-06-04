"""
Test script to verify connectivity to critical endpoints and APIs.

This script verifies that all required API endpoints are accessible before
running any workflow tests, ensuring that failures in the workflow are not
due to connectivity issues with external services.

Usage:
    python test_endpoints.py
"""
import os
import sys
import json
import time
import httpx
import asyncio
import logging
from dotenv import load_dotenv
from typing import Dict, List, Tuple, Optional, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add some color to logs if supported
try:
    import colorama
    colorama.init()
    GREEN = colorama.Fore.GREEN
    RED = colorama.Fore.RED
    YELLOW = colorama.Fore.YELLOW
    RESET = colorama.Style.RESET_ALL
except ImportError:
    GREEN = ""
    RED = ""
    YELLOW = ""
    RESET = ""

# Load environment variables
load_dotenv()

# API Keys and URLs from environment
API_KEYS = {
    "granite_instruct": os.getenv("GRANITE_INSTRUCT_API_KEY"),
    "granite_guardian": os.getenv("GRANITE_GUARDIAN_API_KEY"),
    "granite_embedding": os.getenv("GRANITE_EMBEDDING_API_KEY"),
}

API_URLS = {
    "granite_instruct": os.getenv("GRANITE_INSTRUCT_URL"),
    "granite_guardian": os.getenv("GRANITE_GUARDIAN_URL"),
    "granite_embedding": os.getenv("GRANITE_EMBEDDING_URL"),
    "knowledge_graph": os.getenv("KG_API_URL"),
}

# Test messages for each endpoint
TEST_MESSAGES = {
    "granite_instruct": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ],
    "granite_guardian": [
        {"role": "system", "content": "You are a safety checker. Respond with SAFE or UNSAFE."},
        {"role": "user", "content": "Hello, how are you?"}
    ],
}

# Model IDs for each endpoint
MODEL_IDS = {
    "granite_instruct": os.getenv("GRANITE_INSTRUCT_MODEL_NAME", "granite-3-1-8b-instruct-w4a16"),
    "granite_guardian": os.getenv("GRANITE_GUARDIAN_MODEL_NAME", "granite3-guardian-2b"),
}

# Knowledge Graph API test endpoint
KG_API_TEST_ENDPOINT = "/health"

async def test_llm_endpoint(
    name: str, 
    url: str, 
    api_key: str, 
    messages: List[Dict[str, str]]
) -> Tuple[bool, str]:
    """
    Test an LLM API endpoint to ensure it's responsive.
    
    Args:
        name: Name of the endpoint
        url: API URL
        api_key: API key
        messages: List of messages to send
        
    Returns:
        Tuple of (success, details)
    """
    try:
        # Ensure URL doesn't end with /v1/chat/completions already
        if url.endswith('/v1/chat/completions'):
            base_url = url[:-len('/v1/chat/completions')]
        elif url.endswith('/'):
            base_url = url[:-1]
        else:
            base_url = url
            
        # Prepare the request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # Get model ID
        model_id = MODEL_IDS.get(name)
        
        data = {
            "model": model_id,
            "messages": messages,
            "max_tokens": 50
        }
        
        # Log request details (masked for security)
        masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
        logger.info(f"Testing {name} endpoint at {base_url}/v1/chat/completions")
        logger.info(f"Using API key: {masked_key}")
        logger.info(f"Using model: {model_id}")
        
        # Make the request with timeout
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{base_url}/v1/chat/completions",
                headers=headers,
                json=data
            )
            
        # Log response details
        logger.info(f"Response status: {response.status_code}")
            
        # Check response
        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return True, f"Success: {content[:30]}..."
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
            
    except Exception as e:
        return False, f"Error: {str(e)}"

async def test_kg_api_endpoint(url: str) -> Tuple[bool, str]:
    """
    Test the Knowledge Graph API endpoint.
    
    Args:
        url: API URL
        
    Returns:
        Tuple of (success, details)
    """
    try:
        # Ensure URL has no trailing slash
        if url.endswith('/'):
            url = url[:-1]
            
        # Make the request with timeout
        logger.info(f"Testing KG API endpoint at {url}{KG_API_TEST_ENDPOINT}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{url}{KG_API_TEST_ENDPOINT}")
            
        # Check response
        if response.status_code == 200:
            return True, "KG API is healthy"
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
            
    except Exception as e:
        return False, f"Error: {str(e)}"

async def run_all_tests() -> Dict[str, Tuple[bool, str]]:
    """
    Run all endpoint tests.
    
    Returns:
        Dictionary of test results
    """
    results = {}
    
    # Test LLM endpoints
    for name in ["granite_instruct", "granite_guardian"]:
        if API_KEYS.get(name) and API_URLS.get(name):
            logger.info(f"Testing {name} endpoint...")
            success, details = await test_llm_endpoint(
                name, 
                API_URLS[name], 
                API_KEYS[name],
                TEST_MESSAGES[name]
            )
            results[name] = (success, details)
        else:
            results[name] = (False, "API key or URL not configured")
    
    # Test Knowledge Graph API
    if API_URLS.get("knowledge_graph"):
        logger.info("Testing Knowledge Graph API...")
        success, details = await test_kg_api_endpoint(API_URLS["knowledge_graph"])
        results["knowledge_graph"] = (success, details)
    else:
        results["knowledge_graph"] = (False, "API URL not configured")
    
    return results

def print_results(results: Dict[str, Tuple[bool, str]]) -> bool:
    """
    Print test results in a formatted way.
    
    Args:
        results: Dictionary of test results
    
    Returns:
        True if all tests passed, False otherwise
    """
    print("\n" + "=" * 60)
    print(" ENDPOINT TEST RESULTS ".center(60, "="))
    print("=" * 60)
    
    all_success = True
    
    for name, (success, details) in results.items():
        status = f"{GREEN}✅ PASS{RESET}" if success else f"{RED}❌ FAIL{RESET}"
        print(f"{name.upper().ljust(20)} {status.ljust(10)} {details}")
        if not success:
            all_success = False
    
    print("=" * 60)
    if all_success:
        print(f"{GREEN}🎉 All endpoint tests passed! The system is ready for workflow tests.{RESET}")
    else:
        print(f"{RED}⚠️  Some endpoint tests failed. Fix connectivity issues before running workflow tests.{RESET}")
    print("=" * 60 + "\n")
    
    return all_success

async def main() -> None:
    """Main function to run all tests."""
    print("\nStarting endpoint tests...")
    results = await run_all_tests()
    all_passed = print_results(results)
    
    if not all_passed:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
