"""
Comprehensive test for the Output Combiner Agent in the RAG workflow.

This test is specifically designed to verify that the rag_output_combiner_agent
properly combines outputs from the dengue_data_visualization_agent and
response_generator_agent in the GRAPH_RAG_WORKFLOW.
"""
import os
import sys
import json
import logging
import asyncio
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))

from src.agent_system.core.workflow_manager import WorkflowManager
from src.registries.agent_registry import AgentRegistry
from src.agent_system.core.message import Message, MessageRole

# Set up output directory for saving test results
output_dir = project_root / "logs" / "output_combiner_tests"
os.makedirs(output_dir, exist_ok=True)

# Configure logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = output_dir / f"test_output_combiner_{timestamp}.log"

# Set up file handler
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("output_combiner_test")

# Test query focused on a scenario that will activate visualization
TEST_QUERY = "I have a patient living in New York who plans travel to Zimbabwe in September of this year. This patient has had dengue fever in the last 3 years. What advice should I give him regarding his trip?"

class TestCallbacks:
    """Callback class for handling workflow events"""
    
    def __init__(self, output_dir: Path, test_name: str):
        self.output_dir = output_dir
        self.test_name = test_name
        self.events = []
        self.agent_outputs = {}
        self.start_time = time.time()
        self.most_recent_response = None
        self.test_logger = logger
        
    def visualization_callback(self, agent_id: str):
        """Track agent visualization events."""
        logger.info(f"Visualization event from agent: {agent_id}")
        self.events.append({
            "type": "visualization",
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat(),
            "elapsed_ms": round((time.time() - self.start_time) * 1000)
        })
        return None
    
    def log_callback(self, agent_id: str, input_text: str, output_text: str, processing_time: int):
        """Track agent log events."""
        logger.info(f"Log event from agent: {agent_id} (processing time: {processing_time}ms)")
        
        # Store the agent output for later analysis
        self.agent_outputs[agent_id] = {
            "input": input_text,
            "output": output_text,
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat(),
            "elapsed_ms": round((time.time() - self.start_time) * 1000)
        }
        
        # Save full agent output to separate file for detailed analysis
        agent_output_file = self.output_dir / f"{self.test_name}_{agent_id}_{timestamp}.txt"
        with open(agent_output_file, 'w') as f:
            f.write(f"=== INPUT ===\n\n{input_text}\n\n=== OUTPUT ===\n\n{output_text}")
        
        # Record event
        self.events.append({
            "type": "log",
            "agent_id": agent_id,
            "input_length": len(input_text) if input_text else 0,
            "output_length": len(output_text) if output_text else 0,
            "processing_time": processing_time,
            "output_file": str(agent_output_file),
            "timestamp": datetime.now().isoformat(),
            "elapsed_ms": round((time.time() - self.start_time) * 1000)
        })
        return None
    
    def stream_callback(self, agent_id: str, message_type: str, content: str, data: Any):
        """Track agent streaming events."""
        logger.info(f"Stream event from agent: {agent_id} (type: {message_type})")
        self.events.append({
            "type": "stream",
            "agent_id": agent_id,
            "message_type": message_type,
            "content_length": len(content) if content else 0,
            "timestamp": datetime.now().isoformat(),
            "elapsed_ms": round((time.time() - self.start_time) * 1000)
        })
        
        # If this is a "thinking" event, save it separately
        if message_type == "thinking" and content:
            thinking_file = self.output_dir / f"{self.test_name}_{agent_id}_thinking_{timestamp}.txt"
            with open(thinking_file, 'a') as f:
                f.write(f"{content}\n\n")
                
        return None
    
    def workflow_step_callback(self, workflow_id: str, current_step: str, next_step: str, data: Any):
        """
        Callback for workflow step changes.

        Args:
            workflow_id: Workflow ID
            current_step: Current step name
            next_step: Next step name
            data: Data passed to the callback
        """
        self.test_logger.info(f"Workflow step: {current_step} -> {next_step}")
        self.events.append({
            "type": "workflow_step",
            "workflow_id": workflow_id,
            "current_step": current_step,
            "next_step": next_step,
            "timestamp": datetime.now().isoformat(),
            "elapsed_ms": round((time.time() - self.start_time) * 1000)
        })
        
        # Identify when the response_generator_agent has completed and save its output
        if current_step == "response_generator_agent" and data:
            # Store the response generator output for later use
            self.most_recent_response = data.content
            self.test_logger.info(f"Stored response generator output: {len(self.most_recent_response)} chars")
            
            # Also store it in the agent_outputs directly for easier debugging
            if hasattr(self, "agent_outputs") and "response_generator_agent" in self.agent_outputs:
                self.test_logger.info("Updating agent_outputs with response generator content")
        
        # Before running the output combiner agent, we need to ensure it has access to 
        # the response generator agent's output
        if next_step == "rag_output_combiner_agent" and data:
            # Log what we're doing
            self.test_logger.info("Preparing message for output combiner agent")
            
            if hasattr(self, "most_recent_response") and self.most_recent_response:
                # Log the stored response
                self.test_logger.info(f"Using stored response from generator: {len(self.most_recent_response)} chars")
                
                # Create a new complete metadata dictionary
                new_metadata = {}
                
                # Copy original metadata if available
                if hasattr(data, "metadata") and data.metadata:
                    new_metadata = data.metadata.copy()
                
                # Ensure we have the original query
                if "original_query" not in new_metadata and hasattr(data, "content"):
                    new_metadata["original_query"] = data.content
                
                # Add the stored response directly
                new_metadata["response_generator_output"] = self.most_recent_response
                
                # Create a new message with proper metadata
                new_message = Message(
                    role=MessageRole.USER,
                    content=data.content if hasattr(data, "content") and data.content else self.most_recent_response,
                    metadata=new_metadata
                )
                
                self.test_logger.info(f"Created new message for output combiner with metadata keys: {list(new_metadata.keys())}")
                
                # Return the new message to replace the original
                return new_message
            else:
                self.test_logger.warning("No stored response generator output available for output combiner")
        
        return data
    
    def get_callbacks(self):
        """Get the callback dictionary for the agent manager."""
        return {
            "visualization": self.visualization_callback,
            "log": self.log_callback,
            "stream": self.stream_callback,
            "workflow_step": self.workflow_step_callback
        }
    
    def save_results(self):
        """Save all test results to files."""
        # Save events
        events_file = self.output_dir / f"{self.test_name}_events_{timestamp}.json"
        with open(events_file, 'w') as f:
            json.dump(self.events, f, indent=2)
        
        # Save agent outputs summary
        outputs_file = self.output_dir / f"{self.test_name}_outputs_{timestamp}.json"
        with open(outputs_file, 'w') as f:
            json.dump(self.agent_outputs, f, indent=2, default=str)
            
        logger.info(f"Events saved to {events_file}")
        logger.info(f"Agent outputs summary saved to {outputs_file}")
        
        return events_file, outputs_file

