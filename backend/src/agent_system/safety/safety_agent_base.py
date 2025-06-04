"""
Base class for all safety agents.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from src.agent_system.core.base_agent import BaseAgent
from src.agent_system.core.message import Message, MessageRole
from src.agent_system.core.metadata import BaseMetadata, MetadataKeys

logger = logging.getLogger(__name__)


class SafetyAgentBase(BaseAgent):
    """
    Base class for all safety agents.
    
    Safety agents implement the "Compliance Sandwich" pattern, providing
    protection at the beginning and end of the agent workflow.
    """
    
    def __init__(self, config: Dict[str, Any], workflow_manager=None):
        """
        Initialize the safety agent.
        
        Args:
            config: Agent configuration dictionary
            workflow_manager: Optional reference to the parent WorkflowManager
        """
        super().__init__(config, workflow_manager)
        
        # Load additional safety-specific configuration
        self.block_patterns = config.get("block_patterns", [])
        self.allow_patterns = config.get("allow_patterns", [])
        self.safety_threshold = config.get("safety_threshold", 0.8)
        self.safety_mode = config.get("safety_mode", "strict")
    
    async def _stream_thinking_hook(self, stream_callback: Any):
        """
        Optional hook called by BaseAgent.process to stream initial thoughts.
        """
        await self.stream_thinking(
            thinking=f"Performing {self.name} safety check...",
            stream_callback=stream_callback
        )
        
    async def _execute_processing(
        self, 
        message: Message, 
        session_id: Optional[str] = None
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Core processing logic for safety agents.
        
        Args:
            message: The input message to check
            session_id: Optional session identifier
            
        Returns:
            Tuple of (response_message, next_agent_id)
            If safe, next_agent_id will point to the next agent in workflow
            If blocked, next_agent_id will be None
        """
        # Perform safety evaluation
        is_safe, confidence, block_reason = await self._evaluate_safety(message.content)
        
        # Create safety metadata using standard methods
        safety_metadata = BaseMetadata.create(
            safety_checked=True,
            safety_agent_id=self.agent_id,
            safety_check_passed=is_safe,
            safety_confidence=confidence
        )
        
        if not is_safe:
            # Update metadata with block information
            BaseMetadata.update(safety_metadata, 
                blocked=True,
                block_reason=block_reason,
                safety_violation=True
            )
            
            # Create blocking response
            block_message = f"I'm sorry, but I cannot process this request as it appears to {block_reason}."
            response = Message(
                role=MessageRole.ASSISTANT,
                content=block_message,
                metadata=safety_metadata
            )
            
            logger.warning(f"Safety agent {self.agent_id} blocked message: {block_reason}")
            return response, None
        
        # Message is safe, return with metadata and continue to next agent
        logger.info(f"Safety agent {self.agent_id} passed message with confidence {confidence}")
        response = Message(
            role=MessageRole.ASSISTANT,
            content="Content passed safety check",
            metadata=safety_metadata
        )
        
        # Return the appropriate next agent ID
        return response, "next"  # "next" is a special token that means "continue to next agent"
        
    async def _evaluate_safety(self, content: str) -> Tuple[bool, float, str]:
        """
        Evaluate the safety of a message.
        
        Args:
            content: The message content to evaluate
            
        Returns:
            Tuple of (is_safe, confidence, block_reason)
            
        Note:
            This method should be implemented by subclasses.
        """
        # This is a placeholder that should be overridden by subclasses
        raise NotImplementedError("Subclasses must implement _evaluate_safety()")