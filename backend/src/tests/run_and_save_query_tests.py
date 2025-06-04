"""
Run GraphRAG query tests and save the results to a file.

This script runs a series of queries against the GraphRAG test workflow and saves
the generated Cypher queries and their results to a file for analysis.
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
logger = logging.getLogger("query_test_results")

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
        A dictionary containing the query and results
    """
    logger.info(f"=== Testing Query: {test_message} ===")
    
    # Load the agent registry
    agent_registry = AgentRegistry()
    
    # Create a workflow manager with the correct initialization
    workflow_manager = WorkflowManager(registry_dir=WORKFLOWS_REGISTRY_DIR, agent_registry=agent_registry)
    
    # Execute the workflow with the correct parameter names
    response = await workflow_manager.process_message(
        message_content=test_message,
        workflow_id=workflow_id
    )
    
    # Extract the query and results
    query = None
    results = []
    
    if (isinstance(response, dict) and 'metadata' in response and 
            'query' in response['metadata']):
        query = response['metadata']['query']
    
    # Try to extract results from the response
    try:
        if isinstance(response, dict) and 'response' in response:
            response_data = json.loads(response['response'])
            if 'results' in response_data:
                results = response_data['results']
    except (json.JSONDecodeError, KeyError):
        logger.warning(f"Could not extract results for query: {test_message}")
    
    return {
        "query": test_message,
        "cypher_query": query,
        "results": results
    }

async def run_query_tests():
    """Run tests for all the predefined test queries and save results to a file."""
    workflow_id = "QUERY_TEST_WORKFLOW"
    
    logger.info(f"Starting query workflow tests for workflow: {workflow_id}")
    logger.info(f"Testing {len(TEST_QUERIES)} different query patterns")
    
    # Run each test query
    all_results = []
    for i, query in enumerate(TEST_QUERIES):
        logger.info(f"\n\n=== Test #{i+1}: {query} ===")
        try:
            result = await test_workflow(workflow_id, query)
            all_results.append(result)
            logger.info(f"Test #{i+1} completed successfully")
        except Exception as e:
            logger.error(f"Error testing query '{query}': {str(e)}")
            all_results.append({
                "query": query,
                "error": str(e),
                "cypher_query": None,
                "results": []
            })
    
    # Save results to a file
    output_file = os.path.join(project_root, "query_test_results.json")
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)
    
    logger.info(f"Results saved to {output_file}")
    
    # Also create a markdown summary
    markdown_file = os.path.join(project_root, "query_test_results.md")
    with open(markdown_file, "w") as f:
        f.write("# GraphRAG Query Test Results\n\n")
        f.write("Generated on: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
        
        for i, result in enumerate(all_results):
            f.write(f"## Query {i+1}: {result['query']}\n\n")
            
            if "error" in result:
                f.write(f"**Error:** {result['error']}\n\n")
            else:
                f.write("### Generated Cypher Query\n\n")
                f.write("```cypher\n")
                f.write(result['cypher_query'] or "No query generated")
                f.write("\n```\n\n")
                
                f.write("### Results\n\n")
                if result['results']:
                    f.write("```json\n")
                    f.write(json.dumps(result['results'], indent=2))
                    f.write("\n```\n\n")
                else:
                    f.write("No results returned\n\n")
            
            f.write("---\n\n")
    
    logger.info(f"Markdown summary saved to {markdown_file}")
    
    return all_results

if __name__ == "__main__":
    asyncio.run(run_query_tests())
