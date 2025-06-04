"""
Dengue Data Visualization Agent

A specialized agent for retrieving dengue data from the prediction service and 
generating visualizations to enhance responses with data-driven insights.

This agent:
1. Deterministically checks if countries mentioned in the query have available data
2. Retrieves dengue data from the prediction service using ONLY the DengueDataTool
3. Creates visualization data and formats it for response

IMPORTANT: This agent must NEVER make direct API calls to the dengue prediction service.
Always use the DengueDataTool for ALL interactions with the API. If functionality
is missing from the tool, modify the tool instead of working around it.
"""

import re
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union

from src.agent_system.core.base_agent import BaseAgent
from src.agent_system.core.message import Message, MessageRole
from src.agent_system.core.metadata import BaseMetadata, MetadataKeys, ResultMetadata
from src.tools.dengue_data_tool import DengueDataTool
from src.tools.extract_dates_from_natural_language_tool import ExtractDatesFromNaturalLanguageTool
from src.registries.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)

class DengueDataVisualizationAgent(BaseAgent):
    """A specialized agent for generating data-driven visualizations for dengue data.
    
    This agent enhances responses by:
    1. Identifying relevant countries in the query that have available data
    2. Retrieving historical and predicted dengue data via DengueDataTool
    3. Creating structured data that can be used to render visualizations
    
    IMPORTANT: This agent must NEVER make direct API calls to the dengue prediction service.
    Always use the DengueDataTool for ALL interactions with the API.
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], **kwargs):
        """
        Initialize the DengueDataVisualizationAgent.
        
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
                "max_tokens": 512,
                "temperature": 0.2
            }
        elif "model_type" not in config["model_config"]:
            config["model_config"]["model_type"] = "instruct"
            
        super().__init__(config, **kwargs)
        
        # Initialize the data tool - ALWAYS use this tool for API calls
        api_url = config.get("dengue_api_url", None)
        self.data_tool = DengueDataTool(api_url=api_url)
        
        # Initialize the date extraction tool
        self.date_tool = ExtractDatesFromNaturalLanguageTool({})
        
        # Get a reference to the prompt registry for any prompts we might need
        self.prompt_registry = PromptRegistry()
        
        # Available countries in the dataset based on the API response
        # This is the source of truth for which countries have actual data
        self.available_countries = ["australia", "new_caledonia", "saudi_arabia"]
        
        # Country mapping - key is how it might appear in text, value is API country name
        self.country_mapping = {
            # Direct matches
            "australia": "australia",
            "new caledonia": "new_caledonia",
            "new_caledonia": "new_caledonia",
            "saudi arabia": "saudi_arabia",
            "saudi_arabia": "saudi_arabia",
            
            # Common variations
            "aus": "australia",
            "aussie": "australia",
            "down under": "australia",
            "caledonia": "new_caledonia",
            "saudi": "saudi_arabia",
            "ksa": "saudi_arabia",
            "arabia": "saudi_arabia",
        }
        
        logger.info(f"Initialized DengueDataVisualizationAgent")
        logger.info(f"Available API countries: {self.available_countries}")
        logger.info(f"Country mapping: {self.country_mapping}")
        
    async def _execute_processing(
            self, 
            message: Message, 
            session_id: Optional[str] = None
        ) -> Tuple[Message, Optional[str]]:
        """
        Core processing logic for the DengueDataVisualizationAgent.
        
        Args:
            message: The input message to process
            session_id: Optional session identifier
            
        Returns:
            Tuple of (response_message, next_agent_id)
        """
        try:
            logger.info("=========== DENGUE DATA VISUALIZATION AGENT START ===========")
            
            # Extract the original query from the message using standard metadata method
            original_query = BaseMetadata.get(message.metadata, MetadataKeys.ORIGINAL_QUERY, message.content)
            
            logger.info(f"Processing dengue data visualization request for query: {original_query}")
            logger.info(f"Message metadata keys: {list(message.metadata.keys())}")
            
            try:
                # STEP 1: DETERMINISTICALLY IDENTIFY COUNTRIES IN THE QUERY
                # Extract all country mentions
                country_mentions = self._extract_country_mentions(original_query)
                logger.info(f"All country mentions in query: {country_mentions}")
                
                # STEP 2: DETERMINISTICALLY CHECK IF WE HAVE DATA FOR ANY MENTIONED COUNTRIES
                # Match mentioned countries to our available API countries
                available_data_countries = []
                mapped_api_countries = set()  # Keep track of countries we've already mapped
                
                for country in country_mentions:
                    try:
                        api_country = self._map_to_api_country(country)
                        if api_country:
                            logger.info(f"Successfully mapped '{country}' to API country '{api_country}'")
                            
                            # Only add if this API country wasn't already added
                            if api_country not in mapped_api_countries:
                                mapped_api_countries.add(api_country)
                                available_data_countries.append({
                                    "mentioned_country": country,
                                    "api_country": api_country
                                })
                                logger.info(f"Added '{api_country}' to available_data_countries")
                            else:
                                logger.info(f"Skipping duplicate API country '{api_country}' from mention '{country}'")
                        else:
                            logger.info(f"Country '{country}' could not be mapped to any API country")
                    except Exception as country_err:
                        logger.error(f"Error mapping country {country}: {str(country_err)}", exc_info=True)
                
                logger.info(f"Countries with available data: {available_data_countries}")
                
                # If no countries with available data were mentioned, return a clear "no data" response
                if not available_data_countries:
                    countries_text = ", ".join(country_mentions) if country_mentions else "the mentioned locations"
                    logger.info(f"No data available for requested countries: {countries_text}")
                    
                    return self._create_no_data_response(original_query, country_mentions), None
                    
                # If we have countries with data, continue processing
                logger.info(f"Found {len(available_data_countries)} countries with available data")
                
                # STEP 3: EXTRACT DATE INFORMATION USING THE DATE EXTRACTION TOOL
                # Use the date extraction tool to find any dates in the query
                try:
                    # Call the date extraction tool
                    date_result = await self.date_tool._execute({"text": original_query})
                    date_data = date_result["result"]
                    
                    # Extract date information
                    has_future_date = date_data.get("has_future_date", False)
                    dates = date_data.get("dates", [])
                    
                    # Log all extracted dates for debugging
                    logger.info(f"Date extraction found {len(dates)} dates:")
                    for date in dates:
                        logger.info(f"  - Date: {date.get('date')}, Type: {date.get('type')}, Future: {date.get('is_future')}, Match: '{date.get('match')}'")
                    
                    # Get the latest date if present (dates are already sorted chronologically)
                    iso_date = None
                    if dates and has_future_date:
                        # Find the latest future date
                        future_dates = [d for d in dates if d.get("is_future", False)]
                        if future_dates:
                            iso_date = future_dates[-1].get("date")
                            logger.info(f"Found future date for prediction: {iso_date}")
                    
                    logger.info(f"Date extraction results: has_future_date={has_future_date}, iso_date={iso_date}")
                    
                except Exception as date_err:
                    logger.error(f"Error extracting date information: {str(date_err)}", exc_info=True)
                    has_future_date, iso_date = False, None
                
                # STEP 4: FOR EACH COUNTRY WITH DATA, GET THE DATA USING THE TOOL
                result_data = {
                    "original_query": original_query,
                    "countries": [item["mentioned_country"] for item in available_data_countries],
                    "has_future_date": has_future_date,
                    "target_date": iso_date,
                    "countries_data": []
                }
                
                # For each identified country, get dengue data USING THE DATA TOOL ONLY
                for country_info in available_data_countries:
                    try:
                        mentioned_country = country_info["mentioned_country"]
                        api_country = country_info["api_country"]
                        
                        logger.info(f"Getting dengue data for {mentioned_country} using API country {api_country}")
                        
                        # IMPORTANT: ALWAYS use the data_tool for API interactions
                        try:
                            if has_future_date and iso_date:
                                # Make a single API call that includes both historical and prediction data
                                logger.info(f"Getting prediction data through {iso_date} for {api_country}")
                                visualization_data = await self.data_tool.get_dengue_data(
                                    country=api_country,
                                    time_period=iso_date
                                )
                            else:
                                # Just get historical data if no future date was mentioned
                                logger.info(f"Getting historical data only for {api_country}")
                                visualization_data = await self.data_tool.get_dengue_data(
                                    country=api_country
                                )
                        except Exception as api_err:
                            logger.error(f"Error calling data tool API: {str(api_err)}", exc_info=True)
                            continue
                        
                        # Check if we got data successfully
                        if "error" in visualization_data:
                            error_msg = visualization_data.get("error", "Unknown error")
                            logger.error(f"Error retrieving data for {mentioned_country}: {error_msg}")
                            continue
                        
                        # Add country-specific information
                        visualization_data["country"] = mentioned_country
                        visualization_data["api_country"] = api_country
                        
                        # Add to the results
                        result_data["countries_data"].append(visualization_data)
                        
                        logger.info(f"Successfully retrieved data for {mentioned_country}")
                        
                    except Exception as country_err:
                        logger.error(f"Error processing country {country_info}: {str(country_err)}", exc_info=True)
                
                # STEP 5: GENERATE RESPONSE WITH LLM ANALYSIS WHEN WE HAVE DATA
                if result_data["countries_data"]:
                    try:
                        # We have data, so generate an analysis using the LLM
                        analysis_response = await self._generate_dengue_data_analysis(result_data)
                        result_data["analysis"] = analysis_response
                    except Exception as analysis_err:
                        logger.error(f"Error generating analysis: {str(analysis_err)}", exc_info=True)
                        result_data["analysis"] = {
                            "text": "Unable to generate analysis due to an error.",
                            "insights": ["Data available but analysis generation failed."],
                            "recommendations": [
                                "Use insect repellent containing DEET, picaridin, or IR3535.",
                                "Wear long-sleeved shirts and long pants.",
                                "Stay in accommodations that are well-screened or air-conditioned.",
                                "Consult with a travel health specialist before your trip."
                            ]
                        }
                    
                    # Create metadata using the standard ResultMetadata approach
                    metadata = ResultMetadata.create_result_metadata(
                        results=result_data,
                        assessment="Successfully retrieved dengue data and generated analysis"
                    )
                    
                    # Add visualization-specific metadata using standard keys
                    BaseMetadata.update(metadata, **{
                        MetadataKeys.ORIGINAL_QUERY.value: original_query,
                        MetadataKeys.HAS_VISUALIZATION_DATA.value: True,
                        MetadataKeys.VISUALIZATION_DATA.value: result_data
                    })
                    
                    # Create the response message
                    response_message = Message(
                        role=MessageRole.ASSISTANT,
                        content="",  # Empty content as we're returning data via metadata
                        metadata=metadata
                    )
                    
                    logger.info("Successfully created response with visualization data")
                    logger.info(f"Response metadata keys: {list(metadata.keys())}")
                    logger.info("=========== DENGUE DATA VISUALIZATION AGENT END ===========")
                    
                    return response_message, "next"
                else:
                    # We couldn't get data for any of the countries
                    logger.info("No country data retrieved, returning no_data response")
                    logger.info("=========== DENGUE DATA VISUALIZATION AGENT END ===========")
                    return self._create_no_data_response(original_query, country_mentions), None
                    
            except Exception as processing_err:
                logger.error(f"Error in visualization agent processing: {str(processing_err)}", exc_info=True)
                # Create a fallback response using standard metadata classes
                metadata = ResultMetadata.create_result_metadata(
                    error=f"Error processing visualization request: {str(processing_err)}"
                )
                
                # Add visualization-related metadata
                BaseMetadata.update(metadata, **{
                    MetadataKeys.ORIGINAL_QUERY.value: original_query,
                    MetadataKeys.HAS_VISUALIZATION_DATA.value: False
                })
                
                fallback_message = Message(
                    role=MessageRole.ASSISTANT,
                    content="",  # Empty content
                    metadata=metadata
                )
                logger.info("Returning fallback message due to processing error")
                logger.info("=========== DENGUE DATA VISUALIZATION AGENT END ===========")
                return fallback_message, None
                
        except Exception as e:
            logger.error(f"Unexpected error in DengueDataVisualizationAgent: {str(e)}", exc_info=True)
            # Create error metadata using standard classes
            metadata = ResultMetadata.create_result_metadata(
                error=f"Unexpected error: {str(e)}"
            )
            
            return Message(
                role=MessageRole.ASSISTANT,
                content="",
                metadata=metadata
            ), None
    
    def _extract_country_mentions(self, text: str) -> List[str]:
        """
        Extract all country mentions from the text.
        This is a deterministic function that finds countries in the text.
        
        Args:
            text: The text to extract country mentions from
            
        Returns:
            A list of country mentions
        """
        # Simple country name extraction - look for any supported country in the text
        country_mentions = []
        text_lower = text.lower()
        
        # Check for exact matches and common variations
        for country_name in self.country_mapping.keys():
            # Look for the country name as a word boundary
            pattern = r'\b' + re.escape(country_name) + r'\b'
            if re.search(pattern, text_lower):
                country_mentions.append(country_name)
                logger.info(f"Found country mention: '{country_name}' in text")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_mentions = []
        for country in country_mentions:
            if country.lower() not in seen:
                seen.add(country.lower())
                unique_mentions.append(country)
        
        logger.info(f"Extracted unique country mentions: {unique_mentions}")
        return unique_mentions
    
    def _map_to_api_country(self, country: str) -> Optional[str]:
        """
        Map a country mention to an available API country.
        
        Args:
            country: The country mentioned in the query
            
        Returns:
            The corresponding API country name, or None if not available
        """
        country_lower = country.lower()
        
        # Debug the country matching process
        logger.info(f"DEBUG: _map_to_api_country called with country '{country}', lower: '{country_lower}'")
        logger.info(f"DEBUG: Available mapping keys: {list(self.country_mapping.keys())}")
        logger.info(f"DEBUG: Is 'saudi arabia' in mapping keys? {'saudi arabia' in self.country_mapping}")
        
        # Handle Saudi Arabia explicitly as a special case
        if country_lower == "saudi arabia" or country_lower == "saudi" or country_lower == "arabia":
            logger.info(f"DEBUG: Special case match for Saudi Arabia: '{country_lower}'")
            return "saudi_arabia"
            
        # Direct lookup in our mapping
        if country_lower in self.country_mapping:
            mapped = self.country_mapping[country_lower]
            logger.info(f"DEBUG: Direct match found: '{country_lower}' -> '{mapped}'")
            return mapped
            
        # Check for partial matches
        for key, value in self.country_mapping.items():
            if key in country_lower or country_lower in key:
                logger.info(f"DEBUG: Partial match found: '{country_lower}' ~ '{key}' -> '{value}'")
                return value
        
        # If all else fails, log the failure
        logger.error(f"DEBUG: No mapping found for country '{country}'")
        return None
    
    async def _generate_dengue_data_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an analysis of the dengue data using the LLM.
        
        Args:
            data: The dengue data to analyze
            
        Returns:
            A dictionary containing the analysis
        """
        # Get the dengue data visualization prompt from the registry
        prompt_id = "enhancement.dengue_data_visualization"
        prompt_text = self.prompt_registry.get_prompt(prompt_id)
        
        if not prompt_text:
            logger.error(f"Could not find prompt with ID: {prompt_id}")
            prompt_text = """
            You are a specialized agent for analyzing dengue fever data and generating insights.
            Analyze the provided dengue data and identify important trends, particularly for travelers.
            
            Focus on:
            1. Current dengue fever trends (increasing, decreasing, or stable)
            2. Expected dengue activity during any mentioned travel periods
            3. Specific recommendations based on the data
            
            Your analysis should prioritize relevant, actionable insights.
            """
        
        # Prepare data for the prompt
        countries_data = []
        for country_data in data["countries_data"]:
            countries_data.append({
                "country": country_data["country"],
                "historical_data": country_data["historical_data"][-5:] if "historical_data" in country_data else [],
                "predicted_data": country_data["predicted_data"] if "predicted_data" in country_data else [],
                "has_future_prediction": data["has_future_date"],
                "target_date": data["target_date"]
            })
        
        # Convert to JSON string for the prompt
        data_json = json.dumps(countries_data, indent=2)
        
        # Create the full prompt with data
        full_prompt = prompt_text + "\n\nQUERY:\n" + data["original_query"] + "\n\nDATA:\n" + data_json + "\n\nPlease provide your analysis:"
        
        try:
            # Create a list of Message objects as expected by BaseAgent.call_llm
            messages = [
                Message(
                    role=MessageRole.SYSTEM,
                    content=prompt_text
                ),
                Message(
                    role=MessageRole.USER,
                    content=f"Query: {data['original_query']}\n\nData:\n{data_json}\n\nPlease provide your analysis:"
                )
            ]
            
            # Call the LLM with the proper Message list format
            analysis_text, _ = await self.call_llm(messages)
            
            logger.info(f"Successfully generated analysis of length {len(analysis_text)}")
            
            # Parse the analysis text into structured form
            return {
                "text": analysis_text,
                "insights": self._extract_insights(analysis_text),
                "recommendations": self._extract_recommendations(analysis_text)
            }
        except Exception as e:
            logger.error(f"Error generating analysis: {str(e)}", exc_info=True)
            return {
                "text": "Unable to generate analysis due to an error.",
                "insights": ["Data available but analysis generation failed."],
                "recommendations": [
                    "Use insect repellent containing DEET, picaridin, or IR3535.",
                    "Wear long-sleeved shirts and long pants.",
                    "Stay in accommodations that are well-screened or air-conditioned.",
                    "Consult with a travel health specialist before your trip."
                ]
            }
    
    def _extract_insights(self, analysis_text: str) -> List[str]:
        """Extract insights from the analysis text."""
        insights = []
        insights_section = re.search(r'(?:Insights|Key Findings|Trends):(.*?)(?:\n\n|$)', analysis_text, re.DOTALL | re.IGNORECASE)
        
        if insights_section:
            section_text = insights_section.group(1).strip()
            # Split by bullet points or numbered items
            items = re.split(r'\n\s*[-•*]|\n\s*\d+\.', section_text)
            for item in items:
                if item.strip():
                    insights.append(item.strip())
        
        # If no structured insights found, create generic ones from the text
        if not insights:
            sentences = re.split(r'\.(?:\s+|\n)', analysis_text)
            insights = [s.strip() + '.' for s in sentences if len(s.strip()) > 20 and s.strip()][:3]
        
        return insights
    
    def _extract_recommendations(self, analysis_text: str) -> List[str]:
        """Extract recommendations from the analysis text."""
        recommendations = []
        recommendations_section = re.search(r'(?:Recommendations|Advice|Suggestions):(.*?)(?:\n\n|$)', analysis_text, re.DOTALL | re.IGNORECASE)
        
        if recommendations_section:
            section_text = recommendations_section.group(1).strip()
            # Split by bullet points or numbered items
            items = re.split(r'\n\s*[-•*]|\n\s*\d+\.', section_text)
            for item in items:
                if item.strip():
                    recommendations.append(item.strip())
        
        # If no structured recommendations found, provide generic ones
        if not recommendations:
            recommendations = [
                "Use insect repellent containing DEET, picaridin, or IR3535.",
                "Wear long-sleeved shirts and long pants.",
                "Stay in accommodations that are well-screened or air-conditioned.",
                "Consult with a travel health specialist before your trip."
            ]
        
        return recommendations
    
    def _create_no_data_response(self, original_query: str, country_mentions: List[str]) -> Message:
        """
        Create a response message for when no data is available.
        
        Args:
            original_query: The original query text
            country_mentions: List of countries mentioned in the query
            
        Returns:
            A Message object with the appropriate metadata
        """
        # Define country list for the message
        countries_text = ", ".join(country_mentions) if country_mentions else "any country"
        
        # Generate a helpful message about data availability
        content = (
            f"I don't have dengue data available for {countries_text}. "
            f"Currently, I only have data for Australia, New Caledonia, and Saudi Arabia. "
            f"Would you like information about dengue precautions for travelers in general?"
        )
        
        # Create metadata using the standard metadata classes
        metadata = ResultMetadata.create_result_metadata(
            results=None,
            assessment=f"No dengue data available for requested countries: {countries_text}",
            result_count=0
        )
        
        # Add visualization-related metadata
        BaseMetadata.update(metadata, **{
            MetadataKeys.ORIGINAL_QUERY.value: original_query,
            MetadataKeys.HAS_VISUALIZATION_DATA.value: False
        })
        
        # Create and return the message
        logger.info(f"Created no_data response for query: {original_query}")
        return Message(role=MessageRole.ASSISTANT, content=content, metadata=metadata)
