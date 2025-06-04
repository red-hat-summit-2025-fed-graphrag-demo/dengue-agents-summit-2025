"""
Test script for the ICL-based graph query generation approach.

This script directly tests the ICLGraphQueryWriterAgent in isolation to evaluate
the in-context learning approach for generating Cypher queries.
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

from src.agent_system.rag_system.query.icl_graph_query_writer_agent import ICLGraphQueryWriterAgent
from src.agent_system.core.message import Message, MessageRole

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("icl_query_test")

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
    "What climate factors affect dengue transmission?",
    "What are the risk factors for severe dengue?",
    "What are the complications of dengue fever?"
]

async def test_icl_query_writer_agent(query: str):
    """
    Test the ICLGraphQueryWriterAgent with a specific query.
    
    Args:
        query: The query to test
        
    Returns:
        Generated cypher query string
    """
    logger.info(f"Testing query: {query}")
    
    # Initialize the ICLGraphQueryWriterAgent
    agent_config = {
        "agent_id": "test_icl_query_writer_agent",
        "prompt_id": "rag.icl_graph_query_generator",
        "class_name": "ICLGraphQueryWriterAgent",
        "model_config": {
            "model_type": "instruct",
            "temperature": 0.1,
            "max_tokens": 1024
        }
    }
    
    agent = ICLGraphQueryWriterAgent(
        agent_id="test_icl_query_writer_agent", 
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
    reasoning = query_data.get("reasoning", "No reasoning provided")
    
    logger.info(f"Generated query: {generated_query}")
    logger.info(f"Reasoning: {reasoning}")
    
    return generated_query

async def run_tests():
    """Run tests for all queries and save results."""
    results = []
    
    for query in TEST_QUERIES:
        try:
            generated_query = await test_icl_query_writer_agent(query)
            results.append({
                "query": query,
                "generated_query": generated_query
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
    output_file = os.path.join(project_root, "icl_query_results.md")
    with open(output_file, "w") as f:
        f.write("# ICL Graph Query Generation Test Results\n\n")
        
        for i, result in enumerate(results):
            f.write(f"## Query {i+1}: {result['query']}\n\n")
            
            if "error" in result:
                f.write(f"**Error:** {result['error']}\n\n")
            else:
                f.write("**Generated Cypher Query:**\n\n")
                f.write("```cypher\n")
                f.write(result.get('generated_query', 'No query generated'))
                f.write("\n```\n\n")
            
            f.write("---\n\n")
    
    logger.info(f"Results saved to {output_file}")
    
    return results

async def compare_approaches(query: str):
    """
    Compare both query generation approaches (two-step vs ICL) for a specific query.
    
    Args:
        query: The query to test with both approaches
    """
    # Import two-step agent
    from src.agent_system.rag_system.query.query_writer_agent import QueryWriterAgent
    
    logger.info(f"Comparing approaches for query: {query}")
    
    # Initialize the ICL agent
    icl_agent_config = {
        "agent_id": "test_icl_query_writer_agent",
        "prompt_id": "rag.icl_graph_query_generator",
        "class_name": "ICLGraphQueryWriterAgent",
        "model_config": {
            "model_type": "instruct",
            "temperature": 0.1,
            "max_tokens": 1024
        }
    }
    
    icl_agent = ICLGraphQueryWriterAgent(
        agent_id="test_icl_query_writer_agent", 
        config=icl_agent_config
    )
    
    # Initialize the two-step agent
    two_step_agent_config = {
        "agent_id": "test_two_step_query_writer_agent",
        "prompt_id": "rag.graph_query_generator",
        "class_name": "QueryWriterAgent",
        "model_config": {
            "model_type": "instruct",
            "temperature": 0.1,
            "max_tokens": 1024
        }
    }
    
    two_step_agent = QueryWriterAgent(
        agent_id="test_two_step_query_writer_agent", 
        config=two_step_agent_config
    )
    
    # Create a message from the query
    message = Message(
        role=MessageRole.USER,
        content=query
    )
    
    # Process the message with both agents
    logger.info("Processing with ICL agent...")
    icl_response, _ = await icl_agent.process(message)
    
    logger.info("Processing with two-step agent...")
    two_step_response, _ = await two_step_agent.process(message)
    
    # Extract the query information
    icl_query = icl_response.metadata.get("query", "No query generated")
    two_step_query = two_step_response.metadata.get("query", "No query generated")
    
    # Print results
    logger.info("\n" + "=" * 80)
    logger.info(f"QUERY: {query}")
    logger.info("\nICL APPROACH:\n")
    logger.info(icl_query)
    logger.info("\nTWO-STEP APPROACH:\n")
    logger.info(two_step_query)
    logger.info("=" * 80)
    
    # Save results to a file
    output_file = os.path.join(project_root, "approach_comparison.md")
    with open(output_file, "w") as f:
        f.write(f"# Query Approach Comparison\n\n")
        f.write(f"## Query: {query}\n\n")
        
        f.write("### ICL Approach\n\n")
        f.write("```cypher\n")
        f.write(icl_query)
        f.write("\n```\n\n")
        
        f.write("### Two-Step Approach\n\n")
        f.write("```cypher\n")
        f.write(two_step_query)
        f.write("\n```\n\n")
    
    logger.info(f"Comparison saved to {output_file}")
    
    return icl_query, two_step_query

if __name__ == "__main__":
    # Get command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--compare" and len(sys.argv) > 2:
            # Run comparison mode with the specified query
            query = " ".join(sys.argv[2:])
            asyncio.run(compare_approaches(query))
        else:
            # Run test with a single query
            query = " ".join(sys.argv[1:])
            asyncio.run(test_icl_query_writer_agent(query))
    else:
        # Run all tests
        asyncio.run(run_tests())
