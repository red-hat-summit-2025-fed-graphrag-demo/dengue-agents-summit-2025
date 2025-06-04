#!/usr/bin/env python
"""
Direct test script for simple_query_writer_agent and graph_query_executor_agent without workflow manager.
"""
import os
import sys
import asyncio
import logging
import json
import time
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

# Import necessary components after path setup
from src.agent_system.core.message import Message, MessageRole
from src.agent_system.rag_system.query.simple_query_writer_agent import SimpleQueryWriterAgent
from src.agent_system.rag_system.retrieval.graph_query_executor_agent import GraphQueryExecutorAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("query_agents_test")

async def test_query_agents(message: str) -> None:
    """
    Test the simple_query_writer_agent and graph_query_executor_agent directly.
    
    Args:
        message: Test message to process
    """
    logger.info(f"=== Testing Query Agents Directly ===")
    logger.info(f"Test message: {message}")
    
    # Initialize the simple_query_writer_agent
    query_writer_config = {
        "agent_id": "simple_query_writer_agent",
        "name": "Simple Query Writer Agent",
        "model_config": {
            "model_type": "instruct",
            "temperature": 0.2
        }
    }
    
    # Initialize the graph_query_executor_agent
    query_executor_config = {
        "agent_id": "graph_query_executor_agent",
        "name": "Graph Query Executor Agent",
        "model_config": {
            "model_type": "instruct",
            "temperature": 0.2
        }
    }
    
    # Create agent instances
    query_writer = SimpleQueryWriterAgent(
        agent_id="simple_query_writer_agent", 
        config=query_writer_config
    )
    
    query_executor = GraphQueryExecutorAgent(
        agent_id="graph_query_executor_agent", 
        config=query_executor_config
    )
    
    # Create input message for query writer
    input_message = Message(
        role=MessageRole.USER,
        content=message
    )
    
    try:
        # Process with query writer
        logger.info("Processing with simple_query_writer_agent...")
        query_writer_response, next_agent = await query_writer.process(input_message)
        
        # Log the query writer output
        logger.info(f"Query Writer Output:")
        logger.info(f"Content: {query_writer_response.content[:100]}...")
        logger.info(f"Metadata: {json.dumps(query_writer_response.metadata, indent=2)}")
        logger.info(f"Next agent: {next_agent}")
        
        # Process with query executor
        logger.info("Processing with graph_query_executor_agent...")
        query_executor_response, _ = await query_executor.process(query_writer_response)
        
        # Log the query executor output
        logger.info(f"Query Executor Output:")
        logger.info(f"Content: {query_executor_response.content[:100]}...")
        logger.info(f"Metadata: {json.dumps(query_executor_response.metadata, indent=2)}")
        
        # Print results if available
        if "results" in query_executor_response.metadata:
            results = query_executor_response.metadata["results"]
            logger.info(f"Number of results: {len(results)}")
            for i, result in enumerate(results[:5]):  # Show first 5 results
                logger.info(f"Result {i+1}: {result}")
        
    except Exception as e:
        logger.error(f"Error testing query agents: {str(e)}", exc_info=True)
        
async def main() -> int:
    """Main test function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test query agents directly")
    parser.add_argument("message", help="Test message to process")
    
    args = parser.parse_args()
    
    logger.info("Starting direct query agents test...")
    await test_query_agents(args.message)
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
