"""
Test script for the Graph RAG workflow - comprehensive symptoms test with citations.

This test will execute a specific question about dengue symptoms through the
updated Graph RAG workflow and output the full response with citations.
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional, Callable, List

from src.agent_system.core.message import Message
from src.agent_system.core.workflow_manager import WorkflowManager
from src.registries.agent_registry import AgentRegistry
from src.registries.prompt_registry import PromptRegistry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Output paths
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "symptoms_test_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def test_comprehensive_symptoms():
    """
    Test the Graph RAG workflow with a dengue symptoms query.
    Captures the full processing details and agent outputs.
    """
    # Test query - specific question about dengue symptoms
    query = "What are the main symptoms of dengue fever, and how do they differ from similar diseases?"
    
    # Create output filename with timestamp to avoid overwriting
    timestamp = int(time.time())
    output_file = os.path.join(OUTPUT_DIR, f"symptoms_comprehensive_{timestamp}.md")
    
    # Initialize workflow manager with registries
    workflow_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "registries", "workflows")
    agent_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "registries", "agents")
    
    logger.info(f"Loading workflows from: {workflow_dir}")
    logger.info(f"Loading agent configs from: {agent_dir}")
    
    agent_registry = AgentRegistry()
    workflow_manager = WorkflowManager(workflow_dir, agent_registry)
    
    # Collect detailed agent processing logs
    thinking_logs = []
    processing_logs = []
    
    # Define callback functions
    async def visualization_callback(agent_id: str):
        """Called when an agent starts processing."""
        thinking_logs.append(f"## Agent: {agent_id}\n\n")
    
    async def log_callback(agent_id: str, input_text: str, output_text: str, processing_time: int):
        """Called after an agent completes processing."""
        processing_logs.append({
            "agent_id": agent_id,
            "input": input_text[:500] + ("..." if len(input_text) > 500 else ""),
            "output": output_text[:1000] + ("..." if len(output_text) > 1000 else ""),
            "processing_time_ms": processing_time
        })
    
    async def stream_callback(agent_id: str, message_type: str, content: str, data: Any):
        """Called when an agent streams thinking or other information."""
        if message_type == "thinking":
            thinking_logs.append(f"### {agent_id} thinking:\n\n{content}\n\n")
    
    # Set up callbacks
    callbacks = {
        "visualization": visualization_callback,
        "log": log_callback,
        "stream": stream_callback
    }
    
    # Execute the workflow
    logger.info(f"Executing workflow GRAPH_RAG_WORKFLOW with query: {query}")
    result = await workflow_manager.process_message(
        message_content=query,
        user_id="test_user",
        metadata={"test": True},
        callbacks=callbacks,
        workflow_id="GRAPH_RAG_WORKFLOW"
    )
    
    # Write results to a markdown file
    with open(output_file, "w") as f:
        f.write(f"# Comprehensive Symptoms Test Results\n\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Query:\n\n{query}\n\n")
        
        # Add response
        if isinstance(result, dict) and "response" in result:
            f.write(f"## Response:\n\n{result['response']}\n\n")
            
            # Extract metadata including citations
            if "metadata" in result:
                f.write("## Metadata:\n\n")
                for key, value in result["metadata"].items():
                    f.write(f"### {key}:\n")
                    try:
                        if isinstance(value, dict) or isinstance(value, list):
                            f.write("```json\n")
                            f.write(json.dumps(value, indent=2))
                            f.write("\n```\n\n")
                        else:
                            f.write(f"{value}\n\n")
                    except:
                        f.write(f"{str(value)}\n\n")
        else:
            f.write(f"## Response (Raw):\n\n```\n{json.dumps(result, indent=2)}\n```\n\n")
        
        # Add agent thinking logs
        f.write("## Agent Processing Details\n\n")
        for log in thinking_logs:
            f.write(log)
        
        # Add processing logs
        f.write("## Agent Processing Summary\n\n")
        for log in processing_logs:
            f.write(f"### {log['agent_id']}\n\n")
            f.write("**Input:**\n\n")
            f.write(f"```\n{log['input']}\n```\n\n")
            f.write("**Output:**\n\n")
            f.write(f"```\n{log['output']}\n```\n\n")
            f.write(f"**Processing Time:** {log['processing_time_ms']} ms\n\n")
    
    logger.info(f"Comprehensive symptoms test completed. Results saved to {output_file}")
    
    # Return the path to the output file
    return output_file

if __name__ == "__main__":
    """Run the test when script is executed directly."""
    asyncio.run(test_comprehensive_symptoms())
