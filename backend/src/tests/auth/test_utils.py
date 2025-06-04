"""
Test suite for authentication utilities.
"""
import unittest
from unittest.mock import patch, MagicMock

from src.auth.utils import get_agent_permissions, agent_can_use_tool, verify_auth_token
from src.auth.constants import format_tool_permission, PERMISSION_PREFIX, PERMISSION_VERB


class TestAuthUtils(unittest.TestCase):
    """Test cases for authentication utilities."""
    
    @patch('src.registries.registry_factory.RegistryFactory.get_tool_registry')
    def test_get_agent_permissions(self, mock_get_tool_registry):
        """Test getting agent permissions from registry."""
        # Setup mock registry
        mock_registry = MagicMock()
        mock_get_tool_registry.return_value = mock_registry
        
        # Mock list_tools to return test tools
        mock_registry.list_tools.return_value = [
            {
                "id": "schema_tool",
                "allowed_agents": ["schema_agent", "admin_agent"]
            },
            {
                "id": "data_tool",
                "allowed_agents": ["data_agent", "admin_agent"]
            },
            {
                "id": "common_tool",
                "allowed_agents": ["*"]  # Available to all agents
            }
        ]
        
        # Test getting permissions for schema_agent
        permissions = get_agent_permissions("schema_agent")
        
        # Should have permission to use schema_tool and common_tool
        self.assertIn(format_tool_permission("schema_tool"), permissions)
        self.assertIn(format_tool_permission("common_tool"), permissions)
        self.assertNotIn(format_tool_permission("data_tool"), permissions)
        
        # Should also have agent execution permission
        agent_execute = f"{PERMISSION_PREFIX['AGENT']}:schema_agent:{PERMISSION_VERB['EXECUTE']}"
        self.assertIn(agent_execute, permissions)
        
        # Test getting permissions for admin_agent
        permissions = get_agent_permissions("admin_agent")
        
        # Should have permission to use all tools
        self.assertIn(format_tool_permission("schema_tool"), permissions)
        self.assertIn(format_tool_permission("data_tool"), permissions)
        self.assertIn(format_tool_permission("common_tool"), permissions)
    
    @patch('src.registries.registry_factory.RegistryFactory.get_tool_registry')
    def test_agent_can_use_tool(self, mock_get_tool_registry):
        """Test checking if an agent can use a specific tool."""
        # Setup mock registry
        mock_registry = MagicMock()
        mock_get_tool_registry.return_value = mock_registry
        
        # Mock get_tool to return test tools
        mock_registry.get_tool.side_effect = lambda tool_id: {
            "schema_tool": {
                "id": "schema_tool",
                "active": True,
                "allowed_agents": ["schema_agent", "admin_agent"]
            },
            "inactive_tool": {
                "id": "inactive_tool",
                "active": False,
                "allowed_agents": ["schema_agent"]
            },
            "common_tool": {
                "id": "common_tool",
                "active": True,
                "allowed_agents": ["*"]  # Available to all agents
            },
            "nonexistent_tool": None
        }.get(tool_id)
        
        # Test agent with permission
        self.assertTrue(agent_can_use_tool("schema_agent", "schema_tool"))
        
        # Test agent without permission
        self.assertFalse(agent_can_use_tool("data_agent", "schema_tool"))
        
        # Test wildcard permission
        self.assertTrue(agent_can_use_tool("any_agent", "common_tool"))
        
        # Test inactive tool
        self.assertFalse(agent_can_use_tool("schema_agent", "inactive_tool"))
        
        # Test nonexistent tool
        self.assertFalse(agent_can_use_tool("schema_agent", "nonexistent_tool"))
    
    @patch('src.auth.factory.get_auth_adapter')
    def test_verify_auth_token(self, mock_get_auth_adapter):
        """Test verifying an authentication token."""
        # Setup mock auth adapter
        mock_adapter = MagicMock()
        mock_get_auth_adapter.return_value = mock_adapter
        
        # Mock verify_access to return test results
        mock_adapter.verify_access.side_effect = lambda token, tool_id: {
            ("valid_token", "allowed_tool"): True,
            ("valid_token", "disallowed_tool"): False,
            ("invalid_token", "any_tool"): False
        }.get((token, tool_id), False)
        
        # Test valid token with allowed tool
        self.assertTrue(verify_auth_token("valid_token", "allowed_tool"))
        
        # Test valid token with disallowed tool
        self.assertFalse(verify_auth_token("valid_token", "disallowed_tool"))
        
        # Test invalid token
        self.assertFalse(verify_auth_token("invalid_token", "allowed_tool"))
    
    @patch('src.auth.factory.get_auth_adapter')
    def test_verify_auth_token_import_error(self, mock_get_auth_adapter):
        """Test fallback when auth adapter is not available."""
        # Simulate ImportError when getting the auth adapter
        mock_get_auth_adapter.side_effect = ImportError("Auth module not found")
        
        # Should fall back to allowing access
        self.assertTrue(verify_auth_token("any_token", "any_tool"))
    
    @patch('src.auth.factory.get_auth_adapter')
    def test_verify_auth_token_exception(self, mock_get_auth_adapter):
        """Test error handling when verifying token."""
        # Setup mock auth adapter that raises an exception
        mock_adapter = MagicMock()
        mock_get_auth_adapter.return_value = mock_adapter
        mock_adapter.verify_access.side_effect = Exception("Test exception")
        
        # Should return False on exception
        self.assertFalse(verify_auth_token("any_token", "any_tool"))


if __name__ == '__main__':
    unittest.main()
