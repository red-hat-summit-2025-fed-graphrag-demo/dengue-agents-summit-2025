"""
Test script for the conversational feedback approach to query validation.

This script tests the HybridQueryWriterAgent with a focus on how it handles
validation errors using conversational feedback.
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
logger = logging.getLogger("feedback_query_test")

# Test queries that are likely to produce validation errors initially
TEST_QUERIES = [
    # This query uses non-existent relationship types
    "What is the relationship between dengue serotypes and disease severity?",
    
    # This query might trigger incorrect relationship direction
    "Tell me about mosquitoes and dengue fever transmission",
    
    # This query involves complex relationships
    "How do climate factors affect dengue transmission in different regions?",
    
    # This query will need sophisticated handling
    "What treatments work best for severe dengue complications?",
    
    # This query deliberately contains invalid entities to test feedback
    "Explain the connection between INVALID_NODE_LABEL and NONEXISTENT_RELATIONSHIP_TYPE in dengue fever research",
]

async def test_hybrid_query_writer_with_feedback(query: str):
    """
    Test the HybridQueryWriterAgent with a specific query, focusing on feedback.
    
    Args:
        query: The query to test
    """
    logger.info(f"Testing query with feedback: {query}")
    
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
    
    # Get key information from response
    generated_query = response_message.metadata.get("query", "No query generated")
    approach = response_message.metadata.get("approach", "unknown")
    
    # Get attempts from metadata (not content)
    attempts = response_message.metadata.get("attempts", 0)
    
    logger.info(f"Generated query using {approach} approach after {attempts} attempts:")
    logger.info(f"{generated_query}")
    
    return {
        "query": query,
        "generated_query": generated_query,
        "approach": approach,
        "attempts": attempts
    }

async def run_tests():
    """Run tests for all queries and save results."""
    results = []
    
    for query in TEST_QUERIES:
        try:
            result = await test_hybrid_query_writer_with_feedback(query)
            results.append(result)
            logger.info(f"Test for '{query}' completed successfully")
            logger.info("-" * 80)
        except Exception as e:
            logger.error(f"Error testing query '{query}': {str(e)}")
            results.append({
                "query": query,
                "error": str(e)
            })
    
    # Save results to a file
    output_file = os.path.join(project_root, "feedback_query_results.md")
    with open(output_file, "w") as f:
        f.write("# Feedback-Based Query Generation Test Results\n\n")
        
        for i, result in enumerate(results):
            f.write(f"## Query {i+1}: {result['query']}\n\n")
            
            if "error" in result:
                f.write(f"**Error:** {result['error']}\n\n")
            else:
                f.write(f"**Approach Used:** {result.get('approach', 'unknown')}\n\n")
                f.write(f"**Attempts Required:** {result.get('attempts', 0)}\n\n")
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
        asyncio.run(test_hybrid_query_writer_with_feedback(query))
    else:
        # Run all tests
        asyncio.run(run_tests())
