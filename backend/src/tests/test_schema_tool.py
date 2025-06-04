"""
Test script for the Schema Tool.

This script tests the basic functionality of the Schema Tool to ensure 
it can connect to the Neo4j database and retrieve the basic schema.

Usage:
    python test_schema_tool.py
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

# Set the proper Python path for imports
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

# Import the Schema Tool
try:
    # Try direct import from tools package
    from tools.schema_tool import SchemaTool
    logger.info("Imported SchemaTool directly from tools")
except ImportError:
    try:
        # Try import with src prefix
        from src.tools.schema_tool import SchemaTool
        logger.info("Imported SchemaTool with src prefix")
    except ImportError:
        try:
            # Try relative import
            import sys
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            from tools.schema_tool import SchemaTool
            logger.info("Imported SchemaTool with relative import")
        except ImportError:
            # Try importing from parent directory
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "schema_tool", 
                os.path.join(src_dir, "tools/schema_tool.py")
            )
            schema_tool_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(schema_tool_module)
            SchemaTool = schema_tool_module.SchemaTool
            logger.info("Imported SchemaTool using importlib")

# Load environment variables
load_dotenv()

async def test_schema_connection() -> bool:
    """
    Test if the Schema tool can connect to the database and retrieve the basic schema.
    
    Returns:
        True if the connection and schema retrieval is successful, False otherwise
    """
    try:
        # Create a SchemaTool instance
        schema_tool = SchemaTool()
        print(f"Created SchemaTool with endpoint: {schema_tool.schema_endpoint}")
        
        # Get the schema
        print("Retrieving schema...")
        schema = await schema_tool.get_schema()
        print(f"Schema retrieved successfully")
        
        # Check if we got a valid schema structure
        if schema and isinstance(schema, dict):
            # Check for basic schema elements
            has_node_labels = "node_labels" in schema and isinstance(schema["node_labels"], list)
            has_rel_types = "relationship_types" in schema and isinstance(schema["relationship_types"], list)
            
            if has_node_labels and has_rel_types:
                print(f"{GREEN}✅ Successfully retrieved schema with {len(schema['node_labels'])} node labels and {len(schema['relationship_types'])} relationship types{RESET}")
                return True
            else:
                print(f"{RED}❌ Retrieved schema is missing expected structure{RESET}")
                print(f"Available keys: {', '.join(schema.keys())}")
                return False
        else:
            print(f"{RED}❌ Retrieved schema is not a valid dictionary{RESET}")
            return False
            
    except Exception as e:
        print(f"{RED}❌ Error retrieving schema: {str(e)}{RESET}")
        return False

async def main() -> None:
    """Main function to run the test."""
    print("\n" + "=" * 60)
    print(" SCHEMA TOOL TEST ".center(60, "="))
    print("=" * 60)
    
    try:
        # Run the basic connection test
        success = await test_schema_connection()
        
        print("\n" + "=" * 60)
        if success:
            print(f"{GREEN}🎉 Schema Tool test passed!{RESET}")
            print("=" * 60 + "\n")
        else:
            print(f"{RED}⚠️  Schema Tool test failed.{RESET}")
            print("=" * 60 + "\n")
            sys.exit(1)
            
    except Exception as e:
        print(f"{RED}❌ Unexpected error during test: {str(e)}{RESET}")
        print("\n" + "=" * 60)
        print(f"{RED}⚠️  Could not complete Schema Tool test.{RESET}")
        print("=" * 60 + "\n")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())