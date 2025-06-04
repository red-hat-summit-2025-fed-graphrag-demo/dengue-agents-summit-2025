"""
Test for DengueDataVisualizationAgent with unsupported countries

This script tests the DengueDataVisualizationAgent with a query about an unsupported country
to verify that it correctly handles the case and provides appropriate response.
"""
import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
import pytest

from src.agent_system.rag_system.enhancement.dengue_data_visualization_agent import DengueDataVisualizationAgent
from src.agent_system.core.message import Message, MessageRole
from src.agent_system.rag_system.synthesis.response_generator_agent import ResponseGeneratorAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.anyio
async def test_unsupported_country_visualization():
    """Test the DengueDataVisualizationAgent with an unsupported country query."""
    
    # Create agent configuration
    agent_config = {
        "agent_id": "dengue_data_viz_test",
        "model_config": {
            "model_type": "instruct",
            "max_tokens": 512,
            "temperature": 0.2
        }
    }
    
    # Initialize the visualization agent
    viz_agent = DengueDataVisualizationAgent(agent_id="dengue_data_viz_test", config=agent_config)
    
    # Create a test query for an unsupported country (Zimbabwe)
    test_query = """
    I have a patient living in New York who plans travel to Zimbabwe in September of this year. 
    This patient has had dengue fever in the last 3 years. What advice should I give him regarding his trip?
    """
    
    # Create a message object to simulate another agent's request
    message = Message(
        role=MessageRole.USER,
        content=test_query,
        metadata={
            "original_query": test_query
        }
    )
    
    logger.info(f"Processing test query for unsupported country: {test_query}")
    
    # Process the message through the visualization agent
    viz_response, next_agent_id = await viz_agent.process(message)
    
    # Extract the visualization data
    if viz_response:
        # Initialize the response generator agent
        response_config = {
            "agent_id": "response_generator_test",
            "model_config": {
                "model_type": "instruct",
                "max_tokens": 1024,
                "temperature": 0.5
            }
        }
        
        resp_agent = ResponseGeneratorAgent(agent_id="response_generator_test", config=response_config)
        
        # Create a message for the response generator with the visualization data
        resp_message = Message(
            role=MessageRole.SYSTEM,
            content="Generate a response based on the provided visualization data.",
            metadata={
                "original_query": test_query,
                "visualization_data": viz_response.metadata.get('dengue_data', {}) if viz_response and viz_response.metadata else {}
            }
        )
        
        # Process the message through the response generator
        final_response, _ = await resp_agent.process(resp_message)
        
        # Create results directory if it doesn't exist
        output_dir = Path("unsupported_country_results")
        os.makedirs(output_dir, exist_ok=True)
        
        # Create a timestamped output filename
        timestamp = int(datetime.now().timestamp())
        output_file = output_dir / f"unsupported_country_test_{timestamp}.md"
        
        # Write results to markdown file
        with open(output_file, "w") as f:
            f.write("# Unsupported Country Test Results\n\n")
            f.write(f"Test performed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"Query: {test_query}\n\n")
            
            # Add visualization data
            if viz_response and viz_response.metadata and 'dengue_data' in viz_response.metadata:
                f.write("## Visualization Agent Response\n\n")
                f.write("```json\n")
                f.write(json.dumps(viz_response.metadata['dengue_data'], indent=2))
                f.write("\n```\n\n")
                
                # Check for unsupported countries
                if "unsupported_countries" in viz_response.metadata['dengue_data']:
                    f.write(f"### Unsupported Countries\n\n")
                    f.write(f"The following countries are not supported: {', '.join(viz_response.metadata['dengue_data']['unsupported_countries'])}\n\n")
            
            # Add response generator output
            if final_response:
                f.write("## Final Response\n\n")
                f.write(final_response.content)
        
        # Also write to the main dengue_response.md file
        user_md_file = Path("/Users/wesjackson/Code/Summit2025/dengue-agents-summit-2025/dengue_response.md")
        with open(user_md_file, 'w') as f:
            f.write("# Dengue Data Analysis Report\n\nRESPONSE:\n\n")
            if final_response and final_response.content:
                f.write(final_response.content)
        
        logger.info(f"Test results written to {output_file}")
        logger.info(f"User response written to {user_md_file}")
        return str(output_file)
    else:
        logger.error("No response received from agent")
        return None

if __name__ == "__main__":
    # Run the test
    output_file = asyncio.run(test_unsupported_country_visualization())
    if output_file:
        print(f"Test completed successfully! Results saved to: {output_file}")
        print(f"Response also saved to: /Users/wesjackson/Code/Summit2025/dengue-agents-summit-2025/dengue_response.md")
    else:
        print("Test failed! No output file was created.")
