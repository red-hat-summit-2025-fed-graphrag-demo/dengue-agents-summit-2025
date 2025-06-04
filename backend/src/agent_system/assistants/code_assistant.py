"""
Code Assistant

An agent implementation specialized for programming and technical assistance.
Uses the code_assistant prompt from the prompt registry for its system message.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.agent_system.core.base_agent import BaseAgent
from src.agent_system.core.message import Message, MessageRole
from src.agent_system.core.metadata import BaseMetadata, MetadataKeys, ResultMetadata
from src.registries.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)

class CodeAssistant(BaseAgent):
    """
    A specialized agent for providing programming and technical assistance.
    Uses the code_assistant prompt from the registry for its system message.
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], **kwargs):
        """
        Initialize the CodeAssistant.
        
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
                "max_tokens": 2048,        # Larger context for code explanations
                "temperature": 0.2         # Lower temperature for more precise responses
            }
        elif "model_type" not in config["model_config"]:
            config["model_config"]["model_type"] = "instruct"
            
        super().__init__(config, **kwargs)
        
        # Get a reference to the prompt registry
        self.prompt_registry = PromptRegistry()
        
        # Extract prompt_id from config or use default code assistant prompt
        self.prompt_id = config.get("prompt_id", "assistants.code_assistant")
        
        logger.info(f"Initialized CodeAssistant with prompt_id: {self.prompt_id}")
    
    async def _stream_thinking_hook(self, stream_callback: Any):
        """Optional hook called by BaseAgent.process to stream initial thoughts."""
        await self.stream_thinking(
            thinking=f"Using programming assistance prompt: {self.prompt_id}\nAnalyzing code question and formulating response...",
            stream_callback=stream_callback
        )
        
    async def _execute_processing(
        self, 
        message: Message, 
        session_id: Optional[str] = None
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Core processing logic for the CodeAssistant.
        Handles prompt retrieval, LLM call, and response generation.
        Error handling and standard status updates are managed by BaseAgent.process.
        
        Args:
            message: The input message to process
            session_id: Optional session identifier
            
        Returns:
            Tuple of (response_message, next_agent_id)
        """
        # Get the prompt from the registry
        system_prompt = self.prompt_registry.get_prompt(
            prompt_id=self.prompt_id,
            message=message.content
        )
            
        # Prepare messages for the LLM
        messages = [
            Message(role=MessageRole.SYSTEM, content=system_prompt),
            message  # The user's message
        ]
            
        # Call the LLM (error handling is in BaseAgent.process)
        response_text, _ = await self.call_llm(messages)
            
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
