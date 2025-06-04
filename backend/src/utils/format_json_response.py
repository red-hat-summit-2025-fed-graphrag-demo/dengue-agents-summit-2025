#!/usr/bin/env python3
"""
Utility script to extract and format the response field from JSON output files.

This script parses the JSON files created during testing, extracts the response field,
and formats it for easier review.

Usage:
    python format_json_response.py <path_to_json_file> [output_file]

If no output file is specified, the formatted response will be printed to stdout.
"""

import json
import sys
import os
import argparse
from typing import Dict, Any, Optional, Union
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("format_json_response")


def parse_json_file(file_path: str) -> Dict[str, Any]:
    """
    Parse a JSON file and return its contents as a dictionary.
    
    Args:
        file_path: Path to the JSON file to parse
        
    Returns:
        Dictionary containing the parsed JSON data
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON file {file_path}: {e}")
        raise
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error parsing file {file_path}: {e}")
        raise


def extract_response(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract the response field from the JSON data.
    
    Args:
        data: Dictionary containing the parsed JSON data
        
    Returns:
        Extracted response data or None if not found
    """
    # Check if there's a response field directly in the data
    if "response" in data:
        try:
            # Some responses are JSON strings that need to be parsed
            if isinstance(data["response"], str):
                try:
                    return json.loads(data["response"])
                except json.JSONDecodeError:
                    return {"text_response": data["response"]}
            else:
                return data["response"]
        except Exception as e:
            logger.warning(f"Error extracting response field: {e}")
            return None
    
    logger.warning("No 'response' field found in the JSON data")
    return None


def format_json(data: Dict[str, Any], indent: int = 2) -> str:
    """
    Format a dictionary as a pretty-printed JSON string.
    
    Args:
        data: Dictionary to format
        indent: Number of spaces for indentation
        
    Returns:
        Formatted JSON string
    """
    return json.dumps(data, indent=indent, ensure_ascii=False)


def convert_to_markdown(data: Dict[str, Any]) -> str:
    """
    Convert JSON data to a markdown representation.
    
    Args:
        data: Dictionary to convert to markdown
        
    Returns:
        Markdown string representation
    """
    md_output = ["# JSON Response Data\n"]
    
    # Process the top-level keys
    for key, value in data.items():
        md_output.append(f"## {key.title()}\n")
        
        if isinstance(value, dict):
            md_output.append(render_dict_as_markdown(value, level=3))
        elif isinstance(value, list):
            md_output.append(render_list_as_markdown(value, level=3))
        else:
            md_output.append(f"{value}\n\n")
    
    return "".join(md_output)


def render_dict_as_markdown(data: Dict[str, Any], level: int = 1) -> str:
    """
    Render a dictionary as markdown content with headers.
    
    Args:
        data: Dictionary to render
        level: Header level (1-6)
        
    Returns:
        Markdown string
    """
    if not data:
        return "_Empty object_\n\n"
    
    md_lines = []
    
    for key, value in data.items():
        # Ensure header level doesn't exceed 6
        header_level = min(level, 6)
        header_prefix = "#" * header_level
        
        # Format key as header
        if header_level < 6:  # Use headers for levels 1-5
            md_lines.append(f"{header_prefix} {key.replace('_', ' ').title()}\n")
        else:  # Use bold for level 6+
            md_lines.append(f"**{key.replace('_', ' ').title()}**\n")
        
        # Process value based on its type
        if isinstance(value, dict):
            md_lines.append(render_dict_as_markdown(value, level + 1))
        elif isinstance(value, list):
            md_lines.append(render_list_as_markdown(value, level + 1))
        else:
            # Format primitive values
            if isinstance(value, str) and len(value) > 80 and "\n" in value:
                # Format multi-line text with code block
                md_lines.append("```\n" + value + "\n```\n\n")
            elif isinstance(value, str) and (value.startswith("**") or value.startswith("# ")):
                # Already formatted markdown
                md_lines.append(value + "\n\n")
            else:
                md_lines.append(f"{value}\n\n")
    
    return "".join(md_lines)


