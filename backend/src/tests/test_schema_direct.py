"""
Direct test of the schema tool to retrieve and display the Neo4j database schema.
"""
import os
import sys
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List

# Add the project root to the Python path
project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))

from src.tools.schema_tool import SchemaTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("schema_test")

async def test_schema_retrieval():
    """Directly test schema retrieval without going through agents"""
    logger.info("Initializing schema tool and retrieving schema directly")
    
    # Load environment variables to get endpoint from .env
    # Get the KG_API_URL from environment or default to the standard dengue endpoint
    kg_api_url = os.environ.get(
        "KG_API_URL", 
        "https://dengue-fastapi-dengue-kg-project.apps.cluster-8gvkk.8gvkk.sandbox888.opentlc.com"
    )
    schema_endpoint = f"{kg_api_url}/schema"
    
    logger.info(f"Using schema endpoint: {schema_endpoint}")
    
    # Initialize the schema tool with the endpoint
    schema_tool = SchemaTool(api_url=kg_api_url)
    
    # Retrieve the schema
    schema = await schema_tool.get_schema()
    
    # Save schema to a file for inspection
    output_file = os.path.join(project_root, "schema_direct_output.json")
    with open(output_file, "w") as f:
        json.dump(schema, f, indent=2)
    
    # Display summary info
    if schema and isinstance(schema, dict):
        node_labels = schema.get("node_labels", [])
        relationship_types = schema.get("relationship_types", [])
        
        logger.info(f"Retrieved schema with {len(node_labels)} node labels and {len(relationship_types)} relationship types")
        logger.info(f"Node labels: {', '.join(node_labels)}")
        logger.info(f"Relationship types: {', '.join(relationship_types)}")
        
        # Create a markdown report with more details
        report_file = os.path.join(project_root, "schema_direct_report.md")
        with open(report_file, "w") as f:
            f.write("# Neo4j Schema Report\n\n")
            
            f.write("## Node Labels\n\n")
            for label in node_labels:
                f.write(f"- `{label}`\n")
            
            f.write("\n## Relationship Types\n\n")
            for rel in relationship_types:
                f.write(f"- `{rel}`\n")
            
            # Include property keys if available
            if "property_keys" in schema:
                f.write("\n## Property Keys\n\n")
                for prop in schema["property_keys"]:
                    f.write(f"- `{prop}`\n")
            
            # Include full schema details for reference
            f.write("\n## Full Schema JSON\n\n")
            f.write("```json\n")
            f.write(json.dumps(schema, indent=2))
            f.write("\n```\n")
        
        logger.info(f"Detailed schema report saved to {report_file}")
    else:
        logger.error(f"Failed to retrieve schema or unexpected format: {schema}")
    
    return output_file, schema

if __name__ == "__main__":
    output_file, schema = asyncio.run(test_schema_retrieval())
    print(f"\nSchema saved to: {output_file}")
    print("Summary of found data:")
    if schema:
        print(f"Node labels: {len(schema.get('node_labels', []))}")
        print(f"Relationship types: {len(schema.get('relationship_types', []))}")
    else:
        print("No schema data retrieved.")
