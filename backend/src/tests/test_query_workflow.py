"""
Test script for the Query Generation and Execution Workflow.

This script tests the query generation and execution pipeline without the safety
wrapping or response generation. It allows us to see the raw Cypher queries
being generated and their results.
"""
import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))

from src.agent_system.core.workflow_manager import WorkflowManager
from src.registries.agent_registry import AgentRegistry
from src.agent_system.core.message import Message, MessageRole

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("query_workflow_test")

# Path to the workflows registry directory
WORKFLOWS_REGISTRY_DIR = os.path.join(project_root, "src", "registries", "workflows")

# Test queries covering different aspects of dengue information
TEST_QUERIES = [
    "What are the symptoms of dengue fever?",
    "How is dengue fever transmitted?",
    "What are the warning signs of severe dengue?",
    "How is dengue diagnosed?",
    "What treatments are available for dengue fever?",
    "How can I prevent dengue fever?",
    "What regions have high rates of dengue fever?",
    "What are the different types of dengue fever?",
    "What mosquito species transmit dengue?",
    "What climate factors affect dengue transmission?"
]

async def test_workflow(workflow_id: str, test_message: str) -> dict:
    """
    Test a specific workflow with the given message.
    
    Args:
        workflow_id: The ID of the workflow to test
        test_message: The test message to send through the workflow
        
    Returns:
        The workflow response
    """
    logger.info(f"=== Testing Query: {test_message} ===")
    
    # Load the agent registry
    agent_registry = AgentRegistry()
    
    # Create a workflow manager with the correct initialization
    workflow_manager = WorkflowManager(registry_dir=WORKFLOWS_REGISTRY_DIR, agent_registry=agent_registry)
    
    # Start timing
    start_time = datetime.now()
    
    # Execute the workflow with the correct parameter names
    response = await workflow_manager.process_message(
        message_content=test_message,
        workflow_id=workflow_id
    )
    
    # End timing
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    
    logger.info(f"Response time: {elapsed:.2f}s")
    
    # Extract the last message from the response (if it's a dict with 'messages')
    last_message = None
    if isinstance(response, dict) and 'messages' in response and response['messages']:
        last_message = response['messages'][-1]
    
    # Log the query that was generated
    try:
        if last_message and hasattr(last_message, 'metadata') and 'query' in last_message.metadata:
            logger.info(f"Generated Cypher Query: {last_message.metadata['query']}")
    except (AttributeError, TypeError):
        logger.warning("Could not extract query from response metadata")
    
    # Format and print the response content nicely
    try:
        if last_message and hasattr(last_message, 'content'):
            content = last_message.content
            # Try to parse the content as JSON
            content_data = json.loads(content)
            logger.info("Query Execution Results:")
            logger.info(json.dumps(content_data, indent=2))
        else:
            # If not a message object, print as is
            logger.info("Query Execution Results (raw):")
            logger.info(json.dumps(response, indent=2) if isinstance(response, dict) else str(response))
    except (json.JSONDecodeError, AttributeError):
        # If not valid JSON, print as is
        logger.info("Query Execution Results (raw):")
        logger.info(str(response))
    
    return response

async def run_query_tests():
    """Run tests for all the predefined test queries."""
    workflow_id = "QUERY_TEST_WORKFLOW"
    
    logger.info(f"Starting query workflow tests for workflow: {workflow_id}")
    logger.info(f"Testing {len(TEST_QUERIES)} different query patterns")
    
    # Run each test query
    results = []
    for i, query in enumerate(TEST_QUERIES):
        logger.info(f"\n\n=== Test #{i+1}: {query} ===")
        try:
            response = await test_workflow(workflow_id, query)
            results.append({
                "query": query,
                "success": True,
                "response": response.content if hasattr(response, 'content') else str(response)
            })
            logger.info(f"Test #{i+1} completed successfully")
        except Exception as e:
            logger.error(f"Error testing query '{query}': {str(e)}")
            results.append({
                "query": query,
                "success": False,
                "error": str(e)
            })
    
    # Print summary
    logger.info("\n\n=== TEST SUMMARY ===")
    success_count = sum(1 for r in results if r["success"])
    logger.info(f"Tested {len(results)} queries")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {len(results) - success_count}")
    
    return results

async def test_single_query(query: str):
    """Run a test for a single specified query."""
    workflow_id = "QUERY_TEST_WORKFLOW"
    
    logger.info(f"Testing query: {query}")
    try:
        response = await test_workflow(workflow_id, query)
        logger.info("Test completed successfully")
        return response
    except Exception as e:
        logger.error(f"Error testing query '{query}': {str(e)}")
        return None

if __name__ == "__main__":
    # Check if a specific query was provided
    if len(sys.argv) > 1:
        # Join all arguments as a single query string
        query = " ".join(sys.argv[1:])
        asyncio.run(test_single_query(query))
    else:
        # Run all test queries
        asyncio.run(run_query_tests())
