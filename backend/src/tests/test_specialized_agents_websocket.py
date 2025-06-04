#!/usr/bin/env python
"""
Test script to verify specialized agents via WebSocket API.

This script:
1. Tests specialized agents (code assistant, etc.) with appropriate test cases
2. Validates the output using agent-specific validators
3. Records results for each agent and test case
4. Outputs a summary table at the end

Specialized agents tested:
- code_assistant: Tests for proper code generation
- (other specialized agents will be added here as they are developed)

Requirements:
- websocat command-line tool must be installed
"""
import os
import sys
import json
import time
import re
import ast
import asyncio
import logging
import subprocess
import socket
from typing import Dict, List, Any, Tuple, Callable, Optional

# Add parent directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import agent registry
from src.registries.agent_registry import AgentRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("specialized_agent_test")

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Load test cases from the test_cases directory
def load_test_cases(agent_id: str) -> List[Dict[str, Any]]:
    """
    Load test cases for a specific agent from the test_cases directory.
    
    Args:
        agent_id: ID of the agent
        
    Returns:
        List of test case dictionaries
    """
    test_cases_dir = os.path.join(
        os.path.dirname(__file__), 
        "test_cases", 
        agent_id
    )
    
    # If directory doesn't exist, create it and use default test cases
    if not os.path.exists(test_cases_dir):
        os.makedirs(test_cases_dir, exist_ok=True)
        return DEFAULT_TEST_CASES.get(agent_id, [])
    
    # Load all JSON files in the directory
    test_cases = []
    for filename in os.listdir(test_cases_dir):
        if filename.endswith(".json"):
            with open(os.path.join(test_cases_dir, filename), "r") as f:
                try:
                    test_case = json.load(f)
                    test_cases.append(test_case)
                except json.JSONDecodeError:
                    logger.error(f"Error parsing test case file: {filename}")
    
    # If no valid test cases found, use defaults
    if not test_cases:
        return DEFAULT_TEST_CASES.get(agent_id, [])
        
    return test_cases

# Default test cases for agents that don't have specific test files
DEFAULT_TEST_CASES = {
    "code_assistant": [
        {
            "name": "Fibonacci function",
            "input": "Write a Python function to calculate the first 10 Fibonacci numbers",
            "validation": {
                "type": "code_validation",
                "criteria": {
                    "language": "python",
                    "must_contain": ["def", "fibonacci", "return"],
                    "expected_patterns": ["\\bdef\\s+\\w+\\s*\\(", "for\\s+\\w+\\s+in\\s+range|while"],
                    "syntax_check": True
                }
            }
        },
        {
            "name": "Sorting algorithm",
            "input": "Write a JavaScript function to implement merge sort",
            "validation": {
                "type": "code_validation",
                "criteria": {
                    "language": "javascript",
                    "must_contain": ["function", "sort", "return"],
                    "expected_patterns": ["function\\s+\\w+\\s*\\(", "\\bmerge\\b"],
                    "syntax_check": True
                }
            }
        }
    ]
}

# Timeout for agent response (seconds)
RESPONSE_TIMEOUT = 60  # Shorter timeout for testing
# WebSocket server connection details
WS_HOST = "localhost"
WS_PORT = 8000
WS_PATH = "/ws/agent"

class SpecializedAgentTestResult:
    """Class to store specialized agent test results."""
    
    def __init__(self, agent_id: str, test_name: str):
        self.agent_id = agent_id
        self.test_name = test_name
        self.validation_success = False
        self.validation_message = None
        self.error_message = None
        self.response_time = 0
        self.response_content = None
        
    def __str__(self) -> str:
        status = "SUCCESS" if self.validation_success else "FAILED"
        time_str = f"{self.response_time:.2f}s" if self.response_time else "n/a"
        return f"{self.agent_id} - {self.test_name} ({status} in {time_str})"

class BaseValidator:
    """Base class for output validators."""
    
    def __init__(self, criteria: Dict[str, Any]):
        self.criteria = criteria
        
    async def validate(self, response: str) -> Tuple[bool, str]:
        """
        Validate a response and return success status and reason.
        
        Args:
            response: The agent's response to validate
            
        Returns:
            Tuple of (success, reason)
        """
        raise NotImplementedError("Validator subclasses must implement validate()")