def render_list_as_markdown(data: list, level: int = 1) -> str:
    """
    Render a list as markdown bullet points or numbered list.
    
    Args:
        data: List to render
        level: Current header level (used for nested dictionaries)
        
    Returns:
        Markdown string
    """
    if not data:
        return "_Empty list_\n\n"
    
    md_lines = []
    
    # Special case for list of dictionaries with similar structure (table)
    if all(isinstance(item, dict) for item in data) and len(data) > 0:
        # Check if all dictionaries have similar keys and simple values
        sample_keys = set(data[0].keys())
        all_similar = all(set(item.keys()) == sample_keys for item in data)
        all_simple = all(all(not isinstance(v, (dict, list)) for v in item.values()) for item in data)
        
        # Special case for summary entries that contain markdown content
        if "summary" in sample_keys and any("**" in str(item.get("summary", "")) for item in data):
            for item in data:
                md_lines.append(f"#### {item.get('country', 'Unknown Location')}\n\n")
                md_lines.append(f"{item.get('summary', '')}\n\n")
            return "".join(md_lines)
        
        # For regular tables
        elif all_similar and all_simple and len(sample_keys) <= 5:
            # Render as markdown table
            headers = list(sample_keys)
            md_lines.append("| " + " | ".join(h.replace('_', ' ').title() for h in headers) + " |\n")
            md_lines.append("| " + " | ".join("---" for _ in headers) + " |\n")
            
            for item in data[:10]:  # Limit to 10 items to avoid extremely large tables
                md_lines.append("| " + " | ".join(str(item.get(h, "")) for h in headers) + " |\n")
            
            if len(data) > 10:
                md_lines.append("\n_Table truncated, showing 10 of " + str(len(data)) + " items_\n")
            
            md_lines.append("\n")
            return "".join(md_lines)
    
    # Regular list formatting
    for i, item in enumerate(data):
        if isinstance(item, dict):
            # For dictionaries, use nested headers
            if len(item) == 1 and list(item.keys())[0] in ["country", "name", "title", "id"]:
                # For dictionaries with a single key that looks like an identifier
                key = list(item.keys())[0]
                md_lines.append(f"- **{key.title()}**: {item[key]}\n")
                
                # If there's more content after the identifier
                remaining = {k: v for k, v in item.items() if k != key}
                if remaining:
                    md_lines.append(render_dict_as_markdown(remaining, level + 1))
            else:
                md_lines.append(f"- Item {i+1}:\n")
                md_lines.append(render_dict_as_markdown(item, level + 1))
        elif isinstance(item, list):
            # For nested lists
            md_lines.append(f"- Item {i+1}:\n")
            md_lines.append(render_list_as_markdown(item, level + 1))
        else:
            # For simple items
            md_lines.append(f"- {item}\n")
    
    md_lines.append("\n")
    return "".join(md_lines)


def format_response(file_path: str, output_file: Optional[str] = None, output_format: str = "json") -> None:
    """
    Extract and format the response field from a JSON file.
    
    Args:
        file_path: Path to the JSON file to parse
        output_file: Optional path to write the formatted response to
        output_format: Format to output the response in (json or markdown)
    """
    try:
        # Parse the JSON file
        data = parse_json_file(file_path)
        
        # Extract the response field
        response_data = extract_response(data)
        
        if response_data:
            # Format the response based on the requested format
            if output_format == "markdown":
                formatted_response = convert_to_markdown(response_data)
            else:
                formatted_response = format_json(response_data)
            
            # Write to output file or print to stdout
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(formatted_response)
                logger.info(f"Formatted response written to {output_file}")
            else:
                print(formatted_response)
        else:
            logger.error("No response data found or unable to extract response")
    except Exception as e:
        logger.error(f"Error formatting response: {e}")
        sys.exit(1)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Extract and format response field from JSON output files")
    parser.add_argument('file_path', help="Path to the JSON file to process")
    parser.add_argument('-o', '--output', help="Path to write the formatted output (defaults to stdout)")
    parser.add_argument('--analyze', action='store_true', help="Analyze and print statistics about the response data")
    parser.add_argument('--format', choices=['json', 'markdown'], default='json',
                       help="Output format (json or markdown)")
    
    return parser.parse_args()


def analyze_response(response_data: Dict[str, Any]) -> None:
    """
    Analyze and print statistics about the response data.
    
    Args:
        response_data: The response data to analyze
    """
    print("\n=== Response Analysis ===")
    
    if not response_data:
        print("No response data to analyze")
        return
    
    print(f"Response type: {type(response_data).__name__}")
    
    if isinstance(response_data, dict):
        print(f"Number of top-level fields: {len(response_data)}")
        print("Top-level fields:")
        for key, value in response_data.items():
            value_type = type(value).__name__
            value_preview = str(value)
            if len(value_preview) > 50:
                value_preview = value_preview[:47] + "..."
            print(f"  - {key} ({value_type}): {value_preview}")
            
            # For nested data structures, provide more details
            if isinstance(value, dict):
                print(f"    Keys: {', '.join(value.keys())}")
            elif isinstance(value, list) and value:
                print(f"    Length: {len(value)}")
                if value and isinstance(value[0], dict):
                    print(f"    Sample keys: {', '.join(value[0].keys())}")


def main():
    """Main entry point for the script."""
    args = parse_arguments()
    
    try:
        # Parse the JSON file
        data = parse_json_file(args.file_path)
        
        # Extract the response field
        response_data = extract_response(data)
        
        if response_data:
            # Analyze response if requested
            if args.analyze:
                analyze_response(response_data)
            
            # Format the response based on the requested format
            if args.format == "markdown":
                formatted_response = convert_to_markdown(response_data)
            else:
                formatted_response = format_json(response_data)
            
            # Determine file extension based on format
            file_ext = ".md" if args.format == "markdown" else ".json"
            
            # Write to output file or print to stdout
            if args.output:
                # Add appropriate extension if not already present
                output_path = args.output
                if not output_path.endswith(file_ext):
                    output_path += file_ext
                
                with open(output_path, 'w') as f:
                    f.write(formatted_response)
                logger.info(f"Formatted response written to {output_path}")
            else:
                print(formatted_response)
        else:
            logger.error("No response data found or unable to extract response")
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
