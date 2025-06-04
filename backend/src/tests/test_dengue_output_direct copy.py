"""
Direct test for the Output Combiner Agent focusing specifically on dengue data handling.

This test directly creates an OutputCombinerAgent and calls it with simulated dengue data
to verify the raw data is included in the final output.
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

from src.agent_system.rag_system.output_combiner_agent import OutputCombinerAgent
from src.agent_system.core.message import Message, MessageRole

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dengue_output_test")

# Sample dengue data for testing
SAMPLE_DENGUE_DATA = {
    "countries_data": [
        {
            "country": "Saudi Arabia",
            "api_country": "saudi_arabia",
            "current_date": "2025-05-02",
            "presentation_date": "2025-05-22",
            "historical_data": [
                {
                    "calendar_start_date": "2022-01-01",
                    "country": "saudi_arabia",
                    "dengue_total": 42,
                    "avg_temperature": 22.5,
                    "avg_humidity": 35.3
                },
                {
                    "calendar_start_date": "2022-02-01",
                    "country": "saudi_arabia",
                    "dengue_total": 51,
                    "avg_temperature": 24.2,
                    "avg_humidity": 33.1
                },
                {
                    "calendar_start_date": "2022-03-01",
                    "country": "saudi_arabia",
                    "dengue_total": 75,
                    "avg_temperature": 27.1,
                    "avg_humidity": 31.7
                }
            ],
            "predicted_data": [
                {
                    "calendar_start_date": "2025-05-01",
                    "country": "saudi_arabia",
                    "dengue_total": 76.08,
                    "avg_temperature": None,
                    "avg_humidity": None
                },
                {
                    "calendar_start_date": "2025-06-01",
                    "country": "saudi_arabia",
                    "dengue_total": 112.33,
                    "avg_temperature": None,
                    "avg_humidity": None
                }
            ]
        }
    ],
    "original_query": "Test query about dengue in Saudi Arabia",
    "query_context": "travel",
    "analysis": {
        "summaries": [
            {
                "country": "Saudi Arabia",
                "summary_text": "**DENGUE DATA STATISTICS FOR SAUDI ARABIA**\n\n• Data source: Saudi_Arabia\n• Recent trend: Dengue fever cases have been decreasing\n• Average cases: 169.0 cases per reporting period\n• September historical average: 196.0 cases\n"
            }
        ]
    }
}

async def test_output_combiner_with_dengue_data():
    """Test that OutputCombinerAgent correctly includes raw dengue data."""
    logger.info("Starting direct test of OutputCombinerAgent with dengue data")
    
    # Create test output directory
    output_dir = project_root / "logs" / "output_combiner_tests"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create an OutputCombinerAgent instance with required parameters
    agent_id = "rag_output_combiner_agent"
    config = {
        "llm_config": {
            "model": "gpt-3.5-turbo",
            "temperature": 0.2
        }
    }
    agent = OutputCombinerAgent(agent_id=agent_id, config=config)
    
    # Create a message with dengue data in metadata
    dengue_data_str = json.dumps(SAMPLE_DENGUE_DATA)
    
    metadata = {
        "original_query": "I have a patient traveling to Saudi Arabia who had dengue before. Advice?",
        "dengue_data_visualization_agent": dengue_data_str,
        "data_summaries": [
            {
                "country": "Saudi Arabia",
                "summary_text": "**DENGUE DATA STATISTICS FOR SAUDI ARABIA**\n\n• Data source: Saudi_Arabia\n• Recent trend: Dengue fever cases have been decreasing\n• Average cases: 169.0 cases per reporting period\n• September historical average: 196.0 cases\n"
            }
        ]
    }
    
    test_message = Message(
        role=MessageRole.USER,
        content="This is a test message",
        metadata=metadata
    )
    
    # Process the message with the OutputCombinerAgent
    result_message, _ = await agent._execute_processing(test_message)
    
    # Save the result to a file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = output_dir / f"direct_dengue_test_{timestamp}.txt"
    
    with open(result_file, "w") as f:
        f.write(f"=== RESULT CONTENT ===\n{result_message.content}\n\n")
        f.write(f"=== RESULT METADATA ===\n{json.dumps(result_message.metadata, indent=2)}\n")
    
    logger.info(f"Test result saved to: {result_file}")
    
    # Check if the raw dengue data is in the result content
    if "countries_data" in result_message.content and "historical_data" in result_message.content:
        logger.info("SUCCESS: Raw dengue data found in output content")
        print(f"SUCCESS: Raw dengue data found in output!")
        print(f"See detailed results in: {result_file}")
        return True
    else:
        logger.error("FAILURE: Raw dengue data not found in output content")
        print(f"FAILURE: Raw dengue data not found in output!")
        print(f"See detailed results in: {result_file}")
        return False

if __name__ == "__main__":
    print("Starting direct test of Output Combiner with dengue data...")
    asyncio.run(test_output_combiner_with_dengue_data())
