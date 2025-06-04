#!/usr/bin/env python
"""
Direct agent integration test.

This script tests two connected agents directly, bypassing the workflow manager
to verify they work properly when exchanging metadata.
"""
import os
import sys
import asyncio
import logging
from typing import Dict, Any, Optional

# Determine the backend directory and ensure it's in the Python path
script_path = os.path.abspath(__file__)
tests_dir = os.path.dirname(script_path)
src_dir = os.path.dirname(tests_dir)
backend_dir = os.path.dirname(src_dir)

# Ensure backend directory is in Python path
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import necessary classes
from src.agent_system.core.message import Message, MessageRole
from src.agent_system.core.metadata import MetadataKeys, QueryMetadata
from src.agent_system.rag_system.query.simple_query_writer_agent import SimpleQueryWriterAgent
from src.agent_system.rag_system.retrieval.graph_query_executor_agent import GraphQueryExecutorAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("direct_test")

async def test_direct_agent_connection(query: str) -> None:
    """
    Test two agents connected directly without the workflow manager.
    
    Args:
        query: Query to test with
    """
    logger.info("=" * 60)
    logger.info("Starting direct agent test")
    logger.info("=" * 60)
    
    # Generate a test session ID
    session_id = "direct-test-session"
    
    # 1. Create the agents
    logger.info("Initializing QueryWriterAgent...")
    query_writer = SimpleQueryWriterAgent(
        agent_id="simple_query_writer_agent",
        config={
            "model_config": {
                "model_type": "instruct",
                "temperature": 0.0
            }
        }
    )
    
    logger.info("Initializing GraphQueryExecutorAgent...")
    query_executor = GraphQueryExecutorAgent(
        config={
            "agent_id": "graph_query_executor_agent",
            "model_config": {
                "model_type": "instruct",
                "temperature": 0.0
            }
        }
    )
    
    # 2. Create initial message
    user_message = Message(
        role=MessageRole.USER,
        content=query
    )
    
    # 3. Process through first agent
    logger.info(f"Processing query through SimpleQueryWriterAgent: {query}")
    query_response, next_agent_id = await query_writer.process(
        user_message, 
        session_id
    )
    
    # 4. Log the first agent's output
    logger.info("-" * 60)
    logger.info(f"QueryWriter Result: {query_response.content}")
    logger.info(f"Next agent: {next_agent_id}")
    logger.info(f"Metadata keys: {list(query_response.metadata.keys())}")
    logger.info(f"Full metadata: {query_response.metadata}")
    logger.info("-" * 60)
    
    # 5. Process through second agent
    logger.info("Processing through GraphQueryExecutorAgent")
    executor_response, final_next_agent_id = await query_executor.process(
        query_response,  # Pass the first agent's response directly
        session_id
    )
    
    # 6. Log the result
    logger.info("=" * 60)
    logger.info("FINAL RESULT")
    logger.info("=" * 60)
    logger.info(f"Response: {executor_response.content}")
    logger.info(f"Next agent: {final_next_agent_id}")
    logger.info(f"Metadata keys: {list(executor_response.metadata.keys())}")
    logger.info("=" * 60)
    
    # Check if we got a successful result or error
    if "error" in executor_response.metadata:
        logger.error(f"Test failed with error: {executor_response.metadata.get('error')}")
        return False
    else:
        logger.info("Test completed successfully!")
        return True

async def main() -> None:
    """Main function to run the test."""
    # Test with a specific query
    test_query = "What are the symptoms of dengue fever?"
    await test_direct_agent_connection(test_query)
    
if __name__ == "__main__":
    asyncio.run(main())
