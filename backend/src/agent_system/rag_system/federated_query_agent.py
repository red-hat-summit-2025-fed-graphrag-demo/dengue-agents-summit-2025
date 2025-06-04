"""
Federated Query RAG Agent

A specialized agent for federated query functionality
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
from src.registries.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)

class FederatedQueryAgent(BaseAgent):  
    """
    A specialized agent for federated query functionality
    
    This class implements the Federated Query RAG Agent functionality by:
    1. Using a specific prompt from the prompt registry
    2. Processing user messages with appropriate LLM calls
    3. [Add any additional core functionality here]
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], **kwargs):
        """
        Initialize the FederatedQueryAgent.
        
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
        self.prompt_id = config.get("prompt_id", "rag.get_country_and_dates_from_query")
        
        logger.info(f"Initialized FederatedQueryAgent with prompt_id: {self.prompt_id}")
    
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
        Core processing logic for the FederatedQueryAgent.
        Handles prompt retrieval, LLM call, and response generation.
        Error handling and standard status updates are managed by BaseAgent.process.
        
        Args:
            message: The input message to process
            session_id: Optional session identifier
            
        Returns:
            Tuple of (response_message, next_agent_id)
        """
        # TODO: Implement your agent-specific processing logic here
        
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
        
        # TODO: Add any post-processing of the response here
            
        # Create and return the response message
        response_message = Message(
            role=MessageRole.ASSISTANT,
            content=response_text,
            metadata={"prompt_id": self.prompt_id}  # Attach metadata for logging
        )
            
        # If your agent should chain to another agent, return its ID as the second element
        # For example: return response_message, "next_agent_id"
        return response_message, None
