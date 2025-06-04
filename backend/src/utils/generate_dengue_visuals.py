"""
Generate Dengue Visualizations

A standalone script that processes test results from the DengueDataVisualizationAgent
and creates visualizations that can be embedded in markdown documents.
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import re

def extract_json_from_markdown(md_file_path):
    """Extract the JSON data from a markdown file."""
    with open(md_file_path, 'r') as f:
        content = f.read()
    
    # Find the raw JSON section
    json_section_match = re.search(r'## Raw JSON Response\s+```json\s+(.*?)\s+```', content, re.DOTALL)
    if json_section_match:
        json_str = json_section_match.group(1)
        return json.loads(json_str)
    return None

def generate_chart_code(country_data, chart_id):
    """Generate the JavaScript code for a Chart.js visualization."""
    country = country_data.get("country", "Unknown")
    
    # Extract historical and predicted data
    historical_data = country_data.get("historical_data", [])
    predicted_data = country_data.get("predicted_data", [])
    
    # Process data for the chart
    dates = []
    historical_cases = []
    historical_temps = []
    predicted_dates = []
    predicted_cases = []
    
    # Parse historical data
    for item in historical_data:
        date = item.get("calendar_start_date")
        if date:
            dates.append(date)
            historical_cases.append(item.get("dengue_total", 0))
            historical_temps.append(item.get("avg_temperature", None))
    
    # Parse predicted data
    for item in predicted_data:
        date = item.get("calendar_start_date")
        if date:
            predicted_dates.append(date)
            predicted_cases.append(item.get("dengue_total", 0))
    
    # Format data for Chart.js
    labels_json = json.dumps(dates + predicted_dates)
    historical_json = json.dumps(historical_cases + [None] * len(predicted_dates))
    predicted_json = json.dumps([None] * len(dates) + predicted_cases)
    
    # Generate HTML/JS code for the chart
    chart_code = f"""
<div>
  <canvas id="dengueChart{chart_id}" width="800" height="400"></canvas>
</div>
<script>
  // Create the chart once the page is loaded
  document.addEventListener('DOMContentLoaded', function() {{
    const ctx = document.getElementById('dengueChart{chart_id}').getContext('2d');
    const chart = new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: {labels_json},
        datasets: [
          {{
            label: 'Historical Dengue Cases',
            data: {historical_json},
            borderColor: 'rgba(54, 162, 235, 1)',
            backgroundColor: 'rgba(54, 162, 235, 0.2)',
            borderWidth: 2,
            pointRadius: 3,
            tension: 0.1
          }},
          {{
            label: 'Predicted Dengue Cases',
            data: {predicted_json},
            borderColor: 'rgba(255, 99, 132, 1)',
            backgroundColor: 'rgba(255, 99, 132, 0.2)',
            borderWidth: 2,
            borderDash: [5, 5],
            pointRadius: 3,
            tension: 0.1
          }}
        ]
      }},
      options: {{
        responsive: true,
        plugins: {{
          title: {{
            display: true,
            text: 'Dengue Fever Cases in {country}',
            font: {{
              size: 18
            }}
          }},
          tooltip: {{
            mode: 'index',
            intersect: false,
          }},
          legend: {{
            position: 'top',
          }}
        }},
        scales: {{
          x: {{
            title: {{
              display: true,
              text: 'Date'
            }}
          }},
          y: {{
            title: {{
              display: true,
              text: 'Number of Cases'
            }},
            beginAtZero: true
          }}
        }}
      }}
    }});
  }});
</script>
"""
    return chart_code

def generate_static_markdown_chart(country_data):
    """Generate a static ASCII chart for markdown when interactive options aren't available."""
    country = country_data.get("country", "Unknown")
    historical_data = country_data.get("historical_data", [])
    predicted_data = country_data.get("predicted_data", [])
    
    if not historical_data:
        return f"No historical data available for {country}"
    
    # Find the max number of cases to scale the chart
    all_cases = [item.get("dengue_total", 0) for item in historical_data]
    if predicted_data:
        all_cases += [item.get("dengue_total", 0) for item in predicted_data]
    max_cases = max(all_cases) if all_cases else 0
    
    # Generate a simple ASCII chart
    chart = [f"# Dengue Cases in {country}\n"]
    chart.append("```")
    chart.append(f"Max cases: {max_cases:.1f}")
    chart.append("")
    
    # Generate historical data points
    for item in historical_data[-10:]:  # Last 10 data points for brevity
        date = item.get("calendar_start_date", "")
        cases = item.get("dengue_total", 0)
        bar_length = int((cases / max_cases) * 50) if max_cases > 0 else 0
        chart.append(f"{date[:7]} | {'#' * bar_length} {cases}")
    
    # Add separator between historical and predicted
    chart.append("-" * 60)
    
    # Generate predicted data points
    for item in predicted_data:
        date = item.get("calendar_start_date", "")
        cases = item.get("dengue_total", 0)
        bar_length = int((cases / max_cases) * 50) if max_cases > 0 else 0
        chart.append(f"{date[:7]} | {'*' * bar_length} {cases:.1f}")
    
    chart.append("```")
    chart.append("")
    chart.append("Legend: # = Historical data, * = Predicted data")
    
    return "\n".join(chart)

