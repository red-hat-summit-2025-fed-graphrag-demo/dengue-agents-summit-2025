"""
Simple Query Writer Agent

This agent uses prescriptive patterns with verified data to generate Cypher queries.
Only uses relationship patterns that are confirmed to exist in the knowledge graph.

IMPORTANT IMPLEMENTATION NOTE:
------------------------------
This agent MUST use the SchemaTool for ALL interactions with the knowledge graph schema.
DO NOT attempt to:
1. Access the Neo4j database directly via bolt:// protocols
2. Create new connections to the database
3. Bypass the SchemaTool abstraction layer
4. Add direct API calls to the knowledge graph endpoints

The SchemaTool handles:
- API endpoint configuration
- Schema retrieval and caching
- Error handling
- Data validation

Example usage:
```python
# CORRECT: Initialize the SchemaTool with optional API URL override
self.schema_tool = SchemaTool(api_url=self.kg_api_url)

# CORRECT: Get schema information through the tool
schema = await self.schema_tool.get_schema()
```
"""
import logging
import re
import asyncio
from typing import Any, Dict, List, Optional, Tuple, Set

from src.agent_system.core.base_agent import BaseAgent
from src.agent_system.core.message import Message, MessageRole
from src.agent_system.core.metadata import QueryMetadata, MetadataKeys
from src.tools.schema_tool import SchemaTool
from src.tools.extract_dates_from_natural_language_tool import ExtractDatesFromNaturalLanguageTool
from src.tools.dengue_data_tool import DengueDataTool

logger = logging.getLogger(__name__)

