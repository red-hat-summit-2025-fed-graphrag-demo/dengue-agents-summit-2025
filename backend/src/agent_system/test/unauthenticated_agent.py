"""
Unauthenticated Test Agent

A simple agent that uses a tool that doesn't require authentication.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.agent_system.core.base_agent import BaseAgent
from src.agent_system.core.message import Message, MessageRole
from src.registries.prompt_registry import PromptRegistry
from src.registries.registry_factory import RegistryFactory

logger = logging.getLogger(__name__)

class UnauthenticatedAgent(BaseAgent):
    """
    A simple agent that demonstrates using a tool without authentication.
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], **kwargs):
        """
        Initialize the UnauthenticatedAgent.
        
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
                "model_type": "instruct",
                "max_tokens": 500,
                "temperature": 0.7
            }
        elif "model_type" not in config["model_config"]:
            config["model_config"]["model_type"] = "instruct"
            
        super().__init__(config, **kwargs)
        
        # Get a reference to the prompt registry
        self.prompt_registry = PromptRegistry()
        
        # Define the tool ID we'll use
        self.hello_tool_id = "simple_hello_tool"
        
        # Extract prompt_id from config or use default
        self.prompt_id = config.get("prompt_id", "test.hello_agent")
        
        # Ensure tool registry is initialized
        self.tool_registry = RegistryFactory.get_tool_registry()
        
    async def _execute_processing(
        self, 
        message: Message, 
        session_id: Optional[str] = None
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Core processing logic for the UnauthenticatedAgent.
        
        Args:
            message: The input message to process
            session_id: Optional session identifier
            
        Returns:
            Tuple of (response_message, next_agent_id)
        """
        # Use a hardcoded prompt for testing
        system_prompt = "You are a helpful assistant for testing the authentication system. \n\nIf you receive a greeting from a tool, respond with a friendly message that includes:\n1. The greeting that was received\n2. Whether the tool was authenticated or not\n3. Any additional message provided by the tool\n\nKeep your response brief, friendly, and informative."
            
        # Get name from the message or use default
        username = message.metadata.get("username", "Test User")
        
        # Use the simple hello tool (doesn't require auth)
        try:
            logger.info(f"Using simple hello tool for user: {username}")
            hello_result = await self.use_tool(
                tool_id=self.hello_tool_id,
                method_name="execute",
                name=username
            )
            
            # Log the result
            logger.info(f"Received greeting from simple tool: {hello_result}")
            
            # Prepare context for LLM
            context = {
                "greeting": hello_result.get("greeting", "Hello!"),
                "message": hello_result.get("message", "No additional message"),
                "authenticated": hello_result.get("authenticated", False),
            }
            
            # Prepare messages for the LLM
            messages = [
                Message(role=MessageRole.SYSTEM, content=system_prompt),
                Message(role=MessageRole.USER, content=f"Process this greeting: {message.content}"),
                Message(role=MessageRole.USER, content=f"Tool response: {context}")
            ]
            
            # Call the LLM - returns (content, processing_time_ms)
            logger.info(f"Calling LLM with Message objects")
            llm_response, processing_time = await self.call_llm(messages)
            logger.info(f"LLM response: '{llm_response}', processing time: {processing_time}ms")
            
            # Create the response message
            response_content = llm_response
            response = Message(
                role=MessageRole.ASSISTANT,
                content=response_content,
                metadata=message.metadata.copy()
            )
            
            # Set the next agent ID
            next_agent_id = None
            
            return response, next_agent_id
            
        except Exception as e:
            logger.error(f"Error in UnauthenticatedAgent: {str(e)}", exc_info=True)
            error_message = Message(
                role=MessageRole.ASSISTANT,
                content=f"I encountered an error: {str(e)}",
                metadata=message.metadata.copy()
            )
            return error_message, None
