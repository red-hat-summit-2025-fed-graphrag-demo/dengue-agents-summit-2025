"""
Test for the Dengue Data Visualization with Saudi Arabia data

This script tests the enhanced GraphRAG workflow with the DengueDataVisualizationAgent,
using a query about a patient traveling to Saudi Arabia to verify direct API country processing.
"""

import os
import json
import asyncio
import time
import logging
import sys
from datetime import datetime
from pathlib import Path

from src.registries.agent_registry import AgentRegistry
from src.agent_system.core.workflow_manager import WorkflowManager
from src.tools.dengue_data_tool import DengueDataTool

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create output directory if it doesn't exist
VISUALIZATION_TEST_OUTPUT_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "saudi_visualization_results"
VISUALIZATION_TEST_OUTPUT_DIR.mkdir(exist_ok=True)


async def test_saudi_visualization_workflow():
    """
    Test the complete Graph RAG workflow with the Dengue Data Visualization enhancement
    for Saudi Arabia, which is a direct API country.
    
    This test simulates a user query about a patient traveling to Saudi Arabia in October,
    which should trigger both graph retrieval and data visualization.
    """
    # Initialize workflow manager
    workflow_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "registries", "workflows")
    agent_registry = AgentRegistry()
    workflow_manager = WorkflowManager(workflow_dir, agent_registry)
    
    # Define a test query that should trigger visualization for Saudi Arabia
    test_query = "I have a patient who is traveling to Saudi Arabia in October. What should I tell them about dengue fever risk and prevention?"
    
    # Get current timestamp for unique output files
    timestamp = int(time.time())
    
    # Process the query through the workflow
    logger.info(f"Processing query: {test_query}")
    
    # Capture agent thinking logs
    thinking_logs = []
    
    async def stream_callback(agent_id, message_type, content, data):
        if message_type == "thinking":
            thinking_logs.append(f"### {agent_id} thinking:\n\n{content}\n\n")
            logger.info(f"Agent {agent_id} thinking: {content[:100]}...")
    
    # Process message through workflow
    result = await workflow_manager.process_message(
        message_content=test_query,
        user_id="test_user",
        metadata={"test": True},
        callbacks={"stream": stream_callback},
        workflow_id="GRAPH_RAG_WORKFLOW"
    )
    
    # Get the final response content and metadata
    response_text = ""
    metadata = {}
    
    if isinstance(result, dict):
        if "response" in result:
            response_text = result["response"]
        if "metadata" in result:
            metadata = result["metadata"]
    else:
        response_text = str(result)
    
    # Check if we have visualization data
    has_visualization = metadata.get("has_visualization_data", False)
    visualization_code = metadata.get("visualization_code", {})
    
    logger.info(f"Has visualization data: {has_visualization}")
    
    # Write the results to a file
    output_file = VISUALIZATION_TEST_OUTPUT_DIR / f"saudi_visualization_test_{timestamp}.md"
    
    with open(output_file, "w") as f:
        f.write(f"# Saudi Arabia Dengue Data Visualization Test Report\n\n")
        f.write(f"**Test timestamp:** {datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Query:** {test_query}\n\n")
        
        f.write(f"## Final Response\n\n")
        f.write(f"```markdown\n{response_text}\n```\n\n")
        
        f.write(f"## Response Metadata\n\n")
        f.write("```json\n")
        f.write(json.dumps(metadata, indent=2))
        f.write("\n```\n\n")
        
        f.write(f"## Agent Highlights\n\n")
        for log in thinking_logs:
            f.write(log)
            
        if has_visualization and visualization_code:
            f.write(f"## Visualization Code\n\n")
            for country, code in visualization_code.items():
                f.write(f"### {country} Visualization\n\n")
                f.write("```python\n")
                f.write(code)
                f.write("\n```\n\n")
                
    logger.info(f"Test results saved to {output_file}")
    
    # Additional data dump for debugging
    detailed_output_file = VISUALIZATION_TEST_OUTPUT_DIR / f"saudi_visualization_data_dump_{timestamp}.json"
    with open(detailed_output_file, "w") as f:
        json.dump({
            "query": test_query,
            "result": result,
            "timestamp": timestamp
        }, f, indent=2, default=str)
        
    logger.info(f"Detailed data dump saved to {detailed_output_file}")
    
    return output_file


async def test_direct_tool_usage():
    """
    Test the DengueDataTool directly to verify API connectivity for Saudi Arabia.
    """
    tool = DengueDataTool()
    results = {}
    
    country = "Saudi Arabia"
    
    # Log information about the test
    logger.info(f"Testing direct tool usage for {country}")
    
    # Get visualization data
    data = await tool.get_visualization_data(country)
    
    # Log basic stats
    historical_count = len(data.get("historical_data", []))
    predicted_count = len(data.get("predicted_data", []))
    
    logger.info(f"{country} - Historical data points: {historical_count}, Predicted data points: {predicted_count}")
    
    results[country] = {
        "historical_count": historical_count,
        "predicted_count": predicted_count,
        "sample_historical": data.get("historical_data", [])[:2],
        "sample_predicted": data.get("predicted_data", [])[:2]
    }
    
    # Save results to a file
    timestamp = int(time.time())
    output_file = VISUALIZATION_TEST_OUTPUT_DIR / f"saudi_tool_test_{timestamp}.json"
    
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
        
    logger.info(f"Saudi Arabia tool test results saved to {output_file}")
    
    return output_file


async def run_tests():
    """Run all tests sequentially"""
    # First verify the tool works directly
    logger.info("Testing DengueDataTool directly for Saudi Arabia...")
    tool_test_file = await test_direct_tool_usage()
    
    # Then test the full workflow
    logger.info("Testing full visualization workflow for Saudi Arabia...")
    workflow_test_file = await test_saudi_visualization_workflow()
    
    logger.info("All tests completed")
    logger.info(f"Tool test results: {tool_test_file}")
    logger.info(f"Workflow test results: {workflow_test_file}")


if __name__ == "__main__":
    asyncio.run(run_tests())
