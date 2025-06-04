"""
Response Generator Agent

A specialized agent for generating high-quality responses about dengue fever,
with integrated capabilities for detecting countries, extracting dates,
and retrieving relevant dengue data.
"""
import re
import json
import logging
import traceback
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from src.agent_system.core.base_agent import BaseAgent
from src.agent_system.core.message import Message, MessageRole
from src.agent_system.core.metadata import MetadataKeys, BaseMetadata, ResultMetadata, ErrorMetadata 
from src.registries.prompt_registry import PromptRegistry
from src.tools.dengue_data_tool import DengueDataTool
from src.tools.extract_dates_from_natural_language_tool import ExtractDatesFromNaturalLanguageTool

logger = logging.getLogger(__name__)

class ResponseGeneratorAgent(BaseAgent):
    """
    An agent that generates comprehensive responses about dengue fever with integrated
    data retrieval capabilities.
    
    This agent:
    1. Identifies countries mentioned in the user query
    2. Extracts dates if present in the query 
    3. Retrieves relevant dengue data when applicable
    4. Generates a high-quality response using all available information
    5. Appends structured data to the response when available
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
                "model_type": "instruct",
                "max_tokens": 2048,  # Larger context for detailed responses
                "temperature": 0.5   # Balanced between creativity and factuality
            }
        elif "model_type" not in config["model_config"]:
            config["model_config"]["model_type"] = "instruct"
            
        super().__init__(config, **kwargs)
        
        # Get a reference to the prompt registry
        self.prompt_registry = PromptRegistry()
        
        # Extract prompt_id from config or use default
        self.prompt_id = config.get("prompt_id", "rag.response_generator")
        
        # Initialize tools
        self.dengue_data_tool = DengueDataTool()
        self.date_extraction_tool = ExtractDatesFromNaturalLanguageTool()
        
        logger.info(f"Initialized ResponseGeneratorAgent with prompt_id: {self.prompt_id}")
    
    async def _stream_thinking_hook(self, stream_callback: Any):
        """Optional hook called by BaseAgent.process to stream initial thoughts."""
        await self.stream_thinking(
            thinking=f"Analyzing query for countries and dates, retrieving dengue data if applicable, and generating a comprehensive response...",
            stream_callback=stream_callback
        )
    
    async def _execute_processing(self, message: Message, session_id: Optional[str] = None):
        """
        Core processing logic for the ResponseGeneratorAgent with standardized metadata handling.
        
        Args:
            message: The input message to process (containing processed query results)
            session_id: Optional session identifier
            
        Returns:
            Tuple of (response_message, next_agent_id)
        """
        original_query = None
        countries = []
        dates = []
        dengue_data = None
        result_count = 0
        assessment = "no_results"
        cypher_query = None
        citations = []
        
        try:
            logger.info(f"Starting response generation processing for session: {session_id}")
            
            # --- Step 1: Extract data from message metadata using standardized methods ---
            try:
                original_query = BaseMetadata.get(message.metadata, MetadataKeys.ORIGINAL_QUERY, None)
                if not original_query:
                    logger.warning("Original query not found in metadata, extracting from message")
                    original_query = self._get_original_input(message)
                
                cypher_query = BaseMetadata.get(message.metadata, MetadataKeys.CYPHER_QUERY, None)
                if cypher_query:
                    logger.debug(f"Cypher query found: {cypher_query[:100]}...")
                else:
                    logger.warning("No Cypher query found in metadata")
                    
                query_results = BaseMetadata.get(message.metadata, MetadataKeys.RESULTS, [])
                result_count = len(query_results) if query_results else 0
                assessment = BaseMetadata.get(message.metadata, MetadataKeys.ASSESSMENT, "no_results")
                
                # Extract citations using standard metadata helper
                citations = self._extract_citations(message)
                
                logger.info(f"Processing query: '{original_query[:100]}...' with {result_count} results, Assessment: {assessment}")
                logger.debug(f"Metadata keys available: {list(message.metadata.keys())}")
            except Exception as e:
                logger.error(f"Error extracting data from message metadata: {str(e)}")
                logger.error(traceback.format_exc())
                raise RuntimeError(f"Failed to extract data from message: {str(e)}")
            
            # --- Step 2: Identify target countries ---
            try:
                countries = self._identify_target_countries(original_query)
                logger.info(f"Identified countries: {countries}")
            except Exception as e:
                logger.error(f"Error identifying target countries: {str(e)}")
                logger.error(traceback.format_exc())
                countries = []
            
            # --- Step 3: Extract dates if present ---
            dates = []
            if countries:
                try:
                    logger.debug(f"Attempting to extract dates from: '{original_query[:100]}...'")
                    dates = await self._extract_dates(original_query)
                    logger.info(f"Extracted dates: {dates}")
                except Exception as e:
                    logger.error(f"Error extracting dates: {str(e)}")
                    logger.error(traceback.format_exc())
                    dates = []
            
            # --- Step 4: Retrieve dengue data if applicable ---
            dengue_data = None
            if countries:
                country = countries[0]  # Use the first identified country
                try:
                    if dates:
                        # If dates are present, get prediction data
                        logger.info(f"Retrieving predictions for country: {country}, date: {dates[0]}")
                        dengue_data = await self.dengue_data_tool.get_predictions(country, dates[0])
                    else:
                        # Otherwise get historical data
                        logger.info(f"Retrieving historical data for country: {country}")
                        dengue_data = await self.dengue_data_tool.get_historical_data(country)
                    
                    if dengue_data:
                        logger.info(f"Successfully retrieved dengue data for {country}")
                        logger.debug(f"Dengue data summary: {json.dumps({k: v for k, v in dengue_data.items() if k not in ['data', 'historical_data', 'predicted_data']})}")
                    else:
                        logger.warning(f"No dengue data returned for {country}")
                except Exception as e:
                    logger.error(f"Error retrieving dengue data for {country}: {str(e)}")
                    logger.error(traceback.format_exc())
                    dengue_data = None
            
            # --- Step 5: Prepare data for response generation ---
            try:
                logger.debug("Preparing prompt data...")
                prompt_data = self._prepare_prompt_data(
                    original_query=original_query,
                    cypher_query=cypher_query,
                    query_results=query_results,
                    assessment=assessment,
                    citations=citations,
                    countries=countries,
                    dates=dates,
                    dengue_data=dengue_data
                )
                logger.debug(f"Prompt data keys: {list(prompt_data.keys())}")
            except Exception as e:
                logger.error(f"Error preparing prompt data: {str(e)}")
                logger.error(traceback.format_exc())
                raise RuntimeError(f"Failed to prepare prompt data: {str(e)}")
            
            # --- Step 6: Generate the response ---
            try:
                logger.info("Generating response text...")
                response_text = await self._generate_response(prompt_data)
                logger.info(f"Generated response with {len(response_text)} characters")
                logger.debug(f"Response preview: {response_text[:100]}...")
            except Exception as e:
                logger.error(f"Error generating response: {str(e)}")
                logger.error(traceback.format_exc())
                raise RuntimeError(f"Failed to generate response: {str(e)}")
            
            # --- Step 7: Append dengue data if available ---
            if dengue_data:
                try:
                    logger.debug("Appending dengue data to response...")
                    response_text = self._append_data_to_response(response_text, dengue_data)
                    logger.debug(f"Final response length: {len(response_text)} characters")
                except Exception as e:
                    logger.error(f"Error appending dengue data: {str(e)}")
                    logger.error(traceback.format_exc())
                    # Continue without appended data if this fails
            
            # --- Step 8: Create result metadata using standard patterns ---
            try:
                logger.debug("Creating result metadata...")
                result_metadata = ResultMetadata.create_result_metadata(
                    results=query_results,
                    assessment=assessment,
                    result_count=result_count
                )
                
                # Add additional metadata using standard methods and keys
                # Pass keys explicitly using MetadataKeys enum
                BaseMetadata.update(result_metadata, {
                    MetadataKeys.GENERATED.value: response_text, 
                    MetadataKeys.HAS_CITATIONS: len(citations) > 0,
                    MetadataKeys.CITATION_COUNT: len(citations)
                    }
                )
                
                # Add custom metadata for our specific needs
                if citations:
                    result_metadata[MetadataKeys.CITATIONS.value] = citations
                    
                if countries:
                    result_metadata["countries"] = countries
                    
                if dates:
                    result_metadata["dates"] = dates
                    
                if dengue_data:
                    result_metadata["has_dengue_data"] = True
                    # Store a simplified version of dengue data
                    result_metadata["dengue_data_summary"] = {
                        "country": dengue_data.get("requested_country", "Unknown"),
                        "has_historical": "historical_data" in dengue_data or "data" in dengue_data,
                        "has_predictions": "predicted_data" in dengue_data and dengue_data["predicted_data"]
                    }
                
                # Preserve existing metadata
                for key, value in message.metadata.items():
                    if key not in result_metadata and key != MetadataKeys.RESULTS.value:
                        result_metadata[key] = value
                        
                logger.debug(f"Final metadata keys: {list(result_metadata.keys())}")
            except Exception as e:
                logger.error(f"Error creating result metadata: {str(e)}")
                logger.error(traceback.format_exc())
                raise RuntimeError(f"Failed to create result metadata: {str(e)}")
            
            # Set the generated content in metadata for downstream agents
            BaseMetadata.update(result_metadata, {
                MetadataKeys.GENERATED.value: response_text,
            })
            
            # --- Step 9: Create and return the response message ---
            try:
                response_message = Message(
                    content=response_text,
                    role=MessageRole.ASSISTANT,
                    metadata=result_metadata
                )
                logger.info("Successfully created response message")
                return response_message, None
            except Exception as e:
                logger.error(f"Error creating response message: {str(e)}")
                logger.error(traceback.format_exc())
                raise RuntimeError(f"Failed to create response message: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error in ResponseGeneratorAgent._execute_processing: {e}")
            logger.error(traceback.format_exc())
            
            # Create error metadata using standard pattern
            try:
                error_metadata = ResultMetadata.create_result_metadata(
                    results=[],
                    assessment="error",
                    error=str(e)
                )
                
                # Add diagnostic information
                diagnostic_info = {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "original_query": original_query if original_query else "No query available",
                    "identified_countries": countries,
                    "extracted_dates": dates,
                    "has_dengue_data": dengue_data is not None,
                    "result_count": result_count,
                    "assessment": assessment
                }
                
                logger.error(f"Diagnostic info: {json.dumps(diagnostic_info)}")
                
                error_metadata["diagnostic_info"] = diagnostic_info
                
                BaseMetadata.update(error_metadata, {
                    MetadataKeys.GENERATED.value: f"I apologize, but I encountered an error while processing your request: {str(e)}"
                })
                
                error_response = Message(
                    content=f"I apologize, but I encountered an error while processing your request: {str(e)}",
                    role=MessageRole.ASSISTANT,
                    metadata=error_metadata
                )
                
                logger.info("Created error response message")
                return error_response, None
            except Exception as nested_error:
                # Last resort error handling
                logger.critical(f"Critical error in error handling: {str(nested_error)}")
                logger.critical(traceback.format_exc())
                
                # Create a basic error message with minimal metadata
                simple_metadata = {
                    "error": str(e),
                    "nested_error": str(nested_error),
                    "assessment": "critical_error"
                }
                
                return Message(
                    content="I apologize, but a critical error occurred while processing your request. Please try again or contact support.",
                    role=MessageRole.ASSISTANT,
                    metadata=simple_metadata
                ), None
    
    def _identify_target_countries(self, query: str) -> List[str]:
        """
        Identify target countries in the user query.
        Uses the country_mapping from DengueDataTool to recognize variations.
        
        Args:
            query: The user query
            
        Returns:
            List of identified target countries
        """
        try:
            if not query:
                logger.warning("Empty query provided to _identify_target_countries")
                return []
                
            identified_countries = []
            query_lower = query.lower()
            
            logger.debug(f"Identifying countries in query: '{query_lower[:100]}...'")
            
            # Get available countries for logging
            available_countries = self.dengue_data_tool.available_countries
            logger.debug(f"Available countries for matching: {available_countries}")
            
            # Look for matches in the DengueDataTool's country_mapping
            for country_term in self.dengue_data_tool.country_mapping:
                try:
                    # Check for whole word match with word boundaries
                    pattern = r'\b' + re.escape(country_term) + r'\b'
                    if re.search(pattern, query_lower):
                        mapped_country = self.dengue_data_tool.country_mapping[country_term]
                        logger.debug(f"Found match: '{country_term}' → '{mapped_country}'")
                        
                        if mapped_country in self.dengue_data_tool.available_countries:
                            # Add the canonical country name
                            if mapped_country not in identified_countries:
                                identified_countries.append(mapped_country)
                                logger.info(f"Added country to results: {mapped_country}")
                        else:
                            logger.warning(f"Mapped country '{mapped_country}' not in available countries list")
                except Exception as term_error:
                    logger.warning(f"Error processing country term '{country_term}': {str(term_error)}")
                    continue
            
            logger.info(f"Country identification complete. Found: {identified_countries}")
            return identified_countries
            
        except Exception as e:
            logger.error(f"Error in _identify_target_countries: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    async def _extract_dates(self, query: str) -> List[str]:
        """
        Extract dates from the user query using the extraction tool.
        
        Args:
            query: The user query
            
        Returns:
            List of extracted dates in ISO format (YYYY-MM-DD)
        """
        try:
            if not query:
                logger.warning("Empty query provided to _extract_dates")
                return []
                
            logger.info(f"Extracting dates from query: '{query[:100]}...'")
            
            # Call the date extraction tool
            try:
                logger.debug("Calling date extraction tool")
                date_result = await self.date_extraction_tool._execute({"text": query})
                logger.debug(f"Date extraction tool response keys: {list(date_result.keys()) if date_result else 'None'}")
            except Exception as tool_error:
                logger.error(f"Date extraction tool error: {str(tool_error)}")
                logger.error(traceback.format_exc())
                return []
            
            if not date_result:
                logger.warning("Date extraction tool returned empty result")
                return []
                
            if "result" not in date_result:
                logger.warning(f"Date extraction missing 'result' key. Keys: {list(date_result.keys())}")
                return []
                
            # Extract dates from the result
            extracted_dates = date_result["result"].get("dates", [])
            logger.debug(f"Raw extracted dates: {extracted_dates}")
            
            if not extracted_dates:
                logger.info("No dates found in query")
                return []
                
            # Log each extracted date with context
            for date_item in extracted_dates:
                logger.debug(f"Extracted date: {date_item.get('date')}, type: {date_item.get('type')}, text: {date_item.get('text')}")
                
            # Sort dates and return ISO format dates
            sorted_dates = sorted([date["date"] for date in extracted_dates])
            logger.info(f"Final extracted dates (sorted): {sorted_dates}")
            return sorted_dates
                
        except Exception as e:
            logger.error(f"Error in _extract_dates: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    def _append_data_to_response(self, response: str, data: Dict[str, Any]) -> str:
        """
        Append dengue data to the response in a formatted code block.
        
        Args:
            response: The text response
            data: The dengue data dictionary
            
        Returns:
            The response with appended data
        """
        try:
            logger.debug(f"Appending dengue data to response of length {len(response)}")
            
            # Create a clean version of the data for display
            display_data = {
                "country": data.get("requested_country", "Unknown"),
                "data_source": data.get("mapped_country", "Unknown")
            }
            
            # Add historical data summary
            try:
                historical_data = data.get("historical_data", data.get("data", []))
                if historical_data:
                    logger.debug(f"Processing historical data with {len(historical_data)} records")
                    display_data["historical_data"] = {
                        "count": len(historical_data),
                        "date_range": {
                            "start": historical_data[0]["date"] if historical_data else "N/A",
                            "end": historical_data[-1]["date"] if historical_data else "N/A"
                        },
                        "summary": {
                            "total_cases": sum(item.get("cases", 0) for item in historical_data),
                            "average_cases_per_day": round(sum(item.get("cases", 0) for item in historical_data) / len(historical_data), 2) if historical_data else 0
                        }
                    }
                    logger.debug(f"Historical data summary added: date range {display_data['historical_data']['date_range']['start']} to {display_data['historical_data']['date_range']['end']}")
                else:
                    logger.debug("No historical data available to append")
            except Exception as hist_error:
                logger.error(f"Error processing historical data: {str(hist_error)}")
                logger.error(traceback.format_exc())
                # Add minimal info to avoid failing
                display_data["historical_data_error"] = str(hist_error)
            
            # Add prediction data summary if available
            try:
                predicted_data = data.get("predicted_data", [])
                if predicted_data:
                    logger.debug(f"Processing prediction data with {len(predicted_data)} records")
                    display_data["prediction_data"] = {
                        "count": len(predicted_data),
                        "date_range": {
                            "start": predicted_data[0]["date"] if predicted_data else "N/A",
                            "end": predicted_data[-1]["date"] if predicted_data else "N/A"
                        },
                        "summary": {
                            "total_predicted_cases": sum(item.get("cases", 0) for item in predicted_data),
                            "average_cases_per_day": round(sum(item.get("cases", 0) for item in predicted_data) / len(predicted_data), 2) if predicted_data else 0
                        }
                    }
                    logger.debug(f"Prediction data summary added: date range {display_data['prediction_data']['date_range']['start']} to {display_data['prediction_data']['date_range']['end']}")
                else:
                    logger.debug("No prediction data available to append")
            except Exception as pred_error:
                logger.error(f"Error processing prediction data: {str(pred_error)}")
                logger.error(traceback.format_exc())
                # Add minimal info to avoid failing
                display_data["prediction_data_error"] = str(pred_error)
            
            # Format the data as JSON in a code block
            try:
                formatted_data = json.dumps(display_data, indent=2)
                data_block = f"\n\n```json\n{formatted_data}\n```"
                logger.debug(f"Formatted JSON data block with {len(formatted_data)} characters")
            except Exception as format_error:
                logger.error(f"Error formatting data as JSON: {str(format_error)}")
                logger.error(traceback.format_exc())
                # Fallback to simple string representation
                data_block = f"\n\n```\n{str(display_data)}\n```"
            
            # Add explanatory text before the data block
            data_intro = "\n\n**Dengue Data Summary:**\n\nBelow is a summary of dengue data for your reference:"
            
            final_response = response + data_intro + data_block
            logger.info(f"Final response with appended data: {len(final_response)} characters")
            return final_response
            
        except Exception as e:
            logger.error(f"Error in _append_data_to_response: {str(e)}")
            logger.error(traceback.format_exc())
            # Return original response to avoid failing completely
            return response + "\n\n**Note:** There was an error processing the dengue data for display."

    def _get_original_input(self, message: Message) -> str:
        """
        Extract the original user input from the message or its metadata.
        
        Args:
            message: The input message
            
        Returns:
            The original user query as a string
        """
        try:
            logger.debug("Attempting to extract original input from message")
            
            # Try to get from the standardized metadata field
            original_query = BaseMetadata.get(message.metadata, MetadataKeys.ORIGINAL_QUERY, None)
            
            if original_query:
                logger.debug(f"Found original query in metadata: '{original_query[:50]}...'")
                return original_query
                
            # If not found, try to get from message content
            if message.content:
                logger.debug(f"Using message content as original query: '{message.content[:50]}...'")
                return message.content
                
            # Default fallback
            logger.warning("Could not find original query in metadata or message content")
            return "No query found"
            
        except Exception as e:
            logger.error(f"Error in _get_original_input: {str(e)}")
            logger.error(traceback.format_exc())
            return "No query found"
    
    def _extract_citations(self, message: Message) -> List[Dict[str, Any]]:
        """
        Extract citation information from message metadata.
        
        Args:
            message: The input message
            
        Returns:
            List of citation dictionaries
        """
        try:
            logger.debug("Extracting citations from message metadata")
            
            # Use BaseMetadata helper to get citations with proper key
            citations = BaseMetadata.get(message.metadata, MetadataKeys.CITATIONS, [])
            
            # Ensure we have a list
            if citations and not isinstance(citations, list):
                logger.warning(f"Citations found but not in list format, converting: {type(citations)}")
                citations = [citations]
                
            citation_count = len(citations) if citations else 0
            logger.debug(f"Found {citation_count} citations in metadata")
            
            # Verify citation format
            valid_citations = []
            for i, citation in enumerate(citations):
                try:
                    if isinstance(citation, dict) and "title" in citation:
                        valid_citations.append(citation)
                    else:
                        logger.warning(f"Skipping invalid citation format at index {i}: {citation}")
                except Exception as cite_error:
                    logger.warning(f"Error processing citation at index {i}: {str(cite_error)}")
                    
            if len(valid_citations) != citation_count:
                logger.warning(f"Some citations were invalid: {citation_count} found, {len(valid_citations)} valid")
                
            return valid_citations
            
        except Exception as e:
            logger.error(f"Error in _extract_citations: {str(e)}")
            logger.error(traceback.format_exc())
            return []
        
    def _add_citations_to_response(self, response_text: str, citations: List[Dict[str, Any]]) -> str:
        """
        Add citations to the response text if they're not already included.
        
        Args:
            response_text: The original response text
            citations: List of citation dictionaries
            
        Returns:
            Response text with citations added
        """
        try:
            logger.debug(f"Adding {len(citations)} citations to response")
            
            if not citations:
                logger.debug("No citations to add, returning original response")
                return response_text
                
            # Check if response already has numbered citations
            if re.search(r'\[\d+\]', response_text):
                logger.debug("Response already contains numbered citations, keeping original")
                return response_text
                
            # Build a citations section with numbered references
            citation_section = "\n\n## References\n\n"
            
            for i, citation in enumerate(citations):
                try:
                    title = citation.get("title", "Unknown Source")
                    authors = citation.get("authors", "")
                    year = citation.get("year", "")
                    url = citation.get("url", "")
                    
                    # Format the citation text
                    citation_text = f"[{i+1}] {title}"
                    
                    if authors:
                        citation_text += f". {authors}"
                        
                    if year:
                        citation_text += f", {year}"
                        
                    if url:
                        citation_text += f". Available at: {url}"
                        
                    citation_section += citation_text + "\n\n"
                    logger.debug(f"Added citation {i+1}: {title[:50]}...")
                    
                except Exception as cite_error:
                    logger.warning(f"Error formatting citation {i+1}: {str(cite_error)}")
                    citation_section += f"[{i+1}] Citation information unavailable\n\n"
            
            # Append the citations to the response
            result = response_text + citation_section
            logger.info(f"Response with citations: {len(result)} characters")
            return result
            
        except Exception as e:
            logger.error(f"Error in _add_citations_to_response: {str(e)}")
            logger.error(traceback.format_exc())
            return response_text
    
    async def _generate_response(self, prompt_data: Dict[str, Any]) -> str:
        """
        Generate a response by applying the prompt template and calling the LLM.
        
        Args:
            prompt_data: Data to fill the prompt template with
            
        Returns:
            The generated response string
        """
        prompt_id = prompt_data.get("prompt_id", self.prompt_id)
        
        try:
            logger.info(f"Generating response using prompt_id: {prompt_id}")
            
            # Get the prompt template
            try:
                prompt_template = self.prompt_registry.get_prompt(prompt_id)
                if not prompt_template:
                    error_msg = f"Could not find prompt template with ID: {prompt_id}"
                    logger.error(error_msg)
                    return f"I apologize, but I am unable to generate a response at this time due to a system error: {error_msg}"
                logger.debug(f"Successfully retrieved prompt template: {prompt_id}")
            except Exception as template_error:
                logger.error(f"Error retrieving prompt template: {str(template_error)}")
                logger.error(traceback.format_exc())
                return f"I apologize, but I am unable to generate a response at this time due to a system error: {str(template_error)}"
            
            # Render the prompt with the provided data
            try:
                logger.debug("Rendering prompt template with data")
                if hasattr(prompt_template, 'render'):
                    prompt = prompt_template.render(**prompt_data)
                    logger.debug(f"Rendered prompt using template.render() method")
                else:
                    # Handle string template or yaml prompt case
                    prompt_text = str(prompt_template.prompt if hasattr(prompt_template, 'prompt') else prompt_template)
                    for key, value in prompt_data.items():
                        placeholder = f"{{{{{key}}}}}"
                        if placeholder in prompt_text:
                            prompt_text = prompt_text.replace(placeholder, str(value))
                    prompt = prompt_text
                    logger.debug(f"Rendered prompt using manual string replacement")
                
                # Log prompt length and preview
                prompt_length = len(prompt)
                logger.debug(f"Rendered prompt with {prompt_length} characters")
                logger.debug(f"Prompt preview: {prompt[:200]}...")
            except Exception as render_error:
                logger.error(f"Error rendering prompt template: {str(render_error)}")
                logger.error(traceback.format_exc())
                return f"I apologize, but I am unable to generate a response at this time due to a system error: {str(render_error)}"
            
            # Add instruction to generate a single, well-formatted response
            prompt += "\n\nIMPORTANT: Generate ONE single response. Do NOT include duplicate content or template sections. Format your response using proper Markdown."
            
            # Call the LLM using the BaseAgent's call_llm method
            try:
                logger.info("Calling LLM to generate response")
                messages = [
                    Message(role=MessageRole.SYSTEM, content=prompt)
                ]
                
                start_time = datetime.now()
                llm_response, llm_metadata = await self.call_llm(messages)
                end_time = datetime.now()
                
                duration_ms = (end_time - start_time).total_seconds() * 1000
                logger.info(f"LLM response received in {duration_ms:.2f}ms")
                
                if llm_metadata:
                    logger.debug(f"LLM metadata: {json.dumps(llm_metadata)}")
            except Exception as llm_error:
                logger.error(f"Error calling LLM: {str(llm_error)}")
                logger.error(traceback.format_exc())
                return f"I apologize, but I am unable to generate a response at this time due to a system error: {str(llm_error)}"
            
            # Extract the text from the LLM response
            try:
                response_text = str(llm_response)
                logger.info(f"Raw LLM response length: {len(response_text)} characters")
                
                # Clean up any response markers
                logger.debug("Cleaning response text")
                response_parts = re.split(r'(?i)(?:RESPONSE:|FINAL RESPONSE:)', response_text)
                
                if len(response_parts) > 1:
                    # Use the last part after a response marker
                    clean_response = response_parts[-1].strip()
                    logger.info(f"Extracted final response section ({len(clean_response)} chars)")
                    logger.debug(f"Response preview: {clean_response[:100]}...")
                    response_text = clean_response
                else:
                    # If no response markers, apply minimal cleanup
                    response_text = response_text.strip()
                    logger.debug("No response markers found, using cleaned full response")
                
                # Add citations if they were provided and not already included
                if prompt_data.get("citations") and "[1]" not in response_text:
                    logger.debug("Adding citations to response")
                    try:
                        response_text = self._add_citations_to_response(response_text, prompt_data["citations"])
                        logger.debug(f"Citations added, new length: {len(response_text)}")
                    except Exception as citation_error:
                        logger.error(f"Error adding citations: {str(citation_error)}")
                        # Continue without citations rather than failing
                
                logger.info(f"Final processed response length: {len(response_text)} characters")
                return response_text
            except Exception as process_error:
                logger.error(f"Error processing LLM response: {str(process_error)}")
                logger.error(traceback.format_exc())
                return f"I apologize, but I am unable to generate a response at this time due to a system error: {str(process_error)}"
                
        except Exception as e:
            logger.error(f"Unexpected error in _generate_response: {str(e)}")
            logger.error(traceback.format_exc())
            return f"I apologize, but I am unable to generate a response at this time due to a system error: {str(e)}"
    
    def _prepare_prompt_data(self, original_query: str, query_results: List[Dict[str, Any]] = None, 
                           assessment: str = "no_results", citations: List[Dict[str, Any]] = None,
                           countries: List[str] = None, dates: List[str] = None,
                           dengue_data: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """
        Prepare the data dictionary to be passed to the prompt template.
        
        Args:
            original_query: The original user query
            query_results: List of query results from the graph database
            assessment: Assessment string (e.g., "no_results", "has_results")
            citations: List of citation dictionaries
            countries: List of identified countries
            dates: List of extracted dates
            dengue_data: Dictionary of dengue data if retrieved
            **kwargs: Additional keyword arguments
            
        Returns:
            Dictionary containing all data needed for the prompt template
        """
        # Create base data dictionary
        data = {
            "query": original_query,
            "cypher_query": kwargs.get("cypher_query", ""),
            "query_results": query_results or [],
            "assessment": assessment,
            "citations": citations or [],
            "has_results": query_results is not None and len(query_results) > 0,
            "result_count": len(query_results) if query_results else 0,
            
            # Country and date information
            "countries": countries or [],
            "has_country_data": bool(countries),
            "dates": dates or [],
            "has_date_data": bool(dates),
            
            # Dengue data information
            "has_dengue_data": dengue_data is not None,
        }
        
        # Add dengue data details if available
        if dengue_data:
            data["dengue_data"] = {
                "country": dengue_data.get("requested_country", "Unknown"),
                "api_country": dengue_data.get("mapped_country", "Unknown"),
                "has_predictions": "predicted_data" in dengue_data and dengue_data["predicted_data"],
                "historical_data_points": len(dengue_data.get("historical_data", dengue_data.get("data", []))),
                "predicted_data_points": len(dengue_data.get("predicted_data", [])),
            }
        
        # Add additional parameters from kwargs
        for key, value in kwargs.items():
            if key not in data:
                data[key] = value
        
        return data
