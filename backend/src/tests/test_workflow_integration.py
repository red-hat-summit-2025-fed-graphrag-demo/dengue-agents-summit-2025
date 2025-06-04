"""
Test script for verifying that the HybridQueryWriterAgent integrates properly
with the full GRAPH_RAG_WORKFLOW.
"""
import os
import sys
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List

# Add the project root to the Python path
project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))

from src.agent_system.core.workflow_manager import WorkflowManager
from src.agent_system.core.message import Message, MessageRole

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("workflow_integration_test")

# Test queries to run through the workflow
TEST_QUERIES = [
    "What are the main symptoms of dengue fever?",
    "How is dengue fever transmitted?",
    "What climate factors affect dengue transmission?"
]

async def test_workflow_integration(query_index: int = 0):
    """Test the integration of HybridQueryWriterAgent in the workflow"""
    query = TEST_QUERIES[query_index]
    logger.info(f"Testing workflow integration with query: {query}")
    
    # Initialize the workflow manager with the proper directory containing workflow files
    registry_dir = os.path.join(project_root, "src", "registries")
    workflow_dir = os.path.join(registry_dir, "workflows")
    agent_registry_dir = os.path.join(registry_dir, "agents")
    
    logger.info(f"Loading workflows from: {workflow_dir}")
    logger.info(f"Loading agent configs from: {agent_registry_dir}")
    
    # Initialize the workflow manager directly with the workflows directory
    workflow_manager = WorkflowManager(registry_dir=workflow_dir)
    
    # List available workflows for logging
    if hasattr(workflow_manager, "_workflows"):
        logger.info(f"Available workflows: {list(workflow_manager._workflows.keys())}")
    
    # Create a message from the query
    message = Message(
        role=MessageRole.USER,
        content=query
    )
    
    # Process the message through the workflow
    workflow_id = "GRAPH_RAG_WORKFLOW"
    try:
        logger.info(f"Executing workflow {workflow_id} with query: {query}")
        # Call process_message with the correct signature
        result = await workflow_manager.process_message(
            message_content=query,
            user_id="test_user",
            session_id=None,
            metadata={"test": True},
            workflow_id=workflow_id
        )
        
        # Save the result to a file
        output_file = os.path.join(project_root, f"workflow_integration_result_{query_index}.md")
        with open(output_file, "w") as f:
            f.write(f"# Workflow Integration Test Result\n\n")
            f.write(f"## Query: {query}\n\n")
            
            # Handle the response content based on what's returned
            if isinstance(result, dict) and "response" in result:
                f.write(f"## Response:\n\n```\n{result['response']}\n```\n\n")
                
                # Extract and display metadata if available
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
            elif isinstance(result, Message):
                f.write(f"## Response:\n\n```\n{result.content}\n```\n\n")
                
                # Extract and display metadata if available
                if hasattr(result, 'metadata') and result.metadata:
                    f.write("## Metadata:\n\n")
                    for key, value in result.metadata.items():
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
                f.write(f"## Response (Unknown Type):\n\n```\n{str(result)}\n```\n\n")
        
        logger.info(f"Workflow integration test completed. Results saved to {output_file}")
        
    except Exception as e:
        logger.error(f"Error executing workflow: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run a specific test by index
        try:
            index = int(sys.argv[1])
            if 0 <= index < len(TEST_QUERIES):
                asyncio.run(test_workflow_integration(index))
            else:
                logger.error(f"Invalid query index. Must be between 0 and {len(TEST_QUERIES)-1}")
        except ValueError:
            logger.error("Please provide a valid integer index")
    else:
        # Run the first test by default
        asyncio.run(test_workflow_integration(0))
