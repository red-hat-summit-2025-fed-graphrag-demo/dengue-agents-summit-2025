#!/usr/bin/env python3
"""
Test script for the LLM-assisted output combiner agent.

This script directly tests the LLM-assisted output combination approach
without using the full workflow manager.
"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Tuple

# Add src directory to python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, os.path.dirname(src_dir))

# Configure logging
log_dir = os.path.join(os.path.dirname(src_dir), "logs", "output_combiner_tests")
os.makedirs(log_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"llm_output_combiner_{timestamp}.log")

# Set up logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("llm_output_combiner_test")

# Import the necessary modules
from src.agent_system.core.message import Message, MessageRole
from src.agent_system.rag_system.output_combiner_agent import OutputCombinerAgent
from src.tools.schema_tool import SchemaTool

# Sample data for testing
SAMPLE_RESPONSE = """
### DENGUE FEVER ADVICE FOR TRAVEL TO SAUDI ARABIA

Given your patient's history of dengue fever in the last three years, it's crucial to provide specific advice regarding the upcoming trip to Saudi Arabia.

**Dengue Fever Prevalence in Saudi Arabia:**
Although dengue fever is not endemic to Saudi Arabia, cases have been reported in the past. The risk is generally low, but it's still essential to take precautions, especially for individuals with a history of dengue infection.

**Increased Risk for Severe Disease:**
Patients who have had dengue fever in the past are at a higher risk of developing severe dengue if infected again. This risk is heightened during travel, as exposure to new environments and mosquito species can occur.

**Preventive Measures:**

1. **Use Insect Repellent:**
   - Apply an EPA-registered insect repellent containing DEET, picaridin, IR3535, or oil of lemon eucalyptus.
   - Reapply as directed on the product label.

2. **Wear Protective Clothing:**
   - Wear long sleeves, long pants, and socks when outdoors, especially during peak mosquito activity (dawn and dusk).

3. **Stay in Accommodations with Air Conditioning or Screens:**
   - Mosquitoes that transmit dengue fever often breed in indoor spaces without proper screening or air conditioning.

4. **Avoid Mosquito Bites:**
   - Use mosquito nets while sleeping and consider using insect repellent on exposed skin.

**Seeking Medical Care:**

- If your patient develops dengue fever symptoms (sudden high fever, severe headache, pain behind the eyes, muscle and joint pain, nausea, and vomiting) during or after travel, seek medical attention immediately.
- Inform the healthcare provider of your patient's history of dengue fever and the recent travel to Saudi Arabia.

**Pre-travel Consultation:**

- It's highly recommended to consult with a travel medicine specialist before the trip.
- The specialist can provide personalized advice based on the latest data and your patient's medical history.

**Sources:**

- Centers for Disease Control and Prevention (CDC): [Dengue Virus](https://www.cdc.gov/dengue/index.html)
- World Health Organization (WHO): [Dengue and Severe Dengue](https://www.who.int/news-room/fact-sheets/detail/dengue-and-severe-dengue)

By following these guidelines, your patient can significantly reduce the risk of dengue fever during the trip to Saudi Arabia.
"""

SAMPLE_VISUALIZATION = """
**DENGUE DATA STATISTICS FOR SAUDI ARABIA**

• Data source: Saudi_Arabia (used as proxy for Saudi Arabia)
• Recent trend: Dengue fever cases have been stable recently
• Average cases: 0.0 cases per reporting period
• September forecast: No specific prediction available for this month

*Data for: Saudi Arabia*
"""

async def stream_thinking_callback(thinking, agent_id=None, **kwargs):
    """Stream thinking callback to log the agent's thought process."""
    logger.info(f"Agent thinking: {thinking}")

async def run_llm_combiner_test() -> Tuple[str, str]:
    """
    Run a direct test of the LLM-assisted output combination.
    
    Returns:
        Tuple of (combined_content, result_file_path)
    """
    logger.info("Initializing OutputCombinerAgent")
    
    # Initialize schema tool
    schema_tool = SchemaTool()
    
    # Create agent with proper initialization
    agent_id = "rag_output_combiner_agent"
    config = {
        "model_config": {
            "temperature": 0.1,
            "model_type": "instruct"
        },
        "tools": {
            "schema_tool": schema_tool
        }
    }
    
    # Initialize the agent with the correct parameters
    output_combiner = OutputCombinerAgent(agent_id, config)
    
    # Create a sample message with all the necessary metadata
    metadata = {
        "visualization_data": {
            "countries": ["Saudi Arabia"],
            "analysis": {
                "summaries": [
                    {
                        "country": "Saudi Arabia",
                        "summary_text": SAMPLE_VISUALIZATION
                    }
                ]
            }
        },
        "response_generator_output": SAMPLE_RESPONSE,
        "dengue_data_retrieved": True,
        "has_visualization_data": True
    }
    
    message = Message(
        role=MessageRole.USER,
        content=SAMPLE_RESPONSE,
        metadata=metadata
    )
    
    # Process the message
    logger.info("Processing message with OutputCombinerAgent")
    
    # Set the callback directly on the current_stream_callback property
    output_combiner.current_stream_callback = stream_thinking_callback
    
    # Process the message
    response_message, _ = await output_combiner._execute_processing(message)
    
    if not response_message:
        logger.error("Failed to get a response from the output combiner agent")
        return "Failed to combine outputs", ""
    
    # Save the result to a file
    result_file = os.path.join(log_dir, f"llm_combiner_result_{timestamp}.txt")
    with open(result_file, "w") as f:
        f.write(response_message.content)
    
    logger.info(f"Result saved to {result_file}")
    
    return response_message.content, result_file

async def main():
    """Main function to run the test."""
    print("Starting LLM-Assisted Output Combiner Agent test...")
    print(f"Log file: {log_file}")
    
    combined_content, result_file = await run_llm_combiner_test()
    
    print("\nTest completed!")
    print(f"Result file: {result_file}")
    
    # Print a summary of the combined content
    content_length = len(combined_content)
    print(f"\nCombined content length: {content_length} characters")
    print("\nFirst 200 characters of combined content:")
    print(f"{combined_content[:200]}...")
    print("\nLast 200 characters of combined content:")
    print(f"...{combined_content[-200:]}")

if __name__ == "__main__":
    asyncio.run(main())
