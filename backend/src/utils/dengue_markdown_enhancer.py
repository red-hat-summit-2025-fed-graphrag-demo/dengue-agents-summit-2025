"""
Dengue Markdown Enhancer

A simple script to enhance dengue data in markdown files with ASCII visualizations
and data tables for better presentation without requiring external libraries.
"""
import json
import os
import sys
import re
from datetime import datetime
from pathlib import Path

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

def generate_ascii_chart(country_data):
    """Generate a simple ASCII chart for the dengue data."""
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
    
    # Prepare chart data
    chart_items = []
    
    # Use only the last 10 historical and all predicted items for a cleaner chart
    display_historical = historical_data[-10:] if len(historical_data) > 10 else historical_data
    
    # Create the ASCII chart header
    header = f"### Dengue Cases in {country}\n\n"
    header += "Time series visualization (# = historical data, * = predicted data)\n\n"
    
    chart = ["```"]
    chart.append(f"DATE       | CASES {'=' * 50}")
    
    # Format the data points
    for item in display_historical:
        date = item.get("calendar_start_date", "")
        cases = item.get("dengue_total", 0)
        bar_length = int((cases / max_cases) * 40) if max_cases > 0 else 0
        chart.append(f"{date} | {cases:5.0f} {'#' * bar_length}")
    
    # Add a separator
    chart.append("-" * 70)
    
    # Add predicted data
    for item in predicted_data:
        date = item.get("calendar_start_date", "")
        cases = item.get("dengue_total", 0)
        bar_length = int((cases / max_cases) * 40) if max_cases > 0 else 0
        chart.append(f"{date} | {cases:5.1f} {'*' * bar_length}")
    
    chart.append("```\n")
    
    return header + "\n".join(chart)

def generate_data_table(country_data):
    """Generate a markdown table with key dengue data points."""
    country = country_data.get("country", "Unknown")
    historical_data = country_data.get("historical_data", [])
    predicted_data = country_data.get("predicted_data", [])
    
    # Create header
    table = f"### Dengue Data Table for {country}\n\n"
    
    # Historical data table
    if historical_data:
        table += "#### Historical Data (Last 6 months)\n\n"
        table += "| Date | Cases | Temperature (°C) | Humidity (%) |\n"
        table += "|------|-------|-----------------|-------------|\n"
        
        # Show only the last 6 months for brevity
        for item in historical_data[-6:]:
            date = item.get("calendar_start_date", "")
            cases = item.get("dengue_total", 0)
            temp = item.get("avg_temperature", "N/A")
            humidity = item.get("avg_humidity", "N/A")
            
            table += f"| {date} | {cases} | {temp} | {humidity} |\n"
        
        table += "\n"
    
    # Predicted data table
    if predicted_data:
        table += "#### Prediction Data\n\n"
        table += "| Date | Predicted Cases |\n"
        table += "|------|----------------|\n"
        
        for item in predicted_data:
            date = item.get("calendar_start_date", "")
            cases = item.get("dengue_total", 0)
            
            table += f"| {date} | {cases:.1f} |\n"
        
        table += "\n"
    
    return table

