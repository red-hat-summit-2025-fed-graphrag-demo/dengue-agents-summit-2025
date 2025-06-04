"""
Test Registry Validator

Unit tests for the registry validation framework.
"""
import os
import json
import unittest
import tempfile
import yaml
from typing import Dict, Any

import sys
import os

# Add parent directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.registries.registry_validator import (
    ValidationSeverity,
    ValidationResult,
    RegistryValidator,
    ToolRegistryValidator,
    AgentRegistryValidator,
    PromptRegistryValidator
)

class TestValidationResult(unittest.TestCase):
    """Test the ValidationResult class."""
    
    def test_creation(self):
        """Test creating a validation result."""
        result = ValidationResult()
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.issues), 0)
    
    def test_add_issue(self):
        """Test adding issues to a validation result."""
        result = ValidationResult()
        
        # Add ERROR issue - should make result invalid
        result.add_issue("field1", "Error message", ValidationSeverity.ERROR)
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.issues), 1)
        
        # Add WARNING issue - should not change validity
        result.add_issue("field2", "Warning message", ValidationSeverity.WARNING)
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.issues), 2)
        
        # Add INFO issue - should not change validity
        result.add_issue("field3", "Info message", ValidationSeverity.INFO)
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.issues), 3)
    
    def test_get_formatted_issues(self):
        """Test getting formatted issue messages."""
        result = ValidationResult()
        result.add_issue("field1", "Error message", ValidationSeverity.ERROR)
        result.add_issue("field2", "Warning message", ValidationSeverity.WARNING)
        
        formatted = result.get_formatted_issues()
        self.assertEqual(len(formatted), 2)
        self.assertIn("ERROR", formatted[0])
        self.assertIn("field1", formatted[0])
        self.assertIn("WARNING", formatted[1])
        self.assertIn("field2", formatted[1])

class TestBaseRegistryValidator(unittest.TestCase):
    """Test the base RegistryValidator class."""
    
    def setUp(self):
        """Set up the validator for testing."""
        self.validator = RegistryValidator()
    
    def test_common_required_fields(self):
        """Test validation of common required fields."""
        # Valid item with all required fields
        valid_item = {
            "id": "test_id",
            "name": "Test Name",
            "description": "Test description",
            "active": True
        }
        
        result = self.validator.validate(valid_item)
        self.assertTrue(result.is_valid)
        
        # Missing required field
        invalid_item = {
            "id": "test_id",
            "name": "Test Name",
            "active": True
            # Missing description
        }
        
        result = self.validator.validate(invalid_item)
        self.assertFalse(result.is_valid)
        
        # Wrong type for required field
        invalid_item = {
            "id": "test_id",
            "name": 123,  # Should be string
            "description": "Test description",
            "active": True
        }
        
        result = self.validator.validate(invalid_item)
        self.assertFalse(result.is_valid)
    
    def test_common_optional_fields(self):
        """Test validation of common optional fields."""
        # Base valid item
        valid_item = {
            "id": "test_id",
            "name": "Test Name",
            "description": "Test description",
            "active": True
        }
        
        # Add valid optional fields
        valid_item_with_options = valid_item.copy()
        valid_item_with_options.update({
            "version": "1.0.0",
            "tags": ["test", "validation"],
            "created_at": "2025-05-14",
            "updated_at": "2025-05-14",
            "author": "Test Author"
        })
        
        result = self.validator.validate(valid_item_with_options)
        self.assertTrue(result.is_valid)
        
        # Add invalid optional fields - in the actual implementation, this doesn't make the
        # item invalid, but adds warnings, so we check that we have warning issues
        invalid_item_with_options = valid_item.copy()
        invalid_item_with_options.update({
            "version": 100,  # Should be string
            "tags": "not_a_list",  # Should be list
            "created_at": "2025-05-14",
            "updated_at": "2025-05-14",
            "author": "Test Author"
        })
        
        result = self.validator.validate(invalid_item_with_options)
        
        # The item is still considered valid (with warnings)
        self.assertTrue(result.is_valid)
        
        # But we should have warning issues for the invalid fields
        warning_count = 0
        for issue in result.issues:
            if issue["severity"] == ValidationSeverity.WARNING:
                warning_count += 1
        
        # Should have warnings for version and tags being wrong types
        self.assertGreaterEqual(warning_count, 2)
    
    def test_version_format(self):
        """Test validation of version format."""
        # Base valid item
        valid_item = {
            "id": "test_id",
            "name": "Test Name",
            "description": "Test description",
            "active": True
        }
        
        # Valid semantic version
        valid_version_item = valid_item.copy()
        valid_version_item["version"] = "1.0.0"
        
        result = self.validator.validate(valid_version_item)
        self.assertTrue(result.is_valid)
        
        # Invalid semantic version - just warning, not error
        invalid_version_item = valid_item.copy()
        invalid_version_item["version"] = "1.0"
        
        result = self.validator.validate(invalid_version_item)
        self.assertTrue(result.is_valid)  # Still valid as it's just a warning
        
        # Check that there's a warning about the version format
        version_warning_found = False
        for issue in result.issues:
            if (issue["field"] == "version" and 
                issue["severity"] == ValidationSeverity.WARNING):
                version_warning_found = True
                break
                
        self.assertTrue(version_warning_found, "No warning about version format found")
    
    def test_date_format(self):
        """Test validation of date format."""
        # Base valid item
        valid_item = {
            "id": "test_id",
            "name": "Test Name",
            "description": "Test description",
            "active": True
        }
        
        # Valid date format
        valid_date_item = valid_item.copy()
        valid_date_item["created_at"] = "2025-05-14"
        valid_date_item["updated_at"] = "2025-05-14"
        
        result = self.validator.validate(valid_date_item)
        self.assertTrue(result.is_valid)
        
        # Invalid date format - just warning, not error
        invalid_date_item = valid_item.copy()
        invalid_date_item["created_at"] = "05/14/2025"
        
        result = self.validator.validate(invalid_date_item)
        self.assertTrue(result.is_valid)  # Still valid as it's just a warning
        
        # Check that there's a warning about the date format
        date_warning_found = False
        for issue in result.issues:
            if (issue["field"] == "created_at" and 
                issue["severity"] == ValidationSeverity.WARNING):
                date_warning_found = True
                break
                
        self.assertTrue(date_warning_found, "No warning about date format found")

