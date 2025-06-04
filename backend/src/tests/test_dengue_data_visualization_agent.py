"""
Test for DengueDataVisualizationAgent

This script tests the DengueDataVisualizationAgent by simulating a query from another agent,
processing it through the visualization agent, and saving the results to a file.
"""
import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path

from src.agent_system.rag_system.enhancement.dengue_data_visualization_agent import DengueDataVisualizationAgent
from src.agent_system.core.message import Message, MessageRole

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_dengue_visualization_agent():
    """Test the DengueDataVisualizationAgent with a sample query."""
    
    # Create agent configuration
    agent_config = {
        "agent_id": "dengue_data_viz_test",
        "model_config": {
            "model_type": "instruct",
            "max_tokens": 512,
            "temperature": 0.2
        },
        # By default, the agent will use the URL from the DENGUE_DATA_URL env var or the default URL
        # defined in DengueDataTool if neither is provided here
    }
    
    # Initialize the agent
    agent = DengueDataVisualizationAgent(agent_id="dengue_data_viz_test", config=agent_config)
    
    # Create a test query for dengue data that another agent might send
    # This includes the date range specified (July 1, 2024 to September 1, 2025)
    test_query = """
    Provide dengue fever information for Saudi Arabia with historical data and predictions 
    for the period from July 1, 2024 to September 1, 2025. Include analysis of trends and 
    visualization data for this time period.
    """
    
    # Create a message object to simulate another agent's request
    message = Message(
        role=MessageRole.USER,
        content=test_query,
        metadata={
            "original_query": test_query,
            "date_range": {
                "start": "2024-07-01",
                "end": "2025-09-01"
            }
        }
    )
    
    logger.info(f"Processing test query: {test_query}")
    
    # Process the message through the agent
    response_message, next_agent_id = await agent.process(message)
    
    # Extract the results
    if response_message:
        # Create results directory if it doesn't exist
        output_dir = Path("saudi_visualization_results")
        os.makedirs(output_dir, exist_ok=True)
        
        # Create a timestamped output filename
        timestamp = int(datetime.now().timestamp())
        output_file = output_dir / f"saudi_visualization_test_{timestamp}.md"
        
        # Parse the JSON response
        try:
            result_data = json.loads(response_message.content)
            
            # Create a markdown report with the results
            with open(output_file, "w") as f:
                f.write("# Dengue Data Visualization Test Results\n\n")
                f.write(f"Test performed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"Query: {test_query}\n\n")
                f.write(f"Next agent: {next_agent_id}\n\n")
                
                # Add metadata
                f.write("## Metadata\n\n")
                f.write("```json\n")
                f.write(json.dumps(response_message.metadata, indent=2))
                f.write("\n```\n\n")
                
                # Add countries data
                f.write("## Countries Data\n\n")
                for country_data in result_data.get("countries_data", []):
                    country = country_data.get("country", "Unknown")
                    api_country = country_data.get("api_country", "Unknown")
                    
                    f.write(f"### {country} (API Source: {api_country})\n\n")
                    
                    # Historical data points
                    historical_data = country_data.get("historical_data", [])
                    f.write(f"Historical data points: {len(historical_data)}\n\n")
                    
                    # Sample of historical data
                    if historical_data:
                        f.write("Sample historical data:\n```json\n")
                        f.write(json.dumps(historical_data[:3], indent=2))
                        f.write("\n```\n\n")
                    
                    # Predicted data points
                    predicted_data = country_data.get("predicted_data", [])
                    f.write(f"Predicted data points: {len(predicted_data)}\n\n")
                    
                    # Sample of predicted data
                    if predicted_data:
                        f.write("Sample predicted data:\n```json\n")
                        f.write(json.dumps(predicted_data[:3], indent=2))
                        f.write("\n```\n\n")
                
                # Add analysis
                if "analysis" in result_data:
                    f.write("## Analysis\n\n")
                    
                    # Insights
                    f.write("### Insights\n\n")
                    for insight in result_data["analysis"].get("insights", []):
                        f.write(f"- {insight}\n")
                    
                    # Trends
                    f.write("\n### Trends\n\n")
                    for trend in result_data["analysis"].get("trends", []):
                        f.write(f"- {trend}\n")
                    
                    # Recommendations
                    f.write("\n### Recommendations\n\n")
                    for recommendation in result_data["analysis"].get("recommendations", []):
                        f.write(f"- {recommendation}\n")
                    
                    # Summaries (for human-readable results)
                    f.write("\n### Data Summaries\n\n")
                    for summary in result_data["analysis"].get("summaries", []):
                        f.write(f"#### {summary.get('country', 'Unknown')}\n\n")
                        f.write(f"{summary.get('summary', 'No summary available')}\n\n")
                
                # Add raw JSON response for reference
                f.write("## Raw JSON Response\n\n")
                f.write("```json\n")
                f.write(json.dumps(result_data, indent=2))
                f.write("\n```\n")
            
            logger.info(f"Test results written to {output_file}")
            return str(output_file)
        
        except json.JSONDecodeError:
            logger.error("Failed to parse agent response as JSON")
            
            # Save the raw response
            with open(output_file, "w") as f:
                f.write("# Dengue Data Visualization Test Results (Error)\n\n")
                f.write(f"Test performed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"Query: {test_query}\n\n")
                f.write("Error: Failed to parse agent response as JSON\n\n")
                f.write("## Raw Response\n\n")
                f.write(response_message.content)
            
            logger.info(f"Error report written to {output_file}")
            return str(output_file)
    else:
        logger.error("No response received from agent")
        return None

if __name__ == "__main__":
    # Run the test
    output_file = asyncio.run(test_dengue_visualization_agent())
    if output_file:
        print(f"Test completed successfully! Results saved to: {output_file}")
    else:
        print("Test failed! No output file was created.")
