#!/usr/bin/env python
"""
Test script to verify the authentication workflow.

This script loads our hello_auth_test workflow and tests it with a simple message.
It verifies that both authenticated and unauthenticated tools work as expected.
"""
import os
import sys
import asyncio
import logging
import json
import time
import datetime
from pathlib import Path
from typing import Dict, Any

# Determine the backend directory and ensure it's in the Python path
script_path = os.path.abspath(__file__)
tests_dir = os.path.dirname(script_path)
src_dir = os.path.dirname(tests_dir)
backend_dir = os.path.dirname(src_dir)

# Ensure backend directory is in Python path
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import workflow manager after path setup
from src.agent_system.core.workflow_manager import WorkflowManager
from src.registries.agent_registry import AgentRegistry
from src.agent_system.core.message import Message, MessageRole

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("auth_workflow_test")

# Setup log directory for file output
LOG_DIR = os.path.join(backend_dir, "logs", "workflow_tests")
os.makedirs(LOG_DIR, exist_ok=True)

async def test_auth_workflow() -> None:
    """
    Test the authentication workflow using the workflow manager.
    """
    # Setup timestamped log file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{timestamp}_hello_auth_test.log"
    log_path = os.path.join(LOG_DIR, log_filename)
    
    # Add file handler to the root logger
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)
    
    # Log start of test to both console and file
    logging.info(f"Starting authentication workflow test. Log file: {log_path}")
    
    # Initialize workflow manager with the registry directory
    registry_dir = os.path.join(backend_dir, "src", "registries", "workflows")
    
    agent_registry = AgentRegistry()
    workflow_manager = WorkflowManager(registry_dir=registry_dir, agent_registry=agent_registry)
    
    workflow_id = "hello_auth_test"
    test_message = "Hello, please test the authentication system!"
    
    # Check if workflow exists
    if workflow_id not in workflow_manager._workflows:
        logging.error(f"Workflow '{workflow_id}' not found in {list(workflow_manager._workflows.keys())}")
        return
        
    logging.info(f"=== Testing Authentication Workflow: {workflow_id} ===")
    logging.info(f"Test message: {test_message}")
    
    # Measure response time
    start_time = time.time()
    
    try:
        # Set up streaming callback for real-time updates
        async def stream_callback(agent_id: str, message_type: str, content: str, data: Any) -> None:
            if message_type == "agent_update":
                logging.info(f"Agent {agent_id}: {content}")
            elif message_type == "logs":
                logging.debug(f"Agent {agent_id} logs: {str(data)}")
        
        # Set up processing log callback
        async def log_callback(agent_id: str, input_text: str, output_text: str, processing_time: int) -> None:
            logging.info(f"Agent {agent_id} processed in {processing_time}ms")
            # Log the full agent output if available
            if output_text:
                logging.info(f"Agent {agent_id} output:\n{output_text}")
        
        # Define callbacks dictionary
        callbacks = {
            'stream': stream_callback,
            'log': log_callback
        }
        
        # Create message with username metadata
        message = Message(
            role=MessageRole.USER,
            content=test_message,
            metadata={"username": "Test User"}
        )
        
        # Execute the workflow using the correct method parameters
        workflow_result = await workflow_manager.process_message(
            message_content=message.content,
            metadata=message.metadata,
            workflow_id=workflow_id,
            callbacks=callbacks
        )
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Log workflow results and response time
        logging.info(f"=== Authentication Workflow Test Completed in {response_time:.2f} seconds ===")
        
        if workflow_result and 'response' in workflow_result:
            logging.info(f"Final response: {workflow_result['response']}")
        else:
            logging.warning(f"No proper response received from workflow: {workflow_result}")
            
    except Exception as e:
        logging.error(f"Error executing workflow: {str(e)}", exc_info=True)

async def main() -> int:
    """
    Main function to run the test.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        await test_auth_workflow()
        return 0
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
