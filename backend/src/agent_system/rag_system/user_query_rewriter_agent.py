"""
User Query Rewriter Agent

This agent reformulates user queries to make them more effective for retrieval.
It considers the knowledge graph schema to ensure rewrites are aligned with available data.

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

import os
import re
import json
import logging
import traceback
from typing import Dict, List, Any, Optional, Tuple, Union

from src.agent_system.core.base_agent import BaseAgent
from src.agent_system.core.message import Message, MessageRole
from src.agent_system.core.metadata import BaseMetadata, MetadataKeys
from src.registries.prompt_registry import PromptRegistry
from src.tools.schema_tool import SchemaTool

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserQueryRewriterAgent(BaseAgent):
    """
    Agent to rewrite user queries for more effective graph database interaction.
    
    This agent:
    1. Analyzes the user's original query
    2. Fetches the schema of the graph database
    3. Rewrites the query to make it more aligned with the graph structure
    4. Returns both the rewritten query and the original query
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], **kwargs):
        """
        Initialize the user query rewriter agent.
        
        Args:
            agent_id: The unique identifier for this agent
            config: Agent configuration dictionary
            **kwargs: Additional keyword arguments
        """
        # Make sure agent_id is in the config
        if "agent_id" not in config:
            config["agent_id"] = agent_id
        
        super().__init__(config, **kwargs)
        
        # Get API URL from config or environment
        api_url = config.get("graph_api_url", None)
        self.schema_tool = SchemaTool(api_url=api_url)
        self.prompt_registry = PromptRegistry()
        logger.info(f"UserQueryRewriterAgent initialized with ID: {agent_id}")
    
    async def _execute_processing(self, message: Message, session_id: Optional[str] = None) -> Tuple[Optional[Message], Optional[str]]:
        """
        Process a message by rewriting the user query.
        
        Args:
            message: The input message containing the user's query
            session_id: Optional session identifier for multi-turn conversations
        
        Returns:
            Tuple containing (response_message, next_agent_id)
        """
        logger.info("Starting to process user query for rewriting")
        
        # Extract the user query from the message
        user_query = message.content
        
        if not user_query or not isinstance(user_query, str):
            logger.warning("Invalid user query received")
            return Message(content="Invalid query received. Please provide a valid text query."), None
        
        try:
            # Get the graph database schema
            try:
                logger.info("Retrieving schema from graph database...")
                schema = await self.schema_tool.get_schema()
                logger.info(f"Retrieved schema with {len(schema.get('nodeLabels', []))} node labels and "
                          f"{len(schema.get('relationshipTypes', []))} relationship types")
            except Exception as e:
                logger.error(f"Error retrieving schema: {str(e)}\n{traceback.format_exc()}")
                # Create a minimal schema instead of failing
                schema = {
                    "nodeLabels": ["Disease", "Symptom", "Country", "Treatment", "Prevention"],
                    "relationshipTypes": ["HAS_SYMPTOM", "IS_LOCATED_IN", "HAS_TREATMENT", "RECOMMENDS_PREVENTION"],
                    "propertyKeys": ["name", "description", "severity", "region", "effectiveness"]
                }
                logger.info("Using fallback schema data due to schema retrieval error")
            
            # Get additional information about node properties if available
            try:
                node_properties = await self.schema_tool.get_node_properties()
                logger.info(f"Retrieved properties for {len(node_properties)} node types")
                # Add node properties to the schema
                schema["nodeProperties"] = node_properties
            except Exception as e:
                logger.error(f"Error retrieving node properties: {str(e)}")
                schema["nodeProperties"] = {}
            
            # Get additional information about relationship properties if available
            try:
                relationship_properties = await self.schema_tool.get_relationship_properties()
                logger.info(f"Retrieved properties for {len(relationship_properties)} relationship types")
                # Add relationship properties to the schema
                schema["relationshipProperties"] = relationship_properties
            except Exception as e:
                logger.error(f"Error retrieving relationship properties: {str(e)}")
                schema["relationshipProperties"] = {}
                
            # Format schema for the prompt
            formatted_schema = self._format_schema_for_prompt(schema)
            
            # Create the prompt by combining the template with variables
            try:
                logger.info("Loading prompt template...")
                prompt_template = self.prompt_registry.get_prompt("rag_system.user_query_rewriter")
                logger.info("Prompt template loaded successfully")
                
                # Check if prompt_template is a string or an object with render method
                if hasattr(prompt_template, 'render'):
                    # It's a template object, use render method
                    prompt = prompt_template.render(
                        user_query=user_query,
                        schema=formatted_schema
                    )
                else:
                    # It's a string, manually replace placeholders
                    prompt = str(prompt_template)
                    prompt = prompt.replace("{{user_query}}", user_query)
                    prompt = prompt.replace("{{schema}}", formatted_schema)
                
                logger.info("Prompt prepared successfully")
            except Exception as e:
                logger.error(f"Error preparing prompt: {str(e)}\n{traceback.format_exc()}")
                return Message(
                    role=MessageRole.ASSISTANT,
                    content=user_query,
                    metadata={"original_query": user_query, "error": f"Error preparing prompt: {str(e)}"}
                ), None
            
            # Generate the rewritten query using the LLM
            try:
                logger.info("Calling LLM to generate rewritten query...")
                messages = [
                    Message(role=MessageRole.SYSTEM, content=prompt),
                    Message(role=MessageRole.USER, content=user_query)
                ]
                llm_response = await self.call_llm(messages)
                llm_response = llm_response[0] if isinstance(llm_response, tuple) and llm_response else ""
                logger.info(f"LLM response received, length: {len(llm_response)}")
            except Exception as e:
                logger.error(f"Error calling LLM: {str(e)}\n{traceback.format_exc()}")
                # Create error metadata with standardized methods
                error_metadata = BaseMetadata.create_metadata(
                    **{
                        MetadataKeys.ORIGINAL_QUERY.value: user_query,
                        MetadataKeys.ERROR.value: f"Error calling LLM: {str(e)}"
                    }
                )
                
                return Message(
                    role=MessageRole.ASSISTANT,
                    content=user_query,
                    metadata=error_metadata
                ), None
            
            # Extract the rewritten query from the LLM response
            rewritten_query = self._extract_rewritten_query(llm_response, user_query)
            logger.info(f"Extracted rewritten query: {rewritten_query[:100]}...")
            
            # Create schema summary for metadata
            schema_summary = self._create_schema_summary(schema)
            
            # Create result message with standardized metadata
            result_metadata = BaseMetadata.create_metadata(
                **{
                    MetadataKeys.ORIGINAL_QUERY.value: user_query,
                    MetadataKeys.REWRITTEN_QUERY.value: rewritten_query,
                    "schema_summary": schema_summary
                }
            )
            
            # Create result message with metadata
            result_message = Message(
                role=MessageRole.ASSISTANT,
                content=rewritten_query,
                metadata=result_metadata
            )
            
            logger.info(f"Query rewriting complete. Original: '{user_query[:50]}...' → Rewritten: '{rewritten_query[:50]}...'")
            return result_message, None
            
        except Exception as e:
            logger.error(f"Unexpected error in query rewriter: {str(e)}\n{traceback.format_exc()}")
            
            # Create standardized error metadata
            error_metadata = BaseMetadata.create_metadata(
                **{
                    MetadataKeys.ORIGINAL_QUERY.value: user_query, 
                    MetadataKeys.ERROR.value: f"Unexpected error in query rewriter: {str(e)}"
                }
            )
            
            # Return the original query if there's an error, but include error in metadata
            return Message(
                role=MessageRole.ASSISTANT,
                content=user_query,
                metadata=error_metadata
            ), None
    
    def _format_schema_for_prompt(self, schema: Dict[str, Any]) -> str:
        """
        Format the schema in a way that's useful for the LLM.
        
        Args:
            schema: The graph database schema
            
        Returns:
            A formatted string representation of the schema
        """
        try:
            schema_str = "Graph Database Schema:\n\n"
            
            # Add node labels
            schema_str += "Node Labels:\n"
            for label in schema.get("nodeLabels", []):
                schema_str += f"- {label}\n"
            
            # Add relationship types
            schema_str += "\nRelationship Types:\n"
            for rel_type in schema.get("relationshipTypes", []):
                schema_str += f"- {rel_type}\n"
            
            # Add node properties
            if "nodeProperties" in schema and schema["nodeProperties"]:
                schema_str += "\nNode Properties:\n"
                for node_type, properties in schema["nodeProperties"].items():
                    schema_str += f"- {node_type}: {', '.join(properties)}\n"
            
            # Add relationship properties
            if "relationshipProperties" in schema and schema["relationshipProperties"]:
                schema_str += "\nRelationship Properties:\n"
                for rel_type, properties in schema["relationshipProperties"].items():
                    schema_str += f"- {rel_type}: {', '.join(properties)}\n"
            
            return schema_str
        except Exception as e:
            logger.error(f"Error formatting schema: {str(e)}")
            # Return a simple version of the schema if there's an error
            return "Graph Database Schema: Dengue fever knowledge graph with disease, symptom, treatment, and location information"
    
    def _create_schema_summary(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a summary of the schema for debugging purposes.
        
        Args:
            schema: The graph database schema
            
        Returns:
            A dictionary with schema summary information
        """
        try:
            return {
                "node_label_count": len(schema.get("nodeLabels", [])),
                "relationship_type_count": len(schema.get("relationshipTypes", [])),
                "property_key_count": len(schema.get("propertyKeys", [])),
                "node_labels": schema.get("nodeLabels", [])[:10],  # First 10 labels
                "relationship_types": schema.get("relationshipTypes", [])[:10]  # First 10 rel types
            }
        except Exception as e:
            logger.error(f"Error creating schema summary: {str(e)}")
            return {"error": str(e)}
    
    def _extract_rewritten_query(self, llm_response: str, original_query: str) -> str:
        """
        Extract the rewritten query from the LLM response.
        
        Args:
            llm_response: The response from the LLM
            original_query: The original user query (fallback)
            
        Returns:
            The rewritten query
        """
        try:
            # First, look for a query wrapped in triple backticks
            backtick_pattern = r"```(?:query)?\s*(.*?)\s*```"
            backtick_matches = re.findall(backtick_pattern, llm_response, re.DOTALL)
            if backtick_matches:
                return backtick_matches[0].strip()
            
            # Then, look for "Rewritten Query:" or similar patterns
            rewritten_pattern = r"(?:Rewritten Query|REWRITTEN QUERY|New Query|ENHANCED QUERY):?\s*(.*?)(?:\n\n|\Z)"
            rewritten_matches = re.findall(rewritten_pattern, llm_response, re.DOTALL)
            if rewritten_matches:
                return rewritten_matches[0].strip()
            
            # If we can't find any patterns, just return the last paragraph
            paragraphs = llm_response.split("\n\n")
            if paragraphs:
                return paragraphs[-1].strip()
            
            # Fallback to the original query if we can't extract anything
            return original_query
        except Exception as e:
            logger.error(f"Error extracting rewritten query: {str(e)}")
            return original_query
