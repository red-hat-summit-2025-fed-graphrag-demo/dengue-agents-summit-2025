"""
Simple Test Agent

A minimal agent implementation to demonstrate the agent system architecture.
Uses a prompt from the prompt registry for its system message.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.agent_system.core.base_agent import BaseAgent
from src.agent_system.core.message import Message, MessageRole
from src.agent_system.core.metadata import BaseMetadata, MetadataKeys, ResultMetadata
from src.registries.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)

class SimpleTestAgent(BaseAgent):
    """
    A simple test agent that demonstrates the basic agent architecture.
    Uses a prompt from the registry for its system message.
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], **kwargs):
        """
        Initialize the SimpleTestAgent.
        
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
                "model_type": "instruct",  # Use Granite Instruct by default
                "max_tokens": 1024,
                "temperature": 0.7
            }
        elif "model_type" not in config["model_config"]:
            config["model_config"]["model_type"] = "instruct"
            
        super().__init__(config, **kwargs)
        
        # Get a reference to the prompt registry
        self.prompt_registry = PromptRegistry()
        
        # Extract prompt_id from config or use default
        self.prompt_id = config.get("prompt_id", "test.simple_test")
        
        logger.info(f"Initialized SimpleTestAgent with prompt_id: {self.prompt_id}")
    
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
        Core processing logic for the SimpleTestAgent.
        Handles prompt retrieval, LLM call, and response generation.
        Error handling and standard status updates are managed by BaseAgent.process.
        
        Args:
            message: The input message to process
            session_id: Optional session identifier
            
        Returns:
            Tuple of (response_message, next_agent_id)
        """
        # Logging is handled by the BaseAgent wrapper
        # Initial status update ("processing") is handled by BaseAgent
        
        # Get the prompt from the registry
        system_prompt = self.prompt_registry.get_prompt(
            prompt_id=self.prompt_id,
            message=message.content
        )
            
        # Optional 'Thinking' update is now handled via _stream_thinking_hook
        
        # Prepare messages for the LLM
        messages = [
            Message(role=MessageRole.SYSTEM, content=system_prompt),
            message  # The user's message
        ]
            
        # Call the LLM (error handling is in BaseAgent.process)
        response_text, _ = await self.call_llm(messages)
        # Timing and detailed logging are handled by BaseAgent.process
            
        # Final status updates ("completed" or "error") are handled by BaseAgent
            
        # Create standardized metadata for the response
        result_metadata = ResultMetadata.create_result_metadata(
            **{MetadataKeys.PROMPT_ID.value: self.prompt_id}
        )
            
        # Create and return the response message
        response_message = Message(
            role=MessageRole.ASSISTANT,
            content=response_text,
            metadata=result_metadata
        )
            
        # This agent doesn't chain
        return response_message, None