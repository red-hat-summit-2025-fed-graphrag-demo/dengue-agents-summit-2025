# Agent System Tools

This directory contains utilities and tools used by the Dengue Fever Knowledge Graph agent system.

## CypherTool

The `CypherTool` provides a simple way to execute Cypher queries against a Neo4j database via REST API, with additional capabilities for retrieving and including citations.

### Features

- Execute arbitrary Cypher queries against the Neo4j database
- Support for parameterized queries
- Automatic citation inclusion for query results
- Dedicated citation retrieval methods for nodes and topics
- Error handling and validation
- Formatting of results into usable structures

### Usage

Basic usage example:

```python
from src.tools import CypherTool

# Create a tool instance using environment variable KG_API_URL
cypher_tool = CypherTool()

# Or specify a custom API URL
# cypher_tool = CypherTool(api_url="http://your-neo4j-api.com")

# Execute a simple query
results = await cypher_tool.execute_query("MATCH (n) RETURN count(n) as count")

# Execute a parameterized query
params = {"name": "Dengue Fever"}
results = await cypher_tool.execute_query(
    "MATCH (d:Disease {name: $name})-[:HAS_SYMPTOM]->(s:Symptom) RETURN s.name as symptom LIMIT 5",
    params=params
)

# Format the results if needed
formatted_results = cypher_tool.format_results(results)
```

### Citation Support

The CypherTool includes several methods for working with citations, which is essential for RAG applications that need to cite information sources.

#### Automatically Including Citations in Queries

You can enhance any query with citation information by setting `include_citations=True`:

```python
# Execute a query and automatically include citation information
results = await cypher_tool.execute_query(
    "MATCH (d:Disease {name: 'Dengue Fever'}) RETURN d.name as disease",
    include_citations=True
)

# The results will include citation fields like source_title, source_publisher, source_url and source_citation
for result in results["results"]:
    print(f"Disease: {result['disease']}")
    print(f"Source: {result['source_title']} ({result['source_publisher']})")
    print(f"Citation: {result['source_citation']}")
    print(f"URL: {result['source_url']}")
```

#### Retrieving Citations for Specific Nodes

To get all citations for a specific node:

```python
# Get citations for a disease
disease_citations = await cypher_tool.get_citations_for_node(
    node_label="Disease", 
    node_id_or_name="Dengue Fever"
)

# The citations are returned as a list of citation objects
for citation_data in disease_citations["data"]:
    citation = citation_data["citation"]
    print(f"Title: {citation['title']}")
    print(f"Publisher: {citation.get('publisher', 'Unknown')}")
    print(f"URL: {citation['url']}")
    print(f"Full citation: {citation['full_text']}")
```

#### Searching for Citations by Topic

To find citations related to a specific topic:

```python
# Find citations related to "mosquito" across all nodes
topic_citations = await cypher_tool.get_citations_for_topic(
    topic="mosquito", 
    limit=5
)

# The results are grouped by the matching node's name
for topic_data in topic_citations["data"]:
    print(f"Topic: {topic_data['topic']}")
    for citation in topic_data["citations"]:
        print(f"  - {citation['title']} ({citation.get('publisher', 'Unknown')})")
        print(f"    {citation['url']}")
```

### Error Handling

The tool provides helpful error messages for common issues:

- Empty or invalid queries
- HTTP errors from the API
- Network or connection errors

Example with error handling:

```python
try:
    results = await cypher_tool.execute_query(query)
    # Process results...
except ValueError as e:
    # Handle validation or API errors
    print(f"Query error: {str(e)}")
except Exception as e:
    # Handle other unexpected errors
    print(f"Unexpected error: {str(e)}")
```

## SchemaTool

The `SchemaTool` provides functionality for retrieving schema information from a Neo4j database via REST API. It can fetch node labels, relationship types, property keys, and more detailed schema information.

### Features

- Retrieve basic schema information (node labels, relationship types, property keys)
- Get detailed schema including properties for each node label and relationship type
- Retrieve sample data for nodes and relationships
- Fallback mechanisms for when dedicated schema endpoints are not available

### Usage

Basic usage example:

```python
from src.tools import SchemaTool

# Create a tool instance using environment variable KG_API_URL
schema_tool = SchemaTool()

# Or specify a custom API URL
# schema_tool = SchemaTool(api_url="http://your-neo4j-api.com")

# Get basic schema information
schema = await schema_tool.get_schema()

# Get detailed schema including properties
detailed_schema = await schema_tool.get_detailed_schema()

# Get properties for a specific node label
disease_props = await schema_tool.get_node_properties("Disease")

# Get properties for a specific relationship type
has_symptom_props = await schema_tool.get_relationship_properties("HAS_SYMPTOM")

# Get sample data (limited to 5 items per type)
sample_data = await schema_tool.get_sample_data(limit=5)
```

### Testing

Use the provided test scripts to verify the tools' functionality:

```bash
# From the backend directory
python src/tests/test_cypher_tool_fix.py
python src/tests/test_schema_tool.py
python src/tests/test_cypher_citations.py

# Or use the run_tests.sh script
chmod +x run_tests.sh
./run_tests.sh cypher     # Test only the basic CypherTool functionality
./run_tests.sh schema     # Test only the SchemaTool
./run_tests.sh citations  # Test the citation functionality
./run_tests.sh all        # Run all tests
```

The citation tests verify:
1. Retrieving citations for specific nodes
2. Searching for citations by topic
3. Automatically including citations in query results

### Import Troubleshooting

If you encounter import errors, try the following:

1. Make sure your PYTHONPATH includes the project root:
   ```bash
   export PYTHONPATH=/path/to/dengue-agents-summit-2025
   ```

2. Try running from the project root directory:
   ```bash
   cd /path/to/dengue-agents-summit-2025
   python backend/src/tests/test_cypher_tool_fix.py
   ```

3. Use the provided shell script:
   ```bash
   cd /path/to/dengue-agents-summit-2025/backend
   ./run_tests.sh cypher
   ```

