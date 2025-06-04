#!/usr/bin/env python
"""
Test script to verify all workflows in the registry.

This script:
1. Loads all registered workflows from the workflow registry
2. Tests each workflow individually by sending a test message
3. Records success or failure for each workflow
4. Outputs a summary table at the end

Requirements:
- Backend server should be running locally
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

# Import workflow manager
from src.agent_system.core.workflow_manager import WorkflowManager
from src.registries.agent_registry import AgentRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("workflow_test")

# Load environment variables
load_dotenv()

# Test messages to use for each workflow
DEFAULT_TEST_MESSAGES = {
    "BASIC_TEST_WORKFLOW": "How does dengue fever spread?",
    "COMPLIANCE_SANDWICH_WORKFLOW": "Tell me about dengue fever prevention methods.",
    "SINGLE_AGENT_WORKFLOW": "What are the symptoms of dengue fever?",
    # Default test message for any workflow not listed
    "default": "Please provide information about dengue fever."
}

# Timeout for workflow response (seconds)
RESPONSE_TIMEOUT = 120

class WorkflowTestResult:
    """Class to store workflow test results."""
    
    def __init__(self, workflow_id: str, workflow_name: str):
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.success = False
        self.error_message = None
        self.response_time = 0
        self.response_content = None
    
    def __str__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        time_str = f"{self.response_time:.2f}s" if self.success else "n/a"
        return f"{self.workflow_id} ({status} in {time_str})"

async def test_workflow(workflow_manager: WorkflowManager, workflow_id: str, workflow_name: str) -> WorkflowTestResult:
    """
    Test a specific workflow using the workflow manager.
    
    Args:
        workflow_manager: The workflow manager instance
        workflow_id: ID of the workflow to test
        workflow_name: Name of the workflow (for reporting)
        
    Returns:
        WorkflowTestResult object with test results
    """
    result = WorkflowTestResult(workflow_id, workflow_name)
    
    # Select appropriate test message based on workflow ID
    if workflow_id in DEFAULT_TEST_MESSAGES:
        test_message = DEFAULT_TEST_MESSAGES[workflow_id]
    else:
        test_message = DEFAULT_TEST_MESSAGES["default"]
    
    logger.info(f"=== Testing Workflow: {workflow_id} ({workflow_name}) ===")
    logger.info(f"Test message: {test_message}")
    
    # Measure response time
    start_time = time.time()
    
    try:
        # Set up streaming callback for real-time updates
        async def stream_callback(agent_id: str, message_type: str, content: str, data: Any) -> None:
            if message_type == "agent_update":
                logger.info(f"Agent {agent_id}: {content}")
            elif message_type == "logs":
                logger.debug(f"Agent {agent_id} logs: {str(data)}")
        
        # Set up processing log callback
        async def log_callback(agent_id: str, input_text: str, output_text: str, processing_time: int) -> None:
            logger.info(f"Agent {agent_id} processed in {processing_time}ms")
            # Log the full agent output if available
            if output_text:
                logger.info(f"Agent {agent_id} output:\n{output_text}")
        
        # Define callbacks dictionary
        callbacks = {
            'stream': stream_callback,
            'log': log_callback
        }
        
        # Create a unique session ID for this test
        session_id = f"test-{workflow_id}-{int(time.time())}"
        
        # Process the message through the workflow
        response = await workflow_manager.process_message(
            message_content=test_message,
            session_id=session_id,
            callbacks=callbacks,
            workflow_id=workflow_id
        )
        
        # Calculate response time
        end_time = time.time()
        result.response_time = end_time - start_time
        
        # Log the response
        logger.info("\n" + "=" * 60)
        logger.info(" WORKFLOW RESPONSE ".center(60, "="))
        logger.info("=" * 60)
        
        # Store full response content
        content = response.get("response", "")
        logger.info(content)
        
        result.response_content = content
        result.success = True
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error testing workflow {workflow_id}: {str(e)}", exc_info=True)
        result.error_message = str(e)
    
    return result

async def test_all_workflows() -> Dict[str, WorkflowTestResult]:
    """
    Test all workflows in the registry.
    
    Returns:
        Dictionary mapping workflow IDs to test results
    """
    # Initialize workflow manager with the registry directory
    registry_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 
        "../registries/workflows"
    )
    
    agent_registry = AgentRegistry()
    workflow_manager = WorkflowManager(registry_dir=registry_dir, agent_registry=agent_registry)
    
    results: Dict[str, WorkflowTestResult] = {}
    
    # Get all workflow IDs 
    workflow_ids = list(workflow_manager._workflows.keys())
    logger.info(f"Found {len(workflow_ids)} workflows to test")
    
    for workflow_id in workflow_ids:
        # Skip README files or any non-workflow files
        if workflow_id.lower() == "readme":
            continue
            
        # Get workflow data
        workflow_data = workflow_manager._workflows[workflow_id]
        
        # Skip template workflows
        if workflow_data.get("template", False):
            logger.info(f"Skipping template workflow: {workflow_id}")
            continue
            
        # Skip inactive workflows
        if workflow_data.get("inactive", False):
            logger.info(f"Skipping inactive workflow: {workflow_id}")
            continue
            
        # Get workflow name
        workflow_name = workflow_data.get("name", workflow_id)
        
        # Test the workflow
        try:
            result = await test_workflow(workflow_manager, workflow_id, workflow_name)
            results[workflow_id] = result
        except Exception as e:
            logger.error(f"Error in workflow test {workflow_id}: {str(e)}", exc_info=True)
            # Create a failed result
            failed_result = WorkflowTestResult(workflow_id, workflow_name)
            failed_result.error_message = str(e)
            results[workflow_id] = failed_result
    
    return results

def generate_results_table(results: Dict[str, WorkflowTestResult]) -> str:
    """
    Generate a formatted table of test results without using external dependencies.
    
    Args:
        results: Dictionary of test results
        
    Returns:
        Formatted table as string
    """
    # Define table columns and widths
    col_sizes = {
        "Workflow ID": 30,
        "Status": 10,
        "Response Time": 15,
        "Error Message": 50
    }
    
    headers = list(col_sizes.keys())
    
    # Create the header row
    header_row = " | ".join(h.ljust(col_sizes[h]) for h in headers)
    separator = "-" * len(header_row)
    
    # Start building the table
    table = [separator, header_row, separator]
    
    # Add data rows
    for workflow_id, result in results.items():
        status = "✅ PASS" if result.success else "❌ FAIL"
        response_time = f"{result.response_time:.2f}s" if result.success else "n/a"
        error = result.error_message or ""
        if error and len(error) > col_sizes["Error Message"] - 3:
            error = error[:col_sizes["Error Message"] - 3] + "..."
            
        row_data = [
            workflow_id.ljust(col_sizes["Workflow ID"]),
            status.ljust(col_sizes["Status"]),
            response_time.ljust(col_sizes["Response Time"]),
            error.ljust(col_sizes["Error Message"])
        ]
        
        table.append(" | ".join(row_data))
    
    table.append(separator)
    
    return "\n".join(table)

async def main() -> int:
    """
    Main test function.
    
    Returns:
        Exit code (0 for success, 1 for any failures)
    """
    logger.info("Starting workflow tests...")
    
    try:
        # Test all workflows
        results = await test_all_workflows()
        
        # Generate and print results table
        table = generate_results_table(results)
        print("\n" + "=" * 80)
        print(" WORKFLOW TEST RESULTS ".center(80, "="))
        print("=" * 80)
        print(table)
        print("=" * 80)
        
        # Determine exit code based on results
        failed_count = sum(1 for result in results.values() if not result.success)
        success_count = len(results) - failed_count
        
        print(f"\nSUMMARY: {success_count} workflows passed, {failed_count} workflows failed")
        
        return 1 if failed_count > 0 else 0
    
    except Exception as e:
        logger.error(f"Error in test harness: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