class TestToolRegistryValidator(unittest.TestCase):
    """Test the ToolRegistryValidator class."""
    
    def setUp(self):
        """Set up the validator for testing."""
        self.validator = ToolRegistryValidator()
    
    def test_tool_specific_fields(self):
        """Test validation of tool-specific required fields."""
        # Valid tool item
        valid_tool = {
            "id": "test_tool",
            "name": "Test Tool",
            "description": "Test tool description",
            "active": True,
            "module_path": "src.tools.test_tool",
            "class_name": "TestTool",
            "config_path": "configs/test_tool.yaml",
            "allowed_agents": ["*"]
        }
        
        result = self.validator.validate(valid_tool)
        self.assertTrue(result.is_valid)
        
        # Missing tool-specific required field
        invalid_tool = {
            "id": "test_tool",
            "name": "Test Tool",
            "description": "Test tool description",
            "active": True,
            "module_path": "src.tools.test_tool",
            "class_name": "TestTool",
            # Missing config_path
            "allowed_agents": ["*"]
        }
        
        result = self.validator.validate(invalid_tool)
        self.assertFalse(result.is_valid)
    
    def test_empty_allowed_agents(self):
        """Test validation of empty allowed_agents list."""
        # Tool with empty allowed_agents list
        tool_with_empty_allowed = {
            "id": "test_tool",
            "name": "Test Tool",
            "description": "Test tool description",
            "active": True,
            "module_path": "src.tools.test_tool",
            "class_name": "TestTool",
            "config_path": "configs/test_tool.yaml",
            "allowed_agents": []
        }
        
        result = self.validator.validate(tool_with_empty_allowed)
        self.assertTrue(result.is_valid)  # Still valid, but should have warning
        
        # Find the warning about empty allowed_agents
        warning_found = False
        for issue in result.issues:
            if (issue["field"] == "allowed_agents" and 
                issue["severity"] == ValidationSeverity.WARNING):
                warning_found = True
                break
        
        self.assertTrue(warning_found, "No warning about empty allowed_agents")

