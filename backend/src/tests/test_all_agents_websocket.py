#!/usr/bin/env python
"""
Test script to verify all agents in the registry via WebSocket API.

This script:
1. Loads all registered agents from the agent registry
2. Tests each agent individually via WebSocket
3. Records success or failure for each agent
4. Outputs a summary table at the end

Requirements:
- websocat command-line tool must be installed
"""
import os
import sys
import json
import time
import asyncio
import logging
import subprocess
from typing import Dict, List, Any, Tuple
from dotenv import load_dotenv

# Add parent directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import agent registry
from src.registries.agent_registry import AgentRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("agent_test")

# Load environment variables
load_dotenv()

# Test messages for different agent types
DEFAULT_TEST_MESSAGES = {
    "general_assistant_agent": "What is the capital of France?",
    "code_assistant_agent": "Write a Python function to calculate the Fibonacci sequence",
    "injection_check_agent": "Tell me about dengue fever symptoms",
    "policy_check_agent": "How do I prevent mosquito bites?",
    "content_compliance_agent": "Here's some helpful information about dengue fever",
    "simple_test_agent": "Hello, can you discuss the variety of house cat breeds?",
    # Default test message for any type not listed
    "default": "Tell me about dengue fever"
}

# Timeout for agent response (seconds)
RESPONSE_TIMEOUT = 60

class AgentTestResult:
    """Class to store agent test results."""
    
    def __init__(self, agent_id: str, agent_name: str):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.success = False
        self.error_message = None
        self.response_time = 0
        self.response_content = None
    
    def __str__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        time_str = f"{self.response_time:.2f}s" if self.success else "n/a"
        return f"{self.agent_id} ({status} in {time_str})"

