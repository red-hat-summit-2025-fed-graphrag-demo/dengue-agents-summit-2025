"""
Message Metadata Standards

This module defines standard metadata structures for agent messages
to ensure consistency throughout the agent workflow system.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)


class MetadataKeys(Enum):
    """
    Standard keys used in message metadata across the agent system.
    
    These keys provide a consistent interface for accessing common metadata
    fields that are passed between agents.
    """
    # Query-related keys
    QUERY = "query"  # The current query being processed (any type)
    CYPHER_QUERY = "cypher_query"  # Legacy key - prefer QUERY
    QUERY_TYPE = "query_type"  # Type of query (e.g., "cypher", "natural_language")
    ORIGINAL_QUERY = "original_query"  # The original user query
    IS_DEFAULT_QUERY = "is_default_query"  # Whether this is a default/fallback query
    
    # Results-related keys
    RESULTS = "results"  # Query results
    RESULT_COUNT = "result_count"  # Number of results returned
    ERROR = "error"  # Error message if query failed
    
    # Assessment keys
    ASSESSMENT = "assessment"  # Assessment of query results
    
    # Pattern-related keys
    PATTERN_NAME = "pattern_name"  # Name of the pattern used for the query
    
    # Citation-related keys
    CITATIONS = "citations"  # List of citations
    CITATION_COUNT = "citation_count"  # Number of citations
    HAS_CITATIONS = "has_citations"  # Boolean indicating presence of citations
    
    # Visualization-related keys  
    HAS_VISUALIZATION_DATA = "has_visualization_data"  # Boolean indicating presence of visualization data
    VISUALIZATION_DATA = "visualization_data"  # Visualization data
    
    # Safety-related keys
    SAFETY_CHECKED = "safety_checked"  # Whether safety checks were performed
    SAFETY_AGENT_ID = "safety_agent_id"  # ID of safety agent that performed checks
    SAFETY_CHECK_PASSED = "safety_check_passed"  # Whether safety checks were passed
    SAFETY_CONFIDENCE = "safety_confidence"  # Confidence score of safety check
    
    # Response-related keys
    GENERATED = "generated"  # Generated response
    IS_JSON_RESPONSE = "is_json_response"  # Whether response is in JSON format
    
    # Compliance-related keys
    COMPLIANCE_CHECKED = "compliance_checked"  # Whether compliance checks were performed
    COMPLIANCE_AGENT_ID = "compliance_agent_id"  # ID of compliance agent
    IS_COMPLIANT = "is_compliant"  # Whether content is compliant
    COMPLIANCE_CONFIDENCE = "compliance_confidence"  # Confidence score of compliance check
    WAS_REMEDIATED = "was_remediated"  # Whether content was modified due to compliance failure
    PII_EXPLANATION = "pii_explanation"  # Explanation of detected PII/PHI
    
    # Rewriting-related keys
    REWRITTEN_QUERY = "rewritten_query"  # Rewritten version of query
    QUERY_REWRITE_ATTEMPTED = "query_rewrite_attempted"  # Whether query rewriting was attempted
    REWRITE_COUNT = "rewrite_count"  # Number of rewrites attempted
    
    # Schema-related keys
    SCHEMA_SUMMARY = "schema_summary"  # Summary of database schema
    
    # Routing-related keys
    ROUTE_CATEGORY = "route_category"  # Classification category for routing
    IS_CLASSIFICATION_RESULT = "is_classification_result"  # Flag indicating classification result
    CLASSIFICATION_CONFIDENCE = "classification_confidence"  # Confidence score for classification
    PROMPT_ID = "prompt_id"  # ID of the prompt used for generation
    QUERY_APPROACH = "approach"  # Approach used to generate the query
    QUERY_ATTEMPTS = "attempts"  # Number of query attempts
    
    # Result type keys
    RESULT_TYPE = "result_type"  # Type of result (e.g., "text", "graph", "visualization")
    RESULT_TYPE_TEXT = "text"  # Text result type
    RESULT_TYPE_GRAPH = "graph"  # Graph result type
    RESULT_TYPE_VISUALIZATION = "visualization"  # Visualization result type
    
    # Timestamp
    TIMESTAMP = "timestamp"  # Timestamp of when metadata was created/updated


class BaseMetadata(ABC):
    """
    Abstract base class for standardized metadata creation.
    
    This class defines the interface for creating and validating metadata
    that is passed between agents in the workflow.
    """
    
    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """
        Create a standardized metadata dictionary with the provided values.
        
        Args:
            **kwargs: Key-value pairs to include in the metadata.
                      Keys should be from MetadataKeys enum.
        
        Returns:
            Dict[str, Any]: A metadata dictionary with standardized keys.
        """
        metadata = {}
        
        # Add all provided key-value pairs using standardized keys
        for key, value in kwargs.items():
            if hasattr(MetadataKeys, key.upper()):
                metadata_key = getattr(MetadataKeys, key.upper()).value
                metadata[metadata_key] = value
            else:
                # Allow custom keys but log a warning
                logger.warning(f"Using non-standard metadata key: {key}")
                metadata[key] = value
                
        return metadata
    
    @classmethod
    def get(cls, metadata: Dict[str, Any], key: Union[str, MetadataKeys], 
            default: Any = None) -> Any:
        """
        Get a value from metadata using a standardized key.
        
        Args:
            metadata: The metadata dictionary to retrieve from
            key: The key to look up (either a string or MetadataKeys enum)
            default: Default value to return if key not found
            
        Returns:
            The value associated with the key, or the default value
        """
        if isinstance(key, MetadataKeys):
            std_key = key.value
        else:
            # If string provided, try to match to enum
            try:
                std_key = getattr(MetadataKeys, key.upper()).value
            except (AttributeError, KeyError):
                # If not a standard key, use as-is
                std_key = key
                
        return metadata.get(std_key, default)
    
    @classmethod
    def update(cls, metadata: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Update metadata with new values using standardized keys.
        
        Args:
            metadata: The metadata dictionary to update
            **kwargs: Key-value pairs to update
            
        Returns:
            Updated metadata dictionary
        """
        new_data = cls.create(**kwargs)
        metadata.update(new_data)
        return metadata


