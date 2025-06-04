"""
Isolation test for the ResponseGeneratorAgent.

This test directly instantiates and runs the ResponseGeneratorAgent
to examine its behavior outside of the workflow, particularly focusing
on citation generation.
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional

from src.agent_system.core.message import Message, MessageRole
from src.agent_system.rag_system.synthesis.response_generator_agent import ResponseGeneratorAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Output directory
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "isolation_test_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def test_response_generator_direct():
    """Test the ResponseGeneratorAgent in isolation, particularly for citations."""
    # Initialize agent with same config as in workflow
    agent_config = {
        "agent_id": "response_generator_agent",
        "model_config": {
            "model_type": "instruct",
            "max_tokens": 1024,
            "temperature": 0.2
        }
    }
    
    agent = ResponseGeneratorAgent("response_generator_agent", agent_config)
    
    # Test the direct dengue symptoms response
    test_query = "What are the main symptoms of dengue fever?"
    
    # Create input message
    input_message = Message(
        role=MessageRole.USER,
        content=test_query,
        metadata={
            "test": True,
            "original_query": test_query
        }
    )
    
    # Process the query directly with no input data
    agent_response, next_agent_id = await agent.process(
        input_message, 
        session_id=None
    )
    
    # Test with mock result data
    symptoms_data = {
        "results": [
            {"symptom": "High Fever", "description": "Temperature above 101°F (38.3°C)"},
            {"symptom": "Severe Headache", "description": "Often described as pain behind the eyes"},
            {"symptom": "Joint and Muscle Pain", "description": "Severe pain that feels like broken bones, hence 'breakbone fever'"},
            {"symptom": "Rash", "description": "Appears 3-4 days after onset of fever"}
        ],
        "citations": [
            {
                "title": "WHO Dengue Guidelines",
                "authors": "World Health Organization",
                "url": "https://www.who.int/denguecontrol/resources/9789241547871/en/",
                "year": 2009
            },
            {
                "title": "CDC Clinical Practice Guidelines for Dengue",
                "authors": "Centers for Disease Control and Prevention",
                "url": "https://www.cdc.gov/dengue/resources/dengue-clinician-guide_508.pdf",
                "year": 2020
            }
        ]
    }
    
    # Create message with result data
    result_message = Message(
        role=MessageRole.SYSTEM,
        content=json.dumps(symptoms_data),
        metadata={
            "test": True,
            "original_query": test_query,
            "cypher_query": "MATCH (d:Disease {name: 'Dengue Fever'})-[:HAS_SYMPTOM]->(s:Symptom) RETURN s.name as symptom, s.description as description",
            "pattern_name": "disease_symptoms",
            "result_count": 4,
            "assessment": "has_results"
        }
    )
    
    # Process with result data
    agent_response_with_data, next_agent_id = await agent.process(
        result_message, 
        session_id=None
    )
    
    # Timestamp for output
    timestamp = int(time.time())
    output_file = os.path.join(OUTPUT_DIR, f"response_generator_isolation_{timestamp}.md")
    
    # Test calling _generate_dengue_symptoms_response directly 
    direct_response_message, _ = await agent._generate_dengue_symptoms_response(
        test_query, 
        result_message
    )
    
    # Create a detailed report
    with open(output_file, "w") as f:
        f.write("# ResponseGeneratorAgent Isolation Test\n\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Agent Configuration\n\n")
        f.write("```json\n")
        f.write(json.dumps(agent_config, indent=2))
        f.write("\n```\n\n")
        
        f.write("## Test 1: Direct Query With No Data\n\n")
        f.write("### Query\n\n")
        f.write(f"`{test_query}`\n\n")
        
        f.write("### Response Content\n\n")
        f.write("```\n")
        f.write(agent_response.content if agent_response and agent_response.content else "No response")
        f.write("\n```\n\n")
        
        f.write("### Metadata\n\n")
        f.write("```json\n")
        f.write(json.dumps(agent_response.metadata, indent=2) if agent_response and agent_response.metadata else "No metadata")
        f.write("\n```\n\n")
        
        f.write("## Test 2: With Mock Symptom Data\n\n")
        f.write("### Input Data\n\n")
        f.write("```json\n")
        f.write(json.dumps(symptoms_data, indent=2))
        f.write("\n```\n\n")
        
        f.write("### Response Content\n\n")
        f.write("```\n")
        f.write(agent_response_with_data.content if agent_response_with_data and agent_response_with_data.content else "No response")
        f.write("\n```\n\n")
        
        f.write("### Metadata\n\n")
        f.write("```json\n")
        f.write(json.dumps(agent_response_with_data.metadata, indent=2) if agent_response_with_data and agent_response_with_data.metadata else "No metadata")
        f.write("\n```\n\n")
        
        f.write("## Test 3: Direct Call to _generate_dengue_symptoms_response\n\n")
        f.write("### Response Content\n\n")
        f.write("```\n")
        f.write(direct_response_message.content if direct_response_message and direct_response_message.content else "No response")
        f.write("\n```\n\n")
        
        f.write("### Metadata\n\n")
        f.write("```json\n")
        f.write(json.dumps(direct_response_message.metadata, indent=2) if direct_response_message and direct_response_message.metadata else "No metadata")
        f.write("\n```\n\n")
        
        f.write("## Analysis\n\n")
        f.write("This test examines the ResponseGeneratorAgent in isolation, particularly its ability to generate responses with citations.\n\n")
        
        # Check if citations are included in the responses
        has_citations_1 = agent_response.metadata and agent_response.metadata.get("has_citations", False) if agent_response else False
        citation_count_1 = agent_response.metadata.get("citation_count", 0) if agent_response and agent_response.metadata else 0
        
        has_citations_2 = agent_response_with_data.metadata and agent_response_with_data.metadata.get("has_citations", False) if agent_response_with_data else False
        citation_count_2 = agent_response_with_data.metadata.get("citation_count", 0) if agent_response_with_data and agent_response_with_data.metadata else 0
        
        has_citations_3 = direct_response_message.metadata and direct_response_message.metadata.get("has_citations", False) if direct_response_message else False
        citation_count_3 = direct_response_message.metadata.get("citation_count", 0) if direct_response_message and direct_response_message.metadata else 0
        
        f.write("### Citation Analysis\n\n")
        f.write(f"- Test 1 (No Data): has_citations={has_citations_1}, citation_count={citation_count_1}\n")
        f.write(f"- Test 2 (Mock Data): has_citations={has_citations_2}, citation_count={citation_count_2}\n")
        f.write(f"- Test 3 (Direct Method Call): has_citations={has_citations_3}, citation_count={citation_count_3}\n\n")
        
        # Look for citation formatting in content
        def has_citation_format(content):
            if not content:
                return False
            return "[1]" in content or "[2]" in content or "References:" in content or "##" in content
        
        format_1 = has_citation_format(agent_response.content if agent_response else None)
        format_2 = has_citation_format(agent_response_with_data.content if agent_response_with_data else None)
        format_3 = has_citation_format(direct_response_message.content if direct_response_message else None)
        
        f.write("### Citation Formatting in Content\n\n")
        f.write(f"- Test 1 (No Data): Citation formatting found = {format_1}\n")
        f.write(f"- Test 2 (Mock Data): Citation formatting found = {format_2}\n")
        f.write(f"- Test 3 (Direct Method Call): Citation formatting found = {format_3}\n")
    
    logger.info(f"ResponseGeneratorAgent isolation test completed. Results saved to {output_file}")
    return output_file

if __name__ == "__main__":
    """Run the test when script is executed directly."""
    asyncio.run(test_response_generator_direct())
