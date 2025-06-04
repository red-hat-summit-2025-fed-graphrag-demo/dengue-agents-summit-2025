"""
Policy check safety agent.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from src.agent_system.core.message import Message, MessageRole
from src.agent_system.safety.safety_agent_base import SafetyAgentBase
from src.registries.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)


class PolicyCheckAgent(SafetyAgentBase):
    """
    Safety agent to enforce policy guidelines and content moderation.
    
    This agent ensures that user requests comply with usage policies,
    do not contain harmful content, and adhere to ethical guidelines.
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], workflow_manager=None, **kwargs):
        """
        Initialize the policy check agent.
        
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
        self.prompt_id = config.get("prompt_id", "safety.policy_check")
        
        logger.info(f"Initialized PolicyCheckAgent with prompt_id: {self.prompt_id}")
    
    async def _stream_thinking_hook(self, stream_callback: Any):
        """Optional hook called by BaseAgent.process to stream initial thoughts."""
        await self.stream_thinking(
            thinking=f"Running policy compliance check using prompt: {self.prompt_id}...",
            stream_callback=stream_callback
        )
    
    async def _evaluate_safety(self, content: str) -> Tuple[bool, float, str]:
        """
        Evaluate message for potential policy violations.
        
        Args:
            content: The message content to evaluate
            
        Returns:
            Tuple of (is_safe, confidence, block_reason)
        """
        # Stream thinking about evaluation
        if self.current_stream_callback:
            await self.stream_thinking(
                thinking="Analyzing message for potential policy violations...",
                stream_callback=self.current_stream_callback
            )
        
        # Get the prompt from the registry
        system_prompt = self.prompt_registry.get_prompt(
            prompt_id=self.prompt_id,
            message=content
        )
        
        # Prepare messages for the policy check
        messages = [
            Message(role=MessageRole.SYSTEM, content=system_prompt),
            Message(role=MessageRole.USER, content=content)
        ]
        
        # Call LLM to check policy compliance
        result, _ = await self.call_llm(messages)
        
        # Stream the result of analysis
        if self.current_stream_callback:
            await self.stream_thinking(
                thinking=f"Policy analysis complete: {result}",
                stream_callback=self.current_stream_callback
            )
        
        # Determine if policy violation was detected
        is_policy_violation = "POLICY_VIOLATION" in result.upper()
        
        if is_policy_violation:
            # Extract explanation if a policy violation was detected
            explanation = result.replace("POLICY_VIOLATION", "").strip()
            if not explanation:
                explanation = "violate our content policies"
                
            logger.warning(f"Policy violation detected: {explanation}")
            
            # Stream the decision
            if self.current_stream_callback:
                await self.stream_thinking(
                    thinking=f"⚠️ Policy violation detected: {explanation}",
                    stream_callback=self.current_stream_callback
                )
            
            return False, 0.9, explanation
        else:
            # Stream the decision
            if self.current_stream_callback:
                await self.stream_thinking(
                    thinking="✅ Content complies with policies",
                    stream_callback=self.current_stream_callback
                )
            
            return True, 0.95, ""