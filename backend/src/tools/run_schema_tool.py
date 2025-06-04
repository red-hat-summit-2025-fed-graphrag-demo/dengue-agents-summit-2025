"""
Script to run the SchemaTool and display the Neo4j graph schema.
"""
import asyncio
import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

from schema_tool import SchemaTool

async def main():
    # Load environment variables from .env file in project root
    project_root = Path(__file__).parents[3]  # Go up 3 levels from tools dir
    env_path = project_root / '.env'
    
    if not env_path.exists():
        print(f"Error: .env file not found at {env_path}")
        sys.exit(1)
        
    load_dotenv(dotenv_path=env_path)
    
    # Get the API URL from environment
    kg_api_url = os.getenv("KG_API_URL")
    if not kg_api_url:
        print("Error: KG_API_URL not found in .env file")
        sys.exit(1)
        
    print(f"Using KG_API_URL: {kg_api_url}")
    
    # Create the schema tool
    schema_tool = SchemaTool(api_url=kg_api_url)
    
    # Get basic schema information
    print("Retrieving basic schema...")
    schema = await schema_tool.get_schema()
    print("\nSchema Overview:")
    print(json.dumps(schema, indent=2))
    
    # Get detailed schema information
    print("\nRetrieving detailed schema...")
    detailed_schema = await schema_tool.get_detailed_schema()
    print("\nDetailed Schema:")
    print(json.dumps(detailed_schema, indent=2))
    
    # Get sample data
    print("\nRetrieving sample data...")
    sample_data = await schema_tool.get_sample_data(limit=3)
    print("\nSample Data:")
    print(json.dumps(sample_data, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
