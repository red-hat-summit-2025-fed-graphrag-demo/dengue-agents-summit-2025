# GraphRAG Template System Guide

This guide explains how to work with the template system in the GraphRAG framework, including how to add new templates, update selection criteria, and integrate templates into the response generation workflow.

## Table of Contents

- [Overview](#overview)
- [Template Structure](#template-structure)
- [Adding New Templates](#adding-new-templates)
- [Template Selection Criteria](#template-selection-criteria)
- [Testing Templates](#testing-templates)
- [Troubleshooting](#troubleshooting)

## Overview

The template system provides structured response formats for common query types, ensuring consistent, high-quality responses. The system consists of:

1. **Templates**: JSON files containing Jinja2 templates for different query types
2. **Template Registry**: Indexes and loads template files
3. **Template Selector**: Identifies which template to use based on the query
4. **Response Generator**: Renders templates with data from query results

## Template Structure

Templates are stored in `/config/templates/` organized in subdirectories by category:

```
config/templates/
├── epidemiology/
│   └── disease_transmission.json
├── general/
│   └── general_overview.json
├── symptoms/
│   └── symptom_overview.json
└── treatment/
    └── treatment_options.json
```

Each template is a JSON file with the following structure:

```json
{
  "name": "Template Name",
  "description": "Template description",
  "query_patterns": [
    "What are the symptoms of X?",
    "How do I know if I have X?"
  ],
  "markers": ["[SYMPTOM_QUERY]", "[VISUALIZATION_READY]"],
  "template_content": "# Title\n\n{% if visualization_data %}\n[VISUALIZATION: Description]\n{% endif %}\n\nTemplate content here with {{ variables }}"
}
```

Key fields:
- `name`: Display name for the template
- `description`: What this template is used for
- `query_patterns`: Example queries that should use this template
- `markers`: System markers that indicate when this template is appropriate
- `template_content`: The Jinja2 template content

## Adding New Templates

To add a new template:

1. **Create a JSON file** in an appropriate subdirectory under `/config/templates/`
2. **Define the template structure** as shown above
3. **Add query patterns** that should trigger this template
4. **Create the template content** using Jinja2 syntax
5. **Rebuild the template index** by running:

```bash
source venv/bin/activate
python build_template_index.py
```

### Template Variables

Templates can use these variables:
- `last_graph_results`: Contains the query results data
- `last_assessment`: Assessment data from the assessor agent
- `visualization_data`: Visualization data if available
- `markers`: List of markers applied to the query
- `original_query`: The original user query

Example:
```
{% for item in last_graph_results.data %}
- **{{ item.s.name }}**: {{ item.s.description }}
{% endfor %}
```

## Template Selection Criteria

The template selection logic is defined in `src/agent_system/template_criteria_selector.py` in the `TemplateCriteriaSelector` class.

### How Selection Works

Templates are selected based on:
1. **Marker matching**: Checking query markers (e.g., `[SYMPTOM_QUERY]`)
2. **Keyword matching**: Looking for specific keywords in the query
3. **Query type classification**: Using the query's general category

### Updating Selection Criteria

To modify the template selection criteria:

1. Open `src/agent_system/template_criteria_selector.py`
2. Locate the `template_criteria` dictionary in the `__init__` method:
```python
self.template_criteria = {
    "symptom_overview": {
        "keywords": ["symptom", "symptoms", "feel", "feeling", "suffer"],
        "markers": ["[SYMPTOM_QUERY]"],
        "priority": 1,
        "description": "Information about dengue fever symptoms"
    },
    # other templates...
}
```

3. **Add or modify** the criteria for each template:
   - `keywords`: List of words that suggest this template (case-insensitive)
   - `markers`: List of system markers that indicate this template
   - `priority`: Priority order (lower number = higher priority)
   - `description`: Description for logging and debugging

4. For special cases, you can also modify:
   - `_get_template_from_keywords`: Logic for keyword-based selection
   - `_get_template_from_markers`: Logic for marker-based selection
   - `_get_template_from_query_type`: Logic for query type-based selection

### Adding Edge Cases

For queries that need special handling:

1. Find the relevant method in `template_criteria_selector.py` (usually `_get_template_from_keywords`)
2. Add condition checks for the edge case:
```python
# Handle specific edge cases first
if "mortality" in query_lower or "death rate" in query_lower:
    return None  # Use free-form for mortality queries
```

## Testing Templates

### Testing Individual Templates

1. Create test queries in `test_criteria_selector.py`:
```python
TEST_QUERIES = [
    {"query": "What are symptoms of dengue?", "expected": "symptom_overview"},
    # Add more test cases...
]
```

2. Run the test:
```bash
source venv/bin/activate
python test_criteria_selector.py
```

### Testing Full Integration

1. Run the integration test that exercises the entire workflow:
```bash
source venv/bin/activate
python test_templates_integration_v2.py
```

2. Check the results in `test_results/` directory

## Troubleshooting

### Common Issues

1. **Template not being selected**: 
   - Check if keywords match the query
   - Ensure the template is registered in the index
   - Check priority values against other templates

2. **Template rendering errors**:
   - Verify Jinja2 syntax is correct
   - Check that expected variables are available in context
   - Look for missing end tags {% endif %}, {% endfor %}

3. **Missing visualization data**:
   - Make sure the visualization data is properly extracted
   - Check that markers are being correctly propagated

### Logging

Enable DEBUG level logging to see detailed template selection info:

```python
logging.getLogger('src.agent_system.template_criteria_selector').setLevel(logging.DEBUG)
```

## Best Practices

1. **Keep templates focused** on specific query types
2. **Use descriptive names** for templates and variables
3. **Test new templates** with a variety of queries
4. **Document template variables** in the template itself
5. **Use conditional sections** to handle missing data gracefully
6. **Consider priority** when templates might overlap
7. **Update keywords regularly** based on actual user queries

---

## Example: Adding a New Template

Here's a complete example of adding a new template for "prevention" queries:

1. Create file `/config/templates/prevention/prevention_measures.json`:
```json
{
  "name": "Dengue Prevention Measures",
  "description": "Template for dengue prevention queries",
  "query_patterns": [
    "How can I prevent dengue?",
    "What are prevention methods for dengue?"
  ],
  "markers": ["[PREVENTION_QUERY]"],
  "template_content": "# Dengue Fever Prevention\n\n{% if visualization_data %}\n[VISUALIZATION: Graph showing prevention methods for Dengue Fever]\n{% endif %}\n\nTo prevent dengue fever, it's important to implement the following measures:\n\n{% if last_graph_results.data %}\n{% for item in last_graph_results.data %}\n- **{{ item.measure }}**: {{ item.description }}\n{% endfor %}\n{% else %}\n- Eliminate mosquito breeding sites by removing standing water\n- Use mosquito repellents on skin and clothing\n- Install screens on windows and doors\n- Wear long-sleeved shirts and long pants\n- Use bed nets, especially during daytime\n{% endif %}\n\n## Public Health Measures\n\n- Community clean-up campaigns\n- Public education and awareness\n- Vector control programs\n\n{% if markers and '[CITATION_MISSING]' in markers %}\n*Note: Specific scientific citations for this information are not available in our knowledge base.*\n{% endif %}\n\n{% if last_assessment.citations %}\n## Sources\n{% for citation in last_assessment.citations %}\n- {{ citation.authors }} ({{ citation.year }}). {{ citation.title }}. *{{ citation.journal }}*\n{% endfor %}\n{% endif %}"
}
```

2. Update selection criteria in `template_criteria_selector.py`:
```python
self.template_criteria = {
    # existing templates...
    "prevention_measures": {
        "keywords": ["prevent", "prevention", "avoid", "protect", "stop", "control"],
        "markers": ["[PREVENTION_QUERY]"],
        "priority": 2,
        "description": "Information about dengue fever prevention"
    }
}
```

3. Add marker detection to `graph_result_assessor_agent.py`:
```python
if any(term in query_lower for term in ["prevent", "prevention", "avoid", "protect"]):
    markers.append("[PREVENTION_QUERY]")
```

4. Rebuild the template index:
```bash
python build_template_index.py
```

5. Test the new template:
```bash
python test_criteria_selector.py
```

That's it! Your new prevention template is now ready to use.
