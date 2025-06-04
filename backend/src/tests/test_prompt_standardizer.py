"""
Test Prompt Standardizer

Unit tests for the prompt standardization utilities.
"""
import os
import unittest
import tempfile
import yaml
import shutil
from typing import Dict, Any

import sys
import os

# Add parent directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.registries.prompt_standardizer import PromptStandardizer
from src.registries.registry_validator import PromptRegistryValidator

class TestPromptStandardizer(unittest.TestCase):
    """Test the PromptStandardizer class."""
    
    def setUp(self):
        """Set up the test case."""
        self.temp_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.temp_dir, "prompts")
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Create test cases with different levels of compliance
        
        # Case 1: Already compliant prompt
        self.compliant_prompt = {
            "id": "test.compliant",
            "name": "Compliant Prompt",
            "description": "A prompt that already follows the standard format",
            "version": "1.0.0",
            "tags": ["test", "compliant"],
            "created_at": "2025-05-14",
            "updated_at": "2025-05-14",
            "author": "Test Author",
            "active": True,
            "models": ["test-model"],
            "prompt": "This is a compliant prompt template."
        }
        
        # Case 2: Partially compliant prompt (missing some optional fields)
        self.partial_prompt = {
            "id": "test.partial",
            "name": "Partial Prompt",
            "description": "A prompt that's missing some optional fields",
            "prompt": "This is a partially compliant prompt template."
        }
        
        # Case 3: Non-compliant prompt (missing required fields)
        self.noncompliant_prompt = {
            "id": "test.noncompliant",
            # Missing name
            "description": "A prompt that's missing required fields",
            "prompt": "This is a non-compliant prompt template."
        }
        
        # Case 4: Invalid data types
        self.invalid_types_prompt = {
            "id": "test.invalid_types",
            "name": "Invalid Types Prompt",
            "description": "A prompt with invalid data types",
            "version": 100,  # Should be string
            "tags": "not_a_list",  # Should be list
            "created_at": "05/14/2025",  # Invalid date format
            "prompt": "This is a prompt with invalid data types."
        }
        
        # Write test files
        with open(os.path.join(self.base_dir, "compliant.yaml"), "w") as f:
            yaml.dump(self.compliant_prompt, f)
        
        with open(os.path.join(self.base_dir, "partial.yaml"), "w") as f:
            yaml.dump(self.partial_prompt, f)
        
        with open(os.path.join(self.base_dir, "noncompliant.yaml"), "w") as f:
            yaml.dump(self.noncompliant_prompt, f)
        
        with open(os.path.join(self.base_dir, "invalid_types.yaml"), "w") as f:
            yaml.dump(self.invalid_types_prompt, f)
        
        # Initialize the standardizer
        self.standardizer = PromptStandardizer(base_dir=self.base_dir)
    
    def tearDown(self):
        """Clean up after the test case."""
        shutil.rmtree(self.temp_dir)
    
    def test_standardize_prompt(self):
        """Test standardizing individual prompts."""
        # Test standardizing already compliant prompt
        standardized = self.standardizer.standardize_prompt(self.compliant_prompt)
        self.assertEqual(standardized["version"], "1.0.0")
        self.assertEqual(standardized["tags"], ["test", "compliant"])
        
        # Test standardizing partially compliant prompt
        standardized = self.standardizer.standardize_prompt(self.partial_prompt)
        self.assertTrue("version" in standardized)
        self.assertTrue("tags" in standardized)
        self.assertTrue("created_at" in standardized)
        self.assertTrue("updated_at" in standardized)
        self.assertTrue("author" in standardized)
        self.assertTrue("active" in standardized)
        self.assertTrue("models" in standardized)
        
        # Test standardizing prompt with invalid data types
        standardized = self.standardizer.standardize_prompt(self.invalid_types_prompt)
        self.assertTrue(isinstance(standardized["version"], str))
        self.assertTrue(isinstance(standardized["tags"], list))
        self.assertEqual(len(standardized["tags"]), 0)  # Default empty list
        self.assertTrue(self._is_valid_iso_date(standardized["created_at"]))
    
    def test_standardize_prompt_file(self):
        """Test standardizing prompt files."""
        # Test standardizing a partially compliant file
        partial_file = os.path.join(self.base_dir, "partial.yaml")
        result = self.standardizer.standardize_prompt_file(partial_file, dry_run=True)
        
        # Validation should pass after standardization
        self.assertTrue(result.is_valid)
        
        # Test standardizing a non-compliant file
        noncompliant_file = os.path.join(self.base_dir, "noncompliant.yaml")
        result = self.standardizer.standardize_prompt_file(noncompliant_file, dry_run=True)
        
        # Validation should fail because name is still missing
        self.assertFalse(result.is_valid)
    
    def test_standardize_all_prompts(self):
        """Test standardizing all prompts in a directory."""
        # Run standardization on all files
        summary = self.standardizer.standardize_all_prompts(dry_run=True)
        
        # Check summary counts
        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["already_valid"], 1)  # compliant.yaml
        self.assertEqual(summary["standardized"], 2)  # partial.yaml and invalid_types.yaml
        self.assertEqual(summary["failed"], 1)  # noncompliant.yaml (missing name)
        
        # Check individual file statuses
        self.assertTrue(summary["files"]["compliant.yaml"]["pre_valid"])
        self.assertTrue(summary["files"]["compliant.yaml"]["post_valid"])
        self.assertFalse(summary["files"]["compliant.yaml"]["changed"])
        
        self.assertFalse(summary["files"]["partial.yaml"]["pre_valid"])
        self.assertTrue(summary["files"]["partial.yaml"]["post_valid"])
        self.assertTrue(summary["files"]["partial.yaml"]["changed"])
        
        self.assertFalse(summary["files"]["noncompliant.yaml"]["pre_valid"])
        self.assertFalse(summary["files"]["noncompliant.yaml"]["post_valid"])
        self.assertTrue("validation_issues" in summary["files"]["noncompliant.yaml"])
    
    def test_create_standardized_template(self):
        """Test creating a standardized prompt template."""
        template_path = os.path.join(self.temp_dir, "template.yaml")
        self.standardizer.create_standardized_template(template_path)
        
        # Check that the file was created
        self.assertTrue(os.path.exists(template_path))
        
        # Load and validate the template
        with open(template_path, "r") as f:
            template = yaml.safe_load(f)
        
        validator = PromptRegistryValidator()
        result = validator.validate(template)
        self.assertTrue(result.is_valid)
        
        # Check required fields
        self.assertTrue("id" in template)
        self.assertTrue("name" in template)
        self.assertTrue("description" in template)
        self.assertTrue("prompt" in template)
        
        # Check optional fields
        self.assertTrue("version" in template)
        self.assertTrue("tags" in template)
        self.assertTrue("created_at" in template)
        self.assertTrue("updated_at" in template)
        self.assertTrue("author" in template)
        self.assertTrue("active" in template)
        self.assertTrue("models" in template)
    
    def _is_valid_iso_date(self, date_str: str) -> bool:
        """Check if a string is a valid ISO date (YYYY-MM-DD)."""
        import re
        return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', date_str))

if __name__ == '__main__':
    unittest.main()
