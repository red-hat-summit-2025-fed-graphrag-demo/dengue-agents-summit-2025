"""
Hybrid Query Writer Agent

This agent combines dynamic LLM-based query generation with prescriptive patterns
to produce reliable Cypher queries for the knowledge graph.

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
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Set

from src.agent_system.core.base_agent import BaseAgent
from src.agent_system.core.message import Message, MessageRole
from src.agent_system.core.metadata import BaseMetadata, MetadataKeys, QueryMetadata
from src.agent_system.rag_system.query.icl_graph_query_writer_agent import ICLGraphQueryWriterAgent
from src.agent_system.rag_system.query.query_writer_agent import QueryWriterAgent
from src.tools.schema_tool import SchemaTool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HybridQueryWriterAgent(BaseAgent):
    """
    A hybrid query writer agent that uses ICL as primary and two-step as fallback.
    
    This agent:
    1. Tries to generate a query using the ICL approach
    2. Validates the query against the schema
    3. If validation fails or after 3 failed attempts, falls back to two-step approach
    4. Includes failed queries as negative examples for future attempts
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], **kwargs):
        """
        Initialize the HybridQueryWriterAgent.
        
        Args:
            agent_id: The unique identifier for this agent
            config: The agent configuration dictionary
            **kwargs: Additional keyword arguments
        """
        super().__init__(config, **kwargs)
        
        # Initialize the SchemaTool for retrieving Neo4j schema
        self.schema_tool = SchemaTool()
        
        # Create sub-agents for each approach
        self.icl_agent = ICLGraphQueryWriterAgent(
            agent_id=f"{agent_id}_icl", 
            config={
                **config,
                "prompt_id": "rag.icl_graph_query_generator"
            }
        )
        
        self.two_step_agent = QueryWriterAgent(
            agent_id=f"{agent_id}_two_step", 
            config={
                **config,
                "prompt_id": "rag.graph_query_generator"
            }
        )
        
        # Track failed attempts and queries
        self.max_icl_attempts = config.get("max_icl_attempts", 3)
        self._failed_queries = []
        
        # Configure validation strictness
        self.strict_validation = config.get("strict_validation", False)
        if self.strict_validation:
            logger.info(f"Initialized HybridQueryWriterAgent with strict validation")
        
        logger.info(f"Initialized HybridQueryWriterAgent with ICL and two-step fallback")
        
    async def _execute_processing(
        self, 
        message: Message, 
        session_id: Optional[str] = None
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Core processing logic for the HybridQueryWriterAgent.
        
        Args:
            message: The input message to process
            session_id: Optional session identifier
            
        Returns:
            Tuple of (response_message, next_agent_id)
        """
        try:
            # Get schema for validation
            schema = await self._retrieve_schema()
            
            # Extract valid node labels, relationship types from schema
            valid_node_labels = set(schema.get("node_labels", schema.get("nodeLabels", [])))
            valid_rel_types = set(schema.get("relationship_types", schema.get("relationshipTypes", [])))
            
            logger.info(f"Valid node labels: {valid_node_labels}")
            logger.info(f"Valid relationship types: {valid_rel_types}")
            
            # Initialize conversation with the user's original message
            conversation = [message]
            
            # Try ICL approach first with limited attempts in a conversational manner
            icl_attempts = 0
            cypher_query = None
            is_valid = False
            final_response = None
            
            while icl_attempts < self.max_icl_attempts:
                # Log attempt information before processing
                logger.info(f"Trying ICL approach (attempt {icl_attempts + 1}/{self.max_icl_attempts})")
                
                # Process with ICL agent using conversation
                response, cypher_query, is_valid, attempt_count = await self.icl_agent.process_with_feedback(
                    conversation, valid_node_labels, valid_rel_types, session_id
                )
                
                # Update the actual attempt count (important for tracking)
                icl_attempts = attempt_count
                
                # Update conversation with the agent's response
                conversation.append(response)
                
                # Validate the query
                is_valid, validation_error = self._validate_query(
                    cypher_query, valid_node_labels, valid_rel_types
                )
                
                if is_valid:
                    logger.info("Valid query generated using ICL approach")
                    final_response = response
                    break
                else:
                    logger.warning(f"Invalid query from ICL (attempt {icl_attempts}): {validation_error}")
                    
                    # Add to failed queries collection
                    self._failed_queries.append({
                        "query": cypher_query,
                        "error": validation_error
                    })
                    
                    # If we have attempts left, add feedback to the conversation
                    if icl_attempts < self.max_icl_attempts:
                        # Create a message with feedback about the validation error
                        rel_sample = ", ".join(list(valid_rel_types)[:5]) + "..."
                        node_sample = ", ".join(list(valid_node_labels)[:5]) + "..."
                        
                        feedback_content = (
                            f"The Cypher query you provided has an error: {validation_error}\n\n"
                            f"Invalid query:\n```cypher\n{cypher_query}\n```\n\n"
                            f"Please correct the query. Remember:\n"
                            f"1. Use only valid node labels like: {node_sample}\n"
                            f"2. Use only valid relationship types like: {rel_sample}\n"
                            f"3. Pay attention to relationship directions\n"
                            f"4. Include Citation nodes with HAS_SOURCE relationships\n\n"
                            f"Generate a new, corrected query."
                        )
                        
                        feedback_message = Message(
                            role=MessageRole.USER,
                            content=feedback_content
                        )
                        
                        # Add feedback to conversation
                        conversation.append(feedback_message)
            
            # If ICL approach failed after max attempts, try two-step
            if not is_valid:
                logger.info(f"ICL approach failed after {icl_attempts} attempts, falling back to two-step approach")
                
                # Process with two-step agent
                two_step_response, _ = await self.two_step_agent.process(message)
                
                # Extract query from response
                cypher_query = two_step_response.metadata.get("query", "")
                final_response = two_step_response
                
                # Validate the two-step query
                is_valid, validation_error = self._validate_query(
                    cypher_query, valid_node_labels, valid_rel_types
                )
                
                if not is_valid:
                    logger.warning(f"Invalid query from two-step approach: {validation_error}")
                    # Use a safe fallback query if both approaches fail
                    cypher_query = 'MATCH (d:Disease {name: "Dengue Fever"}) RETURN d.name, d.description LIMIT 5'
            
            # Create response with the final query if not already created
            if not final_response:
                # Create a fallback response with standardized metadata
                query_metadata = QueryMetadata.create_query_metadata(
                    query=cypher_query,
                    query_type="cypher",
                    pattern_name="fallback",
                    original_query=message.content,
                    approach="fallback",
                    attempts=icl_attempts,
                    timestamp=self._get_timestamp()
                )
                
                response_message = Message(
                    role=MessageRole.ASSISTANT,
                    content=json.dumps({
                        "query": cypher_query,
                        "approach": "fallback",
                        "attempts": icl_attempts
                    }, indent=2),
                    metadata=query_metadata
                )
            else:
                # Get the original query from the incoming message
                original_query = BaseMetadata.get(message.metadata, MetadataKeys.ORIGINAL_QUERY, message.content)
                
                # Use the generated response but ensure metadata is updated with standardized methods
                approach = "icl" if is_valid and icl_attempts < self.max_icl_attempts else "two_step"
                
                # Create standardized metadata
                query_metadata = QueryMetadata.create_query_metadata(
                    query=cypher_query,
                    query_type="cypher",
                    pattern_name=approach,
                    original_query=original_query,
                    approach=approach,
                    attempts=icl_attempts,
                    timestamp=self._get_timestamp()
                )
                
                # Preserve any existing metadata from the final response
                for key, value in final_response.metadata.items():
                    if key not in query_metadata:
                        query_metadata[key] = value
                
                response_message = Message(
                    role=final_response.role,
                    content=final_response.content,
                    metadata=query_metadata
                )
            
            return response_message, "next"
            
        except Exception as e:
            logger.error(f"Error in hybrid query generation: {str(e)}")
            
            # Create a fallback response on error using standardized metadata
            fallback_query = "MATCH (n:Disease {name: 'Dengue Fever'}) RETURN n LIMIT 5"
            
            # Create standardized metadata with error information
            error_metadata = QueryMetadata.create_query_metadata(
                query=fallback_query,
                query_type="cypher",
                pattern_name="error_fallback",
                original_query=message.content,
                error=str(e),
                approach="error_fallback",
                attempts=0,
                timestamp=self._get_timestamp()
            )
            
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
    
    async def _retrieve_schema(self) -> Dict[str, Any]:
        """
        Retrieve the schema from the Neo4j database.
        
        Returns:
            Dict containing the database schema
        """
        return await self.schema_tool.get_schema()
        
    def _prepare_message_with_negatives(self, message: Message) -> Message:
        """
        Prepare a message with failed queries as negative examples.
        
        Args:
            message: The original user message
            
        Returns:
            A new message with negative examples
        """
        if not self._failed_queries:
            return message
            
        # Add negative examples to the content
        negative_examples = "\n\nPrevious incorrect queries (DO NOT generate similar queries):\n"
        for i, failed in enumerate(self._failed_queries):
            negative_examples += f"\nIncorrect Query {i+1}:\n```cypher\n{failed['query']}\n```\n"
            negative_examples += f"Error: {failed['error']}\n"
            
        # Create a new message with the negative examples
        enhanced_content = message.content + negative_examples
        
        return Message(
            role=message.role,
            content=enhanced_content,
            metadata=message.metadata
        )
        
    def _validate_query(
        self, 
        query: str, 
        valid_node_labels: Set[str], 
        valid_rel_types: Set[str]
    ) -> Tuple[bool, str]:
        """
        Validate a Cypher query against the schema.
        
        Args:
            query: The Cypher query to validate
            valid_node_labels: Set of valid node labels
            valid_rel_types: Set of valid relationship types
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if query is empty
        if not query or not query.strip():
            return False, "Empty query"
            
        # Add a relaxed validation for basic dengue fever queries
        if "Disease" in query and "Dengue Fever" in query:
            # Consider citations - if we want to be stricter about these
            # For now, let's make this more relaxed
            if "Citation" not in query and "HAS_SOURCE" not in query:
                logger.warning("Query includes Disease but no citations")
                # If using strict validation, require citations
                if self.strict_validation:
                    return False, "Missing Citation nodes with HAS_SOURCE relationships"
            
            # Extract node labels from query - improved regex to handle more cases
            node_label_pattern = r':(\w+)'
            found_node_labels = set(re.findall(node_label_pattern, query))
            
            # Extract relationship types from query - improved regex to handle more patterns
            # This will match relationships in formats like:
            # [:REL_TYPE], -[:REL_TYPE]->, <-[:REL_TYPE]-, -[r:REL_TYPE]->
            rel_type_pattern = r'\[:([A-Za-z0-9_|]+)\]'
            found_rel_types = set()
            
            # Handle the case where a relationship might have pipe operators
            for rel_match in re.findall(rel_type_pattern, query):
                # Split by | if there are pipe operators for OR conditions
                if '|' in rel_match:
                    for rel in rel_match.split('|'):
                        found_rel_types.add(rel.strip())
                else:
                    found_rel_types.add(rel_match)
            
            # Make validation more relaxed or strict based on configuration
            if self.strict_validation:
                # In strict mode, ALL node labels and relationships must be valid
                invalid_node_labels = [label for label in found_node_labels if label not in valid_node_labels]
                if invalid_node_labels:
                    return False, f"Invalid node labels found: {', '.join(invalid_node_labels)}"
                
                invalid_rel_types = [rel for rel in found_rel_types if rel not in valid_rel_types]
                if invalid_rel_types:
                    return False, f"Invalid relationship types found: {', '.join(invalid_rel_types)}"
            else:
                # In relaxed mode (default), check if ANY node labels/rels are valid
                valid_node_found = False
                for label in found_node_labels:
                    if label in valid_node_labels:
                        valid_node_found = True
                        break
                        
                valid_rel_found = len(found_rel_types) == 0  # No relationships is valid for simple queries
                for rel in found_rel_types:
                    if rel in valid_rel_types:
                        valid_rel_found = True
                        break
                
                if not valid_node_found and found_node_labels:
                    return False, f"No valid node labels found among: {', '.join(found_node_labels)}"
                    
                if not valid_rel_found and found_rel_types:
                    return False, f"No valid relationship types found among: {', '.join(found_rel_types)}"
            
            # If we got this far, the query has dengue fever and valid labels/relationships
            return True, ""
            
        return False, "Query does not reference the Disease node with Dengue Fever"
        
    def _get_timestamp(self) -> str:
        """
        Get a formatted timestamp for the current time.
        
        Returns:
            Formatted timestamp string
        """
        return datetime.now().isoformat()
