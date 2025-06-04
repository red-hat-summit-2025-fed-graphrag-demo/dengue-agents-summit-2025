"""
Tests for permission utilities and registry permission functions.
"""
import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock

# Handle imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.registries.permission_utils import (
    has_permission, 
    get_agent_allowed_tools,
    is_agent_allowed,
    update_tool_permissions,
    get_permission_matrix
)
from src.registries.tool_registry import ToolRegistry

class TestPermissionUtils(unittest.TestCase):
    """Test permission utility functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock tool registry with sample data
        self.mock_registry_data = {
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
        
        # Create patch for the ToolRegistry
        patcher = patch('src.registries.permission_utils.RegistryFactory')
        self.mock_factory = patcher.start()
        self.addCleanup(patcher.stop)
        
        # Configure the mock
        self.mock_tool_registry = MagicMock(spec=ToolRegistry)
        self.mock_factory.get_tool_registry.return_value = self.mock_tool_registry
        
        # Configure the get_tool_config mock
        def mock_get_tool_config(tool_id):
            if tool_id not in self.mock_registry_data:
                raise ValueError(f"Tool '{tool_id}' not found")
            return self.mock_registry_data[tool_id]
        
        self.mock_tool_registry.get_tool_config.side_effect = mock_get_tool_config
        
        # Configure the list_tools mock
        def mock_list_tools(active_only=False):
            if active_only:
                return [t for t in self.mock_registry_data.values() if t.get("active", True)]
            return list(self.mock_registry_data.values())
        
        self.mock_tool_registry.list_tools.side_effect = mock_list_tools
        
        # Configure the check_agent_access mock
        def mock_check_agent_access(agent_id, tool_id):
            if tool_id not in self.mock_registry_data:
                return False
            
            tool = self.mock_registry_data[tool_id]
            if not tool.get("active", True):
                return False
                
            allowed_agents = tool.get("allowed_agents", [])
            if "*" in allowed_agents:
                return True
                
            return agent_id in allowed_agents
        
        self.mock_tool_registry.check_agent_access.side_effect = mock_check_agent_access
    
    def test_has_permission(self):
        """Test the has_permission function."""
        # Test basic permission checks
        self.assertTrue(has_permission("agent1", "test_tool1"))
        self.assertTrue(has_permission("agent2", "test_tool1"))
        self.assertFalse(has_permission("agent3", "test_tool1"))
        
        # Test wildcard permission
        self.assertTrue(has_permission("any_agent", "test_tool2"))
        
        # Test empty allowed_agents list
        self.assertFalse(has_permission("agent1", "test_tool3"))
        
        # Test inactive tool
        self.assertFalse(has_permission("agent1", "test_tool4"))
        
        # Test tool not found
        self.assertFalse(has_permission("agent1", "nonexistent_tool"))
    
    def test_get_agent_allowed_tools(self):
        """Test the get_agent_allowed_tools function."""
        # Test agent with specific permissions
        allowed_tools = get_agent_allowed_tools("agent1")
        self.assertIn("test_tool1", allowed_tools)
        self.assertIn("test_tool2", allowed_tools)
        self.assertNotIn("test_tool3", allowed_tools)
        self.assertNotIn("test_tool4", allowed_tools)  # Inactive tool
        
        # Test agent with no specific permissions
        allowed_tools = get_agent_allowed_tools("agent3")
        self.assertNotIn("test_tool1", allowed_tools)
        self.assertIn("test_tool2", allowed_tools)  # Wildcard tool
        self.assertNotIn("test_tool3", allowed_tools)
        self.assertNotIn("test_tool4", allowed_tools)
    
    def test_is_agent_allowed(self):
        """Test the is_agent_allowed function."""
        # Test basic permissions
        self.assertTrue(is_agent_allowed("agent1", ["agent1", "agent2"]))
        self.assertFalse(is_agent_allowed("agent3", ["agent1", "agent2"]))
        
        # Test wildcard permission
        self.assertTrue(is_agent_allowed("any_agent", ["*"]))
        
        # Test empty allowed list
        self.assertFalse(is_agent_allowed("agent1", []))
    
    def test_update_tool_permissions(self):
        """Test the update_tool_permissions function."""
        # Setup register_tool mock
        self.mock_tool_registry.register_tool.return_value = True
        
        # Test updating permissions
        result = update_tool_permissions("test_tool1", ["agent1", "agent3"])
        self.assertTrue(result)
        
        # Verify register_tool was called with updated config
        self.mock_tool_registry.register_tool.assert_called_once()
        updated_config = self.mock_tool_registry.register_tool.call_args[0][0]
        self.assertEqual(updated_config["allowed_agents"], ["agent1", "agent3"])
        
        # Test updating non-existent tool
        self.mock_tool_registry.get_tool_config.side_effect = ValueError("Tool not found")
        result = update_tool_permissions("nonexistent_tool", ["agent1"])
        self.assertFalse(result)
    
    def test_get_permission_matrix(self):
        """Test the get_permission_matrix function."""
        # Setup agent registry mock
        mock_agent_registry = MagicMock()
        mock_agent_registry.list_agents.return_value = [
            {"id": "agent1", "name": "Agent 1"},
            {"id": "agent2", "name": "Agent 2"}
        ]
        self.mock_factory.get_agent_registry.return_value = mock_agent_registry
        
        # Reset tool_registry mock behavior after it was changed in previous test
        self.mock_tool_registry.get_tool_config.side_effect = lambda tool_id: self.mock_registry_data[tool_id]
        
        # Test the matrix generation
        matrix = get_permission_matrix()
        self.assertIn("agent1", matrix)
        self.assertIn("agent2", matrix)
        
        # Check permissions for agent1
        self.assertIn("test_tool1", matrix["agent1"])
        self.assertIn("test_tool2", matrix["agent1"])
        self.assertNotIn("test_tool3", matrix["agent1"])
        self.assertNotIn("test_tool4", matrix["agent1"])  # Inactive tool
        
        # Check permissions for agent2
        self.assertIn("test_tool1", matrix["agent2"])
        self.assertIn("test_tool2", matrix["agent2"])
        self.assertNotIn("test_tool3", matrix["agent2"])
        self.assertNotIn("test_tool4", matrix["agent2"])

if __name__ == '__main__':
    unittest.main()