class QueryMetadata(BaseMetadata):
    """Specialized metadata class for query-related operations."""
    
    @classmethod
    def create_query_metadata(cls, query: str, 
                             original_query: Optional[str] = None,
                             query_type: str = "cypher",
                             pattern_name: Optional[str] = None,
                             **kwargs) -> Dict[str, Any]:
        """
        Create metadata specifically for query operations.
        
        Args:
            query: The query string
            original_query: The original user query
            query_type: Type of query (default: "cypher")
            pattern_name: Name of the pattern used
            **kwargs: Additional metadata key-value pairs
            
        Returns:
            Dict[str, Any]: Query metadata
        """
        metadata = cls.create(
            query=query,
            query_type=query_type,
            **kwargs
        )
        
        # For backward compatibility, also set the legacy key
        if query_type == "cypher":
            metadata[MetadataKeys.CYPHER_QUERY.value] = query
            
        if original_query:
            metadata[MetadataKeys.ORIGINAL_QUERY.value] = original_query
            
        if pattern_name:
            metadata[MetadataKeys.PATTERN_NAME.value] = pattern_name
            
        return metadata


class ResultMetadata(BaseMetadata):
    """Specialized metadata class for result-related operations."""
    
    @classmethod
    def create_result_metadata(cls, results: Optional[List[Any]] = None,
                              assessment: Optional[str] = None,
                              error: Optional[str] = None,
                              **kwargs) -> Dict[str, Any]:
        """
        Create metadata specifically for query results.
        
        Args:
            results: List of query results, can be None for error cases
            assessment: Assessment of the results
            error: Error message if query failed
            **kwargs: Additional metadata key-value pairs
            
        Returns:
            Dict[str, Any]: Result metadata
        """
        # Start with kwargs
        metadata = {}
        
        # Handle results and result_count separately to avoid conflicts
        if results is not None:
            metadata[MetadataKeys.RESULTS.value] = results
            # Only set result_count if not explicitly provided in kwargs
            if MetadataKeys.RESULT_COUNT.value not in kwargs:
                metadata[MetadataKeys.RESULT_COUNT.value] = len(results) if results else 0
        elif MetadataKeys.RESULT_COUNT.value not in kwargs:
            # For error cases with no results, set count to 0
            metadata[MetadataKeys.RESULT_COUNT.value] = 0
            
        # Add assessment if provided
        if assessment:
            metadata[MetadataKeys.ASSESSMENT.value] = assessment
            
        # Add error if provided
        if error:
            metadata[MetadataKeys.ERROR.value] = error
            
        # Create standardized metadata by merging our built metadata with kwargs
        # Process all kwargs through the standard keys
        for key, value in kwargs.items():
            if hasattr(MetadataKeys, key.upper()):
                metadata_key = getattr(MetadataKeys, key.upper()).value
                metadata[metadata_key] = value
            else:
                # Allow custom keys but log a warning
                logger.warning(f"Using non-standard metadata key in create_result_metadata: {key}")
                metadata[key] = value
                
        return metadata


class CitationMetadata(BaseMetadata):
    """Specialized metadata class for citation-related operations."""
    
    @classmethod
    def create_citation_metadata(cls, citations: List[Dict[str, Any]],
                                **kwargs) -> Dict[str, Any]:
        """
        Create metadata specifically for citations.
        
        Args:
            citations: List of citation objects
            **kwargs: Additional metadata key-value pairs
            
        Returns:
            Dict[str, Any]: Citation metadata
        """
        citation_count = len(citations) if citations else 0
        has_citations = citation_count > 0
        
        return cls.create(
            citations=citations,
            citation_count=citation_count,
            has_citations=has_citations,
            **kwargs
        )
