"""
Test script for the Cypher Tool.

This script tests the functionality of the Cypher Tool for executing
Neo4j Cypher queries via the REST API.

Usage:
    python test_cypher_tool.py
"""
import os
import sys
import json
import asyncio
import logging
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional

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

# Set the proper Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

# Set Python module path to be able to import from tests directory
os.environ['PYTHONPATH'] = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# Import the Cypher Tool
from src.tools import CypherTool

# Load environment variables
load_dotenv()

# Test queries
TEST_QUERIES = [
    {
        "name": "Count all nodes",
        "query": "MATCH (n) RETURN count(n) as count",
        "expected_keys": ["count"],
        "error_message": "Failed to count nodes"
    },
    {
        "name": "Get node types",
        "query": "MATCH (n) RETURN distinct labels(n) as node_types LIMIT 5",
        "expected_keys": ["node_types"],
        "error_message": "Failed to get node types"
    },
    {
        "name": "Find dengue symptoms",
        "query": """
        MATCH (d:Disease {name: 'Dengue Fever'})-[:HAS_SYMPTOM]->(s:Symptom)
        RETURN s.name as symptom
        LIMIT 5
        """,
        "expected_keys": ["symptom"],
        "error_message": "Failed to find dengue symptoms"
    },
    {
        "name": "Test invalid query",
        "query": "MATCH n RETURN count(n",  # Deliberately malformed query
        "expected_error": True,
        "error_message": "Invalid query did not raise an error"
    }
]

async def run_test_queries(cypher_tool: CypherTool) -> bool:
    """
    Run a set of test queries to verify the Cypher Tool functionality.
    
    Args:
        cypher_tool: The CypherTool instance to test
        
    Returns:
        True if all tests passed, False otherwise
    """
    all_passed = True
    
    for test in TEST_QUERIES:
        try:
            print(f"\nRunning query: {test['name']}")
            print(f"Query: {test['query'].strip()}")
            
            if test.get("expected_error", False):
                # This test is expected to fail
                try:
                    result = await cypher_tool.execute_query(test["query"])
                    print(f"{RED}❌ Query did not raise an expected error:{RESET}")
                    print(json.dumps(result, indent=2))
                    all_passed = False
                except Exception as e:
                    print(f"{GREEN}✅ Query raised an expected error:{RESET} {str(e)}")
            else:
                # This test is expected to succeed
                result = await cypher_tool.execute_query(test["query"])
                
                # Format the results
                formatted_result = cypher_tool.format_results(result)
                
                print("Raw result:")
                print(json.dumps(result, indent=2, default=str))
                
                print("\nFormatted result:")
                print(json.dumps(formatted_result, indent=2, default=str))
                
                # Check if the expected keys exist in the results
                keys_found = []
                
                # Try to find expected keys in different result formats
                if "data" in formatted_result and len(formatted_result["data"]) > 0:
                    if "rows" in formatted_result["data"][0] and len(formatted_result["data"][0]["rows"]) > 0:
                        keys_found = list(formatted_result["data"][0]["rows"][0].keys())
                elif "results" in result and len(result["results"]) > 0:
                    keys_found = result["results"][0].get("columns", [])
                else:
                    # Try to find keys directly in the result
                    keys_found = list(result.keys())
                
                # Check if expected keys exist
                expected_keys = test.get("expected_keys", [])
                found_all_keys = all(key in keys_found for key in expected_keys)
                
                if found_all_keys:
                    print(f"{GREEN}✅ Query succeeded:{RESET} Found expected keys: {', '.join(expected_keys)}")
                else:
                    print(f"{RED}❌ Query failed:{RESET} {test['error_message']}")
                    print(f"Expected keys: {', '.join(expected_keys)}")
                    print(f"Found keys: {', '.join(keys_found)}")
                    all_passed = False
                    
        except Exception as e:
            if test.get("expected_error", False):
                print(f"{GREEN}✅ Query raised an expected error:{RESET} {str(e)}")
            else:
                print(f"{RED}❌ Query failed with error:{RESET} {str(e)}")
                all_passed = False
    
    return all_passed

async def main() -> None:
    """Main function to run all tests."""
    print("\n" + "=" * 60)
    print(" CYPHER TOOL TEST ".center(60, "="))
    print("=" * 60)
    
    try:
        # Create a CypherTool instance
        cypher_tool = CypherTool()
        print(f"Created CypherTool with endpoint: {cypher_tool.query_endpoint}")
        
        # Run the test queries
        all_passed = await run_test_queries(cypher_tool)
        
        print("\n" + "=" * 60)
        if all_passed:
            print(f"{GREEN}🎉 All Cypher Tool tests passed!{RESET}")
        else:
            print(f"{YELLOW}⚠️  Some Cypher Tool tests failed. Check the logs for details.{RESET}")
        print("=" * 60 + "\n")
        
        # Exit with error code if any test failed
        if not all_passed:
            sys.exit(1)
            
    except Exception as e:
        print(f"{RED}❌ Failed to initialize Cypher Tool:{RESET} {str(e)}")
        print("\n" + "=" * 60)
        print(f"{RED}⚠️  Could not complete Cypher Tool tests.{RESET}")
        print("=" * 60 + "\n")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
