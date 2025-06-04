"""
Test script for the Citation functionality in Cypher Tool.

This script tests the ability to retrieve citations and
enhance queries with citation information.

Usage:
    python test_cypher_citations.py
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

# Add the necessary paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(current_dir, ".."))
backend_dir = os.path.abspath(os.path.join(src_dir, ".."))
project_dir = os.path.abspath(os.path.join(backend_dir, ".."))

# Add all potential paths
sys.path.insert(0, project_dir)
sys.path.insert(0, backend_dir)
sys.path.insert(0, src_dir)
sys.path.insert(0, current_dir)

# Print the Python path for debugging
logger.info(f"Python path: {sys.path}")

# Try different import approaches
try:
    # Try direct import from tools package
    from tools.cypher_tool import CypherTool
    logger.info("Imported CypherTool directly from tools")
except ImportError:
    try:
        # Try import with src prefix
        from src.tools.cypher_tool import CypherTool
        logger.info("Imported CypherTool with src prefix")
    except ImportError:
        try:
            # Try relative import
            import sys
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            from tools.cypher_tool import CypherTool
            logger.info("Imported CypherTool with relative import")
        except ImportError:
            # Try importing from parent directory
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "cypher_tool", 
                os.path.join(src_dir, "tools/cypher_tool.py")
            )
            cypher_tool_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cypher_tool_module)
            CypherTool = cypher_tool_module.CypherTool
            logger.info("Imported CypherTool using importlib")

# Load environment variables
load_dotenv()

async def test_get_citations_for_node() -> bool:
    """
    Test getting citations for a specific node.
    
    Returns:
        True if the test passed, False otherwise
    """
    try:
        # Create a CypherTool instance
        cypher_tool = CypherTool()
        print(f"Created CypherTool with endpoint: {cypher_tool.query_endpoint}")
        
        # Get citations for Dengue Fever
        print("Getting citations for 'Dengue Fever'...")
        result = await cypher_tool.get_citations_for_node("Disease", "Dengue Fever")
        
        # Print the response
        print(f"Response received with {len(result.get('data', []))} citations")
        print(json.dumps(result, indent=2, default=str)[:1000] + "...")  # Limit output size
        
        # Check if we got a valid response with citations
        if result and "data" in result and len(result["data"]) > 0:
            print(f"{GREEN}✅ Successfully retrieved citations for Dengue Fever{RESET}")
            return True
        else:
            print(f"{RED}❌ No citations found for Dengue Fever{RESET}")
            return False
            
    except Exception as e:
        print(f"{RED}❌ Error getting citations: {str(e)}{RESET}")
        return False

async def test_get_citations_for_topic() -> bool:
    """
    Test getting citations for a topic using fuzzy matching.
    
    Returns:
        True if the test passed, False otherwise
    """
    try:
        # Create a CypherTool instance
        cypher_tool = CypherTool()
        
        # Get citations for a topic
        print("Getting citations for topic 'dengue'...")
        result = await cypher_tool.get_citations_for_topic("dengue", limit=5)
        
        # Print the response
        print(f"Response received with {len(result.get('data', []))} topic matches")
        print(json.dumps(result, indent=2, default=str)[:1000] + "...")  # Limit output size
        
        # Check if we got a valid response with citations
        if result and "data" in result and len(result["data"]) > 0:
            print(f"{GREEN}✅ Successfully retrieved citations for topic 'dengue'{RESET}")
            return True
        else:
            print(f"{RED}❌ No citations found for topic 'dengue'{RESET}")
            return False
            
    except Exception as e:
        print(f"{RED}❌ Error getting citations by topic: {str(e)}{RESET}")
        return False

async def test_query_with_citations() -> bool:
    """
    Test executing a query with citations included.
    
    Returns:
        True if the test passed, False otherwise
    """
    try:
        # Create a CypherTool instance
        cypher_tool = CypherTool()
        
        # Execute a query with citations included
        query = "MATCH (d:Disease {name: 'Dengue Fever'}) RETURN d.name as disease"
        print(f"Executing query with citations: {query}")
        
        result = await cypher_tool.execute_query(query, include_citations=True)
        
        # Print the response
        print(f"Response received")
        print(json.dumps(result, indent=2, default=str)[:1000] + "...")  # Limit output size
        
        # Check if citation fields are included in results
        has_citation_fields = False
        
        if "results" in result and isinstance(result["results"], list):
            for item in result["results"]:
                if "source_title" in item or "source_citation" in item:
                    has_citation_fields = True
                    break
                    
        if "columns" in result and any(col.startswith("source_") for col in result["columns"]):
            has_citation_fields = True
            
        if has_citation_fields:
            print(f"{GREEN}✅ Successfully executed query with citations included{RESET}")
            return True
        else:
            print(f"{RED}❌ Citation fields not found in query results{RESET}")
            return False
            
    except Exception as e:
        print(f"{RED}❌ Error executing query with citations: {str(e)}{RESET}")
        return False

async def main() -> None:
    """Main function to run all tests."""
    print("\n" + "=" * 70)
    print(" CYPHER CITATION TESTS ".center(70, "="))
    print("=" * 70)
    
    try:
        # Run the citation tests
        tests = [
            ("Get citations for node", await test_get_citations_for_node()),
            ("Get citations for topic", await test_get_citations_for_topic()),
            ("Query with citations", await test_query_with_citations())
        ]
        
        # Calculate test results
        all_passed = all(result for _, result in tests)
        passed_count = sum(1 for _, result in tests if result)
        
        # Print summary
        print("\n" + "=" * 70)
        print(" TEST SUMMARY ".center(70, "="))
        print("=" * 70)
        
        for name, result in tests:
            status = f"{GREEN}✅ PASS{RESET}" if result else f"{RED}❌ FAIL{RESET}"
            print(f"{name.ljust(25)} {status}")
            
        print("-" * 70)
        print(f"Passed {passed_count}/{len(tests)} tests")
        
        if all_passed:
            print(f"\n{GREEN}🎉 All Citation tests passed!{RESET}")
        else:
            print(f"\n{YELLOW}⚠️ Some Citation tests failed. Check the logs for details.{RESET}")
        print("=" * 70 + "\n")
        
        # Exit with error code if any test failed
        if not all_passed:
            sys.exit(1)
            
    except Exception as e:
        print(f"{RED}❌ Unexpected error during test: {str(e)}{RESET}")
        print("\n" + "=" * 70)
        print(f"{RED}⚠️ Could not complete Citation tests.{RESET}")
        print("=" * 70 + "\n")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())