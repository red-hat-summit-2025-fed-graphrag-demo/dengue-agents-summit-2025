"""
Cypher Query Tool for Neo4j.

This module provides utilities for executing Cypher queries against a Neo4j database
via the REST API. It handles query validation, execution, and error handling.

Usage:
    from src.tools.cypher_tool import CypherTool
    
    # Create a tool instance
    cypher_tool = CypherTool()
    
    # Execute a query
    results = await cypher_tool.execute_query("MATCH (n) RETURN count(n) as count")
"""
import os
import json
import httpx
import logging
from typing import Dict, List, Any, Optional, Union

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CypherTool:
    """Tool for executing Cypher queries against a Neo4j database via REST API."""
    
    def __init__(self, api_url: Optional[str] = None):
        """
        Initialize the Cypher tool.
        
        Args:
            api_url: Optional override for the Neo4j API URL.
                     If not provided, uses the KG_API_URL environment variable.
        """
        self.api_url = api_url or os.getenv("KG_API_URL")
        if not self.api_url:
            raise ValueError("Neo4j API URL not configured. Set KG_API_URL environment variable or provide api_url parameter.")
        
        # Ensure URL has no trailing slash
        self.api_url = self.api_url.rstrip('/')
        self.query_endpoint = f"{self.api_url}/query/cypher"
        
        logger.info(f"Initialized CypherTool with endpoint: {self.query_endpoint}")

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None, include_citations: bool = False) -> Dict[str, Any]:
        """
        Execute a Cypher query against the Neo4j database.
        
        Args:
            query: The Cypher query to execute
            params: Optional parameters for the query (for parameterized queries)
            include_citations: If True, automatically includes citations for returned data
            
        Returns:
            Dict containing the query results
            
        Raises:
            ValueError: If the query is empty or invalid
            httpx.HTTPStatusError: If the API returns an error response
            httpx.RequestError: If there's a network or connection error
            Exception: For other unexpected errors
        """
        # Validate input
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        # If include_citations flag is set, modify the query to include citation nodes
        if include_citations and not "Citation" in query:
            # Store original query for logging
            original_query = query.strip()
            
            # Modify query to include citations for results
            # Note: This requires careful query modification
            # This approach works with queries that match and return path patterns 
            enhanced_query = self._enhance_query_with_citations(original_query)
            query = enhanced_query
            logger.info(f"Enhanced query with citations. Original: {original_query[:50]}... Enhanced: {enhanced_query[:50]}...")
        
        # Prepare request payload
        payload = {
            "query": query.strip()
        }
        
        # Add parameters if provided
        if params:
            payload["parameters"] = params
        
        try:
            logger.info(f"Executing Cypher query: {query[:100]}{'...' if len(query) > 100 else ''}")
            
            # Execute query with appropriate timeout
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.query_endpoint,
                    json=payload
                )
                
            # Raise HTTP errors if any
            response.raise_for_status()
            
            # Process response
            result_data = response.json()
            
            # Handle different response formats
            if "results" in result_data and isinstance(result_data["results"], list):
                # Standard Neo4j REST API format
                return result_data
            else:
                # Custom API format - return as is
                return result_data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error executing Cypher query: {e.response.status_code} - {e.response.text}")
            # Try to parse the error message from the response
            try:
                error_data = e.response.json()
                error_message = error_data.get("message", str(e))
            except Exception:
                error_message = f"HTTP {e.response.status_code}: {e.response.text}"
            
            raise ValueError(f"Error executing Cypher query: {error_message}")
            
        except httpx.RequestError as e:
            logger.error(f"Request error executing Cypher query: {str(e)}")
            raise ValueError(f"Connection error: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected error executing Cypher query: {str(e)}")
            raise
    
    async def validate_query(self, query: str) -> bool:
        """
        Validate if a Cypher query is syntactically correct without executing it.
        
        This is a simple validation that only checks for empty queries.
        For more advanced validation, a dedicated Neo4j Cypher parser would be needed.
        
        Args:
            query: The Cypher query to validate
            
        Returns:
            True if the query is valid, False otherwise
        """
        return bool(query and query.strip())

    def _enhance_query_with_citations(self, query: str) -> str:
        """
        Enhance a Cypher query to include citation information.
        
        This method attempts to modify an existing query to include citation nodes
        that are connected to the main entities via HAS_SOURCE relationships.
        
        Args:
            query: The original Cypher query
            
        Returns:
            Enhanced query that includes citation information
        """
        # Quick check if this is a simple pattern query (most common case)
        if "MATCH" in query and "RETURN" in query:
            match_part = query[:query.find("RETURN")].strip()
            return_part = query[query.find("RETURN"):].strip()
            
            # Extract the RETURN variables to bind citations only to returned nodes
            return_vars = return_part.replace("RETURN", "").split(",")
            main_vars = []
            
            # Extract variable names (before any "as" clauses)
            for var in return_vars:
                var = var.strip()
                if " as " in var.lower():
                    var = var.split(" as ")[0].strip()
                if "." in var:  # Handle property access like "n.name"
                    var = var.split(".")[0].strip()
                if var and not var.startswith("count(") and not var.startswith("collect("):
                    main_vars.append(var)
            
            # If we can identify main variables, bind citations specifically to them
            if main_vars:
                # Create citation matches for each identified variable
                citation_matches = []
                citation_returns = []
                
                for i, var in enumerate(main_vars):
                    citation_var = f"citation_{i}"
                    citation_matches.append(
                        f"OPTIONAL MATCH ({var})-[:HAS_SOURCE]->({citation_var}:Citation)"
                    )
                    citation_returns.append(
                        f"{citation_var}.title as {var}_source_title, "
                        f"{citation_var}.publisher as {var}_source_publisher, "
                        f"{citation_var}.url as {var}_source_url, "
                        f"{citation_var}.full_text as {var}_source_citation"
                    )
                
                # Build the enhanced query with specific citation bindings
                enhanced_query = f"""
                {match_part}
                {' '.join(citation_matches)}
                {return_part}, {', '.join(citation_returns)}
                """
                return enhanced_query
            
            # Fallback if we couldn't extract specific variables
            return f"""
            {match_part}
            WITH *, [] as citations
            OPTIONAL MATCH (node)-[:HAS_SOURCE]->(citation:Citation)
            WHERE node IN [{', '.join(main_vars) if main_vars else 'null'}]
            WITH *, collect(DISTINCT {{
                title: citation.title,
                publisher: citation.publisher,
                url: citation.url,
                citation_text: citation.full_text
            }}) as citations
            {return_part}, citations
            """
            
        # For complex queries where simple pattern matching won't work,
        # Add a post-processing step to collect distinct citations
        return f"""
        WITH * FROM (
            {query}
        ) as results
        OPTIONAL MATCH (node)-[:HAS_SOURCE]->(citation:Citation)
        WHERE node IN [n IN apoc.coll.flatten(collect(results)) WHERE n IS NOT NULL]
        WITH results, collect(DISTINCT {{
            title: citation.title,
            publisher: citation.publisher,
            url: citation.url,
            citation_text: citation.full_text
        }}) as citations
        RETURN results.*, citations
        """
    
    async def get_citations_for_node(self, node_label: str, node_id_or_name: str, id_property: str = "name") -> Dict[str, Any]:
        """
        Get citations for a specific node.
        
        Args:
            node_label: The label of the node (e.g., 'Disease', 'Symptom')
            node_id_or_name: The id or name value to match
            id_property: The property to use for matching (defaults to 'name')
            
        Returns:
            Dict containing citations for the node
        """
        query = f"""
        MATCH (n:{node_label} {{{id_property}: $node_id}})-[:HAS_SOURCE]->(citation:Citation)
        RETURN citation
        """
        
        params = {"node_id": node_id_or_name}
        
        result = await self.execute_query(query, params)
        return self.format_results(result)
    
    async def get_citations_for_topic(self, topic: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get all citations related to a specific topic using pattern matching.
        
        This is useful for finding relevant citations when the exact node isn't known.
        
        Args:
            topic: The topic to search for in node names or descriptions
            limit: Maximum number of citations to return
            
        Returns:
            Dict containing relevant citations
        """
        # Use a simpler query with pattern matching instead of fulltext search
        # since the API doesn't allow CALL operations
        query = f"""
        MATCH (n)-[:HAS_SOURCE]->(citation:Citation)
        WHERE toLower(n.name) CONTAINS toLower($topic)
        RETURN n.name as topic, collect(citation) as citations
        LIMIT $limit
        """
        
        params = {
            "topic": topic,
            "limit": limit
        }
        
        result = await self.execute_query(query, params)
        formatted = self.format_results(result)
        
        # If no results, try with more node properties if available
        if not formatted.get("data") or len(formatted["data"]) == 0:
            broader_query = f"""
            MATCH (n)-[:HAS_SOURCE]->(citation:Citation)
            WHERE toLower(n.name) CONTAINS toLower($topic) OR 
                  toLower(coalesce(n.description, '')) CONTAINS toLower($topic) OR
                  toLower(coalesce(n.category, '')) CONTAINS toLower($topic) OR
                  toLower(coalesce(n.type, '')) CONTAINS toLower($topic)
            RETURN n.name as topic, collect(citation) as citations
            LIMIT $limit
            """
            
            result = await self.execute_query(broader_query, params)
            formatted = self.format_results(result)
            
        return formatted

    @staticmethod
    def format_results(results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format raw Neo4j results into a more usable structure.
        
        Args:
            results: Raw results from the Neo4j API
            
        Returns:
            Formatted results
        """
        if not results:
            return {"data": []}
            
        # Handle specific format for the Dengue API
        if "results" in results and isinstance(results["results"], list):
            formatted_data = []
            
            # Get the columns if they exist
            columns = results.get("columns", [])
            
            # Process each result item
            for item in results["results"]:
                # The item is already formatted as key-value pairs
                formatted_data.append(item)
                
            return {
                "data": formatted_data,
                "columns": columns,
                "query_time_ms": results.get("query_time_ms")
            }
        
        # Return as is for unknown formats
        return results
