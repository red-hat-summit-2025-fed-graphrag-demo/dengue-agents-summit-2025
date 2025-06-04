"""
Test script for the Knowledge Graph API connection.

This script tests the connection to the Knowledge Graph API and performs
basic queries to ensure data access is working correctly.

Usage:
    python test_graph_connection.py
"""
import os
import sys
import json
import asyncio
import logging
from dotenv import load_dotenv
from typing import Dict, List, Tuple, Optional, Any
import httpx

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add some color to logs if supported
try:
    import colorama
    colorama.init()
    GREEN = colorama.Fore.GREEN
    RED = colorama.Fore.RED
    YELLOW = colorama.Fore.YELLOW
    RESET = colorama.Style.RESET_ALL
except ImportError:
    GREEN = ""
    RED = ""
    YELLOW = ""
    RESET = ""

# Load environment variables
load_dotenv()

# Knowledge Graph API configuration
KG_API_URL = os.getenv("KG_API_URL")

# Test queries
TEST_QUERIES = [
    {
        "name": "Count all nodes",
        "query": "MATCH (n) RETURN count(n) as count",
        "expected": lambda result: result.get("count", 0) > 0,
        "error_message": "No nodes found in the database"
    },
    {
        "name": "Count dengue nodes",
        "query": "MATCH (n:Disease {name: 'Dengue Fever'}) RETURN count(n) as count",
        "expected": lambda result: result.get("count", 0) > 0,
        "error_message": "No Dengue Fever nodes found"
    },
    {
        "name": "Get node types",
        "query": "MATCH (n) RETURN distinct labels(n) as node_types LIMIT 5",
        "expected": lambda result: "node_types" in result and len(result["node_types"]) > 0,
        "error_message": "No node types found"
    },
    {
        "name": "Find dengue symptoms",
        "query": """
        MATCH (d:Disease {name: 'Dengue Fever'})-[:HAS_SYMPTOM]->(s:Symptom)
        RETURN s.name as symptom
        LIMIT 5
        """,
        "expected": lambda result: "symptom" in result,
        "error_message": "No symptoms found for Dengue Fever"
    },
    {
        "name": "Check relationships",
        "query": """
        MATCH ()-[r]->() 
        RETURN type(r) as relationship_type, count(r) as count
        ORDER BY count DESC
        LIMIT 5
        """,
        "expected": lambda result: "relationship_type" in result and "count" in result,
        "error_message": "No relationships found"
    }
]

async def discover_graph_api_endpoints(base_url: str) -> List[str]:
    """
    Discover available API endpoints for the Knowledge Graph API.
    
    Args:
        base_url: Base URL of the Knowledge Graph API
        
    Returns:
        List of discovered endpoints
    """
    discovered_endpoints = []
    
    # Ensure URL has no trailing slash
    base_url = base_url.rstrip('/')
    
    # Common API endpoints to try
    endpoints_to_try = [
        "/",
        "/api",
        "/api/v1",
        "/docs",
        "/swagger",
        "/health",
        "/status",
        "/graph",
        "/cypher"
    ]
    
    logger.info(f"Discovering available endpoints at {base_url}...")
    
    for endpoint in endpoints_to_try:
        endpoint_url = f"{base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(endpoint_url)
                
            # If successful, add to discovered endpoints
            if response.status_code < 400:  # Anything not an error (200-399)
                discovered_endpoints.append(endpoint)
                logger.info(f"Discovered endpoint: {endpoint} (Status: {response.status_code})")
        except Exception:
            # Ignore errors during discovery
            pass
    
    return discovered_endpoints

async def test_kg_api_connection() -> Tuple[bool, str, List[str]]:
    """
    Test Knowledge Graph API connection and discover available endpoints.
    
    Returns:
        Tuple of (success, details, discovered_endpoints)
    """
    try:
        if not KG_API_URL:
            return False, "Knowledge Graph API URL not found in environment variables", []
        
        # Ensure URL has no trailing slash
        base_url = KG_API_URL.rstrip('/')
        health_url = f"{base_url}/health"
        
        # Test the health endpoint
        logger.info(f"Testing health endpoint: {health_url}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(health_url)
            
        if response.status_code == 200:
            # Discover available endpoints
            discovered_endpoints = await discover_graph_api_endpoints(base_url)
            return True, f"Successfully connected to Knowledge Graph API at {KG_API_URL}", discovered_endpoints
        else:
            return False, f"API returned status code {response.status_code}: {response.text}", []
            
    except Exception as e:
        return False, f"Error connecting to Knowledge Graph API: {str(e)}", []

async def find_graph_query_endpoint(base_url: str) -> Tuple[bool, str, Optional[str]]:
    """
    Find the correct endpoint for executing graph queries.
    
    Args:
        base_url: Base URL of the Knowledge Graph API
        
    Returns:
        Tuple of (success, message, endpoint_path)
    """
    # Ensure URL has no trailing slash
    base_url = base_url.rstrip('/')
    
    # Try different endpoint variations to find the correct one for graph queries
    possible_endpoints = [
        "/graph/query",
        "/api/graph/query",
        "/api/v1/graph/query",
        "/cypher",
        "/api/cypher",
        "/query",
        "/api/query"
    ]
    
    # Simple test query
    query_data = {
        "query": "MATCH (n) RETURN count(n) as count LIMIT 1"
    }
    
    for endpoint in possible_endpoints:
        endpoint_url = f"{base_url}{endpoint}"
        logger.info(f"Testing graph query endpoint: {endpoint_url}")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    endpoint_url,
                    json=query_data
                )
                
            # Log response status
            logger.info(f"Response status: {response.status_code}")
            
            # If successful, return endpoint
            if response.status_code == 200:
                try:
                    # Try to parse the response to verify it's a valid graph response
                    result = response.json()
                    
                    # Check if it's a valid response with results
                    if "results" in result or "count" in result:
                        return True, f"Found working graph query endpoint: {endpoint}", endpoint
                except Exception as e:
                    logger.warning(f"Endpoint returned 200 but couldn't parse JSON: {str(e)}")
                    continue
        except Exception as e:
            logger.warning(f"Error testing endpoint {endpoint}: {str(e)}")
            continue
            
    # If we've tried all endpoints and none worked
    return False, "Could not find working graph query endpoint", None

