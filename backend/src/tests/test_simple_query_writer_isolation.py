"""
Isolation test for the SimpleQueryWriterAgent.

This test directly instantiates and runs the SimpleQueryWriterAgent
to examine its behavior outside of the workflow.
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional

from src.agent_system.core.message import Message, MessageRole
from src.agent_system.rag_system.query.simple_query_writer_agent import SimpleQueryWriterAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Output directory
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "isolation_test_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def test_simple_query_writer():
    """Test the SimpleQueryWriterAgent in isolation."""
    # Initialize agent with same config as in workflow
    agent_config = {
        "agent_id": "simple_query_writer_agent",
        "model_config": {
            "model_type": "instruct",
            "max_tokens": 512,
            "temperature": 0.2
        },
        "kg_api_url": "https://dengue-fastapi-dengue-kg-project.apps.cluster-8gvkk.8gvkk.sandbox888.opentlc.com"
    }
    
    agent = SimpleQueryWriterAgent("simple_query_writer_agent", agent_config)
    
    # Test queries
    test_queries = [
        "What are the main symptoms of dengue fever?",
        "What warning signs indicate severe dengue fever?",
        "Which mosquito species transmit dengue fever?",
        "How can I prevent dengue fever?",
        "How is dengue fever diagnosed?",
        "What treatments are available for dengue fever?",
        "In which regions is dengue fever endemic?"
    ]
    
    # Capture thinking logs
    thinking_logs = []
    
    async def stream_callback(agent_id, message_type, content, data):
        if message_type == "thinking":
            thinking_logs.append(f"### Thinking for query: {current_query}\n\n{content}\n\n")
    
    # Timestamp for output
    timestamp = int(time.time())
    output_file = os.path.join(OUTPUT_DIR, f"simple_query_writer_isolation_{timestamp}.md")
    
    # Process each query
    results = []
    for current_query in test_queries:
        thinking_logs = []  # Reset for each query
        
        # Create input message
        input_message = Message(
            role=MessageRole.USER,
            content=current_query,
            metadata={"test": True}
        )
        
        # Process the query
        agent_response, next_agent_id = await agent.process(
            input_message, 
            session_id=None,
            stream_callback=stream_callback
        )
        
        # Record the result
        results.append({
            "query": current_query,
            "response": agent_response.content if agent_response else None,
            "metadata": agent_response.metadata if agent_response else None,
            "next_agent_id": next_agent_id,
            "thinking": "\n".join(thinking_logs)
        })
    
    # Examine agent's valid patterns
    valid_patterns = agent.valid_patterns
    question_patterns = agent.question_patterns
    
    # Create a detailed report
    with open(output_file, "w") as f:
        f.write("# SimpleQueryWriterAgent Isolation Test\n\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Agent Configuration\n\n")
        f.write("```json\n")
        f.write(json.dumps(agent_config, indent=2))
        f.write("\n```\n\n")
        
        f.write("## Valid Patterns\n\n")
        f.write("```json\n")
        f.write(json.dumps(valid_patterns, indent=2))
        f.write("\n```\n\n")
        
        f.write("## Question Pattern Mappings\n\n")
        f.write("```json\n")
        f.write(json.dumps(question_patterns, indent=2))
        f.write("\n```\n\n")
        
        # Write results for each query
        f.write("## Query Results\n\n")
        for idx, result in enumerate(results, 1):
            f.write(f"### Query {idx}: {result['query']}\n\n")
            
            # Write response content
            f.write("#### Response Content\n\n")
            f.write("```\n")
            f.write(result["response"] if result["response"] else "No response")
            f.write("\n```\n\n")
            
            # Write metadata
            f.write("#### Metadata\n\n")
            f.write("```json\n")
            f.write(json.dumps(result["metadata"], indent=2) if result["metadata"] else "No metadata")
            f.write("\n```\n\n")
            
            # Next agent ID
            f.write(f"#### Next Agent: {result['next_agent_id']}\n\n")
            
            # Thinking logs
            f.write("#### Thinking Process\n\n")
            f.write(result["thinking"] if result["thinking"] else "No thinking logs")
            f.write("\n\n")
        
        # Analyze patterns
        f.write("## Analysis\n\n")
        f.write("This test examined the SimpleQueryWriterAgent in isolation to understand its behavior.\n\n")
        f.write("### Pattern Selection\n\n")
        
        # List pattern selection frequency
        pattern_counts = {}
        for result in results:
            if result["metadata"] and "pattern_name" in result["metadata"]:
                pattern = result["metadata"]["pattern_name"]
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        f.write("Pattern selection frequency:\n\n")
        for pattern, count in pattern_counts.items():
            f.write(f"- **{pattern}**: {count} times\n")
        
        # List default fallbacks
        default_count = sum(1 for r in results if r["metadata"] and r["metadata"].get("is_default_query", False))
        f.write(f"\nDefault pattern fallbacks: {default_count} queries\n")
        
    logger.info(f"SimpleQueryWriterAgent isolation test completed. Results saved to {output_file}")
    return output_file

if __name__ == "__main__":
    """Run the test when script is executed directly."""
    asyncio.run(test_simple_query_writer())
