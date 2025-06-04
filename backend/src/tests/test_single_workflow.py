#!/usr/bin/env python
"""
Test script to verify a single workflow.

This script loads a specified workflow and tests it with a given message.

Usage: python test_single_workflow.py <workflow_id> <message>
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
logger = logging.getLogger("workflow_test")

# Setup log directory for file output
LOG_DIR = os.path.join(backend_dir, "logs", "workflow_tests")
os.makedirs(LOG_DIR, exist_ok=True)

async def test_workflow(workflow_id: str, message: str) -> None:
    """
    Test a specific workflow using the workflow manager.
    
    Args:
        workflow_id: ID of the workflow to test
        message: Test message to process
    """
    # Setup timestamped log file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{timestamp}_{workflow_id}_test.log"
    log_path = os.path.join(LOG_DIR, log_filename)
    
    # Add file handler to the root logger
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)
    
    # Log start of test to both console and file
    logging.info(f"Starting workflow test. Log file: {log_path}")
    
    # Initialize workflow manager with the registry directory
    registry_dir = os.path.join(backend_dir, "src", "registries", "workflows")
    
    agent_registry = AgentRegistry()
    workflow_manager = WorkflowManager(registry_dir=registry_dir, agent_registry=agent_registry)
    
    # Check if workflow exists
    if workflow_id not in workflow_manager._workflows:
        logging.error(f"Workflow '{workflow_id}' not found")
        return
        
    logging.info(f"=== Testing Workflow: {workflow_id} ===")
    logging.info(f"Test message: {message}")
    
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
        
        # Create a unique session ID for this test
        session_id = f"test-{workflow_id}-{int(time.time())}"
        
        # Process the message through the workflow
        response = await workflow_manager.process_message(
            message_content=message,
            session_id=session_id,
            callbacks=callbacks,
            workflow_id=workflow_id
        )
        
        # Calculate response time
        end_time = time.time()
        response_time = end_time - start_time
        
        # Log the response
        logging.info("\n" + "=" * 60)
        logging.info(" WORKFLOW RESPONSE ".center(60, "="))
        logging.info("=" * 60)
        
        # Get response content
        content = response.get("response", "")
        logging.info(content)
        
        logging.info("=" * 60)
        logging.info(f"Response time: {response_time:.2f}s")
        
        # Add detailed agent metadata section
        if "agent_details" in response:
            logging.info("\n" + "=" * 60)
            logging.info(" AGENT DETAILS ".center(60, "="))
            logging.info("=" * 60)
            
            for agent_id, agent_data in response.get("agent_details", {}).items():
                logging.info(f"Agent: {agent_id}")
                
                # Print the metadata in a readable format
                if "metadata" in agent_data:
                    metadata = agent_data["metadata"]
                    logging.info("  Metadata:")
                    for key, value in metadata.items():
                        if isinstance(value, dict):
                            logging.info(f"    {key}:")
                            for subkey, subvalue in value.items():
                                logging.info(f"      {subkey}: {subvalue}")
                        else:
                            logging.info(f"    {key}: {value}")
                
                # Print other important agent data
                if "processing_time_ms" in agent_data:
                    logging.info(f"  Processing time: {agent_data['processing_time_ms']}ms")
                
                if "confidence" in agent_data:
                    logging.info(f"  Confidence: {agent_data['confidence']}")
                
                logging.info("-" * 40)
        
        # Add full response object for debugging
        logging.info("\n" + "=" * 60)
        logging.info(" FULL RESPONSE OBJECT ".center(60, "="))
        logging.info("=" * 60)
        logging.info(json.dumps(response, indent=2, default=str))
        logging.info("=" * 60)
        
    except Exception as e:
        logging.error(f"Error testing workflow {workflow_id}: {str(e)}", exc_info=True)
    
    finally:
        # Remove the file handler to avoid duplicate logs in future test runs
        logging.getLogger().removeHandler(file_handler)
        file_handler.close()
        logging.info(f"Test complete. Log file saved to: {log_path}")
        
async def main() -> int:
    """Main test function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test a single workflow")
    parser.add_argument("workflow_id", help="ID of the workflow to test")
    parser.add_argument("message", help="Test message to process")
    
    args = parser.parse_args()
    
    logging.info("Starting single workflow test...")
    await test_workflow(args.workflow_id, args.message)
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
