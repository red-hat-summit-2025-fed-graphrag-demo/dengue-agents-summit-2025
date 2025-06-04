"""
Direct test of the response generator agent to verify its behavior with empty results.
"""
import os
import sys
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List

# Add the project root to the Python path
project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))

from src.agent_system.core.message import Message, MessageRole
from src.agent_system.rag_system.synthesis.response_generator_agent import ResponseGeneratorAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("response_generator_test")

async def test_response_generator():
    """
    Test the response generator with a sample query about dengue symptoms.
    Create multiple test cases:
    1. With good data (simulating successful DB retrieval)
    2. With empty data (simulating no DB results)
    """
    # Create output directory
    output_dir = os.path.join(project_root, "response_generator_test")
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize the agent
    agent_config = {
        "agent_id": "test_response_generator",
        "class_name": "ResponseGeneratorAgent",
        "model_config": {
            "model_type": "instruct",
            "temperature": 0.1
        }
    }
    
    agent = ResponseGeneratorAgent("test_response_generator", agent_config)
    
    # Test case 1: Good data with symptoms
    logger.info("Test case 1: With properly formatted symptom data")
    symptom_data = [
        {"symptom": "Fever", "description": "High fever, typically 39-40°C (102-104°F)"},
        {"symptom": "Headache", "description": "Severe headache, often with retroorbital pain"},
        {"symptom": "Myalgia", "description": "Muscle pain or myalgia"},
        {"symptom": "Arthralgia", "description": "Joint pain"},
        {"symptom": "Rash", "description": "Maculopapular or petechial rash, usually appearing 3-4 days after fever onset"}
    ]
    
    # Create message with good data
    good_message = Message(
        role=MessageRole.USER,
        content="What are the main symptoms of dengue fever?",
        metadata={
            "query": "MATCH (d:Disease {name: 'Dengue Fever'})-[:HAS_SYMPTOM]->(s:Symptom) RETURN s.name as symptom, s.description as description",
            "result_count": len(symptom_data),
            "status": "success",
            "results": symptom_data
        }
    )
    
    # Process the good message
    good_response, _ = await agent.process(good_message)
    
    # Save the good response
    with open(os.path.join(output_dir, "good_response.md"), "w") as f:
        f.write("# Response Generator Test: Good Data\n\n")
        f.write("## Input Question\n\n")
        f.write(f"{good_message.content}\n\n")
        f.write("## Input Metadata\n\n")
        f.write("```json\n")
        f.write(json.dumps(good_message.metadata, indent=2))
        f.write("\n```\n\n")
        f.write("## Response\n\n")
        f.write(f"{good_response.content}\n\n")
        f.write("## Response Metadata\n\n")
        f.write("```json\n")
        f.write(json.dumps(good_response.metadata, indent=2, default=str))
        f.write("\n```\n\n")
    
    # Test case 2: Empty data
    logger.info("Test case 2: With empty results (simulating DB miss)")
    empty_message = Message(
        role=MessageRole.USER,
        content="What is the relationship between rainfall and dengue fever outbreaks?",
        metadata={
            "query": "MATCH (d:Disease {name: 'Dengue Fever'})-[:HAS_CLIMATE_FACTOR]->(cf:ClimateFactor) RETURN cf.name as climate_factor, cf.description as description",
            "result_count": 0,
            "status": "success",
            "has_insufficient_data": True,
            "results": []
        }
    )
    
    # Process the empty message
    empty_response, _ = await agent.process(empty_message)
    
    # Save the empty response
    with open(os.path.join(output_dir, "empty_response.md"), "w") as f:
        f.write("# Response Generator Test: Empty Data\n\n")
        f.write("## Input Question\n\n")
        f.write(f"{empty_message.content}\n\n")
        f.write("## Input Metadata\n\n")
        f.write("```json\n")
        f.write(json.dumps(empty_message.metadata, indent=2))
        f.write("\n```\n\n")
        f.write("## Response\n\n")
        f.write(f"{empty_response.content}\n\n")
        f.write("## Response Metadata\n\n")
        f.write("```json\n")
        f.write(json.dumps(empty_response.metadata, indent=2, default=str))
        f.write("\n```\n\n")
    
    # Test case 3: Workflow processing error 
    logger.info("Test case 3: With a processing error in metadata")
    error_message = Message(
        role=MessageRole.USER,
        content="How do climate factors like temperature and humidity influence the replication rate of the dengue virus in mosquitoes?",
        metadata={
            "query": "MATCH (cf:ClimateFactor)-[:HAS_CLIMATE_FACTOR_ON]->(v:Vector)-[:TRANSMITS]->(d:Disease {name: 'Dengue Fever'}) RETURN cf.name, cf.description",
            "result_count": 0,
            "status": "error",
            "error": "Error executing Cypher query: Relationship type HAS_CLIMATE_FACTOR_ON not found",
            "assessment": "error",
            "results": []
        }
    )
    
    # Process the error message
    error_response, _ = await agent.process(error_message)
    
    # Save the error response
    with open(os.path.join(output_dir, "error_response.md"), "w") as f:
        f.write("# Response Generator Test: Error Data\n\n")
        f.write("## Input Question\n\n")
        f.write(f"{error_message.content}\n\n")
        f.write("## Input Metadata\n\n")
        f.write("```json\n")
        f.write(json.dumps(error_message.metadata, indent=2))
        f.write("\n```\n\n")
        f.write("## Response\n\n")
        f.write(f"{error_response.content}\n\n")
        f.write("## Response Metadata\n\n")
        f.write("```json\n")
        f.write(json.dumps(error_response.metadata, indent=2, default=str))
        f.write("\n```\n\n")
    
    logger.info(f"Response generator test results saved to {output_dir}")
    return output_dir

if __name__ == "__main__":
    output_dir = asyncio.run(test_response_generator())
    print(f"\nTest results saved to: {output_dir}")
