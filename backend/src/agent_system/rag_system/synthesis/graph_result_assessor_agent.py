"""
Graph Result Assessor Agent

A specialized agent for analyzing and assessing the results of graph queries.
This agent takes the raw results from the Graph Query Executor Agent,
analyzes them for relevance and quality, and prepares them for template selection.
"""
import logging
import json
from typing import Any, Dict, List, Optional, Tuple

from src.agent_system.core.base_agent import BaseAgent
from src.agent_system.core.message import Message, MessageRole
from src.registries.prompt_registry import PromptRegistry
from src.agent_system.core.metadata import ResultMetadata, QueryMetadata, MetadataKeys, BaseMetadata

logger = logging.getLogger(__name__)

class GraphResultAssessorAgent(BaseAgent):  
    """
    A specialized agent for assessing graph query results
    
    This class implements the Graph Result Assessor Agent functionality by:
    1. Analyzing query results for relevance, quality, and completeness
    2. Extracting key facts and information from the results
    3. Determining the appropriate template category for response generation
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any], **kwargs):
        """
        Initialize the GraphResultAssessorAgent.
        
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
                "max_tokens": 1024,
                "temperature": 0.4  # Lower temperature for more factual assessments
            }
        elif "model_type" not in config["model_config"]:
            config["model_config"]["model_type"] = "instruct"
            
        super().__init__(config, **kwargs)
        
        # Get a reference to the prompt registry
        self.prompt_registry = PromptRegistry()
        
        # Extract prompt_id from config or use default
        self.prompt_id = config.get("prompt_id", "rag.graph_result_assessor")
        
        logger.info(f"Initialized GraphResultAssessorAgent with prompt_id: {self.prompt_id}")
    
    async def _stream_thinking_hook(self, stream_callback: Any):
        """Optional hook called by BaseAgent.process to stream initial thoughts."""
        await self.stream_thinking(
            thinking=f"Analyzing query results and assessing data quality...",
            stream_callback=stream_callback
        )
        
    async def _execute_processing(
        self, 
        message: Message, 
        session_id: Optional[str] = None
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Core processing logic for the GraphResultAssessorAgent.
        Simple deterministic assessment of query results - no LLM needed.
        
        Args:
            message: The input message to process (containing query results)
            session_id: Optional session identifier
            
        Returns:
            Tuple of (response_message, next_agent_id)
        """
        logger.info("=========== GRAPH RESULT ASSESSOR AGENT START ===========")
        
        # Extract results from message metadata
        results = message.metadata.get(MetadataKeys.RESULTS.value, [])
        
        # Log input metadata for debugging
        logger.info(f"Input metadata keys: {list(message.metadata.keys())}")
        logger.info(f"Input metadata.get(MetadataKeys.RESULTS.value): {len(results) if isinstance(results, list) else 'not a list'}")
        logger.info(f"Input metadata.get('results'): {len(message.metadata.get('results', [])) if isinstance(message.metadata.get('results', []), list) else 'not a list'}")
        logger.info(f"Input metadata.get(MetadataKeys.RESULT_COUNT.value): {message.metadata.get(MetadataKeys.RESULT_COUNT.value)}")
        logger.info(f"Input metadata.get('result_count'): {message.metadata.get('result_count')}")
        
        # Ensure results is always a list
        if not isinstance(results, list):
            results = [results] if results else []
        
        # Get actual count of results
        raw_result_count = len(results)
        logger.info(f"Assessing query results: Found {raw_result_count} results")
        
        # Extract other metadata fields we need to preserve
        query = message.metadata.get(MetadataKeys.QUERY.value, "")
        original_query = message.metadata.get(MetadataKeys.ORIGINAL_QUERY.value, "")
        pattern_name = message.metadata.get(MetadataKeys.PATTERN_NAME.value, None)
        query_type = message.metadata.get(MetadataKeys.QUERY_TYPE.value, "cypher")
        
        # Determine assessment type based on results
        if raw_result_count > 0:
            # Check for null values in the results
            null_values_count = sum(1 for item in results if any(value is None for value in item.values()))
            
            if null_values_count > 0:
                logger.info(f"Assessment: partial_results ({null_values_count} results have null values)")
                assessment_type = "partial_results"
                explanation = f"Found {raw_result_count} results, but {null_values_count} have missing values."
                
                # CRITICAL CHANGE: For partial results, set actual_result_count to 0
                # This ensures the workflow loop will trigger again to try a different query
                actual_result_count = 0
                logger.info("IMPORTANT: Setting actual_result_count = 0 for partial_results to trigger workflow loop")
            else:
                logger.info("Assessment: good_results (all values present)")
                assessment_type = "good_results"
                explanation = f"Found {raw_result_count} complete results."
                actual_result_count = raw_result_count
        else:
            logger.info("Assessment: no_results (empty result set)")
            assessment_type = "no_results"
            explanation = "No results were returned for the query."
            actual_result_count = 0
        
        # CRITICAL KEY FOR WORKFLOW LOOP: setting 'result_count' - must be an actual number
        # The workflow loop uses this to determine whether to iterate again
        logger.info(f"Setting critical metadata: 'result_count' = {actual_result_count} (raw count was {raw_result_count})")
        
        # Create a simple response object
        assessment_data = {
            "assessment": assessment_type,
            "explanation": explanation,
            "query": query,
            "original_query": original_query,
            "result_count": actual_result_count  # Use the adjusted count
        }
        
        # Create standardized metadata using ResultMetadata.create_result_metadata
        metadata = ResultMetadata.create_result_metadata(
            results=results,
            result_count=actual_result_count,  # Use the adjusted count
            assessment=assessment_type,
            query=query,
            query_type=query_type,
            raw_result_count=raw_result_count  # Keep track of original count for debugging
        )
        
        # Preserve original query and pattern name if present
        if original_query:
            metadata = BaseMetadata.update(metadata, **{MetadataKeys.ORIGINAL_QUERY.value: original_query})
        if pattern_name:
            metadata = BaseMetadata.update(metadata, **{MetadataKeys.PATTERN_NAME.value: pattern_name})
            
        # Copy all other metadata except results (which we've already handled)
        for key, value in message.metadata.items():
            if key != MetadataKeys.RESULTS.value and key not in metadata:
                metadata = BaseMetadata.update(metadata, **{key: value})
        
        # Double-check our result_count is set
        logger.info(f"CRITICAL CHECK - metadata['result_count'] = {metadata.get('result_count', 'NOT SET!')}")
        logger.info(f"CRITICAL CHECK - metadata[MetadataKeys.RESULT_COUNT.value] = {metadata.get(MetadataKeys.RESULT_COUNT.value, 'NOT SET!')}")
        
        # Create the response message
        response_message = Message(
            role=MessageRole.ASSISTANT,
            content=json.dumps(assessment_data, indent=2),
            metadata=metadata
        )
        
        # Final check on the message we're about to return
        logger.info(f"FINAL CHECK - response_message.metadata.get('result_count') = {response_message.metadata.get('result_count', 'NOT SET!')}")
        logger.info(f"FINAL CHECK - response_message.metadata.get(MetadataKeys.RESULT_COUNT.value) = {response_message.metadata.get(MetadataKeys.RESULT_COUNT.value, 'NOT SET!')}")
        
        # Log all metadata keys we're returning
        logger.info(f"Returning metadata with keys: {list(metadata.keys())}")
        
        logger.info("=========== GRAPH RESULT ASSESSOR AGENT END ===========")
        
        # Pass to the next stage in the workflow
        return response_message, "next"