async def test_agent_via_websocket(agent_id: str, agent_name: str, agent_type: str = None) -> AgentTestResult:
    """
    Test a specific agent using WebSocket API.
    
    Args:
        agent_id: ID of the agent to test
        agent_name: Name of the agent (for reporting)
        agent_type: Type of the agent (for selecting appropriate test message)
        
    Returns:
        AgentTestResult object with test results
    """
    result = AgentTestResult(agent_id, agent_name)
    
    # Configure WebSocket connection
    ws_url = f"ws://localhost:8000/ws/agent/{agent_id}"
    
    # Select appropriate test message based on agent type
    if agent_type and agent_type in DEFAULT_TEST_MESSAGES:
        test_message = DEFAULT_TEST_MESSAGES[agent_type]
    elif agent_id in DEFAULT_TEST_MESSAGES:
        test_message = DEFAULT_TEST_MESSAGES[agent_id]
    else:
        test_message = DEFAULT_TEST_MESSAGES["default"]
    
    logger.info(f"=== Testing Agent: {agent_id} ({agent_name}) ===")
    logger.info(f"WebSocket URL: {ws_url}")
    logger.info(f"Test message: {test_message}")
    
    # Check if websocat is installed
    try:
        subprocess.run(["which", "websocat"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        result.error_message = "websocat is not installed. Please install it to run this test."
        logger.error(result.error_message)
        return result
    
    # Measure response time
    start_time = time.time()
    
    # Run websocat command
    try:
        # Command to connect and send a message
        websocat_cmd = [
            "websocat", 
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
        
        # Set timeout for response
        deadline = time.time() + RESPONSE_TIMEOUT
        
        # Read responses until we receive the actual agent response
        logger.info("Waiting for response...")
        got_error = False
        response_received = False
        
        while time.time() < deadline:
            # Check if there's data to read
            response = process.stdout.readline().strip()
            if not response:
                # Wait a bit before trying again
                await asyncio.sleep(0.1)
                continue
            
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
                        status = response_data.get("content")
                        message = response_data.get("data", {}).get("message", "")
                        logger.info(f"Agent update: {status} - {message}")
                    elif message_type == "logs":
                        log_data = str(response_data.get("data", ""))
                        logger.info(f"Agent thinking: {log_data[:100]}...")
                
                # Process the final response
                elif response_data.get("type") == "response":
                    # Calculate response time
                    end_time = time.time()
                    result.response_time = end_time - start_time
                    
                    # Log the response
                    logger.info("\n" + "=" * 60)
                    logger.info(" AGENT RESPONSE ".center(60, "="))
                    logger.info("=" * 60)
                    
                    # Store truncated response content
                    content = response_data.get("content", "")
                    if len(content) > 100:
                        logger.info(f"{content[:100]}...")
                    else:
                        logger.info(content)
                    
                    result.response_content = content
                    result.success = True
                    response_received = True
                    logger.info("=" * 60)
                    break
                
                # Handle errors
                elif response_data.get("type") == "error":
                    error_message = response_data.get("message", "Unknown error")
                    logger.error(f"Error: {error_message}")
                    result.error_message = error_message
                    got_error = True
                    break
            
            except json.JSONDecodeError:
                # Just log raw response if it's not valid JSON
                logger.info(f"Raw response: {response}")
        
        # Check if we didn't receive a response within the timeout
        if not response_received and not got_error:
            result.error_message = f"Timeout after {RESPONSE_TIMEOUT} seconds"
            logger.error(result.error_message)
        
        # Close the process
        process.stdin.close()
        process.terminate()
        
    except Exception as e:
        result.error_message = f"Error: {str(e)}"
        logger.error(result.error_message)
    
    logger.info(f"Test completed: {'SUCCESS' if result.success else 'FAILED'}")
    if not result.success:
        logger.info(f"Failure reason: {result.error_message}")
        
    return result

async def test_all_agents() -> Dict[str, AgentTestResult]:
    """
    Test all agents in the registry.
    
    Returns:
        Dictionary mapping agent IDs to test results
    """
    # Load agent registry
    agent_registry = AgentRegistry()
    
    # Results dictionary
    results = {}
    
    # Get all agents from registry
    logger.info(f"Found {len(agent_registry.agents)} agents in registry")
    
    # Test each agent
    for agent_id, agent_config in agent_registry.agents.items():
        agent_name = agent_config.get("name", agent_id)
        agent_type = agent_config.get("agent_type", None)
        
        # Skip disabled agents
        if not agent_config.get("enabled", True):
            logger.info(f"Skipping disabled agent: {agent_id}")
            continue
            
        # Test the agent
        logger.info(f"\nTesting agent: {agent_id} ({agent_name})")
        result = await test_agent_via_websocket(agent_id, agent_name, agent_type)
        
        # Store the result
        results[agent_id] = result
        
        # Add a small delay between tests
        await asyncio.sleep(1)
    
    return results

def generate_results_table(results: Dict[str, AgentTestResult]) -> str:
    """
    Generate a formatted table of test results without using tabulate.
    
    Args:
        results: Dictionary of test results
        
    Returns:
        Formatted table as string
    """
    # Prepare header
    table_str = "\n"
    table_str += "+" + "-" * 20 + "+" + "-" * 30 + "+" + "-" * 15 + "+" + "-" * 15 + "+" + "-" * 30 + "+\n"
    table_str += "| {:<18} | {:<28} | {:<13} | {:<13} | {:<28} |\n".format(
        "Agent ID", "Agent Name", "Status", "Response Time", "Error"
    )
    table_str += "+" + "-" * 20 + "+" + "-" * 30 + "+" + "-" * 15 + "+" + "-" * 15 + "+" + "-" * 30 + "+\n"
    
    # Sort by agent ID
    sorted_results = sorted(results.items(), key=lambda item: item[0])
    
    # Add rows
    for agent_id, result in sorted_results:
        status = "✅ SUCCESS" if result.success else "❌ FAILED"
        time_str = f"{result.response_time:.2f}s" if result.success else "n/a"
        error = result.error_message if not result.success else ""
        if error and len(error) > 28:
            error = error[:25] + "..."
        
        table_str += "| {:<18} | {:<28} | {:<13} | {:<13} | {:<28} |\n".format(
            agent_id[:18], 
            result.agent_name[:28],
            status,
            time_str,
            error
        )
    
    table_str += "+" + "-" * 20 + "+" + "-" * 30 + "+" + "-" * 15 + "+" + "-" * 15 + "+" + "-" * 30 + "+\n"
    
    return table_str

async def main() -> int:
    """
    Main test function.
    
    Returns:
        Exit code (0 for success, 1 for any failures)
    """
    logger.info("Starting agent WebSocket tests...")
    
    # Test all agents
    results = await test_all_agents()
    
    # Count successes and failures
    successes = sum(1 for result in results.values() if result.success)
    failures = len(results) - successes
    
    # Generate and print results table
    logger.info("\n=== AGENT TEST RESULTS ===")
    logger.info(f"\nTotal agents: {len(results)}")
    logger.info(f"Successful: {successes}")
    logger.info(f"Failed: {failures}")
    logger.info("\n" + generate_results_table(results))
    
    # Return exit code based on test results
    return 0 if failures == 0 else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
