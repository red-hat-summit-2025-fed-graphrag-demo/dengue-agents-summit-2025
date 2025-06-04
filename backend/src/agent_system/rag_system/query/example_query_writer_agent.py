"""
Example Query Writer Agent

This agent generates Cypher queries based on examples and templates.
It maintains a library of pre-defined query templates tailored to common question patterns.

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
from typing import Any, Dict, Optional, Tuple

from src.agent_system.core.base_agent import BaseAgent
from src.agent_system.core.message import Message, MessageRole
from src.agent_system.core.metadata import QueryMetadata, MetadataKeys
from src.tools.schema_tool import SchemaTool

logger = logging.getLogger(__name__)

class ExampleQueryWriterAgent(BaseAgent):
    """
    Example agent demonstrating standardized metadata usage.
    
    This agent shows how to properly create and update metadata
    using the standardized metadata classes.
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], **kwargs):
        """Initialize the ExampleQueryWriterAgent."""
        if "agent_id" not in config:
            config["agent_id"] = agent_id
            
        super().__init__(config, **kwargs)
        
        # Get API URL from config or environment
        self.kg_api_url = config.get("kg_api_url", None)
        
        # Initialize the schema tool
        self.schema_tool = SchemaTool(api_url=self.kg_api_url)
        
    async def _execute_processing(
        self, 
        message: Message, 
        session_id: Optional[str] = None
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Core processing logic for the ExampleQueryWriterAgent.
        
        This method demonstrates how to use the standardized metadata classes
        to create consistent metadata for messages.
        
        Args:
            message: The input message to process
            session_id: Optional session identifier
            
        Returns:
            Tuple of (response_message, next_agent_id)
        """
        # Extract the user query from the message
        user_query = message.content
        
        # Example query generation
        cypher_query = "MATCH (d:Disease {name: 'Dengue Fever'})-[:HAS_SYMPTOM]->(s:Symptom) RETURN s.name as symptom, s.description as description"
        pattern_name = "disease_symptoms"
        
        # ====== EXAMPLE 1: Create metadata using the QueryMetadata class ======
        # This is the recommended way to create standardized metadata
        metadata = QueryMetadata.create_query_metadata(
            query=cypher_query,
            original_query=user_query,
            query_type="cypher",
            pattern_name=pattern_name,
            is_default_query=True
        )
        
        # Create a response message with standardized metadata
        response_message = Message(
            role=MessageRole.ASSISTANT,
            content=cypher_query,
            metadata=metadata
        )
        
        # ====== EXAMPLE 2: Using Message class methods ======
        # Alternative approach using Message class methods
        response_message2 = Message(
            role=MessageRole.ASSISTANT,
            content=cypher_query,
            metadata={}  # Start with empty metadata
        )
        
        # Update metadata using standardized keys
        response_message2.update_metadata(
            query=cypher_query,
            original_query=user_query,
            query_type="cypher",
            pattern_name=pattern_name,
            is_default_query=True
        )
        
        # ====== EXAMPLE 3: Getting metadata values ======
        # Retrieving metadata using standardized keys
        query = response_message.get_metadata(MetadataKeys.QUERY)
        original_query = response_message.get_metadata("original_query")  # Can use string or enum
        
        # For legacy compatibility, can also access fields directly
        # But prefer using get_metadata to ensure future-proofing
        pattern = response_message.metadata.get(MetadataKeys.PATTERN_NAME.value)
        
        logger.info(f"Generated query: {query}")
        logger.info(f"Original query: {original_query}")
        logger.info(f"Pattern: {pattern}")
        
        # Route to the appropriate next agent
        return response_message, "graph_query_executor_agent"
