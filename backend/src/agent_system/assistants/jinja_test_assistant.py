"""
Jinja Test Assistant

A specialized agent for jinja test functionality
Uses a prompt from the prompt registry for its system message.

IMPLEMENTATION GUIDE:
1. Review and update the docstrings and comments
2. Implement the _execute_processing method for your agent's specific logic
3. Add any additional methods needed for your agent's functionality
4. Update the prompt_id to match the one in your configuration
5. Consider if your agent needs additional tools or special capabilities
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.agent_system.core.base_agent import BaseAgent
from src.agent_system.core.message import Message, MessageRole
from src.registries.base_registry import BaseRegistry
from src.registries.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)

class JinjaTestAssistant(BaseAgent):
    """
    A specialized agent for jinja test functionality
    
    This class implements the Jinja Test Assistant functionality by:
    1. Using a specific prompt from the prompt registry
    2. Processing user messages with appropriate LLM calls
    3. [Add any additional core functionality here]
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], registry_factory=None, **kwargs):
        """
        Initialize the JinjaTestAssistant.
        
        Args:
            agent_id: The unique identifier for this agent
            config: The agent configuration dictionary
            registry_factory: Optional factory providing access to registries
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
        
        # Get registry references (either from factory or create directly)
        self.registry_factory = registry_factory
        if registry_factory:
            self.prompt_registry = registry_factory.get_prompt_registry()
        else:
            # Create registries directly when no factory is provided
            self.prompt_registry = PromptRegistry()
        
        # Extract prompt_id from config or use default
        self.prompt_id = config.get("prompt_id", "assistants.test")
        
        logger.info(f"Initialized JinjaTestAssistant with prompt_id: {self.prompt_id}")
    
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
    ) -> Tuple[Message, Optional[str]]:
        """
        Core processing logic for the JinjaTestAssistant.
        Handles prompt retrieval, LLM call, and response generation.
        Error handling and standard status updates are managed by BaseAgent.process.
        
        Args:
            message: The input message to process
            session_id: Optional session identifier
            
        Returns:
            Tuple of (response_message, next_agent_id)
        """
        logger.info(f"Processing message in {self.__class__.__name__}")
        
        # Get the system prompt from registry - retrieve by ID from config
        prompt_registry = None
        if self.registry_factory:
            prompt_registry = self.registry_factory.get_prompt_registry()
        else:
            # This should be updated to use the registry factory once available
            from src.registries.prompt_registry import PromptRegistry
            prompt_registry = PromptRegistry()
            
        prompt_id = self.config.get("prompts", {}).get("system", {}).get("id", "assistants.test")
        system_prompt = prompt_registry.get_prompt(prompt_id)
        
        if not system_prompt:
            error_msg = f"Could not find system prompt with ID: {prompt_id}"
            logger.error(error_msg)
            return Message(role=MessageRole.ASSISTANT, content=f"Error: {error_msg}"), None
        
        # Prepare messages for LLM call
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message.content}
        ]
        
        # Call LLM
        llm_response = await self.call_llm(messages=messages, session_id=session_id)
        response_content = llm_response.get("content", "No response generated")
        
        # Create response message
        response_message = Message(
            role=MessageRole.ASSISTANT,
            content=response_content,
            # Copy all metadata from the original message
            metadata=message.metadata.copy() if message.metadata else {}
        )
        
        # Set next agent to call, if any
        next_agent_id = None  # Change this if your agent needs to call a specific next agent
        
        return response_message, next_agent_id
