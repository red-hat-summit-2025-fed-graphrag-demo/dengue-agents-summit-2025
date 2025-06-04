"""
Graph Query Generator Agent

A specialized agent that generates Cypher queries for Neo4j graph databases
based on user questions about dengue fever. This agent replaces the traditional
vector retrieval mechanism with graph-based retrieval.

Query Writer Agent

This agent generates Cypher queries for the knowledge graph based on user questions.
It uses a two-step approach:
1. Select appropriate relationship patterns from the schema
2. Compose a Cypher query that follows the selected patterns

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
import json
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from src.agent_system.core.base_agent import BaseAgent
from src.agent_system.core.message import Message, MessageRole
from src.agent_system.core.metadata import BaseMetadata, MetadataKeys, QueryMetadata
from src.tools.schema_tool import SchemaTool
from src.registries.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)

class QueryWriterAgent(BaseAgent):
    """
    A specialized agent for generating graph database Cypher queries.
    
    This class implements the Graph Query Generator Agent functionality by:
    1. Taking a user query about dengue fever
    2. Retrieving the current Neo4j database schema
    3. Generating an appropriate Cypher query
    4. Formatting the query for execution by the Graph Query Executor Agent
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], **kwargs):
        """
        Initialize the QueryWriterAgent.
        
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
                "max_tokens": 1024,  # Sufficient for query generation
                "temperature": 0.2   # Lower temperature for more deterministic outputs
            }
        elif "model_type" not in config["model_config"]:
            config["model_config"]["model_type"] = "instruct"
            
        super().__init__(config, **kwargs)
        
        # Get a reference to the prompt registry
        self.prompt_registry = PromptRegistry()
        
        # Initialize the schema tool
        self.schema_tool = SchemaTool()
        
        # Extract prompt_id from config or use default
        self.prompt_id = config.get("prompt_id", "rag.graph_query_generator")
        
        # Schema refresh interval in seconds (default: 1 hour)
        self.schema_refresh_interval = config.get("schema_refresh_interval", 3600)
        
        # Cache for schema information
        self._schema_cache = None
        self._schema_cache_timestamp = 0
        
        logger.info(f"Initialized QueryWriterAgent with prompt_id: {self.prompt_id}")
    
    async def _retrieve_schema(self) -> Dict[str, Any]:
        """
        Retrieve the Neo4j database schema, using caching for efficiency.
        
        Returns:
            Dict containing the schema information
        """
        import time
        current_time = time.time()
        
        # Check if we have a cached schema that's still valid
        if (self._schema_cache is not None and 
            current_time - self._schema_cache_timestamp < self.schema_refresh_interval):
            logger.info("Using cached schema information")
            return self._schema_cache
            
        # Otherwise, retrieve fresh schema
        try:
            logger.info("Retrieving fresh schema information from database")
            schema = await self.schema_tool.get_schema()
            
            # Update cache
            self._schema_cache = schema
            self._schema_cache_timestamp = current_time
            
            return schema
        except Exception as e:
            logger.error(f"Error retrieving schema: {str(e)}")
            # Return empty schema on error
            return {
                "nodeLabels": [],
                "relationshipTypes": [],
                "propertyKeys": []
            }
    
    async def _stream_thinking_hook(self, stream_callback: Any):
        """Optional hook called by BaseAgent.process to stream initial thoughts."""
        await self.stream_thinking(
            thinking=f"Analyzing query to generate appropriate Cypher query for graph database...",
            stream_callback=stream_callback
        )
        
    async def _execute_processing(
        self, 
        message: Message, 
        session_id: Optional[str] = None
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Core processing logic for the QueryWriterAgent.
        
        Args:
            message: The input message containing the user's query
            session_id: Optional session identifier
            
        Returns:
            Tuple of (response_message, next_agent_id)
        """
        try:
            # Get the schema from the database
            schema_info = await self._get_schema_info()
            
            # Create the template selection prompt
            template_selection_prompt = self._create_template_selection_prompt(
                message.content, 
                self.get_query_templates()
            )
            
            # Call the LLM to select a template using BaseAgent's method
            template_selection_messages = [
                Message(role=MessageRole.SYSTEM, content=template_selection_prompt),
                message
            ]
            template_selection_response, _ = await self.call_llm(template_selection_messages)
            
            # Parse the template selection response
            template_data = self._parse_template_selection(template_selection_response)
            
            # Get the selected template name
            template_name = template_data.get("template_name", "").upper()
            
            # Find the selected template in the template list
            selected_template = None
            all_templates = self.get_query_templates()
            
            # Extract template from the template list
            template_start = all_templates.find(f"{template_name} template")
            if template_start >= 0:
                # Find the code block with the template
                template_code_start = all_templates.find("```", template_start)
                template_code_end = all_templates.find("```", template_code_start + 3)
                if template_code_start >= 0 and template_code_end >= 0:
                    selected_template = all_templates[template_code_start+3:template_code_end].strip()
            
            if not selected_template:
                logging.warning(f"Template '{template_name}' not found, using default query")
                # Use a simple default query if template not found
                selected_template = "MATCH (n:Disease {name: 'Dengue Fever'}) RETURN n LIMIT 5"

            # Step 2: LLM call to generate the final query with the selected template
            query_generation_prompt = self._create_query_generation_prompt(
                message.content,
                selected_template,
                schema_info["formatted_schema"],
                template_data
            )
            
            # Call the LLM to generate the final query using BaseAgent's method
            query_generation_messages = [
                Message(role=MessageRole.SYSTEM, content=query_generation_prompt),
                message
            ]
            query_generation_response, _ = await self.call_llm(query_generation_messages)
            
            # Parse the generated query
            query = self._parse_generated_query(query_generation_response)
            
            # Validate the query against the schema
            query = self._validate_query_against_schema(query, schema_info)
            
            # Create a response message with the generated query
            response_content = json.dumps({
                "query": query,
                "pattern_name": template_name,
                "reasoning": template_data.get("reasoning", "")
            }, indent=2)
            
            # Create standardized metadata using QueryMetadata
            metadata = QueryMetadata.create_query_metadata(
                query=query,
                query_type="cypher",
                original_query=message.content,
                pattern_name=template_name,
                **{
                    MetadataKeys.PROMPT_ID.value: self.prompt_id,
                    MetadataKeys.TIMESTAMP.value: self.get_timestamp()
                }
            )
            
            response_message = Message(
                role=MessageRole.ASSISTANT,
                content=response_content,
                metadata=metadata
            )
            
            return response_message, "next"
            
        except Exception as e:
            logging.error(f"Error in query generation: {str(e)}")
            # Return a default query as fallback
            fallback_query = "MATCH (n:Disease {name: 'Dengue Fever'}) RETURN n LIMIT 5"
            
            # Create standardized error metadata using QueryMetadata
            error_metadata = QueryMetadata.create_query_metadata(
                query=fallback_query,
                query_type="cypher",
                original_query=message.content,
                error=str(e),
                **{
                    MetadataKeys.PROMPT_ID.value: self.prompt_id,
                    MetadataKeys.TIMESTAMP.value: self.get_timestamp()
                }
            )
            
            response_message = Message(
                role=MessageRole.ASSISTANT,
                content=json.dumps({"error": str(e)}),
                metadata=error_metadata
            )
            return response_message, "next"
    
    def get_query_templates(self) -> str:
        """
        Define Cypher query templates for different types of questions.
        
        Returns:
            String containing query templates
        """
        # These templates help the LLM select an appropriate query structure
        templates = """
        1. SYMPTOMS template (For questions about dengue symptoms):
           ```
           MATCH (d:Disease {name: "Dengue Fever"})-[:HAS_SYMPTOM]->(s:Symptom)
           OPTIONAL MATCH (s)-[:HAS_SOURCE]->(c:Citation)
           RETURN s.name as symptom, s.description as description, 
                  collect(c.title) as sources, collect(c.url) as urls
           ```

        2. WARNING_SIGNS template (For questions about severe dengue warning signs):
           ```
           MATCH (d:Disease {name: "Dengue Fever"})-[:HAS_WARNING_SIGN]->(w:WarningSign)
           OPTIONAL MATCH (w)-[:HAS_SOURCE]->(c:Citation)
           RETURN w.name as warning_sign, w.description as description, 
                  collect(c.title) as sources, collect(c.url) as urls
           ```

        3. TREATMENT template (For questions about dengue treatment):
           ```
           MATCH (d:Disease {name: "Dengue Fever"})-[:HAS_TREATMENT]->(t:Treatment)
           OPTIONAL MATCH (t)-[:HAS_SOURCE]->(c:Citation)
           RETURN t.name as treatment, t.description as description, 
                  collect(c.title) as sources, collect(c.url) as urls
           ```

        4. REGIONS template (For questions about dengue regions):
           ```
           MATCH (d:Disease {name: "Dengue Fever"})-[:FOUND_IN]->(r:Region)
           OPTIONAL MATCH (r)-[:HAS_SOURCE]->(c:Citation)
           RETURN r.name as region, r.description as description, 
                  collect(c.title) as sources, collect(c.url) as urls
           ```

        5. DISEASE_INFO template (For general questions about dengue fever):
           ```
           MATCH (d:Disease {name: "Dengue Fever"})
           OPTIONAL MATCH (d)-[:HAS_SOURCE]->(c:Citation)
           RETURN d.name as disease, d.description as description, 
                  collect(c.title) as sources, collect(c.url) as urls
           ```
        """
        return templates
    
    def _create_template_selection_prompt(self, user_query: str, templates: str) -> str:
        """
        Create a prompt for template selection.
        
        Args:
            user_query: The user's question
            templates: The available query templates
            
        Returns:
            A formatted prompt for template selection
        """
        return f"""
        You are a specialized assistant for selecting the appropriate Cypher query template
        for Neo4j graph database queries about dengue fever.
        
        You will be given a user question and a list of available templates.
        Your task is to select the MOST APPROPRIATE template that addresses the user's question.
        
        ## Available Templates
        {templates}
        
        ## CRITICAL INSTRUCTIONS
        1. Select ONE template that best matches the user's question
        2. Extract any entities needed for the template parameters
        3. Provide a brief explanation of why you chose this template
        
        ## Response Format
        Respond with a JSON object containing:
        - "template_name": The selected template name (e.g., "SYMPTOMS", "TREATMENT", etc.)
        - "entities": A dictionary of extracted entities and their values
        - "reasoning": A brief explanation of why you chose this template
        
        Example response format:
        ```json
        {{
          "template_name": "REGIONS",
          "entities": {{
            "region_name": "Thailand"
          }},
          "reasoning": "The user asked about dengue in Thailand, which is best addressed by the REGIONS template."
        }}
        """
    
    def _create_query_generation_prompt(
        self, 
        user_query: str, 
        selected_template: str, 
        schema_info: str,
        template_data: Dict[str, Any]
    ) -> str:
        """
        Create a prompt for query generation with the selected template.
        
        Args:
            user_query: The user's question
            selected_template: The selected query template
            schema_info: The database schema information
            template_data: Data about the selected template
            
        Returns:
            A formatted prompt for query generation
        """
        entities = template_data.get("entities", {})
        entity_string = "\n".join([f"- {k}: {v}" for k, v in entities.items()])
        
        return f"""
        You are a specialized assistant for generating Cypher queries for a Neo4j graph database
        containing information about dengue fever.
        
        ## Your Task
        Generate a Cypher query based on the selected template and the user's question.
        
        ## User Question
        {user_query}
        
        ## Selected Template
        ```cypher
        {selected_template}
        ```
        
        ## Extracted Entities
        {entity_string if entity_string else "No specific entities extracted."}
        
        ## Database Schema
        {schema_info}
        
        ## CRITICAL INSTRUCTIONS
        1. Use the selected template as a starting point
        2. Modify it to incorporate any extracted entities and specific needs of the user's question
        3. Ensure you ONLY use node labels and relationship types that exist in the schema
        4. ALWAYS include citation nodes via HAS_SOURCE relationships where possible
        5. Return property values that would help answer the user's question
        
        ## Response Format
        Respond with ONLY the final Cypher query, nothing else.
        """
    
    def _parse_template_selection(self, response: str) -> Dict[str, Any]:
        """
        Parse the template selection response from the LLM.
        
        Args:
            response: The LLM response text
            
        Returns:
            Dictionary with template selection information
        """
        try:
            # Try to find and extract JSON from the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            
            # If no JSON found, look for template name mention
            template_match = re.search(r'template[_\s-]*name["\s:]*([A-Z_]+)', response, re.IGNORECASE)
            if template_match:
                return {
                    "template_name": template_match.group(1).strip(),
                    "entities": {},
                    "reasoning": "Extracted from non-JSON response"
                }
            
            # Default fallback
            return {
                "template_name": "DISEASE_INFO",
                "entities": {},
                "reasoning": "Default template selected - could not parse LLM response"
            }
            
        except json.JSONDecodeError:
            logging.warning(f"Failed to parse template selection response as JSON: {response}")
            return {
                "template_name": "DISEASE_INFO",
                "entities": {},
                "reasoning": "Default template selected - could not parse JSON"
            }
    
    def _parse_generated_query(self, response: str) -> str:
        """
        Parse the query generation response from the LLM.
        
        Args:
            response: The LLM response text
            
        Returns:
            The generated Cypher query
        """
        # Try to extract the Cypher query from code blocks
        code_block_match = re.search(r'```(?:cypher)?\s*(.*?)\s*```', response, re.DOTALL)
        if code_block_match:
            return code_block_match.group(1).strip()
        
        # If no code block, return the whole response (assuming it's just the query)
        return response.strip()
    
    def _validate_query_against_schema(self, query: str, schema_info: Dict[str, Any]) -> str:
        """
        Validate a Cypher query against the database schema and adjust if needed.
        
        Args:
            query: The Cypher query to validate
            schema_info: The database schema information
            
        Returns:
            Validated Cypher query
        """
        # Get node labels and relationship types from schema
        node_labels = set(schema_info.get("node_labels", schema_info.get("nodeLabels", [])))
        rel_types = set(schema_info.get("relationship_types", schema_info.get("relationshipTypes", [])))
        
        # Check if all labels and relationship types in the query exist in the schema
        # This is a simplified approach and might not catch all issues
        for label in node_labels:
            # If a non-existent label is used in the query, log a warning
            if f":{label}" in query and label not in node_labels:
                logging.warning(f"Node label '{label}' used in query but not found in schema")
                
        for rel_type in rel_types:
            # If a non-existent relationship type is used in the query, log a warning
            if f"[:{rel_type}]" in query and rel_type not in rel_types:
                logging.warning(f"Relationship type '{rel_type}' used in query but not found in schema")
                
        # Return the query as is for now
        # In a more advanced implementation, this could try to fix the query
        return query

    async def _get_schema_info(self) -> Dict[str, Any]:
        """
        Retrieve the current schema from the database and format it for use in prompts.
        
        Returns:
            Formatted schema information dictionary
        """
        # Get the raw schema information
        schema = await self._retrieve_schema()
        
        # Format the schema for inclusion in prompts
        formatted_schema = self._format_schema_for_prompt(schema)
        
        # Return both the raw schema and formatted schema
        schema["formatted_schema"] = formatted_schema
        return schema
        
    def _format_schema_for_prompt(self, schema: Dict[str, Any]) -> str:
        """
        Format the Neo4j schema for inclusion in the prompt.
        
        Args:
            schema: The schema information returned by SchemaTool
            
        Returns:
            Formatted schema string for the prompt
        """
        formatted = "NODE LABELS (Entity Types):\n"
        
        # Add node labels
        node_labels = schema.get("node_labels", schema.get("nodeLabels", []))
        if node_labels:
            formatted += "- " + "\n- ".join(node_labels) + "\n\n"
        else:
            formatted += "- No node labels found\n\n"
            
        # Add relationship types
        formatted += "RELATIONSHIP TYPES:\n"
        rel_types = schema.get("relationship_types", schema.get("relationshipTypes", []))
        if rel_types:
            formatted += "- " + "\n- ".join(rel_types) + "\n\n"
        else:
            formatted += "- No relationship types found\n\n"
            
        # Add properties (if available)
        node_props = schema.get("node_properties", {})
        if node_props:
            formatted += "NODE PROPERTIES:\n"
            for label, props in node_props.items():
                formatted += f"- {label}: {', '.join(props)}\n"
            formatted += "\n"
            
        rel_props = schema.get("relationship_properties", {})
        if rel_props:
            formatted += "RELATIONSHIP PROPERTIES:\n"
            for rel_type, props in rel_props.items():
                formatted += f"- {rel_type}: {', '.join(props)}\n"
                
        # Add note about including citations
        formatted += "\nIMPORTANT: When retrieving data, ALWAYS include any source information or citation nodes that may be connected to the main entities. This is needed to properly cite information sources in the final response."
                
        return formatted

    def get_timestamp(self) -> str:
        """
        Get a formatted timestamp for the current time.
        
        Returns:
            Formatted timestamp string
        """
        from datetime import datetime
        return datetime.now().isoformat()
