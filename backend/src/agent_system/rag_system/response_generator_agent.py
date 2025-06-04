"""
Response Generator RAG Agent

A specialized agent for response generator functionality
Uses a prompt from the prompt registry for its system message.

IMPLEMENTATION GUIDE:
1. Review and update the docstrings and comments
2. Implement the _execute_processing method for your agent's specific logic
3. Add any additional methods needed for your agent's functionality
4. Update the prompt_id to match the one in your configuration
5. Consider if your agent needs additional tools or special capabilities
"""
import logging
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from src.agent_system.core.metadata import MetadataKeys

from src.agent_system.core.base_agent import BaseAgent
from src.agent_system.core.message import Message, MessageRole
from src.registries.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)

class ResponseGeneratorAgent(BaseAgent):  
    """
    A specialized agent for response generator functionality
    
    This class implements the Response Generator RAG Agent functionality by:
    1. Using a specific prompt from the prompt registry
    2. Processing user messages with appropriate LLM calls
    3. [Add any additional core functionality here]
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], **kwargs):
        """
        Initialize the ResponseGeneratorAgent.
        
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
        self.prompt_id = config.get("prompt_id", "rag.response_generator")
        
        logger.info(f"Initialized ResponseGeneratorAgent with prompt_id: {self.prompt_id}")
    
    async def _stream_thinking_hook(self, stream_callback: Any):
        """Optional hook called by BaseAgent.process to stream initial thoughts."""
        await self.stream_thinking(
            thinking=f"Using prompt: {self.prompt_id}\nFormulating response...",
            stream_callback=stream_callback
        )
        
    async def _execute_processing(
        self, 
        message: Message, 
        session_id: Optional[str] = None,
        visualization_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Core processing logic for the ResponseGeneratorAgent.
        Handles prompt retrieval, LLM call, and response generation.
        Error handling and standard status updates are managed by BaseAgent.process.
        
        Args:
            message: The input message to process
            session_id: Optional session identifier
            visualization_data: Optional visualization data to append
            
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
        generated_text = response_text
        logger.info(f"Agent {self.agent_id} successfully generated response.")
        logger.debug(f"Generated response text: \n{generated_text}")

        # The main content is the LLM's generated text without appending visualization
        final_content = generated_text
        
        # Process visualization data if available
        if visualization_data and (visualization_data.get('historical_data') or visualization_data.get('predicted_data')):
            logger.info(f"Processing visualization data for agent {self.agent_id}.")
            try:
                # Calculate statistics from historical data
                historical_data = visualization_data.get('historical_data', [])
                predicted_data = visualization_data.get('predicted_data', [])
                country = visualization_data.get('country', 'saudi_arabia').replace('_', ' ').title()
                
                # Calculate total cases
                total_cases = sum(entry.get('dengue_total', 0) for entry in historical_data)
                
                # Calculate average annual cases
                # Group by year
                years_data = {}
                for entry in historical_data:
                    date_str = entry.get('calendar_start_date', '')
                    if date_str and date_str.startswith('20'):
                        year = date_str.split('-')[0]
                        if year not in years_data:
                            years_data[year] = 0
                        years_data[year] += entry.get('dengue_total', 0)
                
                avg_annual_cases = round(sum(years_data.values()) / len(years_data)) if years_data else 0
                
                # Find peak month
                if historical_data:
                    peak_entry = max(historical_data, key=lambda x: x.get('dengue_total', 0))
                    peak_date = peak_entry.get('calendar_start_date', '')
                    peak_month = ''
                    if peak_date:
                        month_num = int(peak_date.split('-')[1])
                        month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                                      'July', 'August', 'September', 'October', 'November', 'December']
                        if 1 <= month_num <= 12:
                            peak_month = month_names[month_num - 1]
                else:
                    peak_month = 'Unknown'
                
                # Calculate placeholders
                replacements = {
                    '{{total_cases_saudi}}': f"{total_cases:,}",
                    '{{avg_annual_cases}}': f"{avg_annual_cases:,}",
                    '{{peak_month}}': peak_month,
                    '{{notable_outbreaks}}': 'Data not available'
                }

                # First try to replace any placeholder variables
                for placeholder, value in replacements.items():
                    if placeholder in final_content:
                        final_content = final_content.replace(placeholder, value)
                        logger.debug(f"Replaced {placeholder} with {value}")
                
                logger.debug("Successfully processed visualization data and created data table.")
            except Exception as e:
                logger.warning(f"Error processing visualization data: {e}")
        
        # Add citations to the response if results are available
        results = message.metadata.get('results', [])
        if results:
            logger.info(f"Adding citations to response for agent {self.agent_id}.")
            try:
                # Create source mapping
                source_titles = []
                for result in results:
                    title = result.get('disease_citation_title') or result.get('vector_citation_title')
                    url = result.get('disease_citation_url') or result.get('vector_citation_url')
                    if title and url:
                        source_titles.append((title, url))
                
                # If there are sources, add a Sources section at the end
                if source_titles and '**Sources:**' not in final_content and 'Sources:' not in final_content:
                    sources_section = "\n\n**Sources:**\n"
                    for idx, (title, url) in enumerate(source_titles, 1):
                        sources_section += f"{idx}. {title} ({url})\n"
                    
                    final_content += sources_section
                
                logger.debug("Successfully added citations to the response.")
            except Exception as e:
                logger.warning(f"Error adding citations: {e}")
                # Continue with original content if citation fails
                pass
        
        # Initialize metadata with standard keys
        response_metadata = {
            "prompt_id": self.prompt_id,
            MetadataKeys.GENERATED.value: generated_text,  # Use standard metadata key
            MetadataKeys.TIMESTAMP.value: datetime.now().isoformat()
        }
        
        # Handle visualization data by storing it in metadata instead of appending to content
        if visualization_data and (visualization_data.get('historical_data') or visualization_data.get('predicted_data')):
            logger.info(f"Adding visualization data to metadata for agent {self.agent_id}.")
            # Store visualization data in metadata using standard keys
            response_metadata[MetadataKeys.VISUALIZATION_DATA.value] = visualization_data
            response_metadata[MetadataKeys.HAS_VISUALIZATION_DATA.value] = True
            
            # Log success
            logger.debug("Successfully added visualization data to metadata.")
        else:
            logger.info("No visualization data found to include.")
            response_metadata[MetadataKeys.HAS_VISUALIZATION_DATA.value] = False

        response_message = Message(
            role=MessageRole.ASSISTANT,
            content=final_content,
            metadata=response_metadata
        )
            
        # If your agent should chain to another agent, return its ID as the second element
        # For example: return response_message, "next_agent_id"
        return response_message, None