class TestAgentRegistryValidator(unittest.TestCase):
    """Test the AgentRegistryValidator class."""
    
    def setUp(self):
        """Set up the validator for testing."""
        self.validator = AgentRegistryValidator()
    
    def test_agent_specific_fields(self):
        """Test validation of agent-specific required fields."""
        # Valid agent item
        valid_agent = {
            "id": "test_agent",
            "name": "Test Agent",
            "description": "Test agent description",
            "active": True,
            "module_path": "src.agent_system.test_agent",
            "class_name": "TestAgent",
            "config_path": "configs/test_agent.yaml",
            "prompt_id": "test.prompt",
            "model_config": {
                "model_type": "instruct",
                "max_tokens": 1024,
                "temperature": 0.7
            }
        }
        
        result = self.validator.validate(valid_agent)
        self.assertTrue(result.is_valid)
        
        # Missing agent-specific required field
        invalid_agent = {
            "id": "test_agent",
            "name": "Test Agent",
            "description": "Test agent description",
            "active": True,
            "module_path": "src.agent_system.test_agent",
            "class_name": "TestAgent",
            "config_path": "configs/test_agent.yaml",
            # Missing prompt_id
            "model_config": {
                "model_type": "instruct",
                "max_tokens": 1024,
                "temperature": 0.7
            }
        }
        
        result = self.validator.validate(invalid_agent)
        self.assertFalse(result.is_valid)
    
    def test_model_config_validation(self):
        """Test validation of model_config fields."""
        # Valid agent with valid model_config
        valid_agent = {
            "id": "test_agent",
            "name": "Test Agent",
            "description": "Test agent description",
            "active": True,
            "module_path": "src.agent_system.test_agent",
            "class_name": "TestAgent",
            "config_path": "configs/test_agent.yaml",
            "prompt_id": "test.prompt",
            "model_config": {
                "model_type": "instruct",
                "max_tokens": 1024,
                "temperature": 0.7,
                "top_p": 0.95
            }
        }
        
        result = self.validator.validate(valid_agent)
        self.assertTrue(result.is_valid)
        
        # Missing required model_config fields
        invalid_agent = {
            "id": "test_agent",
            "name": "Test Agent",
            "description": "Test agent description",
            "active": True,
            "module_path": "src.agent_system.test_agent",
            "class_name": "TestAgent",
            "config_path": "configs/test_agent.yaml",
            "prompt_id": "test.prompt",
            "model_config": {
                # Missing model_type
                "max_tokens": 1024,
                "temperature": 0.7
            }
        }
        
        result = self.validator.validate(invalid_agent)
        self.assertFalse(result.is_valid)
        
        # Invalid type for model_config fields
        invalid_agent = {
            "id": "test_agent",
            "name": "Test Agent",
            "description": "Test agent description",
            "active": True,
            "module_path": "src.agent_system.test_agent",
            "class_name": "TestAgent",
            "config_path": "configs/test_agent.yaml",
            "prompt_id": "test.prompt",
            "model_config": {
                "model_type": "instruct",
                "max_tokens": "1024",  # Should be number
                "temperature": 0.7
            }
        }
        
        result = self.validator.validate(invalid_agent)
        self.assertFalse(result.is_valid)

class TestPromptRegistryValidator(unittest.TestCase):
    """Test the PromptRegistryValidator class."""
    
    def setUp(self):
        """Set up the validator for testing."""
        self.validator = PromptRegistryValidator()
    
    def test_prompt_specific_fields(self):
        """Test validation of prompt-specific required fields."""
        # Valid prompt item
        valid_prompt = {
            "id": "test.prompt",
            "name": "Test Prompt",
            "description": "Test prompt description",
            "active": True,
            "prompt": "This is a test prompt template."
        }
        
        result = self.validator.validate(valid_prompt)
        self.assertTrue(result.is_valid)
        
        # Missing prompt-specific required field
        invalid_prompt = {
            "id": "test.prompt",
            "name": "Test Prompt",
            "description": "Test prompt description",
            "active": True
            # Missing prompt
        }
        
        result = self.validator.validate(invalid_prompt)
        self.assertFalse(result.is_valid)
    
    def test_short_prompt_warning(self):
        """Test validation warning for very short prompts."""
        # Prompt with suspiciously short text
        short_prompt = {
            "id": "test.prompt",
            "name": "Test Prompt",
            "description": "Test prompt description",
            "active": True,
            "prompt": "Test"  # Very short
        }
        
        result = self.validator.validate(short_prompt)
        self.assertTrue(result.is_valid)  # Still valid, but should have warning
        
        # Find the warning about short prompt
        warning_found = False
        for issue in result.issues:
            if (issue["field"] == "prompt" and 
                issue["severity"] == ValidationSeverity.WARNING):
                warning_found = True
                break
        
        self.assertTrue(warning_found, "No warning about short prompt")

if __name__ == '__main__':
    unittest.main()
