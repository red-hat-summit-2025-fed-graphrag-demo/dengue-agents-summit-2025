"""
Template Selector Agent (Placeholder)

A simplified placeholder for the template selector functionality.
This agent will be expanded in the future to support various response templates.

For now, it simply passes the assessment and results to the response generator.
"""
import logging
import json
from typing import Any, Dict, List, Optional, Tuple

from src.agent_system.core.base_agent import BaseAgent
from src.agent_system.core.message import Message, MessageRole

logger = logging.getLogger(__name__)

class TemplateSelectorAgent(BaseAgent):  
    """
    A placeholder agent for template selection
    
    Currently a simple pass-through that will be expanded in the future to:
    1. Select from various response templates based on query content
    2. Apply appropriate formatting rules for different result types
    3. Support visualization and structured output formats
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], **kwargs):
        """
        Initialize the TemplateSelectorAgent.
        
        Args:
            agent_id: The unique identifier for this agent
            config: The agent configuration dictionary
            **kwargs: Additional keyword arguments
        """
        # Make sure agent_id is in the config
        if "agent_id" not in config:
            config["agent_id"] = agent_id
            
        super().__init__(config, **kwargs)
        
        logger.info(f"Initialized TemplateSelectorAgent (placeholder) with ID: {agent_id}")
    
    async def _stream_thinking_hook(self, stream_callback: Any):
        """Optional hook called by BaseAgent.process to stream initial thoughts."""
        await self.stream_thinking(
            thinking=f"Processing results for response generation...",
            stream_callback=stream_callback
        )
        
    async def _execute_processing(
        self, 
        message: Message, 
        session_id: Optional[str] = None
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Core processing logic for the TemplateSelectorAgent.
        Currently just passes through the assessment data to the response generator.
        
        Args:
            message: The input message to process (containing result assessment)
            session_id: Optional session identifier
            
        Returns:
            Tuple of (response_message, next_agent_id)
        """
        try:
            # Parse the content as JSON
            assessment_data = json.loads(message.content)
            
            # Add a placeholder field to indicate this came through the template selector
            assessment_data["template_processed"] = "placeholder"
            assessment_data["format"] = "default"
            
            # Create simple response that passes the assessment data through
            response_message = Message(
                role=MessageRole.ASSISTANT,
                content=json.dumps(assessment_data, indent=2),
                metadata={
                    "template_processed": "placeholder",
                    "source": "template_selector_agent"
                }
            )
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse assessment from message: {e}")
            # Create a simple error response
            error_data = {
                "error": f"Failed to parse assessment: {str(e)}",
                "template_processed": "placeholder",
                "format": "default",
                "original_message": message.content if len(message.content) < 100 else message.content[:100] + "..."
            }
            
            response_message = Message(
                role=MessageRole.ASSISTANT,
                content=json.dumps(error_data, indent=2),
                metadata={"error": str(e)}
            )
        
        # Chain to the response generator agent
        return response_message, "response_generator_agent"
