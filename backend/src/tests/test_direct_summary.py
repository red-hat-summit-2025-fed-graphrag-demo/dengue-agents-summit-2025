"""
Test script to directly check if our data summaries are being passed correctly
to the ResponseGeneratorAgent and included in the final response.
"""

import json
import logging
import time
import asyncio
import os
from pathlib import Path

from src.agent_system.rag_system.synthesis.response_generator_agent import ResponseGeneratorAgent
from src.agent_system.core.message import Message, MessageRole
from src.agent_system.core.agent_config import AgentConfig
from src.registries.prompt_registry import PromptRegistry
from src.registries.model_registry import ModelRegistry, ModelProvider
from src.models.model_proxy import ModelProxy
from src.registries.citation_registry import CitationRegistry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_direct_summary():
    """
    Test direct summary inclusion in ResponseGeneratorAgent
    """
    logger.info("Testing direct summary inclusion in ResponseGeneratorAgent")
    
    # Initialize registries
    logger.info("Initializing registries...")
    prompt_registry = PromptRegistry()
    model_registry = ModelRegistry()
    citation_registry = CitationRegistry()
    
    # Set up model proxy
    model_proxy = ModelProxy()
    
    # Initialize the ResponseGeneratorAgent with proper parameters
    agent_id = "response_generator_agent"
    config = AgentConfig(
        name="Response Generator Agent",
        description="Generates informative responses based on query results",
        agent_type="synthesis",
        enabled=True,
        model_type="instruct",
        prompt_id="rag.response_generator"
    )
    
    agent = ResponseGeneratorAgent(
        agent_id=agent_id,
        config=config,
        prompt_registry=prompt_registry,
        model_registry=model_registry,
        citation_registry=citation_registry,
        model_provider=ModelProvider.INSTRUCT
    )
    
    # Create a test output directory
    output_dir = Path("/Users/wesjackson/Code/Summit2025/dengue-agents-summit-2025/backend/direct_summary_results")
    output_dir.mkdir(exist_ok=True)
    
    # Create a test message with explicit data summary for Saudi Arabia
    test_message = Message(
        role=MessageRole.ASSISTANT,
        content="Content doesn't matter for this test",
        metadata={
            "original_query": "I have a patient who is traveling to Saudi Arabia in October. What should I tell them about dengue fever risk and prevention?",
            "test": True,
            "dengue_data_retrieved": True,
            "countries": ["Saudi Arabia"],
            "has_data": True,
            "visualization_ready": True,
            "data_summaries": [
                {
                    "country": "Saudi Arabia", 
                    "summary_text": "Based on available data from Saudi_Arabia (used as a proxy for Saudi Arabia), dengue fever cases have been stable recently, with an average of 0.0 cases per reporting period."
                }
            ],
            "has_visualization_data": True,
        }
    )
    
    # Add citations to the metadata
    test_message.metadata["citations"] = [
        {
            "title": "Dengue in Travelers",
            "authors": "Centers for Disease Control and Prevention",
            "url": "https://www.cdc.gov/dengue/prevention/travelers.html",
            "year": 2023
        },
        {
            "title": "CDC Yellow Book: Dengue",
            "authors": "Centers for Disease Control and Prevention",
            "url": "https://wwwnc.cdc.gov/travel/yellowbook/2020/travel-related-infectious-diseases/dengue",
            "year": 2019
        }
    ]
    test_message.metadata["has_citations"] = True
    test_message.metadata["citation_count"] = 2
    
    # Process the message
    logger.info("Processing test message with explicit data summaries")
    response, _ = await agent._execute_processing(test_message)
    
    # Save the result
    timestamp = int(time.time())
    result_file = output_dir / f"direct_summary_test_{timestamp}.md"
    
    with open(result_file, "w") as f:
        f.write(f"# Direct Summary Test\n\n")
        f.write(f"**Test timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Test Summary\n\n")
        f.write(f"Testing if the ResponseGeneratorAgent properly includes data summaries in the response.\n\n")
        f.write(f"### Input Data Summary\n\n")
        f.write(f"Summary text: `{test_message.metadata['data_summaries'][0]['summary_text']}`\n\n")
        f.write(f"## Final Response\n\n")
        f.write(f"```markdown\n{response.content if response else 'No response generated'}\n```\n\n")
        
        # Save the metadata
        f.write(f"## Response Metadata\n\n")
        f.write(f"```json\n{json.dumps(response.metadata if response else {}, indent=2)}\n```\n")
    
    logger.info(f"Test results saved to {result_file}")
    return result_file

if __name__ == "__main__":
    result_file = asyncio.run(test_direct_summary())
    print(f"Test completed. Results saved to: {result_file}")
