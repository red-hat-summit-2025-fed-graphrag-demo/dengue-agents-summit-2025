"""
Comprehensive test script that runs multiple diverse queries through the RAG workflow
and captures full detailed output for review.

This test is specifically designed to record the complete agent interactions,
thought processes, and generated content without any filtering.
"""
import os
import sys
import json
import logging
import asyncio
import time
from pathlib import Path
from typing import Dict, Any, List

# Add the project root to the Python path
project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))

from src.agent_system.core.workflow_manager import WorkflowManager
from src.agent_system.core.message import Message, MessageRole

# Configure logging to capture all details
logging.basicConfig(
    level=logging.DEBUG,  # Use DEBUG level to capture maximum detail
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("workflow_comprehensive_test")

# Test queries - diverse set to test different aspects of knowledge and reasoning
TEST_QUERIES = [
    # Basic symptom/disease information
    "What are the main symptoms of dengue fever?",
    "How is dengue fever transmitted?",
    
    # Complex relational information
    "What is the relationship between rainfall and dengue fever outbreaks?",
    "Which organizations are researching dengue treatments and what have they found?",
    
    # Edge case and challenging queries
    "Does dengue fever cause long-term immunity after infection?",
    "What are the differences between dengue hemorrhagic fever and dengue shock syndrome?",
    
    # Potentially challenging/complex query that might require fallback approaches
    "What preventive measures should be taken in areas with high Aedes aegypti populations during the rainy season?",
    
    # Query that might challenge citation handling
    "What is the latest research on dengue vaccines and their effectiveness in children?",
    
    # Query with potential schema validation challenges
    "How do climate factors like temperature and humidity influence the replication rate of the dengue virus in mosquitoes?"
]

async def test_workflow_comprehensive():
    """Run comprehensive tests through the workflow and capture detailed output"""
    start_time = time.time()
    logger.info(f"Starting comprehensive workflow testing with {len(TEST_QUERIES)} queries")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(project_root, "workflow_test_results")
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize the workflow manager with the proper directory
    workflow_dir = os.path.join(project_root, "src", "registries", "workflows")
    workflow_manager = WorkflowManager(registry_dir=workflow_dir)
    
    # Create the main results file
    main_output_file = os.path.join(output_dir, f"comprehensive_results_{int(start_time)}.md")
    with open(main_output_file, "w") as f:
        f.write("# Comprehensive Workflow Test Results\n\n")
        f.write(f"Test run on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Testing against {len(TEST_QUERIES)} diverse queries\n\n")
        f.write("## Summary\n\n")
        f.write("| Query | Status | Response Length | Processing Time |\n")
        f.write("|-------|--------|-----------------|----------------|\n")
    
    results = []
    
    # Process each query
    for i, query in enumerate(TEST_QUERIES):
        query_start = time.time()
        logger.info(f"Testing query {i+1}/{len(TEST_QUERIES)}: {query}")
        
        # Create individual query result file
        query_file = os.path.join(output_dir, f"query_{i+1}_{int(start_time)}.md")
        with open(query_file, "w") as f:
            f.write(f"# Query {i+1} Test Results\n\n")
            f.write(f"## Query: {query}\n\n")
        
        try:
            # Process the query through the workflow
            workflow_id = "GRAPH_RAG_WORKFLOW"
            result = await workflow_manager.process_message(
                message_content=query,
                user_id="test_user",
                session_id=None,
                metadata={"test": True, "comprehensive": True},
                workflow_id=workflow_id
            )
            
            # Calculate processing time
            processing_time = time.time() - query_start
            
            # Determine response content based on result type
            response_content = "No content"
            response_length = 0
            status = "FAILURE"
            
            if isinstance(result, dict) and "response" in result:
                response_content = result["response"]
                response_length = len(response_content)
                status = "SUCCESS"
            elif hasattr(result, 'content'):
                response_content = result.content
                response_length = len(response_content)
                status = "SUCCESS"
            
            # Save detailed result to individual query file
            with open(query_file, "a") as f:
                f.write(f"## Status: {status}\n\n")
                f.write(f"## Processing Time: {processing_time:.2f} seconds\n\n")
                
                f.write("## Raw Response\n\n")
                f.write("```\n")
                f.write(response_content)
                f.write("\n```\n\n")
                
                f.write("## Full Metadata\n\n")
                f.write("```json\n")
                if isinstance(result, dict):
                    json_result = {k: v for k, v in result.items() if k != "response"}
                    f.write(json.dumps(json_result, indent=2, default=str))
                elif hasattr(result, 'metadata'):
                    f.write(json.dumps(result.metadata, indent=2, default=str))
                else:
                    f.write(json.dumps({"error": "No metadata available"}, indent=2))
                f.write("\n```\n\n")
                
                # Extract agent-specific data when available
                if isinstance(result, dict) and "metadata" in result:
                    f.write("## Agent Highlights\n\n")
                    metadata = result["metadata"]
                    
                    # Hybrid Query Writer info
                    if "query" in metadata:
                        f.write("### Cypher Query\n\n")
                        f.write("```cypher\n")
                        f.write(metadata.get("query", "No query found"))
                        f.write("\n```\n\n")
                        f.write(f"* Approach: {metadata.get('approach', 'unknown')}\n")
                        f.write(f"* Attempts: {metadata.get('attempts', 0)}\n\n")
                    
                    # Query execution info
                    if "result_count" in metadata:
                        f.write("### Query Results\n\n")
                        f.write(f"* Retrieved {metadata.get('result_count', 0)} results\n")
                        f.write(f"* Status: {metadata.get('status', 'unknown')}\n\n")
                    
                    # Assessment info
                    if "assessment" in metadata:
                        f.write("### Result Assessment\n\n")
                        f.write(f"* Assessment: {metadata.get('assessment', 'unknown')}\n")
                        if "error" in metadata:
                            f.write(f"* Error: {metadata.get('error', 'unknown')}\n\n")
            
            # Add to summary results
            results.append({
                "query": query,
                "status": status,
                "response_length": response_length,
                "processing_time": processing_time,
                "file": os.path.basename(query_file)
            })
            
            logger.info(f"Completed query {i+1}: Status {status}, Time: {processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error processing query {i+1}: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Add to summary results
            results.append({
                "query": query,
                "status": "ERROR",
                "response_length": 0,
                "processing_time": time.time() - query_start,
                "file": os.path.basename(query_file) if 'query_file' in locals() else "N/A"
            })
            
            # Save error information
            with open(query_file, "a") as f:
                f.write("## Error\n\n")
                f.write(f"```\n{str(e)}\n```\n\n")
                f.write("## Traceback\n\n")
                f.write("```\n")
                import traceback
                f.write(traceback.format_exc())
                f.write("\n```\n\n")
    
    # Update the main results file with summary
    with open(main_output_file, "a") as f:
        for result in results:
            f.write(f"| {result['query'][:30]}... | {result['status']} | {result['response_length']} chars | {result['processing_time']:.2f}s |\n")
        
        f.write("\n## Details\n\n")
        for i, result in enumerate(results):
            f.write(f"{i+1}. [{result['query'][:50]}...]({result['file']}): {result['status']}\n")
        
        total_time = time.time() - start_time
        f.write(f"\n\nTotal processing time: {total_time:.2f} seconds\n")
    
    logger.info(f"Comprehensive testing completed. Results saved to {output_dir}")
    return main_output_file

if __name__ == "__main__":
    main_output_file = asyncio.run(test_workflow_comprehensive())
    print(f"\nResults available at: {main_output_file}")