def create_visualization_html(data, output_dir=None):
    """Create a standalone HTML file with visualizations."""
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    else:
        output_dir = "."
    
    timestamp = int(datetime.now().timestamp())
    output_file = os.path.join(output_dir, f"dengue_visualization_{timestamp}.html")
    
    # HTML Template
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dengue Data Visualization</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
        }
        h1, h2, h3 {
            color: #2c3e50;
        }
        .chart-container {
            margin: 30px 0;
            border: 1px solid #eee;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .metadata {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .summary {
            background-color: #e9f7ef;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .insights {
            margin: 20px 0;
        }
        .insights ul {
            padding-left: 20px;
        }
    </style>
</head>
<body>
    <h1>Dengue Data Visualization</h1>
    <div class="metadata">
        <h2>Query Information</h2>
        <p><strong>Query:</strong> {query}</p>
        <p><strong>Generated:</strong> {timestamp}</p>
        <p><strong>Context:</strong> {context}</p>
    </div>
    
    {charts_html}
    
    <div class="insights">
        <h2>Analysis</h2>
        <h3>Insights</h3>
        <ul>
            {insights_html}
        </ul>
        
        <h3>Recommendations</h3>
        <ul>
            {recommendations_html}
        </ul>
    </div>
</body>
</html>"""
    
    # Generate chart HTML for each country
    charts_html = ""
    for i, country_data in enumerate(data.get("countries_data", [])):
        country = country_data.get("country", "Unknown")
        charts_html += f'<div class="chart-container">\n'
        charts_html += f'<h2>{country} Dengue Cases</h2>\n'
        
        # Add summary
        for summary in data.get("analysis", {}).get("summaries", []):
            if summary.get("country") == country:
                charts_html += f'<div class="summary">{summary.get("summary", "")}</div>\n'
        
        # Add chart
        charts_html += generate_chart_code(country_data, i)
        charts_html += '</div>\n'
    
    # Generate insights HTML
    insights_html = ""
    for insight in data.get("analysis", {}).get("insights", []):
        insights_html += f"<li>{insight}</li>\n"
    
    # Generate recommendations HTML
    recommendations_html = ""
    for rec in data.get("analysis", {}).get("recommendations", []):
        recommendations_html += f"<li>{rec}</li>\n"
    
    # Fill in the template
    html_content = html_template.format(
        query=data.get("original_query", ""),
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        context=data.get("query_context", "general"),
        charts_html=charts_html,
        insights_html=insights_html,
        recommendations_html=recommendations_html
    )
    
    # Write to file
    with open(output_file, "w") as f:
        f.write(html_content)
    
    return output_file

def enhance_markdown_with_visualizations(md_file_path, output_dir=None):
    """Enhance a markdown file with static visualizations."""
    # Extract JSON data
    data = extract_json_from_markdown(md_file_path)
    if not data:
        return "Could not extract JSON data from markdown file"
    
    # Create enhanced markdown
    output_file = md_file_path.replace(".md", "_enhanced.md")
    
    with open(md_file_path, 'r') as f:
        content = f.read()
    
    # Find a good insertion point
    analysis_pos = content.find("## Analysis")
    if analysis_pos == -1:
        analysis_pos = len(content)
    
    # Create visualizations section
    vis_section = "## Visualizations\n\n"
    
    # Add a static chart for each country
    for country_data in data.get("countries_data", []):
        vis_section += generate_static_markdown_chart(country_data) + "\n\n"
    
    # Insert visualizations
    enhanced_content = content[:analysis_pos] + vis_section + content[analysis_pos:]
    
    # Also create an HTML visualization
    html_file = create_visualization_html(data, output_dir)
    
    # Add link to HTML visualization
    html_link = f"\n\n## Interactive Visualization\n\nFor interactive charts, open the [HTML visualization]({os.path.basename(html_file)}).\n\n"
    enhanced_content = enhanced_content[:analysis_pos] + html_link + enhanced_content[analysis_pos:]
    
    # Write enhanced markdown
    with open(output_file, 'w') as f:
        f.write(enhanced_content)
    
    return {
        "markdown_file": output_file,
        "html_file": html_file
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_dengue_visuals.py <markdown_file> [output_directory]")
        sys.exit(1)
    
    md_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(md_file)
    
    result = enhance_markdown_with_visualizations(md_file, output_dir)
    
    if isinstance(result, dict):
        print(f"Enhanced markdown saved to: {result['markdown_file']}")
        print(f"Interactive HTML visualization saved to: {result['html_file']}")
    else:
        print(f"Error: {result}")
