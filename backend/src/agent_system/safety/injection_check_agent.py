"""
Injection check safety agent.
"""
import re
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from src.agent_system.safety.safety_agent_base import SafetyAgentBase
from src.agent_system.core.message import Message, MessageRole
from src.registries.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)


class InjectionCheckAgent(SafetyAgentBase):
    """
    Safety agent to protect against prompt injection and other malicious input.
    
    This agent uses pattern matching and LLM-based detection to identify
    attempts to bypass system safeguards, obtain unauthorized outputs,
    or otherwise manipulate the system.
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], workflow_manager=None, **kwargs):
        """
        Initialize the injection check agent.
        
        Args:
            agent_id: The unique identifier for this agent
            config: Agent configuration dictionary
            workflow_manager: Optional reference to the parent WorkflowManager
            **kwargs: Additional keyword arguments
        """
        # Make sure agent_id is in the config
        if "agent_id" not in config:
            config["agent_id"] = agent_id
            
        super().__init__(config, workflow_manager=workflow_manager, **kwargs)
        
        # Get a reference to the prompt registry
        self.prompt_registry = PromptRegistry()
        
        # Set the prompt ID (can be overridden in config)
        self.prompt_id = config.get("prompt_id", "safety.injection_check")
        
        logger.info(f"Initialized InjectionCheckAgent with prompt_id: {self.prompt_id}")
    
    async def _stream_thinking_hook(self, stream_callback: Any):
        """Optional hook called by BaseAgent.process to stream initial thoughts."""
        await self.stream_thinking(
            thinking=f"Running injection check using prompt: {self.prompt_id}...",
            stream_callback=stream_callback
        )
    
    async def _evaluate_safety(self, content: str) -> Tuple[bool, float, str]:
        """
        Evaluate message for potential prompt injection attempts.
        
        Args:
            content: The message content to evaluate
            
        Returns:
            Tuple of (is_safe, confidence, block_reason)
        """
        # Stream thinking about evaluation
        if self.current_stream_callback:
            await self.stream_thinking(
                thinking="Analyzing message for potential prompt injection patterns...",
                stream_callback=self.current_stream_callback
            )
        
        # Get the prompt from the registry
        system_prompt = self.prompt_registry.get_prompt(
            prompt_id=self.prompt_id,
            message=content
        )
        
        # Prepare messages for the injection check
        messages = [
            Message(role=MessageRole.SYSTEM, content=system_prompt),
            Message(role=MessageRole.USER, content=content)
        ]
        
        # Call LLM to check for injection
        result, _ = await self.call_llm(messages)
        
        # Stream the result of analysis
        if self.current_stream_callback:
            await self.stream_thinking(
                thinking=f"Analysis complete: {result}",
                stream_callback=self.current_stream_callback
            )
        
        # Determine if injection attempt was detected
        is_injection_detected = "INJECTION_DETECTED" in result.upper()
        
        if is_injection_detected:
            # Extract explanation if an injection was detected
            explanation = result.replace("INJECTION_DETECTED", "").strip()
            if not explanation:
                explanation = "attempt to manipulate the system"
                
            logger.warning(f"Injection attempt detected: {explanation}")
            
            # Stream the decision
            if self.current_stream_callback:
                await self.stream_thinking(
                    thinking=f"⚠️ Injection detected: {explanation}",
                    stream_callback=self.current_stream_callback
                )
            
            return False, 0.9, explanation
        else:
            # Stream the decision
            if self.current_stream_callback:
                await self.stream_thinking(
                    thinking="✅ No injection patterns detected",
                    stream_callback=self.current_stream_callback
                )
            
            return True, 0.95, ""