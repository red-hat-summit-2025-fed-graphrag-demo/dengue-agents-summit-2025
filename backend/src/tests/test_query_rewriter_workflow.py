"""
Test script for the Graph RAG Workflow with Query Rewriter

This test specifically focuses on testing the query rewriter agent
in the workflow to ensure it properly reformulates user queries
before they're sent to the graph database.
"""
import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))

from src.agent_system.core.workflow_manager import WorkflowManager
from src.registries.agent_registry import AgentRegistry

# Set up output directory for test results
output_dir = project_root / "logs" / "query_rewriter_tests"
os.makedirs(output_dir, exist_ok=True)

# Set up logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = output_dir / f"test_query_rewriter_{timestamp}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("query_rewriter_test")

# Test query that previously failed
TEST_QUERY = "I have a patient living in New York who plans travel to Saudi Arabia in September of this year. This patient has had dengue fever in the last 3 years. What advice should I give him regarding his trip?"

class TestCallbacks:
    """Callback handler for the workflow"""
    
    def __init__(self):
        self.callbacks = {}
        self.events = []
        self.agent_outputs = {}
        self.start_time = datetime.now()
    
    def visualization_callback(self, agent_id: str):
        """Track agent visualization events."""
        logger.info(f"Visualization event from agent: {agent_id}")
        self.events.append({
            "type": "visualization",
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat()
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
            "timestamp": datetime.now().isoformat()
        }
        
        # Save full agent output to separate file for detailed analysis
        agent_output_file = output_dir / f"{agent_id}_{timestamp}.txt"
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
            "timestamp": datetime.now().isoformat()
        })
        return None
    
    def stream_callback(self, agent_id: str, message_type: str, content: str, data: dict):
        """Track agent streaming events."""
        logger.info(f"Stream event from agent: {agent_id} (type: {message_type})")
        
        # If this is a thinking event, save it to a file
        if message_type == "thinking" and content:
            thinking_file = output_dir / f"{agent_id}_thinking_{timestamp}.txt"
            with open(thinking_file, 'a') as f:
                f.write(f"{content}\n\n")
        
        # Record the event
        self.events.append({
            "type": "stream",
            "agent_id": agent_id,
            "message_type": message_type,
            "content_length": len(content) if content else 0,
            "timestamp": datetime.now().isoformat()
        })
        return None
    
    def get_callbacks(self):
        """Get the callback dictionary for the agent manager."""
        return {
            "visualization": self.visualization_callback,
            "log": self.log_callback,
            "stream": self.stream_callback
        }
    
    def save_results(self):
        """Save all test results to files."""
        # Save events
        events_file = output_dir / f"events_{timestamp}.json"
        with open(events_file, 'w') as f:
            json.dump(self.events, f, indent=2)
        
        # Save agent outputs
        outputs_file = output_dir / f"outputs_{timestamp}.json"
        with open(outputs_file, 'w') as f:
            json.dump(self.agent_outputs, f, indent=2, default=str)
        
        logger.info(f"Events saved to {events_file}")
        logger.info(f"Agent outputs saved to {outputs_file}")
        
        return events_file, outputs_file

async def run_test():
    """Run the test with the updated workflow"""
    logger.info("Starting Query Rewriter Workflow test")
    
    # Create agent registry
    agent_registry = AgentRegistry()
    
    # Check if the query rewriter agent is in the registry
    try:
        agent_config = agent_registry.get_agent_config("rag_user_query_rewriter_agent")
        logger.info(f"Query rewriter agent found in registry: {agent_config.get('id')}")
    except ValueError:
        logger.error("Query rewriter agent not found in registry!")
        return None
    
    # Get workflow registry directory
    workflow_dir = project_root / "src" / "registries" / "workflows"
    
    # Create workflow manager
    logger.info(f"Initializing WorkflowManager with directory: {workflow_dir}")
    workflow_manager = WorkflowManager(registry_dir=str(workflow_dir), agent_registry=agent_registry)
    
    # Create callback handler
    callback_handler = TestCallbacks()
    
    # Process message
    logger.info(f"Running test with query: {TEST_QUERY}")
    
    # Execute workflow
    try:
        result = await workflow_manager.process_message(
            message_content=TEST_QUERY,
            user_id="test_user",
            callbacks=callback_handler.get_callbacks(),
            workflow_id="GRAPH_RAG_WORKFLOW"
        )
        
        # Save results
        result_file = output_dir / f"final_result_{timestamp}.txt"
        with open(result_file, 'w') as f:
            if isinstance(result, dict):
                json.dump(result, f, indent=2, default=str)
            else:
                f.write(str(result))
        
        logger.info(f"Final result saved to {result_file}")
        
        # Save detailed information about each agent's output
        events_file, outputs_file = callback_handler.save_results()
        
        return {
            "success": True,
            "result_file": str(result_file),
            "events_file": str(events_file),
            "outputs_file": str(outputs_file)
        }
        
    except Exception as e:
        logger.exception(f"Error running workflow: {e}")
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    print(f"Starting Query Rewriter Workflow test...")
    print(f"Test query: {TEST_QUERY}")
    print(f"Log file: {log_file}")
    
    try:
        results = asyncio.run(run_test())
        
        if results and results.get("success"):
            print("\nTest completed successfully!")
            print(f"Result file: {results['result_file']}")
            print(f"Events file: {results['events_file']}")
            print(f"Outputs file: {results['outputs_file']}")
            
            # Analyze how the query rewriter performed
            with open(results['outputs_file'], 'r') as f:
                outputs = json.load(f)
                
            if "rag_user_query_rewriter_agent" in outputs:
                rewriter_output = outputs["rag_user_query_rewriter_agent"]["output"]
                print("\nQuery Rewriter Output:")
                print(rewriter_output[:500] + "..." if len(rewriter_output) > 500 else rewriter_output)
        else:
            print("\nTest failed!")
            if results:
                print(f"Error: {results.get('error')}")
            
    except Exception as e:
        logger.exception(f"Error in test execution: {e}")
        print(f"\nTest execution error: {e}")