def generate_mermaid_chart(country_data):
    """Generate a Mermaid.js chart for the dengue data."""
    country = country_data.get("country", "Unknown")
    historical_data = country_data.get("historical_data", [])
    predicted_data = country_data.get("predicted_data", [])
    
    # Skip if no data
    if not historical_data and not predicted_data:
        return ""
    
    # Create a mermaid line chart
    chart = f"### Mermaid Chart for {country}\n\n"
    chart += "```mermaid\n"
    chart += "%%{init: {'theme': 'default', 'themeVariables': { 'primaryColor': '#007bff', 'primaryTextColor': '#fff', 'primaryBorderColor': '#007bff', 'lineColor': '#007bff', 'secondaryColor': '#ff0000', 'tertiaryColor': '#00ff00'}}%\n"
    chart += "xychart-beta\n"
    chart += f"    title \"Dengue Cases in {country}\"\n"
    chart += "    x-axis [" 
    
    # Add x-axis labels (dates) - use only some to avoid overcrowding
    dates = []
    
    # Use only every 3rd historical date for clarity
    for i, item in enumerate(historical_data):
        if i % 3 == 0:  # Every 3rd item
            date = item.get("calendar_start_date", "")
            if date:
                # Use month-year format to save space
                month_year = "-".join(date.split("-")[:2])
                dates.append(f"\"{month_year}\"")
    
    # Add all prediction dates
    for item in predicted_data:
        date = item.get("calendar_start_date", "")
        if date:
            month_year = "-".join(date.split("-")[:2])
            dates.append(f"\"{month_year}\"")
    
    chart += ", ".join(dates) + "]\n"
    
    # Add y-axis
    chart += "    y-axis \"Cases\"\n"
    
    # Add historical data series
    chart += "    line [" 
    hist_values = []
    for i, item in enumerate(historical_data):
        if i % 3 == 0:  # Every 3rd item to match x-axis
            cases = item.get("dengue_total", 0)
            hist_values.append(str(cases))
    
    chart += ", ".join(hist_values) + "]\n"
    
    # Add predicted data series if available
    if predicted_data:
        chart += "    line [" 
        # Add null values for historical dates to align with x-axis
        pred_values = ["null"] * len(hist_values)
        
        # Add prediction values
        for item in predicted_data:
            cases = item.get("dengue_total", 0)
            pred_values.append(str(cases))
        
        chart += ", ".join(pred_values) + "]\n"
    
    chart += "```\n\n"
    
    # Add legend
    chart += "**Legend:** Blue line = Historical data, Red line = Predicted data\n\n"
    
    return chart

def enhance_markdown_with_visualizations(md_file_path):
    """Enhance a markdown file with data visualizations."""
    # Extract JSON data
    data = extract_json_from_markdown(md_file_path)
    if not data:
        return "Could not extract JSON data from markdown file"
    
    # Create output file path
    output_file = md_file_path.replace(".md", "_enhanced.md")
    
    # Read original markdown
    with open(md_file_path, 'r') as f:
        content = f.read()
    
    # Create visualizations section
    vis_section = "## Data Visualizations\n\n"
    vis_section += "_Note: These visualizations are generated from the agent's output data and provide different ways to interpret the results._\n\n"
    
    # For each country, add visualizations
    for country_data in data.get("countries_data", []):
        country = country_data.get("country", "Unknown")
        
        # Add ASCII chart
        vis_section += generate_ascii_chart(country_data) + "\n"
        
        # Add data table
        vis_section += generate_data_table(country_data) + "\n"
        
        # Add Mermaid chart for platforms that support it
        # vis_section += generate_mermaid_chart(country_data) + "\n"
    
    # Find a good insertion point (before Analysis or at the end)
    analysis_pos = content.find("## Analysis")
    if analysis_pos == -1:
        # If no Analysis section, add at the end
        enhanced_content = content + "\n\n" + vis_section
    else:
        # Insert before Analysis section
        enhanced_content = content[:analysis_pos] + vis_section + content[analysis_pos:]
    
    # Write enhanced markdown
    with open(output_file, 'w') as f:
        f.write(enhanced_content)
    
    return output_file

def main():
    if len(sys.argv) < 2:
        print("Usage: python dengue_markdown_enhancer.py <markdown_file>")
        sys.exit(1)
    
    md_file = sys.argv[1]
    
    if not os.path.exists(md_file):
        print(f"Error: File not found - {md_file}")
        sys.exit(1)
    
    result = enhance_markdown_with_visualizations(md_file)
    
    print(f"Enhanced markdown saved to: {result}")
    print("\nTo integrate visualizations in other markdown documents, copy the Data Visualizations section from the enhanced file.")

if __name__ == "__main__":
    main()
