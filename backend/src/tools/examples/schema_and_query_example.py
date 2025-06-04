#!/usr/bin/env python
"""
Example script demonstrating how to use the SchemaTool and CypherTool together.

This script retrieves the schema from the Neo4j database and then executes
targeted queries based on the schema information.

Usage:
    python schema_and_query_example.py
"""
import os
import sys
import json
import asyncio
import logging
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
tools_dir = os.path.abspath(os.path.join(current_dir, ".."))
src_dir = os.path.abspath(os.path.join(tools_dir, ".."))
backend_dir = os.path.abspath(os.path.join(src_dir, ".."))
project_dir = os.path.abspath(os.path.join(backend_dir, ".."))

# Add all potential paths
sys.path.insert(0, project_dir)
sys.path.insert(0, backend_dir)
sys.path.insert(0, src_dir)
sys.path.insert(0, tools_dir)
sys.path.insert(0, current_dir)

# Import the tools
from src.tools import CypherTool, SchemaTool

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def explore_schema_and_query() -> None:
    """
    Demonstrate how to use the SchemaTool and CypherTool together.
    """
    try:
        # Create tool instances
        schema_tool = SchemaTool()
        cypher_tool = CypherTool()
        
        logger.info("Initialized tools:")
        logger.info(f"  - SchemaTool with endpoint: {schema_tool.schema_endpoint}")
        logger.info(f"  - CypherTool with endpoint: {cypher_tool.query_endpoint}")
        
        # Step 1: Get basic schema information
        logger.info("\nStep 1: Getting basic schema information...")
        schema = await schema_tool.get_schema()
        
        print("\nBasic Schema:")
        print(json.dumps(schema, indent=2))
        
        # Step 2: Get detailed schema
        logger.info("\nStep 2: Getting detailed schema...")
        detailed_schema = await schema_tool.get_detailed_schema()
        
        print("\nDetailed Schema (abbreviated):")
        # Just show the number of node types and relationship types
        print(f"Found {len(detailed_schema['nodes'])} node types and {len(detailed_schema['relationships'])} relationship types")
        
        # Step 3: Find interesting node labels to query
        node_labels = schema.get("nodeLabels", [])
        if "Disease" in node_labels:
            # Step 4: Query disease information
            logger.info("\nStep 4: Querying disease information...")
            
            query = """
            MATCH (d:Disease)
            RETURN d.name as name, d.description as description
            LIMIT 5
            """
            
            print("\nExecuting query:")
            print(query)
            
            result = await cypher_tool.execute_query(query)
            formatted_result = cypher_tool.format_results(result)
            
            print("\nDisease Information:")
            print(json.dumps(formatted_result, indent=2, default=str))
            
            # Step 5: Find if "Dengue Fever" is in the results
            found_dengue = False
            dengue_row = None
            
            if "data" in formatted_result and formatted_result["data"]:
                if "rows" in formatted_result["data"][0] and formatted_result["data"][0]["rows"]:
                    for row in formatted_result["data"][0]["rows"]:
                        if row.get("name") == "Dengue Fever":
                            found_dengue = True
                            dengue_row = row
                            break
            
            # Step 6: If Dengue Fever is found, look for its relationships
            if found_dengue:
                logger.info("\nStep 6: Found Dengue Fever, querying relationships...")
                
                # Find relationship types for Dengue Fever
                query = """
                MATCH (d:Disease {name: 'Dengue Fever'})-[r]->(target)
                RETURN type(r) as relationship_type, labels(target) as target_labels, count(*) as count
                """
                
                print("\nExecuting query:")
                print(query)
                
                result = await cypher_tool.execute_query(query)
                formatted_result = cypher_tool.format_results(result)
                
                print("\nDengue Fever Relationships:")
                print(json.dumps(formatted_result, indent=2, default=str))
                
                # Step 7: Query specific relationships based on the schema
                relationship_types = schema.get("relationshipTypes", [])
                
                if "HAS_SYMPTOM" in relationship_types:
                    logger.info("\nStep 7: Querying Dengue Fever symptoms...")
                    
                    query = """
                    MATCH (d:Disease {name: 'Dengue Fever'})-[:HAS_SYMPTOM]->(s:Symptom)
                    RETURN s.name as symptom
                    LIMIT 10
                    """
                    
                    print("\nExecuting query:")
                    print(query)
                    
                    result = await cypher_tool.execute_query(query)
                    formatted_result = cypher_tool.format_results(result)
                    
                    print("\nDengue Fever Symptoms:")
                    print(json.dumps(formatted_result, indent=2, default=str))
                
                if "HAS_CLINICAL_MANIFESTATION" in relationship_types:
                    logger.info("\nStep 8: Querying Dengue Fever clinical manifestations...")
                    
                    query = """
                    MATCH (d:Disease {name: 'Dengue Fever'})-[:HAS_CLINICAL_MANIFESTATION]->(c:ClinicalManifestation)
                    RETURN c.name as manifestation
                    LIMIT 5
                    """
                    
                    print("\nExecuting query:")
                    print(query)
                    
                    result = await cypher_tool.execute_query(query)
                    formatted_result = cypher_tool.format_results(result)
                    
                    print("\nDengue Fever Clinical Manifestations:")
                    print(json.dumps(formatted_result, indent=2, default=str))
            
            else:
                logger.info("\nDengue Fever not found in the database")
        
        # Step 9: Execute a more complex query that joins multiple node types
        logger.info("\nStep 9: Executing a complex query...")
        
        query = """
        MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom)
        WITH d, count(s) as symptom_count
        ORDER BY symptom_count DESC
        LIMIT 5
        RETURN d.name as disease, symptom_count
        """
        
        print("\nExecuting query:")
        print(query)
        
        result = await cypher_tool.execute_query(query)
        formatted_result = cypher_tool.format_results(result)
        
        print("\nDiseases with Most Symptoms:")
        print(json.dumps(formatted_result, indent=2, default=str))
        
        print("\nExample completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in example: {str(e)}")
        raise

async def main() -> None:
    """Main function."""
    try:
        await explore_schema_and_query()
    except Exception as e:
        logger.error(f"Example failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
