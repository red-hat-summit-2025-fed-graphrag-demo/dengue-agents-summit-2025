"""
Test script for DengueDataVisualizationAgent.

This script directly tests the agent's ability to extract country mentions
and retrieve data for countries that have available data.
"""

import asyncio
import json
import logging
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.src.agent_system.core.message import Message, MessageRole
from backend.src.agent_system.rag_system.enhancement.dengue_data_visualization_agent import DengueDataVisualizationAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("test_visualization_agent")

async def test_agent():
    """Test the visualization agent with a sample query."""
    # Create a test query
    test_query = "I have a patient who lives in New York and plans to travel to Saudi Arabia on September 1, 2025. What should I tell him about how to protect himself from dengue? He has had dengue before."
    
    # Create a message with the test query
    message = Message(
        role=MessageRole.USER,
        content=test_query,
        metadata={
            "original_query": test_query
        }
    )
    
    # Initialize the agent
    agent_config = {
        "agent_id": "dengue_data_visualization_agent",
        "dengue_api_url": "https://dengue-prediction-service-model-service-dengue.apps.cluster-8gvkk.8gvkk.sandbox888.opentlc.com"
    }
    
    agent = DengueDataVisualizationAgent("dengue_data_visualization_agent", agent_config)
    
    logger.info("Testing DengueDataVisualizationAgent with query: %s", test_query)
    
    try:
        # Process the message
        response, next_agent = await agent._execute_processing(message)
        
        # Log the results
        if response:
            logger.info("Agent response received. Metadata keys: %s", list(response.metadata.keys()))
            
            if "countries" in response.metadata:
                logger.info("Detected countries: %s", response.metadata["countries"])
            
            if "dengue_data" in response.metadata:
                dengue_data = response.metadata["dengue_data"]
                logger.info("Dengue data received. Country data count: %d", 
                           len(dengue_data.get("countries_data", [])))
                
                # Save the dengue data to a file for examination
                with open("dengue_data_response.json", "w") as f:
                    json.dump(dengue_data, f, indent=2)
                    logger.info("Saved dengue data to dengue_data_response.json")
        else:
            logger.error("No response received from agent")
            
    except Exception as e:
        logger.exception("Error testing visualization agent: %s", str(e))
        
if __name__ == "__main__":
    asyncio.run(test_agent())
