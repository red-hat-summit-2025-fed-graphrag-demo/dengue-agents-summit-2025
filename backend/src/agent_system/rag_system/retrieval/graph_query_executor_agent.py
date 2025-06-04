"""
Graph Query Executor RAG Agent

A specialized agent for graph query executor functionality
Executes graph queries and collects citations for the retrieved nodes.

IMPLEMENTATION GUIDE:
1. Review and update the docstrings and comments
2. Implement the _execute_processing method for your agent's specific logic
3. Add any additional methods needed for your agent's functionality
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.agent_system.core.base_agent import BaseAgent
from src.agent_system.core.message import Message, MessageRole
from src.agent_system.core.metadata import MetadataKeys, ResultMetadata, CitationMetadata
from src.tools.citation_tool import CitationTool

logger = logging.getLogger(__name__)

class GraphQueryExecutorAgent(BaseAgent):  
    """
    A specialized agent for graph query executor functionality
    
    This class implements the Graph Query Executor RAG Agent functionality by:
    1. Executing graph queries based on message content/metadata
    2. Collecting citations for retrieved items
    3. Returning results with properly formatted metadata
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], **kwargs):
        """
        Initialize the GraphQueryExecutorAgent.
        
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
        
        # Initialize citation tool
        self.citation_tool = CitationTool()
        
        logger.info(f"Initialized GraphQueryExecutorAgent")
    
    async def _stream_thinking_hook(self, stream_callback: Any):
        """Optional hook called by BaseAgent.process to stream initial thoughts."""
        await self.stream_thinking(
            thinking=f"Executing graph query and collecting citations...",
            stream_callback=stream_callback
        )
        
    async def _execute_processing(
        self, 
        message: Message, 
        session_id: Optional[str] = None
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Core processing logic for the GraphQueryExecutorAgent.
        Executes graph queries and collects citations.
        
        Args:
            message: The input message to process
            session_id: Optional session identifier
            
        Returns:
            Tuple of (response_message, next_agent_id)
        """
        # Initialize response metadata
        response_metadata = {}
        
        # Extract query from message content or metadata
        # This would typically be handled by database query execution logic
        # For now, we'll just pass through the message content
        response_text = message.content
        
        # Extract results from metadata if present
        results = message.metadata.get(MetadataKeys.RESULTS.value, [])
        
        # Collect citations for each result node if results exist
        all_citations = []
        if results and isinstance(results, list):
            logger.info(f"Collecting citations for {len(results)} results")
            
            for result in results:
                # Check if result has an id field that can be used to get citations
                node_id = result.get("id")
                if node_id:
                    # Get citations for this node
                    citation_result = self.citation_tool.get_node_citations(node_id)
                    
                    if citation_result["status"] == "success" and citation_result.get("citations"):
                        node_citations = citation_result["citations"]
                        # Add to all citations list
                        all_citations.extend(node_citations)
                        logger.info(f"Found {len(node_citations)} citations for node {node_id}")
            
            # Format citations if any were found
            if all_citations:
                formatted_citations = self.citation_tool.batch_format_citations(all_citations)
                if formatted_citations["status"] == "success":
                    # Create citation metadata and update response metadata
                    citation_metadata = CitationMetadata.create_citation_metadata(
                        citations=formatted_citations["formatted_citations"]
                    )
                    
                    # Update response metadata with citation info
                    response_metadata.update(citation_metadata)
                    logger.info(f"Added {len(all_citations)} citations to response metadata")
        
        # Create result metadata for the response
        result_metadata = ResultMetadata.create_result_metadata(
            results=results,
            error=None  # Add error handling as needed
        )
        
        # Update response metadata with result metadata
        response_metadata.update(result_metadata)
        
        # Create and return the response message
        response_message = Message(
            role=MessageRole.ASSISTANT,
            content=response_text,
            metadata=response_metadata
        )
            
        # If your agent should chain to another agent, return its ID as the second element
        return response_message, None
