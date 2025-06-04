"""
Citation Tool for Neo4j.

This module provides utilities for executing Cypher queries against a Neo4j database, specifically the
citations endpoints.

Usage:
    from src.tools.citation_tool import CitationTool
    
    # Create a tool instance
    citation_tool = CitationTool()
    
    # Execute a query
    results = await citation_tool.get_all_citations(limit=100, offset=0)
"""
import requests
from typing import List, Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)

class CitationTool:
    """Tool for retrieving citation information from the citations API endpoints."""
    
    def __init__(self, base_url: str = "https://dengue-fastapi-dengue-kg-project.apps.cluster-8gvkk.8gvkk.sandbox888.opentlc.com"):
        self.base_url = base_url
    
    def get_all_citations(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """
        Retrieve all citations with pagination
        
        Args:
            limit: Maximum number of citations to return (1-1000)
            offset: Number of citations to skip
            
        Returns:
            Dictionary with status and list of citation objects
        """
        try:
            url = f"{self.base_url}/citations?limit={limit}&offset={offset}"
            response = requests.get(url)
            response.raise_for_status()
            return {
                "status": "success",
                "citations": response.json(),
                "count": len(response.json())
            }
        except Exception as e:
            logger.error(f"Error retrieving citations: {e}")
            return {
                "status": "error",
                "message": str(e),
                "citations": []
            }
    
    def get_citation(self, citation_id: str) -> Dict[str, Any]:
        """
        Retrieve a specific citation by ID
        
        Args:
            citation_id: ID of the citation to retrieve
            
        Returns:
            Dictionary with status and citation object
        """
        try:
            url = f"{self.base_url}/citations/{citation_id}"
            response = requests.get(url)
            response.raise_for_status()
            return {
                "status": "success",
                "citation": response.json()
            }
        except Exception as e:
            logger.error(f"Error retrieving citation {citation_id}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "citation": None
            }
    
    def get_node_citations(self, node_id: Union[int, str]) -> Dict[str, Any]:
        """
        Retrieve all citations for a specific node
        
        Args:
            node_id: ID of the node to get citations for
            
        Returns:
            Dictionary with status and list of citation objects related to the node
        """
        try:
            url = f"{self.base_url}/nodes/{node_id}/citations"
            response = requests.get(url)
            response.raise_for_status()
            return {
                "status": "success",
                "citations": response.json(),
                "count": len(response.json())
            }
        except Exception as e:
            logger.error(f"Error retrieving citations for node {node_id}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "citations": []
            }
    
    def search_citations_by_query(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Search for citations by text query (title, publisher, etc.)
        
        Args:
            query: Search query for citation content
            limit: Maximum number of results to return
            
        Returns:
            Dictionary with status and list of matching citation objects
        """
        try:
            # First get all citations (with a higher limit to search through)
            all_citations_result = self.get_all_citations(limit=200)
            
            if all_citations_result["status"] != "success":
                return all_citations_result
                
            citations = all_citations_result["citations"]
            
            # Simple filtering by query in title, publisher, or full_text
            matches = []
            query = query.lower()
            for citation in citations:
                if any(query in str(citation.get(field, "")).lower() for field in ["title", "publisher", "full_text", "url"]):
                    matches.append(citation)
                    if len(matches) >= limit:
                        break
            
            return {
                "status": "success",
                "citations": matches,
                "count": len(matches),
                "query": query
            }
        except Exception as e:
            logger.error(f"Error searching citations: {e}")
            return {
                "status": "error",
                "message": str(e),
                "citations": []
            }
    
    def format_citation(self, citation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a citation for inclusion in output text
        
        Args:
            citation: Citation object
            
        Returns:
            Dictionary with formatted citation string and original citation
        """
        try:
            if not citation:
                return {
                    "status": "error",
                    "message": "No citation provided",
                    "formatted": "",
                    "citation": None
                }
                
            # Create a properly formatted citation
            formatted = ""
            
            if citation.get("title"):
                formatted += f"{citation['title']}"
            
            if citation.get("publisher"):
                if formatted:
                    formatted += f", {citation['publisher']}"
                else:
                    formatted += f"{citation['publisher']}"
            
            if citation.get("year"):
                formatted += f" ({citation['year']})"
            elif citation.get("access_date"):
                # Extract year from access date if available
                try:
                    year = citation["access_date"].split(", ")[-1]
                    formatted += f" ({year})"
                except (IndexError, AttributeError):
                    pass
            
            if citation.get("url"):
                formatted += f". Available at: {citation['url']}"
            
            if citation.get("access_date"):
                formatted += f" [Accessed: {citation['access_date']}]"
                
            return {
                "status": "success",
                "formatted": formatted,
                "citation": citation
            }
        except Exception as e:
            logger.error(f"Error formatting citation: {e}")
            return {
                "status": "error",
                "message": str(e),
                "formatted": "",
                "citation": citation
            }
    
    def batch_format_citations(self, citations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Format multiple citations
        
        Args:
            citations: List of citation objects
            
        Returns:
            Dictionary with status and list of formatted citations
        """
        try:
            if not citations:
                return {
                    "status": "success",
                    "formatted_citations": [],
                    "count": 0
                }
                
            formatted_citations = []
            
            for citation in citations:
                result = self.format_citation(citation)
                if result["status"] == "success":
                    formatted_citations.append({
                        "formatted": result["formatted"],
                        "citation": citation
                    })
            
            return {
                "status": "success",
                "formatted_citations": formatted_citations,
                "count": len(formatted_citations)
            }
        except Exception as e:
            logger.error(f"Error batch formatting citations: {e}")
            return {
                "status": "error",
                "message": str(e),
                "formatted_citations": []
            }