class SimpleQueryWriterAgent(BaseAgent):
    """
    A specialized agent for generating Cypher queries based on prescriptive patterns.
    
    This agent only uses relationship patterns that are confirmed to have data in the 
    knowledge graph, avoiding queries that return empty results.
    
    Enhanced with the ability to extract dates and countries from user queries,
    and retrieve relevant dengue fever data for visualization.
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], **kwargs):
        """
        Initialize the SimpleQueryWriterAgent.
        
        Args:
            agent_id: The unique identifier for this agent
            config: The agent configuration dictionary
            **kwargs: Additional keyword arguments
        """
        # Make sure agent_id is in the config
        if "agent_id" not in config:
            config["agent_id"] = agent_id
            
        super().__init__(config, **kwargs)
        
        # Get API URL from config or environment
        self.kg_api_url = config.get("kg_api_url", None)
        
        # Initialize the tools
        self.schema_tool = SchemaTool(api_url=self.kg_api_url)
        self.date_tool = ExtractDatesFromNaturalLanguageTool()
        self.dengue_data_tool = DengueDataTool()
        
        # Known valid relationship patterns
        self.valid_patterns = [
            {
                "name": "disease_symptoms",
                "pattern": "(d:Disease {name: 'Dengue Fever'})-[:HAS_SYMPTOM]->(s:Symptom)",
                "return_clause": "s.name as symptom, s.description as description"
            },
            {
                "name": "disease_warning_signs",
                "pattern": "(d:Disease {name: 'Dengue Fever'})-[:HAS_WARNING_SIGN]->(w:WarningSign)",
                "return_clause": "w.name as warning_sign, w.description as description"
            },
            {
                "name": "disease_vectors",
                "pattern": "(v:Vector)-[:TRANSMITS]->(d:Disease {name: 'Dengue Fever'})",
                "return_clause": "v.name as vector, v.description as description"
            },
            {
                "name": "disease_prevention",
                "pattern": "(p:PreventionMeasure)-[:PREVENTS]->(d:Disease {name: 'Dengue Fever'})",
                "return_clause": "p.name as prevention_measure, p.description as description"
            },
            {
                "name": "disease_diagnostic_tests",
                "pattern": "(d:Disease {name: 'Dengue Fever'})-[:DIAGNOSED_BY]->(t:DiagnosticTest)",
                "return_clause": "t.name as test, t.description as description"
            },
            {
                "name": "disease_treatment",
                "pattern": "(t:TreatmentProtocol)-[:RECOMMENDED_FOR]->(d:Disease {name: 'Dengue Fever'})",
                "return_clause": "t.name as treatment, t.description as description"
            },
            {
                "name": "disease_endemic_regions",
                "pattern": "(r:Region)-[:HAS_ENDEMIC_DISEASE]->(d:Disease {name: 'Dengue Fever'})",
                "return_clause": "r.name as region, r.description as description"
            },
            {
                "name": "disease_prevention_alternative",
                "pattern": "(d:Disease {name: 'Dengue Fever'})-[:PREVENTED_BY]->(p:PreventionMeasure)",
                "return_clause": "p.name as prevention_measure, p.description as description"
            },
            {
                "name": "disease_treatment_alternative",
                "pattern": "(d:Disease {name: 'Dengue Fever'})-[:TREATED_WITH]->(t:TreatmentProtocol)",
                "return_clause": "t.name as treatment, t.description as description"
            },
            {
                "name": "disease_comprehensive",
                "pattern": "(d:Disease {name: 'Dengue Fever'}) OPTIONAL MATCH (d)-[:PREVENTED_BY]->(p:PreventionMeasure) OPTIONAL MATCH (d)-[:TREATED_WITH]->(t:TreatmentProtocol) OPTIONAL MATCH (v:Vector)-[:TRANSMITS]->(d)",
                "return_clause": "d.name as disease, d.description as description, d.pathogen as pathogen, d.transmission as transmission, collect(distinct p.name) as prevention_measures, collect(distinct p.description) as prevention_descriptions, collect(distinct t.name) as treatments, collect(distinct t.description) as treatment_descriptions, collect(distinct v.name) as vectors, collect(distinct v.description) as vector_descriptions"
            }
        ]
        
        # Map of question types to patterns
        self.question_patterns = {
            r'symptom': 'disease_symptoms',
            r'sign': 'disease_warning_signs',
            r'vector': 'disease_vectors',
            r'mosquito': 'disease_vectors',
            r'prevent': 'disease_prevention_alternative',
            r'protect': 'disease_prevention_alternative',
            r'avoid': 'disease_prevention_alternative',
            r'test': 'disease_diagnostic_tests',
            r'diagnos': 'disease_diagnostic_tests',
            r'treat': 'disease_treatment_alternative',
            r'manag': 'disease_treatment_alternative',
            r'medic': 'disease_treatment_alternative',
            r'region': 'disease_endemic_regions',
            r'country': 'disease_endemic_regions',
            r'where': 'disease_endemic_regions',
            r'what should i tell': 'disease_comprehensive',
            r'advice': 'disease_comprehensive',
            r'recommend': 'disease_comprehensive',
            r'inform': 'disease_comprehensive',
            r'tell': 'disease_comprehensive'
        }
    
    async def _stream_thinking_hook(self, stream_callback: Any):
        """Optional hook called by BaseAgent.process to stream initial thoughts."""
        await self.stream_thinking(
            thinking=f"Identifying query pattern based on input...",
            stream_callback=stream_callback
        )
    
    async def _execute_processing(
        self, 
        message: Message, 
        session_id: Optional[str] = None
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Core processing logic for the SimpleQueryWriterAgent.
        
        Args:
            message: The input message to process
            session_id: Optional session identifier
            
        Returns:
            Tuple of (response_message, next_agent_id)
        """
        # Get the user query from the message
        user_query = message.content.strip()
        
        # Stream processing updates
        if self.current_stream_callback:
            await self.stream_thinking(
                thinking=f"Analyzing query: '{user_query}'",
                stream_callback=self.current_stream_callback
            )
            
        # Extract dates and countries from the user query
        date_data, countries = await self._extract_dates_and_countries(user_query)
        
        # Check if we have both dates and countries to fetch dengue data
        dengue_data = None
        has_visualization_data = False
        
        if countries and date_data and date_data.get("has_future_date"):
            if self.current_stream_callback:
                await self.stream_thinking(
                    thinking=f"Detected dates and countries. Fetching dengue data for {countries}",
                    stream_callback=self.current_stream_callback
                )
            
            # Get the latest future date for prediction
            future_dates = [d for d in date_data.get("dates", []) if d.get("is_future", False)]
            end_date = max(future_dates, key=lambda d: d["date"], default=None)
            
            # Get dengue data for the first country
            country = countries[0]
            try:
                dengue_data = await self.dengue_data_tool.get_predictions(
                    country=country,
                    end_date=end_date["date"] if end_date else None
                )
                has_visualization_data = True
                
                if self.current_stream_callback:
                    await self.stream_thinking(
                        thinking=f"Successfully retrieved dengue data for {country}",
                        stream_callback=self.current_stream_callback
                    )
            except Exception as e:
                logger.error(f"Error fetching dengue data: {str(e)}")
                if self.current_stream_callback:
                    await self.stream_thinking(
                        thinking=f"Error retrieving dengue data: {str(e)}",
                        stream_callback=self.current_stream_callback
                    )
        
        # Determine the appropriate query pattern based on the question
        pattern_name = self._identify_pattern(user_query)
        
        if pattern_name:
            # Found a pattern, generate the Cypher query
            pattern_info = next(p for p in self.valid_patterns if p["name"] == pattern_name)
            cypher_query = f"MATCH {pattern_info['pattern']} RETURN {pattern_info['return_clause']}"
            
            if self.current_stream_callback:
                await self.stream_thinking(
                    thinking=f"Selected pattern: {pattern_name}\nGenerated Cypher query: {cypher_query}",
                    stream_callback=self.current_stream_callback
                )
            
            # Create a response message with standardized metadata using QueryMetadata
            metadata = QueryMetadata.create_query_metadata(
                query=cypher_query,
                original_query=user_query,
                query_type="cypher",
                pattern_name=pattern_name
            )
            
            # Add visualization data if available
            if has_visualization_data and dengue_data:
                metadata["has_visualization_data"] = True
                metadata["visualization_data"] = dengue_data
                metadata["extracted_countries"] = countries
                metadata["extracted_dates"] = date_data
            
            # Set content to the query to make it easily accessible to the next agent
            response_message = Message(
                role=MessageRole.ASSISTANT,
                content=cypher_query,
                metadata=metadata
            )
            
            # Return the message and route to the query executor agent
            return response_message, "graph_query_executor_agent"
        else:
            # First try using the comprehensive pattern for prevention and treatment
            if "prevention" in user_query.lower() or "treatment" in user_query.lower() or "how to" in user_query.lower():
                # Try the comprehensive pattern for prevention and treatment
                comprehensive_pattern = next(p for p in self.valid_patterns if p["name"] == "disease_comprehensive")
                fallback_query = f"MATCH {comprehensive_pattern['pattern']} RETURN {comprehensive_pattern['return_clause']}"
                pattern_name = "disease_comprehensive"
                
                if self.current_stream_callback:
                    await self.stream_thinking(
                        thinking=f"No specific pattern matched. Using comprehensive prevention and treatment query.\n"
                                 f"Generated Cypher query: {fallback_query}",
                        stream_callback=self.current_stream_callback
                    )
            else:
                # No matching pattern, provide a detailed fallback query with citations
                fallback_query = """
                MATCH (d:Disease {name: "Dengue Fever"})
                OPTIONAL MATCH (v:Vector)-[r:TRANSMITS]->(d)
                OPTIONAL MATCH (d)-[hs:HAS_SOURCE]->(c:Citation)
                OPTIONAL MATCH (v)-[vs:HAS_SOURCE]->(vc:Citation)
                RETURN d.name as disease, d.description as description, 
                       d.pathogen as pathogen, d.transmission as transmission, 
                       v.name as vector, v.description as vector_description,
                       c.title as disease_citation_title, c.url as disease_citation_url,
                       vc.title as vector_citation_title, vc.url as vector_citation_url
                """
                pattern_name = "fallback_comprehensive"
                
                if self.current_stream_callback:
                    await self.stream_thinking(
                        thinking=f"No specific pattern matched. Using general fallback query with citation information.\n"
                                 f"Generated Cypher query: {fallback_query}",
                        stream_callback=self.current_stream_callback
                    )
            
            # Streaming was already handled in the if/else block above
            
            # Create a response message with standardized metadata using QueryMetadata
            metadata = QueryMetadata.create_query_metadata(
                query=fallback_query,
                original_query=user_query,
                query_type="cypher",
                pattern_name=pattern_name,
                is_default_query=True
            )
            
            # Add visualization data if available
            if has_visualization_data and dengue_data:
                metadata["has_visualization_data"] = True
                metadata["visualization_data"] = dengue_data
                metadata["extracted_countries"] = countries
                metadata["extracted_dates"] = date_data
            
            # Set content to the query to make it easily accessible to the next agent
            response_message = Message(
                role=MessageRole.ASSISTANT,
                content=fallback_query,
                metadata=metadata
            )
            
            return response_message, "graph_query_executor_agent"
    
    async def _extract_dates_and_countries(self, query: str) -> Tuple[Dict[str, Any], List[str]]:
        """
        Extract dates and countries from a natural language query.
        
        Args:
            query: The user query to analyze
            
        Returns:
            Tuple of (date_data, countries) where:
            - date_data is a dictionary with date extraction results
            - countries is a list of country names found in the query
        """
        # Extract dates from the query
        try:
            date_result = await self.date_tool._execute({"text": query})
            date_data = date_result.get("result", {})
        except Exception as e:
            logger.error(f"Error extracting dates: {str(e)}")
            date_data = {"has_future_date": False, "dates": []}
        
        # Extract countries from the query using DengueDataTool's country mappings
        countries = []
        country_mapping = self.dengue_data_tool.country_mapping
        
        # Convert query to lowercase and split into words
        query_lower = query.lower()
        
        # Check for each country in the mapping
        for country_name in country_mapping.keys():
            # Add word boundaries to find exact country names
            if re.search(r'\b' + re.escape(country_name) + r'\b', query_lower):
                mapped_country = country_mapping[country_name]
                if mapped_country not in countries:
                    countries.append(mapped_country)
        
        return date_data, countries
    
    def _identify_pattern(self, query: str) -> Optional[str]:
        """
        Identify which query pattern to use based on the user's question.
        
        Args:
            query: The user query
            
        Returns:
            The name of the pattern to use, or None if no matching pattern
        """
        # Convert query to lowercase for matching
        query_lower = query.lower()
        
        # Check for combined prevention and treatment queries first
        if (('prevent' in query_lower or 'protect' in query_lower) and 
            ('treat' in query_lower or 'manag' in query_lower or 'medic' in query_lower)) or \
           ('what should' in query_lower and 'tell' in query_lower) or \
           ('advice' in query_lower and 'dengue' in query_lower):
            return 'disease_comprehensive'
            
        # Check for traveling context with dengue - likely needs comprehensive info
        if ('travel' in query_lower or 'trip' in query_lower) and 'dengue' in query_lower:
            return 'disease_comprehensive'
        
        # Check for patterns with specific relationship directions
        # First check if prevention is mentioned
        if 'prevent' in query_lower or 'protect' in query_lower or 'avoid' in query_lower:
            # Try the alternative prevention relationship direction first
            return 'disease_prevention_alternative'
            
        # Similarly for treatment
        if 'treat' in query_lower or 'manag' in query_lower or 'medic' in query_lower or 'cure' in query_lower:
            return 'disease_treatment_alternative'
        
        # Check for each other pattern keyword
        for keyword, pattern_name in self.question_patterns.items():
            if re.search(keyword, query_lower):
                return pattern_name
        
        # Default to None if no pattern matches
        return None
