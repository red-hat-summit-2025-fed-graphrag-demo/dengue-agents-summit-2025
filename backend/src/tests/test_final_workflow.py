"""
Final test of the Graph RAG workflow with the citation fixes.
Tests the symptoms query which should now include proper citations.
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime

from src.agent_system.core.workflow_manager import WorkflowManager
from src.registries.agent_registry import AgentRegistry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Output directory
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "final_test_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def test_workflow_with_citations():
    """Test the workflow with a symptoms query and verify citations are included."""
    # Initialize workflow manager
    workflow_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "registries", "workflows")
    agent_registry = AgentRegistry()
    workflow_manager = WorkflowManager(workflow_dir, agent_registry)
    
    # Test query about symptoms
    query = "What are the main symptoms of dengue fever?"
    
    # Timestamp for output file
    timestamp = int(time.time())
    output_file = os.path.join(OUTPUT_DIR, f"final_workflow_test_{timestamp}.md")
    
    # Define callbacks for detailed output
    thinking_logs = []
    
    async def stream_callback(agent_id, message_type, content, data):
        if message_type == "thinking":
            thinking_logs.append(f"### {agent_id} thinking:\n\n{content}\n\n")
    
    # Execute the workflow
    logger.info(f"Executing workflow with query: {query}")
    result = await workflow_manager.process_message(
        message_content=query,
        user_id="test_user",
        metadata={"test": True},
        callbacks={"stream": stream_callback},
        workflow_id="GRAPH_RAG_WORKFLOW"
    )
    
    # Create markdown report
    with open(output_file, "w") as f:
        f.write("# Final Workflow Test with Citations\n\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Query\n\n{query}\n\n")
        
        # Add response
        if isinstance(result, dict) and "response" in result:
            response_text = result["response"]
            f.write(f"## Response\n\n```markdown\n{response_text}\n```\n\n")
            
            # Check for citations in the metadata
            has_citations = False
            citation_count = 0
            if "metadata" in result and isinstance(result["metadata"], dict):
                has_citations = result["metadata"].get("has_citations", False)
                citation_count = result["metadata"].get("citation_count", 0)
            
            # Also check content for citations
            content_has_citations = "References" in response_text or "Citations" in response_text or "[1]" in response_text
            
            f.write(f"## Has Citations: {has_citations or content_has_citations}\n\n")
            if citation_count > 0:
                f.write(f"## Citation Count: {citation_count}\n\n")
            
            # Add metadata
            if "metadata" in result:
                f.write("## Response Metadata\n\n")
                f.write("```json\n")
                f.write(json.dumps(result["metadata"], indent=2))
                f.write("\n```\n\n")
        else:
            f.write(f"## Raw Response\n\n```\n{result}\n```\n\n")
        
        # Add thinking logs
        f.write("## Agent Processing Details\n\n")
        for log in thinking_logs:
            f.write(log)
    
    logger.info(f"Final workflow test completed. Results saved to {output_file}")
    return output_file

if __name__ == "__main__":
    """Run the test when script is executed directly."""
    asyncio.run(test_workflow_with_citations())
