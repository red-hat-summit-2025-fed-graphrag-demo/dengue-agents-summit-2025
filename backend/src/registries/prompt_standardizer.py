"""
Prompt Standardizer

Utilities for standardizing prompt registry entries to comply with
the standardized format defined in REGISTRY_STANDARD.md.
"""
import os
import yaml
import logging
import datetime
import glob
from typing import Dict, List, Any, Optional

from src.registries.registry_validator import PromptRegistryValidator, ValidationResult

logger = logging.getLogger(__name__)

class PromptStandardizer:
    """
    Utility for standardizing prompt registry entries.
    
    Provides methods to validate, standardize, and migrate prompt files
    to ensure they comply with the standardized format.
    """
    
    # Default values for required fields
    DEFAULT_VALUES = {
        "version": "1.0.0",
        "tags": [],
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d"),
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d"),
        "author": "Dengue Project Team",
        "active": True,
        "models": []
    }
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize the standardizer.
        
        Args:
            base_dir: Optional base directory for prompt files. If not provided,
                     defaults to the 'prompts' directory in the registries package.
        """
        self.base_dir = base_dir or os.path.join(os.path.dirname(__file__), "prompts")
        self.validator = PromptRegistryValidator()
        
    def standardize_prompt(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize a prompt entry.
        
        Adds any missing fields from the standard format and ensures
        all fields have appropriate types and formats.
        
        Args:
            prompt_data: The original prompt data
            
        Returns:
            Standardized prompt data
        """
        # Create a new dictionary with all existing data
        standardized = prompt_data.copy()
        
        # Ensure required fields exist
        for field, default_value in self.DEFAULT_VALUES.items():
            if field not in standardized:
                standardized[field] = default_value
                logger.info(f"Added missing field '{field}' with default value")
        
        # Format dates properly
        for date_field in ["created_at", "updated_at"]:
            if date_field in standardized:
                # If already a properly formatted date string, keep it
                if isinstance(standardized[date_field], str) and len(standardized[date_field]) == 10:
                    try:
                        # Validate format
                        datetime.datetime.strptime(standardized[date_field], "%Y-%m-%d")
                    except ValueError:
                        # If invalid format, replace with today's date
                        standardized[date_field] = self.DEFAULT_VALUES[date_field]
                        logger.info(f"Reformatted invalid date in '{date_field}'")
                else:
                    # Not a proper date string, use default
                    standardized[date_field] = self.DEFAULT_VALUES[date_field]
                    logger.info(f"Reformatted invalid date in '{date_field}'")
        
        # Ensure tags and models are lists
        for list_field in ["tags", "models"]:
            if not isinstance(standardized.get(list_field), list):
                standardized[list_field] = self.DEFAULT_VALUES[list_field]
                logger.info(f"Ensured '{list_field}' is a list")
        
        # Ensure active is a boolean
        if not isinstance(standardized.get("active"), bool):
            standardized["active"] = self.DEFAULT_VALUES["active"]
            logger.info("Ensured 'active' is a boolean")
        
        # Ensure version follows semantic versioning
        if "version" in standardized:
            version = standardized["version"]
            if not isinstance(version, str) or not self._is_valid_semver(version):
                standardized["version"] = self.DEFAULT_VALUES["version"]
                logger.info("Reformatted invalid version to semantic versioning")
        
        return standardized
    
    def _is_valid_semver(self, version: str) -> bool:
        """
        Check if a version string follows semantic versioning (X.Y.Z).
        
        Args:
            version: The version string to check
            
        Returns:
            True if valid semantic version, False otherwise
        """
        import re
        return bool(re.match(r'^\d+\.\d+\.\d+$', version))
    
    def standardize_prompt_file(self, file_path: str, dry_run: bool = False) -> ValidationResult:
        """
        Standardize a prompt file.
        
        Args:
            file_path: Path to the prompt YAML file
            dry_run: If True, don't actually modify the file
            
        Returns:
            ValidationResult with validation findings
        """
        try:
            # Load the prompt file
            with open(file_path, 'r', encoding='utf-8') as f:
                prompt_data = yaml.safe_load(f)
            
            # Validate before standardization
            pre_validation = self.validator.validate(prompt_data)
            logger.info(f"Pre-standardization validation: {pre_validation.is_valid}")
            
            # Standardize the prompt
            standardized = self.standardize_prompt(prompt_data)
            
            # Validate after standardization
            post_validation = self.validator.validate(standardized)
            logger.info(f"Post-standardization validation: {post_validation.is_valid}")
            
            # Write the standardized prompt back to the file if not a dry run
            if not dry_run and not post_validation.is_valid:
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(standardized, f, default_flow_style=False, sort_keys=False)
                logger.info(f"Standardized prompt file: {file_path}")
            
            return post_validation
        
        except Exception as e:
            logger.error(f"Error standardizing prompt file {file_path}: {str(e)}")
            result = ValidationResult()
            result.add_issue(
                field="file",
                message=f"Error standardizing file: {str(e)}",
                severity="ERROR"
            )
            return result
    
    def standardize_all_prompts(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Standardize all prompt files in the base directory.
        
        Args:
            dry_run: If True, don't actually modify any files
            
        Returns:
            Summary of standardization results
        """
        summary = {
            "total": 0,
            "already_valid": 0,
            "standardized": 0,
            "failed": 0,
            "files": {}
        }
        
        # Find all YAML files in the prompt directory
        pattern = os.path.join(self.base_dir, "**", "*.yaml")
        files = glob.glob(pattern, recursive=True)
        
        summary["total"] = len(files)
        
        for file_path in files:
            try:
                # Load the prompt file
                with open(file_path, 'r', encoding='utf-8') as f:
                    prompt_data = yaml.safe_load(f)
                
                # Validate before standardization
                pre_validation = self.validator.validate(prompt_data)
                
                # Standardize the prompt
                standardized = self.standardize_prompt(prompt_data)
                
                # Validate after standardization
                post_validation = self.validator.validate(standardized)
                
                file_status = {
                    "path": file_path,
                    "pre_valid": pre_validation.is_valid,
                    "post_valid": post_validation.is_valid,
                    "changed": prompt_data != standardized
                }
                
                if pre_validation.is_valid:
                    summary["already_valid"] += 1
                elif post_validation.is_valid:
                    summary["standardized"] += 1
                    # Write the standardized prompt back to the file if not a dry run
                    if not dry_run:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            yaml.dump(standardized, f, default_flow_style=False, sort_keys=False)
                        logger.info(f"Standardized prompt file: {file_path}")
                else:
                    summary["failed"] += 1
                    file_status["validation_issues"] = post_validation.get_formatted_issues()
                
                # Add to summary
                relative_path = os.path.relpath(file_path, self.base_dir)
                summary["files"][relative_path] = file_status
                
            except Exception as e:
                logger.error(f"Error processing prompt file {file_path}: {str(e)}")
                relative_path = os.path.relpath(file_path, self.base_dir)
                summary["files"][relative_path] = {
                    "path": file_path,
                    "error": str(e),
                    "pre_valid": False,
                    "post_valid": False,
                    "changed": False
                }
                summary["failed"] += 1
        
        return summary
    
    def create_standardized_template(self, output_path: str) -> None:
        """
        Create a standardized prompt template file.
        
        Args:
            output_path: Path where to save the template file
        """
        template = {
            "id": "namespace.prompt_id",
            "name": "Example Prompt",
            "description": "Description of the prompt's purpose",
            "version": "1.0.0",
            "tags": ["tag1", "tag2"],
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d"),
            "updated_at": datetime.datetime.now().strftime("%Y-%m-%d"),
            "author": "Dengue Project Team",
            "active": True,
            "models": ["model1", "model2"],
            "prompt": "Your prompt text goes here.\nIt can span multiple lines."
        }
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write template to file
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(template, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Created standardized prompt template at {output_path}")


def standardize_prompts_cli(base_dir: Optional[str] = None, dry_run: bool = False) -> None:
    """
    Command-line interface for standardizing prompts.
    
    Args:
        base_dir: Optional base directory for prompt files
        dry_run: If True, don't actually modify any files
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create standardizer
    standardizer = PromptStandardizer(base_dir)
    
    # Run standardization
    logger.info(f"Standardizing prompt files in {standardizer.base_dir} (dry_run={dry_run})")
    summary = standardizer.standardize_all_prompts(dry_run)
    
    # Print summary
    logger.info("Standardization Summary:")
    logger.info(f"  Total prompt files: {summary['total']}")
    logger.info(f"  Already valid: {summary['already_valid']}")
    logger.info(f"  Standardized: {summary['standardized']}")
    logger.info(f"  Failed: {summary['failed']}")
    
    if summary['failed'] > 0:
        logger.warning("Some prompt files could not be automatically standardized:")
        for file_path, status in summary['files'].items():
            if not status.get('post_valid', False):
                logger.warning(f"  - {file_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Standardize prompt registry entries")
    parser.add_argument("--base-dir", help="Base directory for prompt files")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually modify any files")
    
    args = parser.parse_args()
    
    standardize_prompts_cli(args.base_dir, args.dry_run)
