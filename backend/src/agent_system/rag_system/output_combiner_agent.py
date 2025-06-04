"""
Simplified Output Combiner Agent

A focused agent that combines outputs from visualization and response generator agents
without unnecessary complexity.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.agent_system.core.base_agent import BaseAgent
from src.agent_system.core.message import Message, MessageRole
from src.agent_system.core.metadata import BaseMetadata, MetadataKeys, ResultMetadata

logger = logging.getLogger(__name__)

class OutputCombinerAgent(BaseAgent):
    """
    A simplified agent that reliably combines visualization and response generator outputs.
    
    This combiner prioritizes ensuring a complete response reaches the user by:
    1. Clearly extracting the response generator's output
    2. Validating that a legitimate response is being returned
    3. Falling back to predefined response if extraction fails
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], **kwargs):
        """Initialize the OutputCombinerAgent."""
        # Ensure agent_id is in the config
        if "agent_id" not in config:
            config["agent_id"] = agent_id
            
        # Minimal config
        if "model_config" not in config:
            config["model_config"] = {
                "model_type": "instruct",
                "max_tokens": 256,
                "temperature": 0.1
            }
            
        super().__init__(config, **kwargs)
        logger.info(f"Initialized OutputCombinerAgent")
    
    async def _stream_thinking_hook(self, stream_callback: Any):
        """Optional hook called by BaseAgent.process to stream initial thoughts."""
        await self.stream_thinking(
            thinking=f"Combining visualization and response generator outputs...",
            stream_callback=stream_callback
        )
    
    async def _execute_processing(
        self, 
        message: Message, 
        session_id: Optional[str] = None
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Core processing logic to combine outputs from visualization and response agents.
        
        Args:
            message: The input message to process
            session_id: Optional session identifier
            
        Returns:
            Tuple of (response_message, next_agent_id)
        """
        input_metadata = message.metadata or {}
        
        try:
            # Detailed debug logging to diagnose workflow issues
            logger.info(f"OUTPUT COMBINER DEBUG: Message content type: {type(message.content)}")
            if isinstance(message.content, str):
                logger.info(f"OUTPUT COMBINER DEBUG: Message content snippet: {message.content[:100] if message.content else 'None'}")
            logger.info(f"OUTPUT COMBINER DEBUG: Message metadata keys: {list(input_metadata.keys())}")
            
            # Extract the original user query
            original_query = BaseMetadata.get(input_metadata, MetadataKeys.ORIGINAL_QUERY, "")
            logger.info(f"Original query: {original_query}")
            
            # Try to directly access content from the message first
            if message.content and isinstance(message.content, str) and message.content.strip().startswith("RESPONSE:"):
                content = message.content.strip().replace("RESPONSE:", "", 1).strip()
                if content and len(content) > 20:
                    final_content = content
                    logger.info(f"OUTPUT COMBINER DEBUG: Found and used RESPONSE-prefixed content: {len(final_content)} chars")
            elif message.content and len(message.content) > 50 and not self._is_echoing_query(message.content, original_query):
                final_content = message.content
                logger.info(f"Using direct message content: {len(final_content)} chars")
            else:
                # Extract the response generator content (this is the critical part)
                response_content = self._extract_response_content(message)
                logger.info(f"Extracted response content: {len(response_content) if response_content else 0} chars")
                
                # Extract visualization content if available
                visualization_content = self._extract_visualization_content(message)
                logger.info(f"Extracted visualization content: {len(visualization_content) if visualization_content else 0} chars")
                
                # Validate that response_content is not just echoing the query
                if self._is_valid_response(response_content, original_query):
                    final_content = response_content
                    logger.info("Using response generator content")
                else:
                    # Fallback to a default response if we couldn't extract a valid one
                    final_content = "I apologize, but I couldn't generate a complete response about your query."
                    logger.info("Using fallback response - no valid response found")
                
                # Add visualization content if available
                if visualization_content:
                    final_content = f"{final_content}\n\n{visualization_content}"
                    logger.info("Added visualization content to response")
            
            # Create result metadata
            result_metadata = ResultMetadata.create_result_metadata()
            
            # Add additional metadata
            BaseMetadata.update(result_metadata,
                is_json_response=False,
                has_visualization_data=BaseMetadata.get(input_metadata, "visualization_data", None) is not None,
                generated="graph_rag"
            )
            
            # Preserve existing metadata
            for key, value in input_metadata.items():
                if key not in result_metadata:
                    result_metadata[key] = value
            
            # Create the final message
            result_message = Message(
                role=MessageRole.ASSISTANT,
                content=final_content,
                metadata=result_metadata
            )
            
            return result_message, "content_compliance_agent"
            
        except Exception as e:
            # Log the error
            error_msg = f"Error in output combiner: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
            
            # Return a generic error message
            error_metadata = ResultMetadata.create_result_metadata(
                error=error_msg
            )
            
            error_message = Message(
                role=MessageRole.ASSISTANT,
                content=original_query if original_query else "I apologize, but there was an error processing your request. Please try again.",
                metadata=error_metadata
            )
            
            return error_message, None
    
    def _extract_response_content(self, message: Message) -> str:
        """
        Extract the response content from the message metadata.
        
        Args:
            message: Message to extract content from
            
        Returns:
            Extracted response content or empty string if none found
        """
        logger.info("Looking for response content in metadata")
        metadata = message.metadata or {}
        
        # Try multiple ways to find the response content
        
        # 1. First check if message content contains "RESPONSE:" prefix - common in workflows
        if message.content and isinstance(message.content, str) and message.content.strip().startswith("RESPONSE:"):
            content = message.content.strip().replace("RESPONSE:", "", 1).strip()
            if content and len(content) > 20:
                logger.info(f"Found content with RESPONSE prefix: {len(content)} chars")
                return content
        
        # 2. Check if response_generator_agent is in metadata
        if "response_generator_agent" in metadata:
            agent_data = metadata["response_generator_agent"]
            if isinstance(agent_data, dict) and "content" in agent_data:
                content = agent_data["content"]
                if content and isinstance(content, str) and len(content) > 10:
                    logger.info(f"Found content in response_generator_agent: {len(content)} chars")
                    return content
        
        # 3. Check for content in message directly
        if message.content and isinstance(message.content, str):
            logger.info("Using message content as response")
            return message.content
            
        # 4. Look for agent outputs in workflow-specific metadata
        if "agent_outputs" in metadata:
            agent_outputs = metadata["agent_outputs"]
            if "response_generator_agent" in agent_outputs:
                response_data = agent_outputs["response_generator_agent"]
                
                if isinstance(response_data, dict) and "output" in response_data:
                    content = response_data["output"]
                    if content and isinstance(content, str) and len(content) > 20:
                        logger.info(f"Found content in agent_outputs: {len(content)} chars")
                        return content
        
        # 5. Check for any other agent content in metadata
        for key, value in metadata.items():
            if key.endswith("_agent") and isinstance(value, dict) and "content" in value:
                content = value["content"]
                if content and isinstance(content, str) and len(content) > 10:
                    logger.info(f"Found content in {key}: {len(content)} chars")
                    return content
        
        # 6. Check for content in the main message metadata
        content = metadata.get("content", "")
        if content and isinstance(content, str) and len(content) > 10:
            logger.info(f"Found content in metadata.content: {len(content)} chars")
            return content
            
        logger.warning("No valid response content found, using fallback")
        return "I apologize, but I couldn't retrieve a complete response about your dengue fever query."
    
    def _extract_visualization_content(self, message: Message) -> str:
        """
        Extract visualization content from message metadata.
        
        Args:
            message: The message containing visualization data
            
        Returns:
            The visualization content or empty string if not found
        """
        visualization_content = ""
        
        # Check for data_summaries which sometimes contain visualization text
        if "data_summaries" in message.metadata:
            data_summaries = message.metadata.get("data_summaries")
            if data_summaries and isinstance(data_summaries, list):
                viz_parts = []
                for summary in data_summaries:
                    if isinstance(summary, dict) and "summary_text" in summary:
                        viz_parts.append(summary["summary_text"])
                
                if viz_parts:
                    visualization_content = "\n\n## Dengue Visualization Data\n\n" + "\n\n".join(viz_parts)
                    logger.info(f"Extracted visualization summary text")
        
        # If dengue_data_visualization_agent output exists in agent_outputs, use that
        if "agent_outputs" in message.metadata:
            agent_outputs = message.metadata["agent_outputs"]
            
            if "dengue_data_visualization_agent" in agent_outputs:
                viz_data = agent_outputs["dengue_data_visualization_agent"]
                
                if isinstance(viz_data, dict) and "output" in viz_data:
                    content = viz_data["output"]
                    if content and len(content) > 10:  # Basic validity check
                        if not visualization_content:
                            visualization_content = "\n\n## Dengue Visualization Data\n\n" + content
                        logger.info(f"Found visualization in agent_outputs.dengue_data_visualization_agent.output")
        
        return visualization_content
    
    def _is_valid_response(self, content: str, query: str) -> bool:
        """
        Check if the content is a valid response and not just echoing back the query.
        
        Args:
            content: The content to check
            query: The original query
            
        Returns:
            True if content is valid, False otherwise
        """
        # Safety checks
        if not content or not isinstance(content, str) or len(content) < 20:
            logger.warning("Response content failed basic validation (too short or not string)")
            return False
            
        # Prevent echo responses - these are common failure cases where the model
        # just repeats back the query instead of answering it
        query_lower = query.lower().strip()
        content_lower = content.lower().strip()
        
        # Check for exact match
        if content_lower == query_lower:
            logger.warning("Content is an exact match to the query - invalid")
            return False
            
        # Check if content mostly starts with the query
        if content_lower.startswith(query_lower):
            logger.warning("Content starts with the query - likely invalid")
            # If it's just slightly longer than the query, it's probably invalid
            if len(content) < len(query) * 1.5:
                return False
                
        # Check if content has some minimum length relative to query length
        content_query_ratio = len(content) / max(len(query), 1)
        if content_query_ratio < 1.2:
            logger.warning(f"Content too short compared to query (ratio: {content_query_ratio})")
            return False
            
        # Check for apology phrases that indicate failure
        failure_phrases = [
            "i apologize",
            "i'm sorry",
            "i am sorry",
            "cannot provide",
            "unable to",
            "don't have",
            "do not have",
            "no information",
            "couldn't generate",
            "could not generate"
        ]
        
        if any(phrase in content_lower for phrase in failure_phrases):
            # Only consider it invalid if the entire content is very short and just an apology
            if len(content) < 100:
                logger.warning("Content contains failure phrases and is too short")
                return False
        
        # If we passed all checks, it's a valid response
        return True
    
    def _is_echoing_query(self, content: str, query: str) -> bool:
        """
        Simple check to see if content is echoing the query.
        
        Args:
            content: The content to check
            query: The original query
            
        Returns:
            True if content appears to be echoing the query, False otherwise
        """
        if not content or not isinstance(content, str):
            return False
        
        # Basic checks
        # 1. Content shouldn't be identical to query
        if content.strip().lower() == query.strip().lower():
            return True
            
        # 2. Content shouldn't start with the query (probable echo)
        if content.strip().lower().startswith(query.strip().lower()):
            content_len_ratio = len(content) / len(query)
            if content_len_ratio < 1.5:  # If it's just the query with minimal additions
                return True
        
        return False
