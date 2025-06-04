"""
Test script for the hybrid query generation approach.

This script tests the HybridQueryWriterAgent, which uses ICL as primary and
two-step as fallback, with schema validation for query correctness.
"""
import os
import sys
import json
import logging
import asyncio
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))

from src.agent_system.rag_system.query.hybrid_query_writer_agent import HybridQueryWriterAgent
from src.agent_system.core.message import Message, MessageRole

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("hybrid_query_test")

# Test queries covering different aspects of dengue information
TEST_QUERIES = [
    "What are the symptoms of dengue fever?",
    "How is dengue fever transmitted?",
    "What are the warning signs of severe dengue?",
    # Deliberately invalid query to test fallback
    "What cryptocurrencies are affected by dengue?", 
    "How is dengue diagnosed?",
    "What treatments are available for dengue fever?",
    "How can I prevent dengue fever?",
    "What regions have high rates of dengue fever?",
    "What are the different types of dengue fever?",
    "What mosquito species transmit dengue?",
    "What climate factors affect dengue transmission?",
    "What are the risk factors for severe dengue?",
    "What are the complications of dengue fever?"
]

async def test_hybrid_query_writer_agent(query: str):
    """
    Test the HybridQueryWriterAgent with a specific query.
    
    Args:
        query: The query to test
        
    Returns:
        Generated cypher query string and approach used
    """
    logger.info(f"Testing query: {query}")
    
    # Initialize the HybridQueryWriterAgent
    agent_config = {
        "agent_id": "test_hybrid_query_writer_agent",
        "class_name": "HybridQueryWriterAgent",
        "model_config": {
            "model_type": "instruct",
            "temperature": 0.1,
            "max_tokens": 1024
        },
        "max_icl_attempts": 2  # Set to 2 for faster testing
    }
    
    agent = HybridQueryWriterAgent(
        agent_id="test_hybrid_query_writer_agent", 
        config=agent_config
    )
    
    # Create a message from the query
    message = Message(
        role=MessageRole.USER,
        content=query
    )
    
    # Process the message
    response_message, next_agent = await agent.process(message)
    
    # Extract the query information
    query_data = {}
    try:
        query_data = json.loads(response_message.content)
    except json.JSONDecodeError:
        logger.warning(f"Could not parse response content as JSON: {response_message.content}")
    
    generated_query = response_message.metadata.get("query", "No query generated")
    approach = response_message.metadata.get("approach", "unknown")
    
    logger.info(f"Generated query using {approach} approach: {generated_query}")
    
    return generated_query, approach

async def run_tests():
    """Run tests for all queries and save results."""
    results = []
    
    for query in TEST_QUERIES:
        try:
            generated_query, approach = await test_hybrid_query_writer_agent(query)
            results.append({
                "query": query,
                "generated_query": generated_query,
                "approach": approach
            })
            logger.info(f"Test for '{query}' completed successfully")
            logger.info("-" * 80)
        except Exception as e:
            logger.error(f"Error testing query '{query}': {str(e)}")
            results.append({
                "query": query,
                "error": str(e)
            })
    
    # Save results to a file
    output_file = os.path.join(project_root, "hybrid_query_results.md")
    with open(output_file, "w") as f:
        f.write("# Hybrid Query Generation Test Results\n\n")
        
        for i, result in enumerate(results):
            f.write(f"## Query {i+1}: {result['query']}\n\n")
            
            if "error" in result:
                f.write(f"**Error:** {result['error']}\n\n")
            else:
                f.write(f"**Approach Used:** {result.get('approach', 'unknown')}\n\n")
                f.write("**Generated Cypher Query:**\n\n")
                f.write("```cypher\n")
                f.write(result.get('generated_query', 'No query generated'))
                f.write("\n```\n\n")
            
            f.write("---\n\n")
    
    logger.info(f"Results saved to {output_file}")
    
    return results

if __name__ == "__main__":
    # Get command line arguments
    if len(sys.argv) > 1:
        # Run test with a single query
        query = " ".join(sys.argv[1:])
        asyncio.run(test_hybrid_query_writer_agent(query))
    else:
        # Run all tests
        asyncio.run(run_tests())
