"""
Direct test of the response generator agent with symptom data and citations.
This test bypasses the workflow to directly test response generation with
known good data patterns.
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime

from src.agent_system.core.message import Message, MessageRole
from src.agent_system.rag_system.synthesis.response_generator_agent import ResponseGeneratorAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Output directory
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "direct_response_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Sample symptom data that matches our graph schema
SAMPLE_SYMPTOM_DATA = {
    "original_query": "What are the main symptoms of dengue fever?",
    "results": [
        {
            "symptom": "Fever",
            "description": "High fever, typically 39-40°C (102-104°F)"
        },
        {
            "symptom": "Headache",
            "description": "Severe headache, often with retroorbital pain"
        },
        {
            "symptom": "Myalgia",
            "description": "Muscle pain or myalgia"
        },
        {
            "symptom": "Arthralgia",
            "description": "Joint pain"
        },
        {
            "symptom": "Rash",
            "description": "Maculopapular or petechial rash, usually appearing 3-4 days after fever onset"
        },
        {
            "symptom": "Nausea",
            "description": "Feeling of sickness with an inclination to vomit"
        },
        {
            "symptom": "Vomiting",
            "description": "Forceful expulsion of stomach contents through the mouth"
        }
    ],
    "result_count": 7,
    "assessment": "high_quality",
    "format": "detailed",
    "citations": [
        {
            "title": "WHO Dengue Guidelines for Diagnosis, Treatment, Prevention and Control",
            "authors": "World Health Organization",
            "url": "https://www.who.int/denguecontrol/resources/9789241547871/en/",
            "year": 2009
        },
        {
            "title": "Dengue: Guidelines for Diagnosis, Treatment, Prevention and Control: New Edition",
            "authors": "World Health Organization",
            "url": "https://www.ncbi.nlm.nih.gov/books/NBK143157/",
            "year": 2009
        },
        {
            "title": "Clinical practice guidelines for dengue fever and dengue hemorrhagic fever",
            "authors": "CDC",
            "url": "https://www.cdc.gov/dengue/resources/dengue-clinician-guide_508.pdf",
            "year": 2020
        }
    ]
}

async def test_direct_response_generation():
    """Test the response generator with direct sample data."""
    # Initialize response generator agent
    agent_config = {
        "agent_id": "response_generator_agent",
        "model_config": {
            "model_type": "instruct",
            "max_tokens": 2048,
            "temperature": 0.5
        },
        "prompt_id": "rag.response_generator"
    }
    
    response_agent = ResponseGeneratorAgent("response_generator_agent", agent_config)
    
    # Create timestamp for output
    timestamp = int(time.time())
    output_file = os.path.join(OUTPUT_DIR, f"direct_response_{timestamp}.md")
    
    # Create input message with sample data
    input_message = Message(
        role=MessageRole.USER,
        content=json.dumps(SAMPLE_SYMPTOM_DATA, indent=2),
        metadata={
            "original_query": SAMPLE_SYMPTOM_DATA["original_query"],
            "result_count": SAMPLE_SYMPTOM_DATA["result_count"]
        }
    )
    
    # Process with response generator
    response_message, _ = await response_agent.process(input_message)
    
    # Save results
    with open(output_file, "w") as f:
        f.write("# Direct Response Generator Test\n\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Input Query\n\n")
        f.write(f"{SAMPLE_SYMPTOM_DATA['original_query']}\n\n")
        
        f.write("## Input Data\n\n")
        f.write("```json\n")
        f.write(json.dumps(SAMPLE_SYMPTOM_DATA, indent=2))
        f.write("\n```\n\n")
        
        f.write("## Generated Response\n\n")
        if response_message:
            f.write(f"{response_message.content}\n\n")
            
            # Save metadata
            if response_message.metadata:
                f.write("## Response Metadata\n\n")
                f.write("```json\n")
                f.write(json.dumps(response_message.metadata, indent=2))
                f.write("\n```\n\n")
        else:
            f.write("No response generated.\n\n")
    
    logger.info(f"Direct response test completed. Results saved to {output_file}")
    return output_file

if __name__ == "__main__":
    """Run the test when script is executed directly."""
    asyncio.run(test_direct_response_generation())
