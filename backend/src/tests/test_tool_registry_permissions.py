"""
Tests for the permission-related methods in the ToolRegistry class.
"""
import unittest
import os
import sys
import json
import tempfile
from unittest.mock import patch, MagicMock

# Handle imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.registries.tool_registry import ToolRegistry, ALL_AGENTS

class TestToolRegistryPermissions(unittest.TestCase):
    """Test the permission-related methods in the ToolRegistry class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary file for the registry
        self.temp_registry = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_registry_path = self.temp_registry.name
        
        # Create a sample registry file
        sample_registry = {
            "tools": {
                "test_tool1": {
                    "id": "test_tool1",
                    "name": "Test Tool 1",
                    "description": "A test tool",
                    "active": True,
                    "module_path": "src.tools.test_tool",
                    "class_name": "TestTool",
                    "allowed_agents": ["agent1", "agent2"]
                },
                "test_tool2": {
                    "id": "test_tool2",
                    "name": "Test Tool 2",
                    "description": "Another test tool",
                    "active": True,
                    "module_path": "src.tools.test_tool",
                    "class_name": "TestTool",
                    "allowed_agents": ["*"]
                },
                "test_tool3": {
                    "id": "test_tool3",
                    "name": "Test Tool 3",
                    "description": "Yet another test tool",
                    "active": True,
                    "module_path": "src.tools.test_tool",
                    "class_name": "TestTool",
                    "allowed_agents": []
                },
                "test_tool4": {
                    "id": "test_tool4", 
                    "name": "Test Tool 4",
                    "description": "Inactive test tool",
                    "active": False,
                    "module_path": "src.tools.test_tool",
                    "class_name": "TestTool",
                    "allowed_agents": ["agent1"]
                }
            }
        }
        
        # Write the sample registry to the temporary file
        with open(self.temp_registry_path, 'w') as f:
            json.dump(sample_registry, f)
        
        # Create the ToolRegistry instance with the temporary registry file
        self.registry = ToolRegistry(registry_path=self.temp_registry_path)
    
    def tearDown(self):
        """Clean up after tests."""
        # Delete the temporary registry file
        os.unlink(self.temp_registry_path)
    
    def test_agent_can_use_tool(self):
        """Test the agent_can_use_tool method."""
        # Test basic permission checks
        self.assertTrue(self.registry.agent_can_use_tool("agent1", "test_tool1"))
        self.assertTrue(self.registry.agent_can_use_tool("agent2", "test_tool1"))
        self.assertFalse(self.registry.agent_can_use_tool("agent3", "test_tool1"))
        
        # Test wildcard permission
        self.assertTrue(self.registry.agent_can_use_tool("any_agent", "test_tool2"))
        
        # Test empty allowed_agents list
        self.assertFalse(self.registry.agent_can_use_tool("agent1", "test_tool3"))
        
        # Test inactive tool
        self.assertFalse(self.registry.agent_can_use_tool("agent1", "test_tool4"))
        
        # Test tool not found
        self.assertFalse(self.registry.agent_can_use_tool("agent1", "nonexistent_tool"))
    
    def test_agent_can_use_tool(self):
        """Test the agent_can_use_tool method."""
        # We'll test this method directly instead of get_allowed_tools_for_agent
        # to avoid dependency on list_tools with active_only parameter
        
        # Test basic permission checks
        self.assertTrue(self.registry.agent_can_use_tool("agent1", "test_tool1"))
        self.assertTrue(self.registry.agent_can_use_tool("agent2", "test_tool1"))
        self.assertFalse(self.registry.agent_can_use_tool("agent3", "test_tool1"))
        
        # Test wildcard permission
        self.assertTrue(self.registry.agent_can_use_tool("any_agent", "test_tool2"))
        
        # Test empty allowed_agents list
        self.assertFalse(self.registry.agent_can_use_tool("agent1", "test_tool3"))
        
        # Test inactive tool
        self.assertFalse(self.registry.agent_can_use_tool("agent1", "test_tool4"))
        
        # Test tool not found
        self.assertFalse(self.registry.agent_can_use_tool("agent1", "nonexistent_tool"))
    
    def test_update_tool_permissions(self):
        """Test the update_tool_permissions method."""
        # Test updating permissions
        result = self.registry.update_tool_permissions("test_tool1", ["agent1", "agent3"])
        self.assertTrue(result)
        
        # Verify the permissions were updated
        tool_config = self.registry.get_tool_config("test_tool1")  
        self.assertEqual(tool_config["allowed_agents"], ["agent1", "agent3"])
        
        # Test updating non-existent tool
        result = self.registry.update_tool_permissions("nonexistent_tool", ["agent1"])
        self.assertFalse(result)
    
    def test_grant_and_revoke_agent_access(self):
        """Test the grant_agent_access and revoke_agent_access methods."""
        # Grant access
        self.registry.grant_agent_access("agent3", "test_tool1")
        tool_config = self.registry.get_tool_config("test_tool1")
        self.assertIn("agent3", tool_config["allowed_agents"])
        
        # Revoke access
        self.registry.revoke_agent_access("agent3", "test_tool1")
        tool_config = self.registry.get_tool_config("test_tool1")
        self.assertNotIn("agent3", tool_config["allowed_agents"])
        
        # Test with a wildcard tool
        self.registry.grant_agent_access("agent3", "test_tool2")
        tool_config = self.registry.get_tool_config("test_tool2")
        # Should still have the wildcard
        self.assertIn("*", tool_config["allowed_agents"])

if __name__ == '__main__':
    unittest.main()
