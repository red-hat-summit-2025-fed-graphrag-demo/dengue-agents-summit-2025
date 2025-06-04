"""
Test for the Dengue Data Visualization enhancement

This script tests the enhanced GraphRAG workflow with the DengueDataVisualizationAgent,
verifying that it successfully retrieves dengue data and generates visualizations.
"""
import os
import logging
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

from src.agent_system.core.workflow_manager import WorkflowManager
from src.registries.agent_registry import AgentRegistry
from src.tools.dengue_data_tool import DengueDataTool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create output directory for test results
VISUALIZATION_TEST_OUTPUT_DIR = Path(__file__).parent.parent.parent / "visualization_test_results"
VISUALIZATION_TEST_OUTPUT_DIR.mkdir(exist_ok=True)

async def test_visualization_workflow():
    """
    Test the complete Graph RAG workflow with the Dengue Data Visualization enhancement.
    
    This test simulates a user query about a patient traveling to Thailand in September,
    which should trigger both graph retrieval and data visualization.
    """
    # Initialize workflow manager
    workflow_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "registries", "workflows")
    agent_registry = AgentRegistry()
    workflow_manager = WorkflowManager(workflow_dir, agent_registry)
    
    # Define a test query that should trigger visualization for Thailand
    test_query = "I have a patient who is traveling to Thailand in September. What should I tell them about dengue fever risk and prevention?"
    
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
    output_file = VISUALIZATION_TEST_OUTPUT_DIR / f"visualization_test_{timestamp}.md"
    
    with open(output_file, "w") as f:
        f.write(f"# Dengue Data Visualization Test Report\n\n")
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
    detailed_output_file = VISUALIZATION_TEST_OUTPUT_DIR / f"visualization_data_dump_{timestamp}.json"
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
    Test the DengueDataTool directly to verify API connectivity.
    """
    tool = DengueDataTool()
    
    # Test countries
    countries = ["Thailand", "Indonesia", "Philippines"]
    
    results = {}
    
    for country in countries:
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
    output_file = VISUALIZATION_TEST_OUTPUT_DIR / f"tool_test_{timestamp}.json"
    
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
        
    logger.info(f"Tool test results saved to {output_file}")
    
    return output_file

async def run_tests():
    """Run all tests sequentially"""
    # First verify the tool works directly
    logger.info("Testing DengueDataTool directly...")
    tool_test_file = await test_direct_tool_usage()
    
    # Then test the full workflow
    logger.info("Testing full visualization workflow...")
    workflow_test_file = await test_visualization_workflow()
    
    logger.info("All tests completed")
    logger.info(f"Tool test results: {tool_test_file}")
    logger.info(f"Workflow test results: {workflow_test_file}")

if __name__ == "__main__":
    asyncio.run(run_tests())