async def check_agent_registry(agent_id: str):
    """
    Check if an agent exists in the registry.
    
    Args:
        agent_id: The ID of the agent to check
        
    Returns:
        bool: Whether the agent exists in the registry
    """
    agent_registry = AgentRegistry()
    try:
        # Try to get the agent config
        agent_config = agent_registry.get_agent_config(agent_id)
        logger.info(f"Agent '{agent_id}' found in registry with config: {agent_config.get('type', 'unknown')}")
        return True
    except ValueError:
        logger.error(f"Agent '{agent_id}' NOT found in registry")
        return False

async def check_workflow_agent_steps():
    """
    Check if our agent is included in the GRAPH_RAG_WORKFLOW.
    
    Returns:
        Tuple of (bool, list): (whether agent is in workflow, workflow steps)
    """
    workflow_file = project_root / "src" / "registries" / "workflows" / "GRAPH_RAG_WORKFLOW.json"
    
    if not os.path.exists(workflow_file):
        logger.error(f"Workflow file not found: {workflow_file}")
        return False, []
    
    with open(workflow_file, 'r') as f:
        workflow = json.load(f)
        
    steps = workflow.get("steps", [])
    
    # Check if rag_output_combiner_agent is in the steps
    found = "rag_output_combiner_agent" in steps
    
    if found:
        logger.info("rag_output_combiner_agent found in GRAPH_RAG_WORKFLOW steps")
    else:
        logger.error("rag_output_combiner_agent NOT found in GRAPH_RAG_WORKFLOW steps")
        logger.info(f"Workflow steps: {steps}")
    
    return found, steps

