"""
Test script for DengueDataVisualizationAgent in an isolated workflow.

This script creates a minimal workflow that only contains the visualization agent,
then initializes it with realistic metadata from a full workflow run.
"""

import asyncio
import json
import logging
import sys
import os
import uuid
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("test_visualization_workflow")

# Import workflow components
from backend.src.agent_system.core.workflow_manager import WorkflowManager
from backend.src.agent_system.core.message import Message, MessageRole

async def test_visualization_agent_workflow():
    """Test the visualization agent in an isolated workflow."""
    
    # Create a temporary workflow definition
    temp_workflow_id = "TEST_VISUALIZATION_WORKFLOW"
    temp_workflow_file = os.path.join(
        os.path.dirname(__file__), 
        "..", 
        "registries", 
        "workflows", 
        f"{temp_workflow_id}.json"
    )
    
    # Define a minimal workflow with just the visualization agent
    workflow_def = {
        "steps": [
            "dengue_data_visualization_agent"
        ]
    }
    
    # Create the temporary workflow file
    with open(temp_workflow_file, "w") as f:
        json.dump(workflow_def, f, indent=2)
    
    try:
        # Initialize workflow manager
        registry_dir = os.path.join(os.path.dirname(__file__), "..", "registries", "workflows")
        workflow_manager = WorkflowManager(registry_dir)
        
        # Create a test query
        test_query = "I have a patient who lives in New York and plans to travel to Saudi Arabia on September 1, 2025. What should I tell him about how to protect himself from dengue? He has had dengue before."
        
        # Create a session
        session_id = f"test-{temp_workflow_id}-{uuid.uuid4().hex[:8]}"
        
        # Initialize metadata using values that would typically come from earlier agents
        initial_metadata = {
            "original_query": test_query,
            "rewritten_query": "What are the dengue prevalence rates and travel advisories for Saudi Arabia in September 2025, and what preventative measures should a traveler with prior dengue exposure follow?",
            "safety_checked": True,
            "safety_check_passed": True,
            "query": "MATCH (p:PreventionMeasure)-[:PREVENTS]->(d:Disease {name: 'Dengue Fever'}) RETURN p.name as prevention_measure, p.description as description",
            "query_type": "cypher",
            "pattern_name": "disease_prevention",
            "results": [
                {
                    "prevention_measure": "Protective Clothing",
                    "description": None
                },
                {
                    "prevention_measure": "Bed Nets",
                    "description": None
                },
                {
                    "prevention_measure": "Insect Repellent Use",
                    "description": None
                }
            ],
            "assessment": "partial_results"
        }
        
        # Create the process_message parameters
        message_content = test_query
        
        logger.info(f"Running isolated workflow test for visualization agent: {test_query}")
        
        # Process the message with the temporary workflow and pre-populated metadata
        response = await workflow_manager.process_message(
            message_content=message_content,
            session_id=session_id,
            metadata=initial_metadata,
            workflow_id=temp_workflow_id
        )
        
        # Analyze the results
        if response and "data" in response and "final_metadata" in response["data"]:
            final_metadata = response["data"]["final_metadata"]
            
            # Check the visualization data
            if "dengue_data" in final_metadata:
                dengue_data = final_metadata["dengue_data"]
                logger.info(f"Visualization agent produced dengue_data with keys: {list(dengue_data.keys())}")
                
                if "countries" in dengue_data:
                    logger.info(f"Detected countries: {dengue_data['countries']}")
                
                # Count countries with data
                countries_data = dengue_data.get("countries_data", [])
                logger.info(f"Countries with data: {len(countries_data)}")
                
                # Save the result to a file for detailed inspection
                with open("visualization_test_result.json", "w") as f:
                    json.dump(response, f, indent=2)
                    logger.info("Saved full result to visualization_test_result.json")
                
                return len(countries_data) > 0
            else:
                logger.error("No 'dengue_data' in final metadata")
                logger.info(f"Final metadata keys: {list(final_metadata.keys())}")
                
                # Save the result for debugging
                with open("visualization_test_result.json", "w") as f:
                    json.dump(response, f, indent=2)
                    logger.info("Saved full result to visualization_test_result.json")
                
                return False
        else:
            logger.error("Unexpected response format")
            return False
    
    finally:
        # Clean up the temporary workflow file
        if os.path.exists(temp_workflow_file):
            os.remove(temp_workflow_file)

if __name__ == "__main__":
    result = asyncio.run(test_visualization_agent_workflow())
    
    if result:
        logger.info("TEST PASSED: Visualization agent successfully detected countries and retrieved data")
        sys.exit(0)
    else:
        logger.error("TEST FAILED: Visualization agent did not produce expected country data")
        sys.exit(1)
