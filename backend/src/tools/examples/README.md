# Tool Examples

This directory contains example scripts that demonstrate how to use the agent system tools.

## Schema and Query Example

The `schema_and_query_example.py` script demonstrates how to use the `SchemaTool` and `CypherTool` together to:

1. Retrieve the Neo4j database schema
2. Execute targeted queries based on schema information
3. Process and format query results
4. Build more complex queries based on initial query results

### Running the Example

To run the example:

```bash
# From the project root directory
cd /Users/wesjackson/Code/Summit2025/dengue-agents-summit-2025
python -m backend.src.tools.examples.schema_and_query_example

# Or from the backend directory
cd /Users/wesjackson/Code/Summit2025/dengue-agents-summit-2025/backend
python src/tools/examples/schema_and_query_example.py
```

Make sure that your environment variables are properly set, especially `KG_API_URL` which points to your Neo4j API.

### Expected Output

The example will:

1. Connect to the Neo4j database
2. Retrieve the schema information
3. Execute various queries based on the schema
4. Display the formatted results

This demonstrates the full workflow from schema discovery to query execution and result formatting.

## Using the Tools in Your Code

To use these tools in your own code, you can follow this pattern:

```python
from src.tools import SchemaTool, CypherTool

# Initialize the tools
schema_tool = SchemaTool()
cypher_tool = CypherTool()

# Get schema information
schema = await schema_tool.get_schema()

# Execute a query based on schema knowledge
if "Disease" in schema.get("nodeLabels", []):
    query = """
    MATCH (d:Disease {name: 'Dengue Fever'})-[:HAS_SYMPTOM]->(s:Symptom)
    RETURN s.name as symptom
    LIMIT 5
    """
    result = await cypher_tool.execute_query(query)
    formatted_result = cypher_tool.format_results(result)
    
    # Process the results
    print(formatted_result)
```

This pattern enables dynamic interaction with the Neo4j database based on its current schema.
