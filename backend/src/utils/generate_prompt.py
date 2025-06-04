#!/usr/bin/env python
"""
Prompt Generator

This script generates new prompt files from templates:
1. Creates a prompt YAML file in the appropriate category directory
2. Sets up the basic prompt structure with placeholder content

Usage:
  python -m src.utils.generate_prompt --prompt --category <category> --name <prompt_name> [--model <model_name>]
"""

import argparse
import logging
import os
import datetime
from pathlib import Path
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("prompt_generator")


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate prompt files from templates")
    parser.add_argument("--prompt", action="store_true", help="Generate a new prompt")
    parser.add_argument("--category", type=str, help="Category for the prompt (e.g., 'rag', 'safety')")
    parser.add_argument("--name", type=str, help="Name of the prompt (e.g., 'query_generator')")
    parser.add_argument("--model", type=str, help="Compatible model name", default="granite-3-1-8b-instruct-w4a16")
    parser.add_argument("--tags", nargs="+", help="Tags for the prompt", default=[])
    return parser.parse_args()


def load_template(template_path: str) -> str:
    """Load a template file."""
    logger.info(f"Loading template: {template_path}")
    with open(template_path, "r") as f:
        return f.read()


def generate_prompt_file(
    template_path: str,
    output_path: str,
    prompt_id: str,
    category: str,
    prompt_name: str,
    model_name: str,
    tags: List[str]
) -> None:
    """Generate a prompt file from template."""
    # Load template
    template = load_template(template_path)
    
    # Get current date
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Replace placeholders
    content = template.replace("{{ category }}", category)
    content = content.replace("{{ prompt_id }}", prompt_id)
    content = content.replace("{{ Prompt Name }}", prompt_name)
    content = content.replace("{{ Prompt description }}", f"System prompt for {prompt_name.lower()}")
    
    # Handle tags
    if not tags:
        tags = [category, prompt_id]
    tag_str = ', '.join([f'"{tag}"' for tag in tags])
    content = content.replace('["{{ tag1 }}", "{{ tag2 }}"]', f"[{tag_str}]")
    
    # Update dates
    content = content.replace("YYYY-MM-DD", today)
    
    # Set model
    content = content.replace("{{ compatible_model }}", model_name)
    
    # Add empty benchmarking section
    if "# Performance Benchmarks" not in content:
        benchmark_section = (
            "# Performance Benchmarks\n"
            "benchmarks:                                           # [OPTIONAL] Performance measurements for different models\n"
            "  # Example:\n"
            "  # - model: \"" + model_name + "\"\n"
            "  #   date: \"" + today + "\"\n"
            "  #   metrics:\n"
            "  #     latency_ms: 0\n"
            "  #     tokens_per_second: 0\n"
            "  #     accuracy: 0.0\n"
            "  #     notes: \"Brief notes about the benchmark results\"\n\n"
        )
        # Find the right place to insert it (before the prompt section)
        prompt_section_idx = content.find("# The actual prompt template")
        if prompt_section_idx > 0:
            content = content[:prompt_section_idx] + benchmark_section + content[prompt_section_idx:]
    
    # Set a simple starter prompt text
    starter_prompt = (
        f"You are a specialized {prompt_name} agent.\n\n"
        f"  Your task is to:\n"
        f"  1. [Describe primary task]\n"
        f"  2. [Describe secondary task]\n\n"
        f"  User query: {{{{message}}}}\n\n"
        f"  Please respond in a clear, helpful manner."
    )
    content = content.replace("{{ Your prompt text goes here }}\n  \n  {{ Include instructions, examples, and context as needed }}\n  \n  {{ Use variables like {{variable_name}} for dynamic content }}", starter_prompt)
    
    # Write to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(content)
    
    logger.info(f"Generated prompt file: {output_path}")


def generate_prompt(
    category: str,
    name: str,
    model_name: str = "granite-3-1-8b-instruct-w4a16",
    tags: Optional[List[str]] = None
) -> None:
    """Generate all files for a new prompt."""
    # Setup paths
    backend_dir = Path(__file__).resolve().parents[2]
    templates_dir = backend_dir / "src" / "registries" / "prompts" / "templates"
    category_dir = backend_dir / "src" / "registries" / "prompts" / category
    
    # Generate prompt ID and name
    prompt_id = name.lower().replace(" ", "_")
    prompt_name = " ".join(word.capitalize() for word in name.split("_"))
    full_prompt_name = f"{prompt_name} Prompt"
    
    # Log info
    logger.info(f"Generating new prompt: {full_prompt_name} (Category: {category}, ID: {prompt_id})")
    
    # Generate prompt file
    template_path = templates_dir / "prompt_template.yaml"
    output_path = category_dir / f"{prompt_id}.yaml"
    
    # Create category directory if it doesn't exist
    os.makedirs(category_dir, exist_ok=True)
    
    generate_prompt_file(
        str(template_path),
        str(output_path),
        prompt_id,
        category,
        full_prompt_name,
        model_name,
        tags or []
    )
    
    # Print completion message
    logger.info("\nPrompt generation complete!")
    logger.info(f"Prompt file: {output_path}")
    logger.info("\nNext steps:")
    logger.info("1. Edit the prompt file to provide the actual prompt content")
    logger.info("2. Update the tags and description as needed")
    logger.info("3. Test the prompt with compatible models")


def main() -> None:
    """Main entry point."""
    args = parse_arguments()
    
    if args.prompt and args.category and args.name:
        generate_prompt(args.category, args.name, args.model, args.tags)
    else:
        logger.error("Invalid arguments. Use --prompt --category <category> --name <name>")


if __name__ == "__main__":
    main()