class CodeValidator(BaseValidator):
    """Validator for code-related responses."""
    
    async def validate(self, response: str) -> Tuple[bool, str]:
        """
        Validate code-related responses.
        
        Args:
            response: The agent's response containing code blocks
            
        Returns:
            Tuple of (success, reason)
        """
        # 1. Check for code blocks with regex
        code_blocks = re.findall(r'```(\w*)\n(.*?)```', response, re.DOTALL)
        if not code_blocks:
            return False, "No code blocks found in response"
            
        # 2. Check language if specified
        if self.criteria.get("language"):
            lang_matches = [
                lang.lower() for lang, _ in code_blocks 
                if self.criteria["language"].lower() in lang.lower()
            ]
            if not lang_matches:
                # If language tag is missing, check if any code block exists
                if any(not lang for lang, _ in code_blocks):
                    # Allow code blocks without language specification
                    pass
                else:
                    return False, f"Expected {self.criteria['language']} code block not found"
                
        # 3. Check for required elements
        code_content = "\n".join([code for _, code in code_blocks])
        for required in self.criteria.get("must_contain", []):
            if required not in code_content:
                return False, f"Required element '{required}' not found in code"
                
        # 4. Check pattern matches
        for pattern in self.criteria.get("expected_patterns", []):
            if not re.search(pattern, code_content):
                return False, f"Expected pattern '{pattern}' not found in code"
                
        # 5. Syntax check if requested
        if self.criteria.get("syntax_check", False):
            for _, code in code_blocks:
                if self.criteria.get("language", "").lower() == "python":
                    try:
                        ast.parse(code)
                    except SyntaxError as e:
                        return False, f"Python syntax error: {str(e)}"
                
                # For other languages, we would need language-specific validators
                # JavaScript, etc. would need external tools or services
            
        return True, "Code validation passed"

def get_validator(validation_config: Dict[str, Any]) -> BaseValidator:
    """
    Factory function to create the appropriate validator.
    
    Args:
        validation_config: The validation configuration
        
    Returns:
        A validator instance
    """
    validation_type = validation_config["type"]
    criteria = validation_config["criteria"]
    
    if validation_type == "code_validation":
        return CodeValidator(criteria)
    # Add other validator types as needed
    
    raise ValueError(f"Unknown validation type: {validation_type}")

