"""
Test script for the Graph RAG Workflow with Output Combiner

This script tests the full workflow including the new output_combiner_agent
and logs all outputs to a file for review.
"""
import os
import sys
import json
import asyncio
import logging
import time
from datetime import datetime
from dotenv import load_dotenv

# Set up proper import path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import core components
from src.agent_system.core.message import Message, MessageRole
from src.agent_system.core.workflow_manager import WorkflowManager
from src.registries.agent_registry import AgentRegistry

# Load environment variables
load_dotenv()

# Configure logging
log_dir = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')), "logs")
os.makedirs(log_dir, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"combiner_test_{timestamp}.log")

# Set up file handler
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Set up console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Set up specific logger for this test
logger = logging.getLogger("output_combiner_test")

class TestCallback:
    """Callback class for handling workflow step events"""
    
    def __init__(self):
        self.callbacks = {}
        self.events = []
        self.agent_outputs = {}
    
    def visualization_callback(self, agent_id: str):
        """Track agent visualization events."""
        logger.info(f"Visualization event from agent: {agent_id}")
        self.events.append({
            "type": "visualization",
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat()
        })
        return None
    
    def log_callback(self, agent_id: str, input_text: str, output_text: str, processing_time: int):
        """Track agent log events."""
        logger.info(f"Log event from agent: {agent_id} (processing time: {processing_time}ms)")
        self.events.append({
            "type": "log",
            "agent_id": agent_id,
            "input_length": len(input_text) if input_text else 0,
            "output_length": len(output_text) if output_text else 0,
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat()
        })
        
        # Store the agent output for later analysis
        self.agent_outputs[agent_id] = {
            "input": input_text,
            "output": output_text,
            "processing_time": processing_time
        }
        return None
    
    def stream_callback(self, agent_id: str, message_type: str, content: str, data: dict):
        """Track agent streaming events."""
        logger.info(f"Stream event from agent: {agent_id} (type: {message_type})")
        self.events.append({
            "type": "stream",
            "agent_id": agent_id,
            "message_type": message_type,
            "content_length": len(content) if content else 0,
            "timestamp": datetime.now().isoformat()
        })
        return None
    
    def get_callbacks(self):
        """Get the callback dictionary for the agent manager."""
        return {
            "visualization": self.visualization_callback,
            "log": self.log_callback,
            "stream": self.stream_callback
        }
    
    def save_events(self, output_file):
        """Save all recorded events to a file."""
        with open(output_file, 'w') as f:
            json.dump(self.events, f, indent=2)
        
        # Also save agent outputs
        agent_outputs_file = output_file.replace("events_", "agent_outputs_")
        with open(agent_outputs_file, 'w') as f:
            json.dump(self.agent_outputs, f, indent=2, default=str)
        
        return output_file, agent_outputs_file

async def test_workflow():
    """
    Run the Graph RAG Workflow with the test prompt and log all outputs.
    """
    logger.info("Starting workflow test")
    
    # Test prompt
    test_prompt = "I have a patient living in New York who plans travel to Saudi Arabia in September of this year. This patient has had dengue fever in the last 3 years. What advice should I give him regarding his trip?"
    
    logger.info(f"Test prompt: {test_prompt}")
    
    # Create workflow manager and registry
    agent_registry = AgentRegistry()
    
    # Get workflow registry directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    registry_dir = os.path.join(os.path.dirname(current_dir), "registries", "workflows")
    
    # Create workflow manager
    workflow_manager = WorkflowManager(registry_dir=registry_dir, agent_registry=agent_registry)
    
    # Create callback handler
    callback_handler = TestCallback()
    
    # Process the message
    logger.info(f"Processing message with workflow GRAPH_RAG_WORKFLOW")
    start_time = time.time()
    
    # Set workflow_id in metadata to ensure GRAPH_RAG_WORKFLOW is used
    result = await workflow_manager.process_message(
        message_content=test_prompt,
        user_id="test_user",
        callbacks=callback_handler.get_callbacks(),
        workflow_id="GRAPH_RAG_WORKFLOW"  # Explicitly specify which workflow to use
    )
    
    end_time = time.time()
    processing_time = round((end_time - start_time) * 1000)
    logger.info(f"Processing completed in {processing_time}ms")
    
    # Save events to a file
    events_file = os.path.join(log_dir, f"events_{timestamp}.json")
    events_file, agent_outputs_file = callback_handler.save_events(events_file)
    logger.info(f"Saved event log to {events_file}")
    logger.info(f"Saved agent outputs to {agent_outputs_file}")
    
    # Log the final result
    if result:
        logger.info("Final result received")
        logger.info(f"Result type: {type(result)}")
        
        # Save result content to a separate file for easy review
        content_file = os.path.join(log_dir, f"result_{timestamp}.md")
        with open(content_file, 'w') as f:
            f.write(result)
        logger.info(f"Result content saved to: {content_file}")
    else:
        logger.error("No result returned from workflow execution")
    
    logger.info(f"All logs saved to: {log_file}")
    return result

if __name__ == "__main__":
    try:
        print(f"Starting test with prompt about travel to Saudi Arabia...")
        print(f"Logs will be saved to: {log_file}")
        result = asyncio.run(test_workflow())
        print("\nTest completed. Check these files for details:")
        print(f"- Log file: {log_file}")
        print(f"- Result content: {os.path.join(log_dir, f'result_{timestamp}.md')}")
        print(f"- Events: {os.path.join(log_dir, f'events_{timestamp}.json')}")
    except Exception as e:
        logger.exception(f"Error running test: {e}")
        print(f"\nTest failed with error: {e}")
