"""
Direct test script for the Output Combiner Agent.

This script directly tests the output combiner agent without using the workflow
manager, to isolate and fix any issues with the combination logic.
"""

import sys
import os
import json
import asyncio
import logging
from typing import Dict, Any
from datetime import datetime

# Add the src directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
backend_dir = os.path.dirname(src_dir)
sys.path.append(backend_dir)

from src.agent_system.core.message import Message, MessageRole
from src.agent_system.rag_system.output_combiner_agent import OutputCombinerAgent
from src.tools.schema_tool import SchemaTool

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("direct_output_combiner_test")

async def run_direct_test():
    """Run a direct test of the output combiner agent."""
    # Initialize the output combiner agent
    logger.info("Initializing OutputCombinerAgent")
    
    # Initialize schema tool first
    schema_tool = SchemaTool()
    
    # Create config with all required parameters
    config = {
        "model_config": {
            "temperature": 0.1,
            "model_type": "instruct"
        },
        "tools": {
            "schema_tool": schema_tool
        }
    }
    
    # Initialize the agent with the config
    output_combiner = OutputCombinerAgent(config)
    
    # Create a sample response generator output
    response_content = """
    Given your patient's history of dengue fever in the last three years, I recommend the following advice for his trip to Saudi Arabia in September:

    1. **Dengue Risk Assessment**: Saudi Arabia is not considered a high-risk country for dengue fever. The risk varies by region, but is generally low.

    2. **Preventive Measures**:
       - Use insect repellent containing DEET on exposed skin
       - Wear long-sleeved shirts and long pants, especially during dawn and dusk
       - Stay in accommodations with air conditioning or window/door screens
       - Use a bed net if sleeping areas are not screened or air-conditioned

    3. **Medical Considerations**:
       - Patients with previous dengue infection have a higher risk of severe dengue if infected again
       - Advise him to seek medical attention immediately if he develops symptoms (fever, headache, muscle/joint pain)
       - Carry a medical alert card mentioning his history of dengue fever

    4. **Travel Insurance**: Ensure he has comprehensive travel insurance that covers medical evacuation.

    5. **Pre-Travel Consultation**: Schedule a pre-travel consultation with a travel medicine specialist.

    **Sources**:
    - Centers for Disease Control and Prevention (CDC)
    - World Health Organization (WHO) dengue guidelines
    """
    
    # Create sample visualization data
    visualization_data = {
      "countries": [
        "Saudi Arabia"
      ],
      "analysis": {
        "summaries": [
          {
            "country": "Saudi Arabia",
            "summary_text": "**DENGUE DATA STATISTICS FOR SAUDI ARABIA**\n\n• Data source: Saudi_Arabia (used as proxy for Saudi Arabia)\n• Recent trend: Dengue fever cases have been stable recently\n• Average cases: 0.0 cases per reporting period\n• September forecast: No specific prediction available for this month\n"
          }
        ]
      }
    }
    
    # Create a message with visualization data AND directly set the content to response_content
    message = Message(
        role=MessageRole.USER,
        content=response_content,  # Directly use the response content here
        metadata={
            "visualization_data": visualization_data,
            "response_generator_output": response_content,
            "has_visualization_data": True,
        }
    )
    
    # Process the message through the output combiner agent
    logger.info("Processing message through OutputCombinerAgent")
    start_time = datetime.now()
    result, _ = await output_combiner.process(message)
    end_time = datetime.now()
    
    processing_time = (end_time - start_time).total_seconds() * 1000
    logger.info(f"Processing completed in {processing_time:.2f}ms")
    
    # Check if the result contains both response and visualization content
    combined_content = result.content
    has_response = "Preventive Measures" in combined_content or "patient's history" in combined_content
    has_visualization = "DENGUE DATA STATISTICS" in combined_content and "Saudi Arabia" in combined_content
    
    logger.info(f"Combined content has response: {has_response}")
    logger.info(f"Combined content has visualization: {has_visualization}")
    
    # Save the result to a file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join(backend_dir, "logs", "output_combiner_tests")
    os.makedirs(log_dir, exist_ok=True)
    
    result_file = os.path.join(log_dir, f"direct_output_combiner_result_{timestamp}.txt")
    with open(result_file, 'w') as f:
        f.write(combined_content)
    
    logger.info(f"Result saved to {result_file}")
    return combined_content, has_response, has_visualization, result_file

async def main():
    """Main function to run the test."""
    print("Starting Direct Output Combiner Agent test...")
    
    combined_content, has_response, has_visualization, result_file = await run_direct_test()
    
    if has_response and has_visualization:
        print("\nTest PASSED!")
        print("The output combiner successfully combined both response and visualization content.")
        print(f"Result saved to: {result_file}")
    else:
        print("\nTest FAILED!")
        if not has_response:
            print("- Missing response generator content")
        if not has_visualization:
            print("- Missing visualization content")
        print(f"Result saved to: {result_file}")
    
    # Print a snippet of the combined content
    print("\nCombined Content Preview:")
    print("-" * 40)
    preview = combined_content[:500] + "..." if len(combined_content) > 500 else combined_content
    print(preview)
    print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())