def check_server_running(host: str = WS_HOST, port: int = WS_PORT) -> bool:
    """
    Check if the WebSocket server is running.
    
    Args:
        host: Server host
        port: Server port
        
    Returns:
        True if the server is running, False otherwise
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((host, port))
            return True
        except Exception:
            return False

async def test_specialized_agent(agent_id: str, test_case: Dict[str, Any]) -> SpecializedAgentTestResult:
    """
    Test a specialized agent using WebSocket API.
    
    Args:
        agent_id: ID of the agent to test
        test_case: The test case dictionary
        
    Returns:
        SpecializedAgentTestResult object with test results
    """
    test_name = test_case.get("name", "Unnamed test")
    test_input = test_case.get("input", "")
    validation_config = test_case.get("validation", {})
    
    result = SpecializedAgentTestResult(agent_id, test_name)
    
    # Configure WebSocket connection
    ws_url = f"ws://{WS_HOST}:{WS_PORT}{WS_PATH}/{agent_id}"
    
    logger.info(f"=== Testing Specialized Agent: {agent_id} ===")
    logger.info(f"Test name: {test_name}")
    logger.info(f"Test input: {test_input[:50]}..." if len(test_input) > 50 else f"Test input: {test_input}")
    logger.info(f"WebSocket URL: {ws_url}")
    
    # Check if server is running
    if not check_server_running(WS_HOST, WS_PORT):
        result.error_message = f"WebSocket server not running at {WS_HOST}:{WS_PORT}"
        logger.error(result.error_message)
        return result
    
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
        logger.info("Sending test input...")
        process.stdin.write(test_input + "\n")
        process.stdin.flush()
        
        # Set timeout for response
        deadline = time.time() + RESPONSE_TIMEOUT
        
        # Read responses until we receive the actual agent response
        logger.info("Waiting for response...")
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
                        logger.info(f"Agent thinking: {log_data[:100]}..." if len(log_data) > 100 else log_data)
                
                # Process the final response
                elif response_data.get("type") == "response":
                    # Calculate response time
                    end_time = time.time()
                    result.response_time = end_time - start_time
                    
                    # Store response content
                    content = response_data.get("content", "")
                    result.response_content = content
                    
                    # Log the response (truncated)
                    logger.info("\n" + "=" * 60)
                    logger.info(" AGENT RESPONSE ".center(60, "="))
                    logger.info("=" * 60)
                    logger.info(f"{content[:200]}..." if len(content) > 200 else content)
                    logger.info("=" * 60)
                    
                    # Validate the response
                    if validation_config:
                        logger.info("Validating response...")
                        validator = get_validator(validation_config)
                        success, message = await validator.validate(content)
                        
                        result.validation_success = success
                        result.validation_message = message
                        
                        logger.info(f"Validation result: {success}")
                        logger.info(f"Validation message: {message}")
                    else:
                        # If no validation specified, consider it successful
                        result.validation_success = True
                        result.validation_message = "No validation criteria specified"
                    
                    response_received = True
                    break
                
                # Handle errors
                elif response_data.get("type") == "error":
                    error_message = response_data.get("message", "Unknown error")
                    logger.error(f"Error: {error_message}")
                    result.error_message = error_message
                    break
                
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse WebSocket response: {response[:100]}...")
                continue
        
        # Handle timeout
        if not response_received:
            result.error_message = "Timed out waiting for response"
            logger.error("Timed out waiting for response")
        
        # Terminate the process
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            
        return result
    
    except Exception as e:
        logger.error(f"Error during test: {str(e)}")
        result.error_message = f"Test error: {str(e)}"
        return result

async def test_all_specialized_agents() -> Dict[str, List[SpecializedAgentTestResult]]:
    """
    Test all specialized agents with their test cases.
    
    Returns:
        Dictionary mapping agent IDs to lists of test results
    """
    # Get agent registry
    registry = AgentRegistry()
    
    # Dictionary to store results
    results = {}
    
    # List of specialized agent IDs to test
    specialized_agent_ids = [
        "code_assistant",
        # Add other specialized agents here as they are developed
    ]
    
    # Test each specialized agent
    for agent_id in specialized_agent_ids:
        # Check if agent exists in registry
        try:
            # Using get_agent_config will raise ValueError if agent doesn't exist
            registry.get_agent_config(agent_id)
        except ValueError:
            logger.warning(f"Agent {agent_id} not found in registry, skipping")
            continue
        
        logger.info(f"\n\n=== Starting tests for {agent_id} ===\n")
        
        # Load test cases for this agent
        test_cases = load_test_cases(agent_id)
        
        if not test_cases:
            logger.warning(f"No test cases found for {agent_id}, skipping")
            continue
        
        agent_results = []
        
        # Run each test case
        for test_case in test_cases:
            result = await test_specialized_agent(agent_id, test_case)
            agent_results.append(result)
            
            # Log result
            success = result.validation_success and not result.error_message
            logger.info(f"Test result: {'SUCCESS' if success else 'FAILED'}")
            logger.info(f"Test time: {result.response_time:.2f}s")
            if result.validation_message:
                logger.info(f"Validation message: {result.validation_message}")
            if result.error_message:
                logger.error(f"Error: {result.error_message}")
            
            logger.info("\n" + "-" * 60 + "\n")
        
        # Store results for this agent
        results[agent_id] = agent_results
    
    return results

def format_table(data: List[List[str]], headers: List[str], column_widths: Optional[List[int]] = None) -> str:
    """
    Format data as a table with aligned columns.
    
    Args:
        data: List of rows (each row is a list of values)
        headers: List of column headers
        column_widths: Optional list of column widths
        
    Returns:
        Formatted table as string
    """
    # Calculate column widths if not provided
    if not column_widths:
        # Start with header widths
        column_widths = [len(str(h)) for h in headers]
        
        # Update with data widths
        for row in data:
            for i, val in enumerate(row):
                val_str = str(val)
                if i < len(column_widths):
                    column_widths[i] = max(column_widths[i], len(val_str))
    
    # Format headers
    header_row = " | ".join(str(h).ljust(column_widths[i]) for i, h in enumerate(headers))
    separator = "-" * len(header_row)
    
    # Format data rows
    data_rows = []
    for row in data:
        formatted_row = " | ".join(
            str(val).ljust(column_widths[i]) if i < len(column_widths) else str(val)
            for i, val in enumerate(row)
        )
        data_rows.append(formatted_row)
    
    # Combine into table
    return f"{header_row}\n{separator}\n" + "\n".join(data_rows)

def generate_results_table(results: Dict[str, List[SpecializedAgentTestResult]]) -> str:
    """
    Generate a formatted table of test results.
    
    Args:
        results: Dictionary of test results
        
    Returns:
        Formatted table as string
    """
    headers = ["Agent", "Test Case", "Status", "Time", "Validation"]
    rows = []
    
    # Process results
    for agent_id, agent_results in results.items():
        for result in agent_results:
            status = "SUCCESS" if result.validation_success and not result.error_message else "FAILED"
            time_str = f"{result.response_time:.2f}s" if result.response_time else "n/a"
            validation = result.validation_message if result.validation_message else "N/A"
            
            if result.error_message:
                validation = f"ERROR: {result.error_message}"
            
            rows.append([agent_id, result.test_name, status, time_str, validation])
    
    # Generate table
    return format_table(rows, headers)

async def main() -> int:
    """
    Main test function.
    
    Returns:
        Exit code (0 for success, 1 for any failures)
    """
    logger.info("=== Starting Specialized Agent Tests ===")
    
    try:
        # Test all specialized agents
        results = await test_all_specialized_agents()
        
        # Print results table
        results_table = generate_results_table(results)
        print("\n\n=== Specialized Agent Test Results ===\n")
        print(results_table)
        
        # Check for any failures
        failure = False
        for agent_id, agent_results in results.items():
            for result in agent_results:
                if not result.validation_success or result.error_message:
                    failure = True
                    break
        
        # Print summary
        total_tests = sum(len(agent_results) for agent_results in results.values())
        passed_tests = sum(
            1 for agent_results in results.values()
            for result in agent_results
            if result.validation_success and not result.error_message
        )
        
        print(f"\nSummary: {passed_tests}/{total_tests} tests passed")
        
        # Return exit code
        return 1 if failure else 0
    
    except Exception as e:
        logger.error(f"Error in main test function: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
