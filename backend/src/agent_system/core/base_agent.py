"""
Base agent class for all agent implementations.
"""
import json
import logging
import time
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from src.utils.model_caller import (
    call_granite_instruct, 
    call_granite_guardian, 
    convert_messages_to_dict
)
from src.agent_system.core.message import Message, MessageRole, UserMessage

logger = logging.getLogger(__name__)


class AgentAction(BaseModel):
    """Agent action model for logging and tracking agent activities."""
    agent_id: str
    action: str
    input: str
    result: str
    confidence: float
    processing_time_ms: int
    next_agent: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """
    Base agent class that all specialized agents should inherit from.
    
    This class provides common functionality for model inference, logging, 
    and status updates. Specialized agents implement the process() method.
    """
    def __init__(self, config: Dict[str, Any], workflow_manager=None):
        """
        Initialize the agent using configuration loaded from the registry.

        Args:
            config: Agent configuration dictionary from agent_registry.json
            workflow_manager: Optional reference to the parent WorkflowManager.
        """
        if not config:
            raise ValueError("Agent configuration cannot be empty.")

        # Extract core attributes using the 'config' dictionary
        self.agent_id = config.get("agent_id")
        self.name = config.get("name", f"Unnamed Agent ({self.agent_id})") 
        self.description = config.get("description", "No description provided.") 
        self.system_prompt = config.get("system_prompt", "") 
        self.agent_type = config.get("agent_type")
        self.tools = config.get("tools", [])
        self.shields = config.get("shields", [])
        self.enabled = config.get("enabled", True)

        # Store the reference to the workflow manager
        self.workflow_manager = workflow_manager

        # Store the specific model configuration for this agent
        self.model_config = config.get("model_config")
        if not self.model_config:
            raise ValueError(f"Missing 'model_config' in configuration for agent {self.agent_id}")

        # Ensure model_config has required fields
        if not self.model_config:
            logger.error(f"Config received by BaseAgent __init__ for agent {self.agent_id}: {config}") 
            raise ValueError(f"Missing 'model_config' for agent {self.agent_id}")
            
        # Validate model_config has required fields based on our new approach
        if 'model_type' not in self.model_config:
            logger.warning(f"No model_type specified in model_config for agent {self.agent_id}, defaulting to 'instruct'")
            self.model_config['model_type'] = 'instruct'
            
        self.model_type = self.model_config['model_type']

        # Stream callback reference (used for thinking)
        self.current_stream_callback = None
        
        logger.info(f"Initialized agent '{self.name}' ({self.agent_id}) of type '{self.agent_type}' using model type '{self.model_type}'")

    def _log_action(
        self, 
        action: str, 
        input_text: str, 
        result: str, 
        confidence: float, 
        processing_time_ms: int, 
        next_agent: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> AgentAction:
        """
        Log an agent action for tracking and debugging.
        
        Args:
            action: The type of action performed
            input_text: The input text processed
            result: The result of processing
            confidence: Confidence score (0-1)
            processing_time_ms: Processing time in milliseconds
            next_agent: ID of the next agent to process (if any)
            metadata: Additional metadata about the action
            
        Returns:
            The created AgentAction object
        """
        if metadata is None:
            metadata = {}
        
        # Add timestamp and version information
        metadata["timestamp"] = datetime.now().isoformat()
        
        action_log = AgentAction(
            agent_id=self.agent_id,
            action=action,
            input=input_text,
            result=result,
            confidence=confidence,
            processing_time_ms=processing_time_ms,
            next_agent=next_agent,
            metadata=metadata
        )
        
        logger.info(f"Agent action: {action_log.model_dump()}")
        return action_log

    async def call_llm(
        self, 
        messages: List[Message], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[str, int]:
        """
        Call the LLM with the given messages.

        Args:
            messages: List of Message objects to send to the LLM
            tools: Optional list of tools to make available to the LLM

        Returns:
            Tuple of (response_text, processing_time_ms)
        """
        try:
            # Get the model type from the agent's config
            model_type = self.model_config.get('model_type', 'instruct')
            if not model_type:
                raise ValueError(f"Agent {self.agent_id} does not have a model_type configured.")
            
            # Convert Message objects to dictionary format
            message_dicts = convert_messages_to_dict(messages)
            
            # Get max tokens and temperature from config or use defaults
            max_tokens = self.model_config.get('max_tokens', 1024)
            temperature = self.model_config.get('temperature', 0.7)
            
            # Call the appropriate model based on the model type
            if model_type == 'guardian':
                # Guardian model for safety checks
                logger.debug(f"Calling Granite Guardian with {len(messages)} messages")
                model_response = await call_granite_guardian(
                    messages=message_dicts,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            else:
                # Default to instruct model
                logger.debug(f"Calling Granite Instruct with {len(messages)} messages")
                model_response = await call_granite_instruct(
                    messages=message_dicts,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    tools=tools
                )
            
            return model_response.content, model_response.processing_time_ms

        except Exception as e:
            logger.exception(f"Error calling LLM for agent {self.agent_id}: {e}")
            return f"Error during LLM call for {self.agent_id}: {str(e)}", 0

    async def send_status_update(
        self, 
        stream_callback: Any, 
        status: str, 
        message: str = "", 
        data: Dict[str, Any] = None
    ):
        """
        Send a status update through the stream callback if available.
        
        Args:
            stream_callback: The callback function to use
            status: The status string (e.g., "starting", "thinking", "completed")
            message: An optional detailed message about the status
            data: Optional additional data to include
        """
        if not stream_callback:
            return
            
        # Prepare the data payload
        update_data = {
            "status": status,
            "message": message
        }
        
        # Include additional data if provided
        if data:
            update_data.update(data)
            
        # Send the update
        try:
            await stream_callback(
                agent_id=self.agent_id,
                message_type="agent_update",
                content=status,
                data=update_data
            )
        except Exception as e:
            logger.error(f"Error sending status update: {str(e)}")

    @abstractmethod
    async def _execute_processing(
        self,
        message: Message,
        session_id: Optional[str] = None
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Core processing logic for the agent. Must be implemented by subclasses.

        Args:
            message: The input message to process.
            session_id: Optional session identifier.

        Returns:
            Tuple of (response_message, next_agent_id).
            The response message can be None if processing fails internally but is handled.
        """
        pass

    async def process(
        self,
        message: Message,
        session_id: Optional[str] = None,
        stream_callback: Optional[Any] = None
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Public method to process an incoming message. Handles status updates,
        error handling, and logging around the core agent logic.

        Args:
            message: The input message to process.
            session_id: Optional session identifier.
            stream_callback: Optional callback for streaming status updates.

        Returns:
            Tuple of (response_message, next_agent_id).
        """
        logger.info(f"Agent '{self.agent_id}' starting processing for message: {message.content[:50]}...")
        start_time = time.time()

        # Store the stream callback for use in thinking steps and evaluation
        self.current_stream_callback = stream_callback

        # Send initial status update
        if stream_callback:
            await self.send_status_update(
                stream_callback=stream_callback,
                status="processing",
                message="Processing your message..."
            )

        try:
            # --- Optional Thinking Hook --- 
            # If subclasses want to stream specific 'thinking' messages early,
            # they could implement a method like _stream_initial_thoughts(stream_callback)
            # await self._stream_initial_thoughts(stream_callback) 
            # Example (SimpleTestAgent might move its 'Using prompt...' here)
            if hasattr(self, '_stream_thinking_hook') and stream_callback:
                 await self._stream_thinking_hook(stream_callback)
            # -----------------------------

            # Execute the core agent logic
            response_message, next_agent = await self._execute_processing(
                message=message,
                session_id=session_id
                # Note: stream_callback is NOT typically passed here unless 
                # the core logic needs finer-grained streaming control 
                # beyond the standard status updates handled here.
            )
            
            total_time_ms = int((time.time() - start_time) * 1000)

            # Log the successful action
            if response_message:
                 self._log_action(
                    action="process_message_success",
                    input_text=message.content[:100],
                    result=response_message.content[:100],
                    confidence=getattr(response_message, 'confidence', 1.0), # Attempt to get confidence if set
                    processing_time_ms=total_time_ms,
                    next_agent=next_agent,
                    metadata=getattr(response_message, 'metadata', {}) # Attempt to get metadata if set
                )
            else:
                 # Log even if response is None but no exception occurred
                 self._log_action(
                    action="process_message_no_response",
                    input_text=message.content[:100],
                    result="No response message generated",
                    confidence=0.0,
                    processing_time_ms=total_time_ms,
                    next_agent=next_agent,
                    metadata={}
                 )

            # Send completion status update
            if stream_callback:
                await self.send_status_update(
                    stream_callback=stream_callback,
                    status="completed",
                    message="Processing completed"
                )
            
            # Clean up
            self.current_stream_callback = None
            
            return response_message, next_agent

        except Exception as e:
            total_time_ms = int((time.time() - start_time) * 1000)
            error_message_content = f"Agent {self.agent_id} encountered an error: {str(e)}"
            logger.exception(f"Error during agent processing: {error_message_content}") # Log with stack trace

            # Log the error action
            self._log_action(
                action="process_message_error",
                input_text=message.content[:100],
                result=error_message_content[:100],
                confidence=0.0,
                processing_time_ms=total_time_ms,
                metadata={"error_type": type(e).__name__}
            )

            # Send error status update
            if stream_callback:
                await self.send_status_update(
                    stream_callback=stream_callback,
                    status="error",
                    message=f"Error: {str(e)}"
                )

            # Clean up
            self.current_stream_callback = None
            
            # Return a standardized error message
            error_response = Message(
                role=MessageRole.ASSISTANT,
                content=f"I'm sorry, an internal error occurred while processing your request."
            )
            return error_response, None

    async def stream_thinking(
        self, 
        thinking: str, 
        stream_callback: Optional[Any] = None
    ):
        """
        Stream thinking steps during processing.
        
        Args:
            thinking: The thinking step text
            stream_callback: Optional callback function to handle streaming
        """
        if stream_callback and callable(stream_callback):
            if asyncio.iscoroutinefunction(stream_callback):
                await stream_callback(
                    agent_id=self.agent_id,
                    message_type="logs",
                    content="thinking",
                    data=thinking
                )
            else:
                stream_callback(
                    agent_id=self.agent_id,
                    message_type="logs",
                    content="thinking", 
                    data=thinking
                )