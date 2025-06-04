#!/usr/bin/env python
"""
Prompt Standardization Tool

A command-line tool to standardize prompt registry entries to comply with
the standardized format defined in REGISTRY_STANDARD.md.
"""
import os
import sys
import argparse
import logging

# Add the parent directory to the path so we can import from src
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, parent_dir)

from src.registries.prompt_standardizer import PromptStandardizer

def main():
    """Main entry point for the standardization tool."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Standardize prompt registry entries")
    parser.add_argument(
        "--base-dir", 
        help="Base directory for prompt files (default: src/registries/prompts)"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Don't actually modify any files, just report what would be changed"
    )
    parser.add_argument(
        "--create-template",
        action="store_true",
        help="Create a standardized prompt template file"
    )
    parser.add_argument(
        "--template-path",
        default="src/registries/prompts/templates/standardized_prompt_template.yaml",
        help="Path where to save the template file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    # Create standardizer
    standardizer = PromptStandardizer(args.base_dir)
    
    # Create template if requested
    if args.create_template:
        template_path = os.path.join(parent_dir, args.template_path)
        standardizer.create_standardized_template(template_path)
        logger.info(f"Created standardized prompt template at {template_path}")
        return
    
    # Run standardization
    logger.info(f"Standardizing prompt files in {standardizer.base_dir} (dry_run={args.dry_run})")
    
    # Standardize all prompts
    summary = standardizer.standardize_all_prompts(args.dry_run)
    
    # Print summary
    print("\nStandardization Summary:")
    print(f"  Total prompt files: {summary['total']}")
    print(f"  Already valid: {summary['already_valid']}")
    print(f"  Standardized: {summary['standardized']}")
    print(f"  Failed: {summary['failed']}")
    
    # Print detailed report for files that were changed
    if summary['standardized'] > 0:
        print("\nStandardized Files:")
        for file_path, status in summary['files'].items():
            if status.get('changed', False) and status.get('post_valid', False):
                print(f"  - {file_path}")
    
    # Print warnings for files that could not be standardized
    if summary['failed'] > 0:
        print("\nFiles that could not be automatically standardized:")
        for file_path, status in summary['files'].items():
            if not status.get('post_valid', False):
                print(f"  - {file_path}")
                if 'validation_issues' in status:
                    for issue in status['validation_issues'][:3]:  # Show first 3 issues
                        print(f"      {issue}")
                    if len(status['validation_issues']) > 3:
                        print(f"      ... and {len(status['validation_issues']) - 3} more issues")
    
    # Print next steps
    if args.dry_run:
        print("\nThis was a dry run. To actually make changes, run without --dry-run")
    else:
        print("\nStandardization complete!")
        if summary['failed'] > 0:
            print("Some files could not be automatically standardized and may need manual attention.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
