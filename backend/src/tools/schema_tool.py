"""
Schema Tool for Neo4j.

This module provides utilities for retrieving the current schema from a Neo4j database
via the REST API. It retrieves node labels, relationship types, and property keys.

Usage:
    from src.tools.schema_tool import SchemaTool
    
    # Create a tool instance
    schema_tool = SchemaTool()
    
    # Get the current schema
    schema = await schema_tool.get_schema()
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

class SchemaTool:
    """Tool for retrieving schema information from a Neo4j database via REST API."""
    
    def __init__(self, api_url: Optional[str] = None):
        """
        Initialize the Schema tool.
        
        Args:
            api_url: Optional override for the Neo4j API URL.
                     If not provided, uses the KG_API_URL environment variable.
        """
        self.api_url = api_url or os.getenv("KG_API_URL")
        if not self.api_url:
            raise ValueError("Neo4j API URL not configured. Set KG_API_URL environment variable or provide api_url parameter.")
        
        # Ensure URL has no trailing slash
        self.api_url = self.api_url.rstrip('/')
        self.schema_endpoint = f"{self.api_url}/schema"
        
        # This is the endpoint for running Cypher queries (used as fallback)
        self.query_endpoint = f"{self.api_url}/query/cypher"
        
        logger.info(f"Initialized SchemaTool with endpoint: {self.schema_endpoint}")

    async def get_schema(self) -> Dict[str, Any]:
        """
        Retrieve the current schema from the Neo4j database.
        
        Returns:
            Dict containing schema information including node labels, relationship types, and property keys
            
        Raises:
            httpx.HTTPStatusError: If the API returns an error response
            httpx.RequestError: If there's a network or connection error
            Exception: For other unexpected errors
        """
        try:
            logger.info(f"Retrieving schema from: {self.schema_endpoint}")
            
            # Try the dedicated schema endpoint first
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.schema_endpoint)
                
            # If successful, return the schema
            if response.status_code == 200:
                return response.json()
                
            # If the schema endpoint doesn't exist, fall back to queries
            logger.info(f"Schema endpoint returned status {response.status_code}, falling back to queries")
            return await self._get_schema_from_queries()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error retrieving schema: {e.response.status_code} - {e.response.text}")
            # Try schema from queries as fallback
            return await self._get_schema_from_queries()
            
        except httpx.RequestError as e:
            logger.error(f"Request error retrieving schema: {str(e)}")
            # Try schema from queries as fallback
            return await self._get_schema_from_queries()
            
        except Exception as e:
            logger.error(f"Unexpected error retrieving schema: {str(e)}")
            raise
    
    async def _get_schema_from_queries(self) -> Dict[str, Any]:
        """
        Retrieve schema information using Cypher queries.
        
        This is a fallback method used when the dedicated schema endpoint is not available.
        
        Returns:
            Dict containing schema information
        """
        schema = {
            "nodeLabels": [],
            "relationshipTypes": [],
            "propertyKeys": []
        }
        
        # Queries to get schema information
        queries = [
            {
                "name": "nodeLabels",
                "query": "CALL db.labels()"
            },
            {
                "name": "relationshipTypes",
                "query": "CALL db.relationshipTypes()"
            },
            {
                "name": "propertyKeys",
                "query": "CALL db.propertyKeys()"
            }
        ]
        
        try:
            for query_info in queries:
                logger.info(f"Executing schema query: {query_info['query']}")
                
                payload = {
                    "query": query_info["query"]
                }
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        self.query_endpoint,
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                
                # Process response
                if response.status_code == 200:
                    result_data = response.json()
                    
                    # Handle different response formats
                    if "results" in result_data and isinstance(result_data["results"], list):
                        # Standard Neo4j REST API format
                        result = result_data["results"][0]
                        
                        # Extract values based on the field name
                        field_name = None
                        if query_info["name"] == "nodeLabels":
                            field_name = "label"
                        elif query_info["name"] == "relationshipTypes":
                            field_name = "relationshipType"
                        elif query_info["name"] == "propertyKeys":
                            field_name = "propertyKey"
                        
                        if field_name and "data" in result:
                            # Extract from data rows
                            for row in result["data"]:
                                if "row" in row and row["row"]:
                                    schema[query_info["name"]].append(row["row"][0])
                        elif "columns" in result and "data" in result:
                            # Extract data based on column name
                            try:
                                column_idx = result["columns"].index(field_name)
                                for row in result["data"]:
                                    if "row" in row and len(row["row"]) > column_idx:
                                        schema[query_info["name"]].append(row["row"][column_idx])
                            except (ValueError, IndexError):
                                # If column name not found, just use the first column
                                for row in result["data"]:
                                    if "row" in row and row["row"]:
                                        schema[query_info["name"]].append(row["row"][0])
                    else:
                        # Try to extract values from custom format
                        for key, value in result_data.items():
                            if isinstance(value, list) and value:
                                schema[query_info["name"]] = value
                                break
                
            return schema
                
        except Exception as e:
            logger.error(f"Error retrieving schema from queries: {str(e)}")
            # Return whatever schema info we have
            return schema
            
    async def get_node_properties(self, label: str = None) -> Dict[str, List[str]]:
        """
        Get property keys for specific node labels.
        
        Args:
            label: Optional node label to filter properties
            
        Returns:
            Dict mapping node labels to lists of property keys
        """
        try:
            query = """
            CALL apoc.meta.nodeTypeProperties()
            YIELD nodeType, propertyName
            RETURN nodeType, collect(propertyName) as properties
            """
            
            if label:
                query = f"""
                CALL apoc.meta.nodeTypeProperties()
                YIELD nodeType, propertyName
                WHERE nodeType = '{label}'
                RETURN nodeType, collect(propertyName) as properties
                """
            
            payload = {
                "query": query
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.query_endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
            # Process response
            if response.status_code == 200:
                result_data = response.json()
                node_properties = {}
                
                # Handle different response formats
                if "results" in result_data and isinstance(result_data["results"], list):
                    # Standard Neo4j REST API format
                    result = result_data["results"][0]
                    
                    if "data" in result:
                        for row in result["data"]:
                            if "row" in row and len(row["row"]) >= 2:
                                node_type = row["row"][0]
                                props = row["row"][1]
                                node_properties[node_type] = props
                
                return node_properties
            else:
                logger.error(f"Error retrieving node properties: HTTP {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Error retrieving node properties: {str(e)}")
            return {}
            
    async def get_relationship_properties(self, type_name: str = None) -> Dict[str, List[str]]:
        """
        Get property keys for specific relationship types.
        
        Args:
            type_name: Optional relationship type to filter properties
            
        Returns:
            Dict mapping relationship types to lists of property keys
        """
        try:
            query = """
            CALL apoc.meta.relTypeProperties()
            YIELD relType, propertyName
            RETURN relType, collect(propertyName) as properties
            """
            
            if type_name:
                query = f"""
                CALL apoc.meta.relTypeProperties()
                YIELD relType, propertyName
                WHERE relType = '{type_name}'
                RETURN relType, collect(propertyName) as properties
                """
            
            payload = {
                "query": query
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.query_endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
            # Process response
            if response.status_code == 200:
                result_data = response.json()
                rel_properties = {}
                
                # Handle different response formats
                if "results" in result_data and isinstance(result_data["results"], list):
                    # Standard Neo4j REST API format
                    result = result_data["results"][0]
                    
                    if "data" in result:
                        for row in result["data"]:
                            if "row" in row and len(row["row"]) >= 2:
                                rel_type = row["row"][0]
                                props = row["row"][1]
                                rel_properties[rel_type] = props
                
                return rel_properties
            else:
                logger.error(f"Error retrieving relationship properties: HTTP {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Error retrieving relationship properties: {str(e)}")
            return {}
    
    async def get_detailed_schema(self) -> Dict[str, Any]:
        """
        Get a detailed schema including nodes, relationships, and their properties.
        
        Returns:
            Dict containing detailed schema information
        """
        try:
            # Get the basic schema first
            basic_schema = await self.get_schema()
            
            # Then get property information
            node_properties = await self.get_node_properties()
            relationship_properties = await self.get_relationship_properties()
            
            # Combine into detailed schema
            detailed_schema = {
                "nodes": [],
                "relationships": []
            }
            
            # Process node information
            for label in basic_schema.get("nodeLabels", []):
                node_info = {
                    "label": label,
                    "properties": node_properties.get(label, [])
                }
                detailed_schema["nodes"].append(node_info)
            
            # Process relationship information
            for rel_type in basic_schema.get("relationshipTypes", []):
                rel_info = {
                    "type": rel_type,
                    "properties": relationship_properties.get(rel_type, [])
                }
                detailed_schema["relationships"].append(rel_info)
            
            return detailed_schema
            
        except Exception as e:
            logger.error(f"Error retrieving detailed schema: {str(e)}")
            raise
            
    async def get_sample_data(self, limit: int = 5) -> Dict[str, Any]:
        """
        Get sample data for each node label and relationship type.
        
        Args:
            limit: Maximum number of samples to retrieve for each type
            
        Returns:
            Dict containing sample data
        """
        try:
            # Get the schema first
            schema = await self.get_schema()
            
            sample_data = {
                "nodes": {},
                "relationships": {}
            }
            
            # Get sample nodes for each label
            for label in schema.get("nodeLabels", []):
                query = f"""
                MATCH (n:{label})
                RETURN n LIMIT {limit}
                """
                
                payload = {
                    "query": query
                }
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        self.query_endpoint,
                        json=payload
                    )
                    
                if response.status_code == 200:
                    result_data = response.json()
                    
                    # Extract nodes from response
                    nodes = []
                    
                    if "results" in result_data and isinstance(result_data["results"], list):
                        result = result_data["results"][0]
                        
                        if "data" in result:
                            for row in result["data"]:
                                if "row" in row and row["row"]:
                                    nodes.append(row["row"][0])
                    
                    sample_data["nodes"][label] = nodes
            
            # Get sample relationships for each type
            for rel_type in schema.get("relationshipTypes", []):
                query = f"""
                MATCH ()-[r:{rel_type}]->()
                RETURN r LIMIT {limit}
                """
                
                payload = {
                    "query": query
                }
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        self.query_endpoint,
                        json=payload
                    )
                    
                if response.status_code == 200:
                    result_data = response.json()
                    
                    # Extract relationships from response
                    relationships = []
                    
                    if "results" in result_data and isinstance(result_data["results"], list):
                        result = result_data["results"][0]
                        
                        if "data" in result:
                            for row in result["data"]:
                                if "row" in row and row["row"]:
                                    relationships.append(row["row"][0])
                    
                    sample_data["relationships"][rel_type] = relationships
            
            return sample_data
            
        except Exception as e:
            logger.error(f"Error retrieving sample data: {str(e)}")
            raise
