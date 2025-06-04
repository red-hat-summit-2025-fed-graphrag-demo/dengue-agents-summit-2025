"""
Direct test of Cypher queries against the knowledge graph.
"""
import os
import sys
import json
import logging
import asyncio
import httpx
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add the project root to the Python path
project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("query_test")

async def run_cypher_query(query: str, api_url: Optional[str] = None) -> Dict[str, Any]:
    """Run a Cypher query directly against the knowledge graph API"""
    kg_api_url = api_url or os.environ.get(
        "KG_API_URL", 
        "https://dengue-fastapi-dengue-kg-project.apps.cluster-8gvkk.8gvkk.sandbox888.opentlc.com"
    )
    query_endpoint = f"{kg_api_url}/query/cypher"
    
    logger.info(f"Running Cypher query against endpoint: {query_endpoint}")
    logger.info(f"Query: {query}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                query_endpoint,
                json={"query": query},
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            return result
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        return {"error": str(e), "results": []}

async def test_basic_queries():
    """Run a series of basic queries to verify data access"""
    
    # List of test queries to run
    test_queries = [
        # Basic count of dengue fever nodes
        "MATCH (d:Disease {name: 'Dengue Fever'}) RETURN count(d) as count",
        
        # Count of symptoms linked to dengue fever
        "MATCH (d:Disease {name: 'Dengue Fever'})-[:HAS_SYMPTOM]->(s:Symptom) RETURN count(s) as symptom_count",
        
        # Get all symptom names for dengue fever
        "MATCH (d:Disease {name: 'Dengue Fever'})-[:HAS_SYMPTOM]->(s:Symptom) RETURN s.name as symptom, s.description as description",
        
        # Count relationships between climate factors and disease
        "MATCH (d:Disease {name: 'Dengue Fever'})-[r:HAS_CLIMATE_FACTOR]->(c:ClimateFactor) RETURN count(c) as climate_factor_count",
        
        # Check for citation nodes
        "MATCH (c:Citation) RETURN count(c) as citation_count LIMIT 5",
        
        # Test relationship pattern from one of the failing queries
        "MATCH (cf:ClimateFactor)-[:HAS_CLIMATE_FACTOR_ON]->(v:Vector) RETURN count(cf) as count"
    ]
    
    # Output directory for results
    output_dir = os.path.join(project_root, "query_test_results")
    os.makedirs(output_dir, exist_ok=True)
    
    # Run each query and save results
    all_results = {}
    for i, query in enumerate(test_queries):
        query_id = f"query_{i+1}"
        logger.info(f"Running {query_id}: {query}")
        
        try:
            result = await run_cypher_query(query)
            
            # Save individual query result
            query_file = os.path.join(output_dir, f"{query_id}.json")
            with open(query_file, "w") as f:
                json.dump(result, f, indent=2)
                
            all_results[query_id] = {
                "query": query,
                "result": result
            }
            
            # Log summary of results
            if "error" in result:
                logger.error(f"Query {query_id} failed: {result['error']}")
            else:
                result_count = len(result.get("results", []))
                logger.info(f"Query {query_id} returned {result_count} result(s)")
                
                # For count queries, show the count value
                if "count" in query.lower() and result_count > 0:
                    rows = result.get("results", [])
                    if rows and len(rows) > 0:
                        first_row = rows[0]
                        for key, value in first_row.items():
                            if "count" in key.lower():
                                logger.info(f"Count value: {value}")
        
        except Exception as e:
            logger.error(f"Error processing query {query_id}: {str(e)}")
            all_results[query_id] = {
                "query": query,
                "error": str(e)
            }
    
    # Create a consolidated report
    report_file = os.path.join(output_dir, "direct_query_report.md")
    with open(report_file, "w") as f:
        f.write("# Direct Cypher Query Test Results\n\n")
        
        for query_id, data in all_results.items():
            f.write(f"## {query_id}\n\n")
            f.write("### Query\n\n")
            f.write("```cypher\n")
            f.write(data["query"])
            f.write("\n```\n\n")
            
            f.write("### Results\n\n")
            if "error" in data:
                f.write(f"**ERROR:** {data['error']}\n\n")
            else:
                result = data["result"]
                if "error" in result:
                    f.write(f"**ERROR:** {result['error']}\n\n")
                else:
                    rows = result.get("results", [])
                    result_count = len(rows)
                    f.write(f"**Count:** {result_count} result(s)\n\n")
                    
                    if result_count > 0:
                        f.write("#### Sample Data\n\n")
                        f.write("| " + " | ".join(rows[0].keys()) + " |\n")
                        f.write("| " + " | ".join(["---" for _ in rows[0].keys()]) + " |\n")
                        
                        # Show up to 10 rows
                        for row in rows[:10]:
                            f.write("| " + " | ".join([str(v) for v in row.values()]) + " |\n")
                            
                        if result_count > 10:
                            f.write("\n*... and more rows*\n")
    
    logger.info(f"Consolidated report saved to {report_file}")
    return report_file, all_results

if __name__ == "__main__":
    report_file, results = asyncio.run(test_basic_queries())
    print(f"\nReport saved to: {report_file}")
    
    # Display summary of failures if any
    failures = sum(1 for data in results.values() if "error" in data or "error" in data.get("result", {}))
    if failures > 0:
        print(f"\n⚠️ {failures} queries failed - check the report for details")
    else:
        print("\n✅ All queries executed successfully")
