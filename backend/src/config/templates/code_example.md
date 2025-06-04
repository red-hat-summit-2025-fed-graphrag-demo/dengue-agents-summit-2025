# Dengue Data Analysis Code Example

{% if visualization_data %}
[VISUALIZATION: Graph showing key aspects of dengue data]
{% endif %}

## Background Information

{{ background_information }}

{% if last_graph_results and last_graph_results.data %}
## Available Data

The following data is available for analysis:

{% for item in last_graph_results.data %}
- **{{ item.entity_type if item.entity_type else "Data" }}**: {{ item.description if item.description else item.name if item.name else "Data point" }}
{% endfor %}
{% endif %}

## Code Example

```{{ code_language }}
{{ code_solution }}
```

{% if code_explanation %}
## Code Explanation

{{ code_explanation }}
{% endif %}

{% if code_usage_example %}
## Example Usage

```{{ code_language }}
{{ code_usage_example }}
```

{% if code_output %}
### Expected Output

```
{{ code_output }}
```
{% endif %}
{% endif %}

## Additional Information

{{ additional_information }}

{% if last_assessment.citations %}
## Sources

{% for citation in last_assessment.citations %}
- {{ citation.authors }} ({{ citation.year }}). {{ citation.title }}. *{{ citation.journal }}*
{% endfor %}
{% endif %}
