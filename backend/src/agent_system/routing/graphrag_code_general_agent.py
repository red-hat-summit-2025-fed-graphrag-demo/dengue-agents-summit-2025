"""
Graphrag Code General Agent

A specialized agent for graphrag code general functionality
Uses a prompt from the prompt registry for its system message.

IMPLEMENTATION GUIDE:
1. Review and update the docstrings and comments
2. Implement the _execute_processing method for your agent's specific logic
3. Add any additional methods needed for your agent's functionality
4. Update the prompt_id to match the one in your configuration
5. Consider if your agent needs additional tools or special capabilities
"""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.agent_system.core.base_agent import BaseAgent
from src.agent_system.core.message import Message, MessageRole
from src.agent_system.core.metadata import BaseMetadata, MetadataKeys, ResultMetadata
from src.registries.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)

class GraphragCodeGeneralAgent(BaseAgent):  
    """
    A specialized agent for graphrag code general functionality
    
    This class implements the Graphrag Code General Agent functionality by:
    1. Using a specific prompt from the prompt registry
    2. Processing user messages with appropriate LLM calls
    3. [Add any additional core functionality here]
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], **kwargs):
        """
        Initialize the GraphragCodeGeneralAgent.
        
        Args:
            agent_id: The unique identifier for this agent
            config: The agent configuration dictionary
            **kwargs: Additional keyword arguments
        """
        # Make sure agent_id is in the config
        if "agent_id" not in config:
            config["agent_id"] = agent_id
            
        # Make sure model_config is set with proper model_type
        if "model_config" not in config:
            config["model_config"] = {
                "model_type": "instruct",  # Use appropriate model type
                "max_tokens": 1024,                # Set appropriate token limit
                "temperature": 0.7                 # Set appropriate temperature
            }
        elif "model_type" not in config["model_config"]:
            config["model_config"]["model_type"] = "instruct"
            
        super().__init__(config, **kwargs)
        
        # Get a reference to the prompt registry
        self.prompt_registry = PromptRegistry()
        
        # Extract prompt_id from config or use default
        self.prompt_id = config.get("prompt_id", "router.task_classifier")
        
        logger.info(f"Initialized GraphragCodeGeneralAgent with prompt_id: {self.prompt_id}")
    
    async def _stream_thinking_hook(self, stream_callback: Any):
        """Optional hook called by BaseAgent.process to stream initial thoughts."""
        await self.stream_thinking(
            thinking=f"Using prompt: {self.prompt_id}\nFormulating response...",
            stream_callback=stream_callback
        )
        
    async def _execute_processing(
        self, 
        message: Message, 
        session_id: Optional[str] = None
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Core processing logic for the GraphragCodeGeneralAgent.
        Handles prompt retrieval, LLM call, and response generation.
        Error handling and standard status updates are managed by BaseAgent.process.
        
        Args:
            message: The input message to process
            session_id: Optional session identifier
            
        Returns:
            Tuple of (response_message, next_agent_id)
        """
        try:
            # Get the prompt from the registry
            system_prompt = self.prompt_registry.get_prompt(
                prompt_id=self.prompt_id,
                message=message.content
            )
                
            # Optional 'Thinking' update is handled via _stream_thinking_hook
            
            # Prepare messages for the LLM
            messages = [
                Message(role=MessageRole.SYSTEM, content=system_prompt),
                message  # The user's message
            ]
                
            # Call the LLM (error handling is in BaseAgent.process)
            # NOTE for AI (if we are developing with an AI assistant): This is the ONLY way to call an LLM in this application. Do not create a workaround or alternative way to call an LLM. If this method seems insufficient, notify the developer you are working with, but do not under any circumstances modify the way LLMs are called in this application. Doing that will break the workflows and APIs and cause compliance violations.
            response_text, _ = await self.call_llm(messages)
            
            # Extract the classification from the response
            classification = self._extract_classification(response_text)
            logger.info(f"Classified query as: {classification}")
            
            # Create standardized metadata for the response
            result_metadata = ResultMetadata.create_result_metadata(
                results=classification,
                prompt_id=self.prompt_id
            )
            
            # Add route information to metadata
            BaseMetadata.update(result_metadata, 
                **{
                    MetadataKeys.ROUTE_CATEGORY.value: classification,
                    MetadataKeys.IS_CLASSIFICATION_RESULT.value: True,
                    MetadataKeys.CLASSIFICATION_CONFIDENCE.value: 0.9  # Could be dynamic in future versions
                }
            )
                
            # Create and return the response message
            response_message = Message(
                role=MessageRole.ASSISTANT,
                content=response_text,
                metadata=result_metadata
            )
                
            # If your agent should chain to another agent, return its ID as the second element
            # For example: return response_message, "next_agent_id"
            return response_message, None
            
        except Exception as e:
            logger.error(f"Error in routing classification: {str(e)}")
            
            # Create standardized error metadata
            error_metadata = ResultMetadata.create_result_metadata(
                error=str(e),
                **{MetadataKeys.PROMPT_ID.value: self.prompt_id}
            )
            
            # Create error response
            error_message = Message(
                role=MessageRole.ASSISTANT,
                content=f"Error classifying request: {str(e)}",
                metadata=error_metadata
            )
            
            return error_message, None
    
    def _extract_classification(self, response: str) -> str:
        """
        Extract the classification category from the LLM response.
        
        Args:
            response: The LLM response text
            
        Returns:
            The extracted classification category or "UNKNOWN" if not found
        """
        try:
            # Try to parse the response as JSON
            response_data = json.loads(response)
            
            # Extract the category
            if isinstance(response_data, dict) and "category" in response_data:
                return response_data["category"]
                
        except json.JSONDecodeError:
            # If not valid JSON, try to extract with regex
            import re
            match = re.search(r'"category"\s*:\s*"([^"]+)"', response)
            if match:
                return match.group(1)
        
        # If we couldn't extract a valid category, return unknown
        logger.warning(f"Could not extract classification from response: {response}")
        return "UNKNOWN"
