"""
Test script for the Cypher Tool.

This script tests the basic functionality of the Cypher Tool to ensure 
it can connect to the Neo4j database and execute a simple query.

Usage:
    python test_cypher_tool_fix.py
"""
import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

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
    RESET = colorama.Style.RESET_ALL
except ImportError:
    GREEN = ""
    RED = ""
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

async def test_cypher_connection() -> bool:
    """
    Test if the Cypher tool can connect to the database and execute a simple query.
    
    Returns:
        True if the connection and query execution is successful, False otherwise
    """
    try:
        # Create a CypherTool instance
        cypher_tool = CypherTool()
        print(f"Created CypherTool with endpoint: {cypher_tool.query_endpoint}")
        
        # Execute a simple query to test connection
        query = "MATCH (n) RETURN count(n) as count"
        print(f"Executing query: {query}")
        
        result = await cypher_tool.execute_query(query)
        print(f"Query executed successfully")
        print(f"Response received: {result}")
        
        # Check if we got a valid response structure
        if result and "results" in result:
            print(f"{GREEN}✅ Successfully connected to the database and executed query{RESET}")
            return True
        else:
            print(f"{RED}❌ Received unexpected response format{RESET}")
            return False
            
    except Exception as e:
        print(f"{RED}❌ Error executing Cypher query: {str(e)}{RESET}")
        return False

async def main() -> None:
    """Main function to run the test."""
    print("\n" + "=" * 60)
    print(" CYPHER TOOL TEST ".center(60, "="))
    print("=" * 60)
    
    try:
        # Run the basic connection test
        success = await test_cypher_connection()
        
        print("\n" + "=" * 60)
        if success:
            print(f"{GREEN}🎉 Cypher Tool test passed!{RESET}")
            print("=" * 60 + "\n")
        else:
            print(f"{RED}⚠️  Cypher Tool test failed.{RESET}")
            print("=" * 60 + "\n")
            sys.exit(1)
            
    except Exception as e:
        print(f"{RED}❌ Unexpected error during test: {str(e)}{RESET}")
        print("\n" + "=" * 60)
        print(f"{RED}⚠️  Could not complete Cypher Tool test.{RESET}")
        print("=" * 60 + "\n")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())