"""
ICL (In-Context Learning) Graph Query Writer Agent

This agent generates Cypher queries for the knowledge graph using in-context learning.
It uses examples to help an LLM translate natural language questions into Cypher.

It leverages prompts with examples to facilitate in-context learning,
which enables the LLM to better understand how to generate accurate Cypher queries.

This agent:
1. Retrieves the current database schema
2. Provides example queries and schema in a single prompt
3. Generates a Cypher query based on the user's question
4. Ensures the query follows best practices like including citation nodes

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

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Set
from datetime import datetime

from src.agent_system.core.base_agent import BaseAgent
from src.agent_system.core.message import Message, MessageRole
from src.agent_system.core.metadata import BaseMetadata, MetadataKeys, QueryMetadata
from src.tools.schema_tool import SchemaTool
from src.registries.prompt_registry import PromptRegistry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ICLGraphQueryWriterAgent(BaseAgent):
    """
    A specialized agent for generating Neo4j Cypher queries using in-context learning.
    
    This agent:
    1. Retrieves the current database schema
    2. Provides example queries and schema in a single prompt
    3. Generates a Cypher query based on the user's question
    4. Ensures the query follows best practices like including citation nodes
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], **kwargs):
        """
        Initialize the ICLGraphQueryWriterAgent.
        
        Args:
            agent_id: The unique identifier for this agent
            config: The agent configuration dictionary
            **kwargs: Additional keyword arguments
        """
        super().__init__(config, **kwargs)
        
        # Initialize the SchemaTool for retrieving Neo4j schema
        self.schema_tool = SchemaTool()
        
        # Initialize the prompt registry
        self.prompt_registry = PromptRegistry()
        
        # Get the prompt ID from config or use default
        self.prompt_id = config.get("prompt_id", "rag.icl_graph_query_generator")
        
        # Cache for schema to avoid repeated API calls
        self._schema_cache = None
        self._schema_cache_time = None
        self._schema_cache_ttl = 300  # 5 minutes
        
        logger.info(f"Initialized ICLGraphQueryWriterAgent with prompt_id: {self.prompt_id}")
        
    async def _execute_processing(
        self, 
        message: Message, 
        session_id: Optional[str] = None
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Core processing logic for the ICLGraphQueryWriterAgent.
        
        Args:
            message: The input message to process
            session_id: Optional session identifier
            
        Returns:
            Tuple of (response_message, next_agent_id)
        """
        try:
            # Get the current schema from the database
            schema = await self._retrieve_schema()
            
            # Format schema info for the prompt
            schema_info = self._format_schema_for_prompt(schema)
            
            # Get example queries based on the schema
            example_queries = self._get_example_queries(schema)
            
            # Get the query from the user's message
            user_query = message.content
            
            # Get the prompt from the registry
            system_prompt = self.prompt_registry.get_prompt(
                prompt_id=self.prompt_id,
                schema_info=schema_info,
                example_queries=example_queries,
                query=user_query
            )
                
            # Prepare messages for the LLM
            messages = [
                Message(role=MessageRole.SYSTEM, content=system_prompt),
                message  # The user's message
            ]
                
            # Call the LLM
            response_text, _ = await self.call_llm(messages)
            
            # Extract the Cypher query from the response
            cypher_query = self._extract_cypher_query(response_text)
            
            # If no valid query was extracted, use a fallback
            if not cypher_query:
                logging.warning("No valid Cypher query extracted from response, using fallback")
                cypher_query = "MATCH (n:Disease {name: 'Dengue Fever'}) RETURN n LIMIT 5"
            
            # Create a structured response with metadata
            response_data = {
                "query": cypher_query,
                "reasoning": self._extract_reasoning(response_text),
                "original_query": user_query
            }
            
            # Create standardized metadata using QueryMetadata
            metadata = QueryMetadata.create_query_metadata(
                query=cypher_query,
                query_type="cypher",
                original_query=user_query,
                **{
                    MetadataKeys.PROMPT_ID.value: self.prompt_id,
                    MetadataKeys.TIMESTAMP.value: self._get_timestamp()
                }
            )
            
            # Create the response message
            response_message = Message(
                role=MessageRole.ASSISTANT,
                content=json.dumps(response_data, indent=2),
                metadata=metadata
            )
            
            # Return the response
            return response_message, "next"
            
        except Exception as e:
            logging.error(f"Error in ICL query generation: {str(e)}")
            
            # Create a fallback response on error using standardized metadata
            fallback_query = "MATCH (n:Disease {name: 'Dengue Fever'}) RETURN n LIMIT 5"
            
            # Create standardized error metadata
            error_metadata = QueryMetadata.create_query_metadata(
                query=fallback_query,
                query_type="cypher",
                original_query=message.content,
                error=str(e),
                **{
                    MetadataKeys.PROMPT_ID.value: self.prompt_id,
                    MetadataKeys.TIMESTAMP.value: self._get_timestamp()
                }
            )
            
            # Create fallback response message
            response_message = Message(
                role=MessageRole.ASSISTANT,
                content=json.dumps({
                    "error": str(e),
                    "query": fallback_query,
                    "original_query": message.content
                }),
                metadata=error_metadata
            )
            
            return response_message, "next"
            
    async def process_with_feedback(
        self, 
        messages: List[Message], 
        valid_node_labels: Set[str],
        valid_rel_types: Set[str],
        session_id: Optional[str] = None
    ) -> Tuple[Optional[Message], str, bool, int]:
        """
        Process a conversation with multiple messages, including feedback.
        
        This method is designed to be used in a conversation loop where feedback
        on invalid queries can be provided.
        
        Args:
            messages: The list of messages in the conversation
            valid_node_labels: Set of valid node labels for validation
            valid_rel_types: Set of valid relationship types for validation
            session_id: Optional session identifier
            
        Returns:
            Tuple of (response_message, query, is_valid, attempt_count)
        """
        try:
            # Get the original query from the first message in the conversation
            original_query = messages[0].content
            
            # Get the current schema from the database
            schema = await self._retrieve_schema()
            
            # Format schema info for the prompt
            schema_info = self._format_schema_for_prompt(schema)
            
            # Get example queries based on the schema
            example_queries = self._get_example_queries(schema)
            
            # Increate the attempt counter based on conversation length
            # Every user message after the initial query counts as an attempt
            attempt_count = sum(1 for msg in messages if msg.role == MessageRole.USER) - 1
            if attempt_count < 0:
                attempt_count = 0
                
            # Get the ICL prompt with schema and examples
            system_prompt = self.prompt_registry.get_prompt(
                prompt_id=self.prompt_id,
                schema_info=schema_info,
                example_queries=example_queries,
                query=original_query,
                attempt=attempt_count + 1
            )
            
            # Prepare the base messages for the LLM with the system prompt
            llm_messages = [
                Message(role=MessageRole.SYSTEM, content=system_prompt)
            ]
            
            # Add all conversation messages
            llm_messages.extend(messages)
            
            # Call the LLM with the full conversation
            response_text, _ = await self.call_llm(llm_messages)
            
            # Extract the Cypher query from the response
            cypher_query = self._extract_cypher_query(response_text)
            
            # If no valid query was extracted, use a fallback
            is_valid = False
            if not cypher_query:
                logging.warning("No valid Cypher query extracted from response")
                cypher_query = "MATCH (n:Disease {name: 'Dengue Fever'}) RETURN n LIMIT 5"
            else:
                # Validate the extracted query (done externally in HybridQueryWriterAgent)
                pass
            
            # Create a structured response with metadata
            response_data = {
                "query": cypher_query,
                "reasoning": self._extract_reasoning(response_text),
                "original_query": original_query,
                "attempt": attempt_count
            }
            
            # Create standardized metadata using QueryMetadata
            metadata = QueryMetadata.create_query_metadata(
                query=cypher_query,
                query_type="cypher",
                original_query=original_query,
                **{
                    MetadataKeys.PROMPT_ID.value: self.prompt_id,
                    "attempt": attempt_count,
                    MetadataKeys.TIMESTAMP.value: self._get_timestamp()
                }
            )
            
            # Create the response message
            response_message = Message(
                role=MessageRole.ASSISTANT,
                content=json.dumps(response_data, indent=2),
                metadata=metadata
            )
            
            return response_message, cypher_query, is_valid, attempt_count
            
        except Exception as e:
            logging.error(f"Error in ICL query generation: {str(e)}")
            
            # Create a fallback response on error using standardized metadata
            fallback_query = "MATCH (n:Disease {name: 'Dengue Fever'}) RETURN n LIMIT 5"
            
            # Create standardized error metadata
            error_metadata = QueryMetadata.create_query_metadata(
                query=fallback_query,
                query_type="cypher",
                original_query="Error occurred",
                error=str(e),
                **{
                    MetadataKeys.PROMPT_ID.value: self.prompt_id,
                    "attempt": 0,
                    MetadataKeys.TIMESTAMP.value: self._get_timestamp()
                }
            )
            
            # Create fallback response message
            response_message = Message(
                role=MessageRole.ASSISTANT,
                content=json.dumps({
                    "error": str(e),
                    "query": fallback_query,
                    "original_query": "Error occurred"
                }),
                metadata=error_metadata
            )
            
            return response_message, fallback_query, False, 0
    
    async def _retrieve_schema(self) -> Dict[str, Any]:
        """
        Retrieve the schema from the Neo4j database, with caching.
        
        Returns:
            Dict containing the database schema
        """
        # Check if we have a valid cached schema
        current_time = datetime.now()
        if (self._schema_cache and self._schema_cache_time and 
            (current_time - self._schema_cache_time).total_seconds() < self._schema_cache_ttl):
            return self._schema_cache
            
        # If no valid cache, retrieve fresh schema
        logging.info("Retrieving fresh schema information from database")
        schema = await self.schema_tool.get_schema()
        
        # Update cache
        self._schema_cache = schema
        self._schema_cache_time = current_time
        
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
        
    def _get_example_queries(self, schema: Dict[str, Any]) -> str:
        """
        Generate example Cypher queries based on the schema.
        
        Args:
            schema: The Neo4j schema information
            
        Returns:
            String containing example queries
        """
        # Generate examples based on the schema entities
        node_labels = schema.get("node_labels", schema.get("nodeLabels", []))
        rel_types = schema.get("relationship_types", schema.get("relationshipTypes", []))
        
        # Build example queries
        examples = []
        
        # Always include a query for symptoms since it's common
        examples.append({
            "question": "What are the symptoms of dengue fever?",
            "query": """
MATCH (d:Disease {name: "Dengue Fever"})-[:HAS_SYMPTOM]->(s:Symptom)
OPTIONAL MATCH (s)-[:HAS_SOURCE]->(c:Citation)
RETURN s.name as symptom, s.description as description, 
       collect(c.title) as sources, collect(c.url) as urls
""".strip(),
            "explanation": "This query finds symptoms of Dengue Fever and includes citation sources"
        })
        
        # Include a transmission query if Vector exists
        if "Vector" in node_labels and "TRANSMITS" in rel_types:
            examples.append({
                "question": "How is dengue fever transmitted?",
                "query": """
MATCH (v:Vector)-[:TRANSMITS]->(d:Disease {name: "Dengue Fever"})
OPTIONAL MATCH (v)-[:HAS_SOURCE]->(c:Citation)
RETURN v.name as vector, v.description as description,
       collect(c.title) as sources, collect(c.url) as urls
""".strip(),
                "explanation": "This query finds vectors that transmit Dengue Fever with their citations"
            })
        
        # Include region query if Region exists
        if "Region" in node_labels:
            examples.append({
                "question": "Where is dengue fever most common?",
                "query": """
MATCH (r:Region)-[:HAS_ENDEMIC_DISEASE]->(d:Disease {name: "Dengue Fever"})
OPTIONAL MATCH (r)-[:HAS_SOURCE]->(c:Citation)
RETURN r.name as region, r.description as description,
       collect(c.title) as sources, collect(c.url) as urls
""".strip(),
                "explanation": "This query finds regions where Dengue Fever is endemic"
            })
        
        # Include prevention query if prevention entities exist
        if "PreventionMeasure" in node_labels:
            examples.append({
                "question": "How can I prevent dengue fever?",
                "query": """
MATCH (p:PreventionMeasure)-[:PREVENTS]->(d:Disease {name: "Dengue Fever"})
OPTIONAL MATCH (p)-[:HAS_SOURCE]->(c:Citation)
RETURN p.name as prevention_measure, p.description as description,
       collect(c.title) as sources, collect(c.url) as urls
""".strip(),
                "explanation": "This query finds prevention measures for Dengue Fever"
            })
        
        # Format the examples for inclusion in the prompt
        formatted_examples = ""
        for i, example in enumerate(examples):
            formatted_examples += f"Example {i+1}: {example['question']}\n"
            formatted_examples += "```cypher\n"
            formatted_examples += example['query'] + "\n"
            formatted_examples += "```\n"
            formatted_examples += f"Explanation: {example['explanation']}\n\n"
            
        return formatted_examples
    
    def _extract_cypher_query(self, response: str) -> str:
        """
        Extract a Cypher query from the LLM response.
        
        Args:
            response: The response text from the LLM
            
        Returns:
            The extracted Cypher query or empty string if none found
        """
        # Look for code blocks with Cypher queries
        code_block_match = re.search(r'```(?:cypher)?\s*(.*?)\s*```', response, re.DOTALL)
        if code_block_match:
            return code_block_match.group(1).strip()
            
        # Try to find a MATCH clause directly in the text
        match_clause_match = re.search(r'(MATCH\s+.*?RETURN.*?)', response, re.DOTALL)
        if match_clause_match:
            return match_clause_match.group(1).strip()
            
        # If neither approach works, return empty string
        return ""
    
    def _extract_reasoning(self, response: str) -> str:
        """
        Extract reasoning from the LLM response.
        
        Args:
            response: The response text from the LLM
            
        Returns:
            The extracted reasoning or a default message
        """
        # Look for a section labeled as reasoning
        reasoning_match = re.search(r'(?:Reason(?:ing)?|Explanation):\s*(.*?)(?:\n\n|\Z)', response, re.DOTALL | re.IGNORECASE)
        if reasoning_match:
            return reasoning_match.group(1).strip()
            
        # If no reasoning section found, return a default
        return "Query generated based on the user's question"
    
    def _get_timestamp(self) -> str:
        """
        Get a formatted timestamp for the current time.
        
        Returns:
            Formatted timestamp string
        """
        return datetime.now().isoformat()