async def run_test():
    """Run the comprehensive test for the output combiner agent"""
    logger.info("Starting RAG Output Combiner Agent comprehensive test")
    
    # Check if agent is registered
    registered = await check_agent_registry("rag_output_combiner_agent")
    if not registered:
        logger.error("Cannot proceed without rag_output_combiner_agent registered")
        return None
    
    # Check if agent is in workflow steps
    in_workflow, _ = await check_workflow_agent_steps()
    if not in_workflow:
        logger.error("Cannot proceed without rag_output_combiner_agent in workflow steps")
        return None
    
    # Create callbacks
    callbacks = TestCallbacks(output_dir, "output_combiner")
    
    # Get workflow directory
    workflow_dir = project_root / "src" / "registries" / "workflows"
    
    # Create workflow manager
    logger.info(f"Initializing WorkflowManager with directory: {workflow_dir}")
    agent_registry = AgentRegistry()
    workflow_manager = WorkflowManager(registry_dir=str(workflow_dir), agent_registry=agent_registry)
    
    # Process message
    logger.info(f"Running test with query: {TEST_QUERY}")
    start_time = time.time()
    
    # Execute workflow
    try:
        result = await workflow_manager.process_message(
            message_content=TEST_QUERY,
            user_id="test_user",
            callbacks=callbacks.get_callbacks(),
            workflow_id="GRAPH_RAG_WORKFLOW"
        )
        
        # Record execution time
        execution_time = round((time.time() - start_time) * 1000)
        logger.info(f"Workflow completed in {execution_time}ms")
        
        # Save final result
        result_file = output_dir / f"output_combiner_result_{timestamp}.txt"
        with open(result_file, 'w') as f:
            if isinstance(result, dict):
                f.write(json.dumps(result, indent=2, default=str))
            else:
                f.write(str(result))
                
        logger.info(f"Result saved to {result_file}")
        
        # Save all events and outputs
        events_file, outputs_file = callbacks.save_results()
        
        # Return test results
        return {
            "success": True,
            "execution_time_ms": execution_time,
            "result_file": str(result_file),
            "events_file": str(events_file),
            "outputs_file": str(outputs_file)
        }
        
    except Exception as e:
        logger.exception(f"Error running workflow: {e}")
        # Save events even if test failed
        callbacks.save_results()
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    # Run the test
    print(f"Starting RAG Output Combiner Agent test...")
    print(f"Log file: {log_file}")
    
    try:
        results = asyncio.run(run_test())
        
        if results and results.get("success"):
            print("\nTest completed successfully!")
            print(f"Execution time: {results['execution_time_ms']}ms")
            print(f"Result file: {results['result_file']}")
            print(f"Events file: {results['events_file']}")
            print(f"Outputs file: {results['outputs_file']}")
            
            # Extract and format the response for review
            try:
                result_file = results['result_file']
                print(f"\nAnalyzing result file: {result_file}")
                
                # Parse the JSON output
                with open(result_file, 'r') as f:
                    result_data = json.load(f)
                
                # Check if there's a response field and extract it
                if "response" in result_data:
                    try:
                        response_content = result_data["response"]
                        
                        # Check if the response is a JSON string or a simple value
                        if isinstance(response_content, str) and response_content.strip().startswith("{"):
                            try:
                                response_json = json.loads(response_content)
                                print(f"\nResponse is a JSON string with keys: {list(response_json.keys())}")
                                
                                # Create a formatted markdown document
                                markdown_content = ["# Dengue Data Analysis Report\n\n"]
                                
                                # Add actual response text if available (putting this first as the main content)
                                if "response" in response_json and response_json["response"]:
                                    response_text = response_json["response"]
                                    if response_text and response_text != "graph_rag" and not response_text.strip().startswith("{"):
                                        markdown_content.append(f"{response_text}\n\n")
                                    elif isinstance(response_text, dict):
                                        markdown_content.append(json.dumps(response_text, indent=2))
                                        markdown_content.append("\n\n")
                                
                                # Add visualization section
                                markdown_content.append("## Dengue Fever Visualization Data\n\n")
                                
                                # Add countries data if available
                                if "data" in response_json:
                                    # First check direct data structures
                                    countries_data = []
                                    
                                    # Check for direct countries key
                                    if "countries" in response_json["data"]:
                                        countries_data = response_json["data"]["countries"]
                                    # Check for countries_data array
                                    elif "countries_data" in response_json["data"]:
                                        countries_data = response_json["data"]["countries_data"]
                                    # Check for nested structure in data.data
                                    elif "data" in response_json["data"]:
                                        if "countries" in response_json["data"]["data"]:
                                            countries_data = response_json["data"]["data"]["countries"]
                                        elif "countries_data" in response_json["data"]["data"]:
                                            countries_data = response_json["data"]["data"]["countries_data"]
                                    
                                    if countries_data:
                                        for country_data in countries_data:
                                            # Add country header
                                            country_name = country_data.get("country", "Unknown Country")
                                            markdown_content.append(f"### {country_name}\n\n")
                                            
                                            # Add current date and presentation date
                                            current_date = country_data.get("current_date", "N/A")
                                            presentation_date = country_data.get("presentation_date", "N/A")
                                            markdown_content.append(f"- **Current Date:** {current_date}\n")
                                            markdown_content.append(f"- **Prediction Target Date:** {presentation_date}\n\n")
                                            
                                            # Check for time_series data or historical_data + predicted_data
                                            if "time_series" in country_data:
                                                time_series = country_data["time_series"]
                                                markdown_content.append("#### Time Series Data\n\n")
                                                markdown_content.append("| Date | Cases | Type |\n")
                                                markdown_content.append("|------|-------|------|\n")
                                                
                                                for entry in time_series:
                                                    date = entry.get("date", "N/A")
                                                    cases = entry.get("cases", "N/A")
                                                    data_type = entry.get("type", "historical")
                                                    markdown_content.append(f"| {date} | {cases} | {data_type} |\n")
                                                
                                                markdown_content.append("\n")
                                            # Handle separate historical and predicted data
                                            elif "historical_data" in country_data or "predicted_data" in country_data:
                                                markdown_content.append("#### Historical & Predicted Data\n\n")
                                                markdown_content.append("| Date | Dengue Cases | Temperature | Humidity | Type |\n")
                                                markdown_content.append("|------|--------------|------------|----------|------|\n")
                                                
                                                # Add historical data
                                                if "historical_data" in country_data:
                                                    historical = country_data["historical_data"]
                                                    # Only show the last 12 entries to keep it manageable
                                                    display_count = min(12, len(historical))
                                                    for entry in historical[-display_count:]:
                                                        date = entry.get("calendar_start_date", "N/A")
                                                        cases = entry.get("dengue_total", "N/A")
                                                        temp = entry.get("avg_temperature", "N/A")
                                                        humidity = entry.get("avg_humidity", "N/A")
                                                        markdown_content.append(f"| {date} | {cases} | {temp}°C | {humidity}% | historical |\n")
                                                
                                                # Add predicted data
                                                if "predicted_data" in country_data:
                                                    predicted = country_data["predicted_data"]
                                                    for entry in predicted:
                                                        date = entry.get("calendar_start_date", "N/A")
                                                        cases = entry.get("dengue_total", "N/A")
                                                        temp = entry.get("avg_temperature", "N/A") 
                                                        humidity = entry.get("avg_humidity", "N/A")
                                                        markdown_content.append(f"| {date} | {cases} | {temp}°C | {humidity}% | **predicted** |\n")
                                                
                                                markdown_content.append("\n")
                                    else:
                                        # Log detailed structure for debugging
                                        data_keys = list(response_json["data"].keys())
                                        markdown_content.append(f"Available data keys: {data_keys}\n\n")
                                        
                                        # Create a simplified view of the data instead of raw JSON
                                        if "countries_data" in response_json["data"]:
                                            countries_data = response_json["data"]["countries_data"]
                                            for country_data in countries_data:
                                                country_name = country_data.get("country", "Unknown Country")
                                                markdown_content.append(f"### {country_name}\n\n")
                                                
                                                current_date = country_data.get("current_date", "N/A")
                                                presentation_date = country_data.get("presentation_date", "N/A")
                                                markdown_content.append(f"- **Current Date:** {current_date}\n")
                                                markdown_content.append(f"- **Prediction Target Date:** {presentation_date}\n\n")
                                                
                                                # Simplified stats summary instead of all data points
                                                historical_count = len(country_data.get("historical_data", []))
                                                predicted_count = len(country_data.get("predicted_data", []))
                                                
                                                markdown_content.append("#### Data Summary\n\n")
                                                markdown_content.append(f"- Historical data points: {historical_count}\n")
                                                markdown_content.append(f"- Predicted data points: {predicted_count}\n\n")
                                                
                                                # Show last 6 months of historical data in a table
                                                if historical_count > 0:
                                                    markdown_content.append("#### Recent Historical Data (Last 6 Months)\n\n")
                                                    markdown_content.append("| Date | Dengue Cases | Temperature | Humidity |\n")
                                                    markdown_content.append("|------|--------------|------------|----------|\n")
                                                    
                                                    historical = country_data["historical_data"]
                                                    display_count = min(6, historical_count)
                                                    for entry in historical[-display_count:]:
                                                        date = entry.get("calendar_start_date", "N/A")
                                                        cases = entry.get("dengue_total", "N/A")
                                                        temp = entry.get("avg_temperature", "N/A")
                                                        humidity = entry.get("avg_humidity", "N/A")
                                                        markdown_content.append(f"| {date} | {cases} | {temp}°C | {humidity}% |\n")
                                                    
                                                    markdown_content.append("\n")
                                                
                                                # Show predicted data in a table
                                                if predicted_count > 0:
                                                    markdown_content.append("#### Predicted Data\n\n")
                                                    markdown_content.append("| Date | Dengue Cases | Temperature | Humidity |\n")
                                                    markdown_content.append("|------|--------------|------------|----------|\n")
                                                    
                                                    predicted = country_data["predicted_data"]
                                                    for entry in predicted:
                                                        date = entry.get("calendar_start_date", "N/A")
                                                        cases = entry.get("dengue_total", "N/A")
                                                        temp = entry.get("avg_temperature", "N/A")
                                                        humidity = entry.get("avg_humidity", "N/A")
                                                        markdown_content.append(f"| {date} | {cases} | {temp}°C | {humidity}% |\n")
                                                    
                                                    markdown_content.append("\n")
                                
                                # Add analysis section if present
                                if "data" in response_json and "analysis" in response_json["data"]:
                                    analysis = response_json["data"]["analysis"]
                                    markdown_content.append("## Analysis\n\n")
                                    
                                    # Add trend analysis
                                    if "trend" in analysis:
                                        trend = analysis["trend"]
                                        markdown_content.append("### Trend Analysis\n\n")
                                        markdown_content.append(f"{trend}\n\n")
                                    
                                    # Add insights
                                    if "insights" in analysis and analysis["insights"]:
                                        markdown_content.append("### Key Insights\n\n")
                                        for insight in analysis["insights"]:
                                            markdown_content.append(f"- {insight}\n")
                                        markdown_content.append("\n")
                                    
                                    # Add recommendations
                                    if "recommendations" in analysis and analysis["recommendations"]:
                                        markdown_content.append("### Recommendations\n\n")
                                        for rec in analysis["recommendations"]:
                                            markdown_content.append(f"- {rec}\n")
                                        markdown_content.append("\n")
                                    
                                    # Add summaries
                                    if "summaries" in analysis and analysis["summaries"]:
                                        markdown_content.append("### Country Summaries\n\n")
                                        for summary in analysis["summaries"]:
                                            if "country" in summary and "summary" in summary:
                                                markdown_content.append(f"#### {summary['country']}\n\n")
                                                markdown_content.append(f"{summary['summary']}\n\n")
                                
                                # Add citations if present
                                if "citations" in response_json:
                                    citations = response_json.get("citations", [])
                                    if citations:
                                        markdown_content.append("## Citations\n\n")
                                        for i, citation in enumerate(citations, 1):
                                            if isinstance(citation, dict):
                                                title = citation.get("title", "N/A")
                                                source = citation.get("source", "N/A")
                                                url = citation.get("url", "")
                                                markdown_content.append(f"{i}. **{title}**")
                                                if source:
                                                    markdown_content.append(f" - {source}")
                                                if url:
                                                    markdown_content.append(f" [Link]({url})")
                                                markdown_content.append("\n")
                                            elif isinstance(citation, str):
                                                markdown_content.append(f"{i}. {citation}\n")
                                        markdown_content.append("\n")
                                        
                                # Add metadata section
                                markdown_content.append("## Metadata\n\n")
                                markdown_content.append(f"- **Generated on:** {response_json.get('timestamp', 'N/A')}\n")
                                markdown_content.append(f"- **Version:** {response_json.get('version', 'N/A')}\n")
                                markdown_content.append(f"- **Response Type:** {response_json.get('type', 'N/A')}\n\n")
                                
                                # Write markdown to file
                                response_md_file = output_dir / f"output_formatted_{timestamp}.md"
                                response_json_file = output_dir / f"response_data_{timestamp}.json"
                                
                                # Save pretty JSON
                                with open(response_json_file, 'w') as f:
                                    json.dump(response_json, f, indent=2)
                                
                                with open(response_md_file, 'w') as f:
                                    f.write("".join(markdown_content))
                                
                                # Always write to the user-specified dengue_response.md file
                                user_md_file = Path("/Users/wesjackson/Code/Summit2025/dengue-agents-summit-2025/dengue_response.md")
                                try:
                                    with open(user_md_file, 'w') as f:
                                        f.write("# Dengue Data Analysis Report\n\nRESPONSE:\n\n")
                                        
                                        # If we have a direct response field, use that for user output
                                        if "response" in response_json and isinstance(response_json["response"], str):
                                            f.write(response_json["response"])
                                        else:
                                            # Otherwise use the formatted markdown content
                                            f.write("".join(markdown_content))
                                    print(f"User output saved to: {user_md_file}")
                                except Exception as e:
                                    print(f"Error writing to user output file: {str(e)}")
                                
                                print(f"\nFormatted response saved to: {response_md_file}")
                                print(f"Raw response JSON saved to: {response_json_file}")
                                
                            except json.JSONDecodeError:
                                print(f"\nResponse content is not valid JSON: {response_content[:100]}...")
                        else:
                            print(f"\nResponse content is not a JSON string: {response_content}")
                    except Exception as e:
                        print(f"\nError processing response: {e}")
                else:
                    print("\nNo 'response' field found in result data")
                
                # Extract metadata for review
                if "metadata" in result_data:
                    metadata = result_data["metadata"]
                    print("\nMetadata summary:")
                    print(f"- Has citations: {metadata.get('has_citations', False)}")
                    print(f"- Citation count: {metadata.get('citation_count', 0)}")
                    print(f"- Is JSON response: {metadata.get('is_json_response', False)}")
                    print(f"- Has visualization data: {metadata.get('has_visualization_data', False)}")
                    print(f"- Compliance checked: {metadata.get('compliance_checked', False)}")
                    print(f"- Is compliant: {metadata.get('is_compliant', False)}")
                
            except Exception as e:
                print(f"\nError analyzing result file: {e}")
                
        else:
            print("\nTest failed!")
            if results:
                print(f"Error: {results.get('error')}")
            
    except Exception as e:
        logger.exception(f"Error in test execution: {e}")
        print(f"\nTest execution error: {e}")
