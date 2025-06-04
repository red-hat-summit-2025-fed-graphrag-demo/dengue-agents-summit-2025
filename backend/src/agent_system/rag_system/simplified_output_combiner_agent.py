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

class SimplifiedOutputCombinerAgent(BaseAgent):
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
        logger.info(f"Initialized SimplifiedOutputCombinerAgent")
    
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
            # Extract the original user query
            original_query = BaseMetadata.get(input_metadata, MetadataKeys.ORIGINAL_QUERY, "")
            logger.info(f"Original query: {original_query}")
            
            # Extract the response generator content (this is the critical part)
            response_content = self._extract_response_content(message)
            
            # Extract visualization content if available
            visualization_content = self._extract_visualization_content(message)
            
            # Validate that response_content is not just echoing the query
            # This is a simplified but more reliable check than the original
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
                has_visualization_data=bool(visualization_content),
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
            error_msg = f"Error in simplified output combiner: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
            
            # Return a generic error message
            error_metadata = ResultMetadata.create_result_metadata(
                error=error_msg
            )
            
            error_message = Message(
                role=MessageRole.ASSISTANT,
                content="I apologize, but there was an error processing your request. Please try again.",
                metadata=error_metadata
            )
            
            return error_message, None
    
    def _extract_response_content(self, message: Message) -> str:
        """
        Extract response generator content from various sources.
        Prioritizes looking in these locations:
        1. message.content (if it's a meaningful response)
        2. response_generator_agent output in agent_outputs
        3. other known metadata locations
        
        Args:
            message: The message containing response data
            
        Returns:
            The extracted response content or fallback message
        """
        # Try to find the response content in the metadata
        logger.info(f"Looking for response content in metadata")
        
        # First priority: Check if agent_outputs contains response_generator_agent output
        if "agent_outputs" in message.metadata:
            agent_outputs = message.metadata["agent_outputs"]
            
            if "response_generator_agent" in agent_outputs:
                response_data = agent_outputs["response_generator_agent"]
                
                if isinstance(response_data, dict) and "output" in response_data:
                    content = response_data["output"]
                    if content and len(content) > 20:  # Basic validity check
                        logger.info(f"Found response in agent_outputs.response_generator_agent.output")
                        return content
        
        # Second priority: Direct message content if it's meaningful
        if hasattr(message, 'content') and message.content:
            content = message.content
            if content and len(content) > 20:  # Basic validity check
                logger.info(f"Using message content as response")
                return content
        
        # Third priority: Check for direct response fields in metadata
        possible_fields = [
            "response_generator_output",
            "generated",
            "llm_response",
            "text_response", 
            "response_content"
        ]
        
        for field in possible_fields:
            if field in message.metadata and message.metadata[field]:
                content = message.metadata[field]
                if content and len(content) > 20:  # Basic validity check
                    logger.info(f"Found response in metadata.{field}")
                    return content
        
        # If no valid response was found, return a fallback message
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
        Simple validity check for response content.
        
        Args:
            content: The content to check
            query: The original query
            
        Returns:
            True if content appears to be a valid response, False otherwise
        """
        if not content or not isinstance(content, str):
            return False
        
        # Very basic checks that don't overfilter
        # 1. Content should be significantly longer than the query
        if len(content) < 20:
            return False
            
        # 2. Content shouldn't be identical to query
        if content.strip().lower() == query.strip().lower():
            return False
            
        # 3. Content shouldn't start with the query (probable echo)
        if content.strip().lower().startswith(query.strip().lower()):
            content_len_ratio = len(content) / len(query)
            if content_len_ratio < 1.5:  # If it's just the query with minimal additions
                return False
        
        return True
