"""
Simple script to view the Neo4j schema.
"""
import asyncio
import json
from src.tools.schema_tool import SchemaTool

async def get_schema():
    """Fetch and display the schema."""
    tool = SchemaTool('https://dengue-fastapi-dengue-kg-project.apps.cluster-8gvkk.8gvkk.sandbox888.opentlc.com/schema')
    schema = await tool.get_schema()
    
    print("=== Neo4j Schema ===")
    print("\nNode Labels:")
    for label in schema['node_labels']:
        print(f"- {label}")
    
    print("\nRelationship Types:")
    for rel in schema['relationship_types']:
        print(f"- {rel}")
    
    print("\nDetailed Schema:")
    print(json.dumps(schema, indent=2))

if __name__ == "__main__":
    asyncio.run(get_schema())
