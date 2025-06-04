"""
Test script for LLM API connections.

This script tests connections to various LLM APIs used in the system.
It sends simple requests to each endpoint and verifies responses.

Usage:
    python test_llm_connection.py
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

# API configuration
LLM_CONFIGS = [
    {
        "name": "Granite Instruct",
        "api_key_env": "GRANITE_INSTRUCT_API_KEY",
        "url_env": "GRANITE_INSTRUCT_URL",
        "model_id_env": "GRANITE_INSTRUCT_MODEL_NAME",
        "default_model": "granite-3-1-8b-instruct-w4a16",
        "endpoint_path": "/v1/chat/completions",
        "system_prompt": "You are a helpful assistant.",
        "user_prompt": "Respond with a single sentence about artificial intelligence.",
        "temperature": 0.7,
        "max_tokens": 50,
        "critical": True
    },
    {
        "name": "Granite Guardian",
        "api_key_env": "GRANITE_GUARDIAN_API_KEY",
        "url_env": "GRANITE_GUARDIAN_URL",
        "model_id_env": "GRANITE_GUARDIAN_MODEL_NAME",
        "default_model": "granite3-guardian-2b",
        "endpoint_path": "/v1/chat/completions",
        "system_prompt": "You are a content safety checker. Respond with SAFE or UNSAFE.",
        "user_prompt": "Hello, how are you?",
        "temperature": 0.1,
        "max_tokens": 50,
        "critical": True
    }
]

def get_env_or_default(env_name: str, default: str = "") -> str:
    """Get environment variable or default value."""
    return os.getenv(env_name, default)

async def test_llm_endpoint(config: Dict) -> Tuple[bool, Dict, str]:
    """
    Test an LLM API endpoint.
    
    Args:
        config: LLM configuration dictionary
        
    Returns:
        Tuple of (success, response_data, error_message)
    """
    name = config["name"]
    api_key = get_env_or_default(config["api_key_env"])
    url = get_env_or_default(config["url_env"])
    model_id = get_env_or_default(config["model_id_env"], config["default_model"])
    endpoint_path = config["endpoint_path"]
    
    if not api_key:
        return False, {}, f"API key not found for {name}"
    
    if not url:
        return False, {}, f"URL not found for {name}"
    
    try:
        # Ensure URL is correctly formatted
        if url.endswith('/'):
            url = url[:-1]
        
        # Full endpoint URL
        endpoint_url = f"{url}{endpoint_path}"
        
        # Build request data
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        request_data = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": config["system_prompt"]},
                {"role": "user", "content": config["user_prompt"]}
            ],
            "temperature": config["temperature"],
            "max_tokens": config["max_tokens"]
        }
        
        # Configure timeout and retries
        timeout_seconds = 15.0
        max_retries = 2
        retry_delay = 2.0
        
        # Make request with retries
        for attempt in range(max_retries + 1):
            try:
                start_time = time.time()
                
                # Print request information
                masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
                logger.info(f"Request to: {endpoint_url}")
                logger.info(f"Using API key: {masked_key}")
                logger.info(f"Using model: {model_id}")
                
                # Create client with timeout
                async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                    response = await client.post(
                        endpoint_url,
                        headers=headers,
                        json=request_data
                    )
                
                end_time = time.time()
                
                # Log response status and time
                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response time: {end_time - start_time:.2f}s")
                
                # If successful, return response
                if response.status_code == 200:
                    response_data = response.json()
                    
                    # Extract the response content
                    content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    # Add timing information
                    response_data["_request_time"] = end_time - start_time
                    
                    return True, response_data, ""
                else:
                    error_message = f"HTTP {response.status_code}: {response.text}"
                    
                    if attempt < max_retries:
                        logger.warning(f"{name} request failed (attempt {attempt+1}/{max_retries+1}): {error_message}")
                        await asyncio.sleep(retry_delay)
                    else:
                        return False, {}, error_message
                        
            except httpx.TimeoutException:
                if attempt < max_retries:
                    logger.warning(f"{name} request timed out (attempt {attempt+1}/{max_retries+1})")
                    await asyncio.sleep(retry_delay)
                else:
                    return False, {}, f"Request timed out after {timeout_seconds}s (tried {max_retries+1} times)"
                    
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"{name} request failed (attempt {attempt+1}/{max_retries+1}): {str(e)}")
                    await asyncio.sleep(retry_delay)
                else:
                    return False, {}, f"Error: {str(e)}"
        
        # This should not be reached, but just in case
        return False, {}, "Max retries exceeded"
        
    except Exception as e:
        return False, {}, f"Error: {str(e)}"

async def run_all_llm_tests() -> List[Dict]:
    """
    Run all LLM connection tests.
    
    Returns:
        List of test results
    """
    results = []
    
    for config in LLM_CONFIGS:
        name = config["name"]
            
        logger.info(f"Testing {name} connection...")
        
        try:
            logger.info("-" * 60)
            logger.info(f"TESTING: {name}")
            logger.info("-" * 60)
            
            success, response_data, error_message = await test_llm_endpoint(config)
            
            result = {
                "name": name,
                "success": success,
                "critical": config.get("critical", True)
            }
            
            if success:
                content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                request_time = response_data.get("_request_time", 0)
                
                result.update({
                    "response": content,
                    "request_time": f"{request_time:.2f}s",
                    "model": response_data.get("model", "unknown")
                })
                
                logger.info(f"{GREEN}✅ SUCCESS!{RESET}")
                logger.info(f"Response: \"{content}\"")
            else:
                result["error"] = error_message
                logger.info(f"{RED}❌ FAILED: {error_message}{RESET}")
                
            results.append(result)
            logger.info("-" * 60)
            
        except Exception as e:
            logger.exception(f"Error testing {name}")
            results.append({
                "name": name,
                "success": False,
                "critical": config.get("critical", True),
                "error": f"Unexpected error: {str(e)}"
            })
    
    return results

def print_test_results(results: List[Dict]) -> bool:
    """
    Print test results in a formatted way.
    
    Args:
        results: List of test results
        
    Returns:
        True if all critical tests passed, False otherwise
    """
    print("\n" + "=" * 70)
    print(" LLM API CONNECTION TEST RESULTS ".center(70, "="))
    print("=" * 70)
    
    critical_success = True
    
    for result in results:
        name = result["name"]
        success = result["success"]
        critical = result.get("critical", True)
        
        if success:
            status = f"{GREEN}✅ PASS{RESET}" if success else f"{RED}❌ FAIL{RESET}"
        else:
            status = f"{RED}❌ FAIL{RESET}"
            if critical:
                critical_success = False
        
        print(f"\n{name}:  {status}")
        
        if success:
            print(f"  Model: {result.get('model', 'unknown')}")
            print(f"  Time: {result.get('request_time', 'unknown')}")
            print(f"  Response: \"{result.get('response', '')}\"")
        else:
            print(f"  Error: {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 70)
    if critical_success:
        print(f"{GREEN}🎉 All LLM API tests passed! The models are responding correctly.{RESET}")
    else:
        print(f"{RED}⚠️  Some LLM API tests failed. Check the logs for details.{RESET}")
    print("=" * 70 + "\n")
    
    return critical_success

async def main() -> None:
    """Main function to run all tests."""
    print("\nStarting LLM API connection tests...")
    results = await run_all_llm_tests()
    critical_passed = print_test_results(results)
    
    if not critical_passed:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
