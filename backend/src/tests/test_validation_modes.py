"""
Test script for demonstrating different validation modes in HybridQueryWriterAgent.

This script compares relaxed validation (default) with strict validation on the same query.
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

from src.agent_system.rag_system.query.hybrid_query_writer_agent import HybridQueryWriterAgent
from src.agent_system.core.message import Message, MessageRole

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("validation_test")

# Test queries specifically designed to test validation differences
TEST_QUERIES = [
    # This query uses a non-existent relationship type
    "What is the relationship between rainfall patterns and mosquito breeding cycles in dengue transmission?",
    
    # This query deliberately lacks citation nodes
    "What organizations fund dengue research and what treatments have they developed?"
]

async def test_validation_modes(query_index: int = 0):
    """Test both validation modes on the same query"""
    query = TEST_QUERIES[query_index]
    logger.info(f"Testing validation modes on query: {query}")
    
    results = []
    
    # Test with relaxed validation first (default)
    logger.info("TESTING WITH RELAXED VALIDATION (DEFAULT)")
    relaxed_result = await run_with_validation_mode(query, strict=False)
    results.append(("relaxed", relaxed_result))
    
    # Then test with strict validation
    logger.info("TESTING WITH STRICT VALIDATION")
    strict_result = await run_with_validation_mode(query, strict=True)
    results.append(("strict", strict_result))
    
    # Save results to markdown file
    output_file = os.path.join(project_root, f"validation_test_results_{query_index}.md")
    with open(output_file, "w") as f:
        f.write("# Validation Modes Comparison\n\n")
        f.write(f"## Query: {query}\n\n")
        
        for mode, result in results:
            f.write(f"## {mode.upper()} VALIDATION MODE\n\n")
            f.write(f"**Valid Query:** {result['is_valid']}\n\n")
            
            if not result['is_valid']:
                f.write(f"**Validation Error:** {result['error']}\n\n")
            
            f.write("**Generated Cypher Query:**\n\n")
            f.write("```cypher\n")
            f.write(result['query'])
            f.write("\n```\n\n")
            
            f.write("**Approach Used:** " + result.get('approach', 'unknown') + "\n\n")
            f.write("**Attempts Required:** " + str(result.get('attempts', 0)) + "\n\n")
            
            if 'conversation' in result:
                f.write("### Conversation Exchange\n\n")
                for msg in result['conversation']:
                    if msg['role'] == 'user':
                        f.write(f"**USER:** {msg['content']}\n\n")
                    else:
                        f.write(f"**ASSISTANT:** {msg['content']}\n\n")
            
            f.write("---\n\n")
        
    logger.info(f"Results saved to {output_file}")

async def run_with_validation_mode(query: str, strict: bool) -> Dict[str, Any]:
    """Run the query with a specific validation mode"""
    # Initialize the agent with the specified validation mode
    agent_config = {
        "agent_id": "test_hybrid_agent",
        "class_name": "HybridQueryWriterAgent",
        "model_config": {
            "model_type": "instruct",
            "temperature": 0.1,
            "max_tokens": 1024
        },
        "max_icl_attempts": 2,  # Set to 2 for faster testing
        "strict_validation": strict  # Set validation mode
    }
    
    agent = HybridQueryWriterAgent(
        agent_id="test_hybrid_agent", 
        config=agent_config
    )
    
    # Create a message from the query
    message = Message(
        role=MessageRole.USER,
        content=query
    )
    
    # Process the message
    response_message, _ = await agent.process(message)
    
    # Extract information from the response
    query_data = {}
    try:
        query_data = json.loads(response_message.content)
    except json.JSONDecodeError:
        logger.warning(f"Could not parse response content as JSON: {response_message.content}")
    
    # Get query and validation information
    generated_query = response_message.metadata.get("query", "No query generated")
    approach = response_message.metadata.get("approach", "unknown")
    attempts = response_message.metadata.get("attempts", 0)
    
    # Check if the query is valid
    is_valid = True
    error = ""
    
    # If using ICL approach with multiple attempts or fallback to two-step, query had validation issues
    if attempts > 1 or approach == "two_step" or approach == "fallback":
        is_valid = False
        error = "Query failed validation and required multiple attempts or fallback"
    
    # Return all relevant information
    return {
        "query": generated_query,
        "is_valid": is_valid,
        "error": error,
        "approach": approach,
        "attempts": attempts
    }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run a specific test by index
        try:
            index = int(sys.argv[1])
            if 0 <= index < len(TEST_QUERIES):
                asyncio.run(test_validation_modes(index))
            else:
                logger.error(f"Invalid query index. Must be between 0 and {len(TEST_QUERIES)-1}")
        except ValueError:
            logger.error("Please provide a valid integer index")
    else:
        # Run the first test by default
        asyncio.run(test_validation_modes(0))
