"""
Test script that focuses on generating responses with proper citations
from the knowledge graph for various dengue-related queries.
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

# Output paths
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "citation_test_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# List of test queries designed to target relationships with actual data
TEST_QUERIES = [
    {
        "id": "symptoms",
        "query": "What are the main symptoms of dengue fever?"
    },
    {
        "id": "warning_signs",
        "query": "What warning signs indicate severe dengue fever?"
    },
    {
        "id": "vectors",
        "query": "Which mosquito species transmit dengue fever?"
    },
    {
        "id": "prevention",
        "query": "How can I prevent dengue fever?"
    },
    {
        "id": "diagnosis",
        "query": "How is dengue fever diagnosed?"
    },
    {
        "id": "treatment",
        "query": "What treatments are available for dengue fever?"
    },
    {
        "id": "regions",
        "query": "In which regions is dengue fever endemic?"
    }
]

async def run_query_test(workflow_manager, query_info, timestamp):
    """Run a single query test and save detailed results."""
    query_id = query_info["id"]
    query = query_info["query"]
    
    # Create output filename
    output_file = os.path.join(OUTPUT_DIR, f"citation_test_{query_id}_{timestamp}.md")
    
    # Collect thinking logs
    thinking_logs = []
    
    # Define callback for agent thinking
    async def stream_callback(agent_id, message_type, content, data):
        if message_type == "thinking":
            thinking_logs.append(f"### {agent_id} thinking:\n\n{content}\n\n")
    
    # Execute the workflow
    logger.info(f"Testing query: {query}")
    
    # Add callbacks parameter with stream callback
    result = await workflow_manager.process_message(
        message_content=query,
        user_id="test_user",
        metadata={"test": True},
        callbacks={"stream": stream_callback},
        workflow_id="GRAPH_RAG_WORKFLOW"
    )
    
    # Save the results
    with open(output_file, "w") as f:
        f.write(f"# Citation Test: {query_id}\n\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Query\n\n{query}\n\n")
        
        # Handle result based on its type
        if isinstance(result, dict) and "response" in result:
            f.write(f"## Response\n\n{result['response']}\n\n")
            
            # Extract metadata including citations
            if "metadata" in result:
                metadata = result["metadata"]
                
                # Extract and display result count
                if "result_count" in metadata:
                    f.write(f"## Result Count: {metadata['result_count']}\n\n")
                
                # Extract and display Cypher query
                if "cypher_query" in metadata:
                    f.write(f"## Cypher Query\n\n```cypher\n{metadata['cypher_query']}\n```\n\n")
                
                # Extract and display assessment
                if "assessment" in metadata:
                    f.write(f"## Assessment: {metadata['assessment']}\n\n")
                
                # Check for citations in metadata or response
                if "citations" in metadata:
                    f.write("## Citations\n\n")
                    citations = metadata["citations"]
                    if isinstance(citations, list):
                        for i, citation in enumerate(citations, 1):
                            f.write(f"{i}. ")
                            if isinstance(citation, dict):
                                title = citation.get("title", "No title")
                                authors = citation.get("authors", "Unknown authors")
                                url = citation.get("url", "")
                                f.write(f"**{title}**. {authors}.")
                                if url:
                                    f.write(f" Available at: [{url}]({url})")
                            else:
                                f.write(str(citation))
                            f.write("\n\n")
                    else:
                        f.write(f"{citations}\n\n")
                else:
                    # Look for citation format in the response itself
                    response = result["response"]
                    if "References" in response or "Citations" in response:
                        parts = response.split("References") if "References" in response else response.split("Citations")
                        if len(parts) > 1:
                            f.write("## Extracted Citations\n\n")
                            f.write(parts[1].strip() + "\n\n")
        else:
            f.write(f"## Raw Result\n\n```json\n{json.dumps(result, indent=2)}\n```\n\n")
        
        # Add agent thinking logs
        f.write("## Agent Processing Details\n\n")
        for log in thinking_logs:
            f.write(log)
    
    return output_file

async def test_citations():
    """Run tests for all queries and create a summary report."""
    # Initialize workflow manager
    workflow_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "registries", "workflows")
    
    agent_registry = AgentRegistry()
    workflow_manager = WorkflowManager(workflow_dir, agent_registry)
    
    # Create timestamp for this test run
    timestamp = int(time.time())
    
    # Create summary report file
    summary_file = os.path.join(OUTPUT_DIR, f"citation_test_summary_{timestamp}.md")
    
    # Run all query tests
    result_files = []
    for query_info in TEST_QUERIES:
        output_file = await run_query_test(workflow_manager, query_info, timestamp)
        result_files.append((query_info["id"], output_file))
    
    # Create a summary report
    with open(summary_file, "w") as f:
        f.write("# Citation Test Summary Report\n\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Test Queries\n\n")
        
        for query_info in TEST_QUERIES:
            f.write(f"- **{query_info['id']}**: {query_info['query']}\n")
        
        f.write("\n## Result Files\n\n")
        for query_id, file_path in result_files:
            relative_path = os.path.basename(file_path)
            f.write(f"- [{query_id}]({relative_path})\n")
    
    logger.info(f"Citation tests completed. Summary saved to {summary_file}")
    return summary_file

if __name__ == "__main__":
    """Run the test when script is executed directly."""
    asyncio.run(test_citations())