async def run_test_query(query_info: Dict, graph_endpoint: str) -> Tuple[bool, Dict, str]:
    """
    Run a test query against the Knowledge Graph API.
    
    Args:
        query_info: Dictionary with query information
        graph_endpoint: Graph query endpoint path
        
    Returns:
        Tuple of (success, result, error_message)
    """
    try:
        if not KG_API_URL:
            return False, {}, "Knowledge Graph API URL not found in environment variables"
            
        # Ensure URL has no trailing slash
        base_url = KG_API_URL.rstrip('/')
        query_url = f"{base_url}{graph_endpoint}"
        
        # Prepare query payload
        payload = {
            "query": query_info["query"].strip()
        }
        
        logger.info(f"Executing query: {query_info['query'].strip()}")
        logger.info(f"Endpoint: {query_url}")
        
        # Execute query
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                query_url,
                json=payload
            )
            
        # Check response
        if response.status_code == 200:
            result_data = response.json()
            
            # Try different result formats
            if "results" in result_data and len(result_data["results"]) > 0:
                result = result_data["results"][0]
            else:
                # Assume the entire response is the result
                result = result_data
                
            # Check expected condition
            if query_info["expected"](result):
                return True, result, ""
            else:
                return False, result, query_info["error_message"]
        else:
            return False, {}, f"Query failed with status {response.status_code}: {response.text}"
            
    except Exception as e:
        return False, {}, f"Error running query: {str(e)}"

async def main() -> None:
    """Main function to run all tests."""
    print("\n" + "=" * 60)
    print(" KNOWLEDGE GRAPH API CONNECTION TEST ".center(60, "="))
    print("=" * 60)
    
    # Test basic connection and discover endpoints
    connection_success, connection_message, discovered_endpoints = await test_kg_api_connection()
    
    if connection_success:
        print(f"{GREEN}✅ Connection test:{RESET} {connection_message}")
        
        if discovered_endpoints:
            print(f"\nDiscovered API endpoints:")
            for endpoint in discovered_endpoints:
                print(f"  - {endpoint}")
        
        # Find the graph query endpoint
        logger.info("\nDiscovering graph query endpoint...")
        endpoint_success, endpoint_message, graph_endpoint = await find_graph_query_endpoint(KG_API_URL)
        
        if endpoint_success:
            print(f"{GREEN}✅ Endpoint discovery:{RESET} {endpoint_message}")
            
            # Run test queries
            all_queries_passed = True
            
            for i, query_info in enumerate(TEST_QUERIES):
                print(f"\nRunning query {i+1}: {query_info['name']}")
                print(f"Query: {query_info['query'].strip()}")
                
                success, result, error = await run_test_query(query_info, graph_endpoint)
                
                if success:
                    print(f"{GREEN}✅ Query succeeded:{RESET}")
                    print(json.dumps(result, indent=2))
                else:
                    all_queries_passed = False
                    print(f"{RED}❌ Query failed:{RESET} {error}")
                    if result:
                        print(f"Result: {json.dumps(result, indent=2)}")
            
            print("\n" + "=" * 60)
            if all_queries_passed:
                print(f"{GREEN}🎉 All Knowledge Graph API test queries passed!{RESET}")
            else:
                print(f"{YELLOW}⚠️  Some Knowledge Graph API test queries failed. Check the logs for details.{RESET}")
        else:
            print(f"{RED}❌ Endpoint discovery failed:{RESET} {endpoint_message}")
            print("\n" + "=" * 60)
            print(f"{RED}⚠️  Could not find a working graph query endpoint.{RESET}")
    else:
        print(f"{RED}❌ Connection test failed:{RESET} {connection_message}")
        print("\n" + "=" * 60)
        print(f"{RED}⚠️  Could not connect to the Knowledge Graph API.{RESET}")
    
    print("=" * 60 + "\n")
    
    # Exit with error code if connection failed
    if not connection_success:
        sys.exit(1)
    # Exit with error code if we couldn't find a working query endpoint
    elif not endpoint_success:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
