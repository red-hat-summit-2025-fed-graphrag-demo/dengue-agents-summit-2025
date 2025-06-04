"""
Dengue Visualization Helper

Utility to convert dengue data from the DengueDataVisualizationAgent into
markdown-friendly visualizations using matplotlib and base64 encoding.
"""
import json
import base64
import io
from typing import Dict, Any, List, Optional
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np
from pathlib import Path
import os

def generate_visualizations(json_data: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate visualizations from dengue data JSON and return markdown-embeddable images.
    
    Args:
        json_data: JSON string from DengueDataVisualizationAgent
        output_dir: Optional directory to save image files (if None, only base64 is returned)
    
    Returns:
        Dictionary with visualization content and metadata
    """
    try:
        # Parse JSON data
        data = json.loads(json_data) if isinstance(json_data, str) else json_data
        
        result = {
            "visualizations": [],
            "markdown": [],
            "files": []
        }
        
        # Process each country's data
        for country_data in data.get("countries_data", []):
            country = country_data.get("country", "Unknown")
            
            # Create time series plot of historical and predicted data
            time_series_vis = create_time_series_visualization(country_data)
            if time_series_vis:
                result["visualizations"].append(time_series_vis)
                
                # Create markdown for embedding
                img_markdown = f"![Dengue Cases in {country}]({time_series_vis['data_uri']})"
                result["markdown"].append({
                    "country": country,
                    "visualization_type": "time_series",
                    "markdown": img_markdown
                })
                
                # Save file if output_dir is provided
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    safe_country = country.lower().replace(" ", "_")
                    filename = f"{safe_country}_dengue_time_series.png"
                    file_path = os.path.join(output_dir, filename)
                    
                    # Save the actual image
                    with open(file_path, "wb") as f:
                        # Decode base64 data URI and save
                        img_data = time_series_vis["data_uri"].split(",")[1]
                        f.write(base64.b64decode(img_data))
                    
                    # Add file info to result
                    result["files"].append({
                        "country": country,
                        "visualization_type": "time_series",
                        "file_path": file_path,
                        "markdown": f"![Dengue Cases in {country}]({filename})"
                    })
        
        return result
    
    except Exception as e:
        return {
            "error": str(e),
            "visualizations": [],
            "markdown": [],
            "files": []
        }

def create_time_series_visualization(country_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a time series visualization for dengue cases.
    
    Args:
        country_data: Country-specific data dictionary
    
    Returns:
        Dictionary with visualization data and metadata
    """
    try:
        country = country_data.get("country", "Unknown")
        api_country = country_data.get("api_country", "Unknown")
        historical_data = country_data.get("historical_data", [])
        predicted_data = country_data.get("predicted_data", [])
        
        # Check if we have enough data
        if not historical_data:
            return None
        
        # Extract dates and case counts
        hist_dates = []
        hist_cases = []
        
        for item in historical_data:
            try:
                date_str = item.get("calendar_start_date", "")
                if date_str:
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                    hist_dates.append(date)
                    hist_cases.append(item.get("dengue_total", 0))
            except (ValueError, TypeError):
                continue
        
        # Extract predicted dates and case counts
        pred_dates = []
        pred_cases = []
        
        for item in predicted_data:
            try:
                date_str = item.get("calendar_start_date", "")
                if date_str:
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                    pred_dates.append(date)
                    pred_cases.append(item.get("dengue_total", 0))
            except (ValueError, TypeError):
                continue
        
        # Create the plot
        plt.figure(figsize=(10, 6))
        
        # Plot historical data
        plt.plot(hist_dates, hist_cases, 'b-', label='Historical Data')
        
        # Plot predicted data if available
        if pred_dates and pred_cases:
            plt.plot(pred_dates, pred_cases, 'r--', label='Predictions')
            
            # Add a vertical line between historical and predicted data
            if hist_dates and pred_dates:
                transition_date = max(hist_dates)
                plt.axvline(x=transition_date, color='gray', linestyle='--', alpha=0.7)
                plt.text(transition_date, max(hist_cases + pred_cases) * 0.95, 
                         'Prediction Start', rotation=90, verticalalignment='top')
        
        # Format the plot
        plt.title(f'Dengue Fever Cases in {country}')
        plt.xlabel('Date')
        plt.ylabel('Number of Cases')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Format date axis
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.gcf().autofmt_xdate()
        
        # Add a note about data source if using a proxy
        if country.lower() != api_country.lower():
            plt.figtext(0.5, 0.01, f"Note: Using {api_country} data as a proxy for {country}", 
                       ha='center', fontsize=8, style='italic')
        
        # Convert plot to base64 for embedding in markdown
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
        
        # Create data URI
        data_uri = f"data:image/png;base64,{image_base64}"
        
        return {
            "country": country,
            "api_country": api_country,
            "visualization_type": "time_series",
            "data_uri": data_uri
        }
    
    except Exception as e:
        print(f"Error creating visualization for {country_data.get('country', 'Unknown')}: {str(e)}")
        return None

def process_visualization_file(file_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Process a visualization result file and generate visualizations.
    
    Args:
        file_path: Path to the JSON or markdown file
        output_dir: Optional directory to save image files
    
    Returns:
        Dictionary with visualization content and markdown
    """
    try:
        # Determine file type and load content
        if file_path.endswith('.json'):
            with open(file_path, 'r') as f:
                json_data = json.load(f)
                
            return generate_visualizations(json_data, output_dir)
            
        elif file_path.endswith('.md'):
            # Extract JSON from markdown
            json_content = None
            with open(file_path, 'r') as f:
                content = f.read()
                
                # Look for raw JSON response section
                json_start = content.find('## Raw JSON Response\n\n```json')
                if json_start != -1:
                    json_text_start = content.find('{', json_start)
                    json_text_end = content.find('```', json_text_start)
                    if json_text_start != -1 and json_text_end != -1:
                        json_content = content[json_text_start:json_text_end].strip()
            
            if json_content:
                return generate_visualizations(json_content, output_dir)
            else:
                return {"error": "Could not extract JSON from markdown file"}
        else:
            return {"error": f"Unsupported file format: {file_path}"}
            
    except Exception as e:
        return {
            "error": str(e),
            "visualizations": [],
            "markdown": [],
            "files": []
        }

def update_markdown_with_visualizations(md_file_path: str, output_dir: Optional[str] = None) -> str:
    """
    Update a markdown file with visualizations generated from its data.
    
    Args:
        md_file_path: Path to the markdown file
        output_dir: Directory to save visualization images
    
    Returns:
        Updated markdown content
    """
    try:
        # If output directory not specified, create one beside the markdown file
        if not output_dir:
            md_path = Path(md_file_path)
            output_dir = md_path.parent / f"{md_path.stem}_visualizations"
        
        # Generate visualizations
        vis_result = process_visualization_file(md_file_path, output_dir)
        
        if "error" in vis_result and vis_result["error"]:
            return f"Error generating visualizations: {vis_result['error']}"
        
        # Read original markdown
        with open(md_file_path, 'r') as f:
            md_content = f.read()
        
        # Create visualization section
        vis_section = "\n## Visualizations\n\n"
        
        # Add each visualization
        for item in vis_result.get("files", []):
            country = item.get("country", "Unknown")
            vis_type = item.get("visualization_type", "")
            file_path = item.get("file_path", "")
            
            if file_path:
                # Get relative path for markdown
                rel_path = os.path.relpath(
                    file_path, 
                    os.path.dirname(md_file_path)
                )
                
                vis_section += f"### {country} {vis_type.replace('_', ' ').title()}\n\n"
                vis_section += f"![{country} Dengue Data]({rel_path})\n\n"
        
        # Find a good place to insert visualizations
        analysis_pos = md_content.find("## Analysis")
        if analysis_pos != -1:
            # Insert before analysis
            updated_content = md_content[:analysis_pos] + vis_section + md_content[analysis_pos:]
        else:
            # Append at the end
            updated_content = md_content + "\n" + vis_section
        
        # Save updated markdown
        updated_file_path = md_file_path.replace(".md", "_with_vis.md")
        with open(updated_file_path, 'w') as f:
            f.write(updated_content)
        
        return updated_file_path
    
    except Exception as e:
        return f"Error updating markdown: {str(e)}"

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python dengue_visualization_helper.py <path_to_file> [output_dir]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    if file_path.endswith('.md'):
        result = update_markdown_with_visualizations(file_path, output_dir)
        print(f"Updated markdown saved to: {result}")
    else:
        result = process_visualization_file(file_path, output_dir)
        print(f"Generated {len(result.get('files', []))} visualizations")
        for file_info in result.get("files", []):
            print(f" - {file_info.get('file_path')}")
