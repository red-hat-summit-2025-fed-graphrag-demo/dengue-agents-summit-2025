"""
Test suite for the JWT authentication adapter.
"""
import unittest
from unittest.mock import patch, MagicMock
import jwt
from datetime import datetime, timedelta

from src.auth.adapter.jwt_adapter import LocalJwtAuthAdapter
from src.auth.models import TokenPayload
from src.auth.constants import format_tool_permission


class TestLocalJwtAdapter(unittest.TestCase):
    """Test cases for LocalJwtAuthAdapter."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a test adapter with a fixed secret key
        self.secret_key = "test-secret-key"
        self.adapter = LocalJwtAuthAdapter(
            secret_key=self.secret_key,
            token_expiry_seconds=300,  # 5 minutes
            issuer="test-issuer"
        )
        
        # Prepare test permissions
        self.test_permissions = {
            "test_agent": [
                format_tool_permission("test_tool"),
                format_tool_permission("common_tool")
            ],
            "admin_agent": [
                "admin:*:*",  # Admin wildcard permission
                format_tool_permission("admin_tool")
            ]
        }
        
        # Set permissions directly for testing
        self.adapter.permissions = self.test_permissions

    def test_get_token(self):
        """Test token generation."""
        # Get a token for test_agent
        token = self.adapter.get_token("test_agent")
        
        # Verify it's a string
        self.assertIsInstance(token, str)
        
        # Verify the token can be decoded
        payload = self.adapter.verify_token(token)
        self.assertIsNotNone(payload)
        
        # Check token contents
        self.assertEqual(payload["sub"], "test_agent")
        self.assertEqual(payload["iss"], "test-issuer")
        self.assertIn("exp", payload)
        self.assertIn("iat", payload)
        self.assertIn("jti", payload)
        
        # Check permissions
        self.assertEqual(set(payload["permissions"]), 
                        set(self.test_permissions["test_agent"]))

    def test_verify_token(self):
        """Test token verification."""
        # Get a token
        token = self.adapter.get_token("test_agent")
        
        # Verify it
        payload = self.adapter.verify_token(token)
        self.assertIsNotNone(payload)
        
        # Test with invalid token
        invalid_token = token + "invalid"
        payload = self.adapter.verify_token(invalid_token)
        self.assertIsNone(payload)
        
        # Test with expired token (mock)
        with patch('jwt.decode') as mock_decode:
            mock_decode.side_effect = jwt.ExpiredSignatureError
            payload = self.adapter.verify_token(token)
            self.assertIsNone(payload)

    def test_verify_access(self):
        """Test access verification."""
        # Get a token for test_agent
        token = self.adapter.get_token("test_agent")
        
        # Test access to allowed tool
        has_access = self.adapter.verify_access(token, "test_tool")
        self.assertTrue(has_access)
        
        # Test access to common tool
        has_access = self.adapter.verify_access(token, "common_tool")
        self.assertTrue(has_access)
        
        # Test access to unauthorized tool
        has_access = self.adapter.verify_access(token, "admin_tool")
        self.assertFalse(has_access)
        
        # Get a token for admin_agent
        admin_token = self.adapter.get_token("admin_agent")
        
        # Test admin access (should have access to everything due to wildcard)
        has_access = self.adapter.verify_access(admin_token, "any_tool")
        self.assertTrue(has_access)

    def test_refresh_token(self):
        """Test token refresh."""
        # Get a token
        token = self.adapter.get_token("test_agent")
        
        # Refresh it
        new_token = self.adapter.refresh_token(token)
        
        # Verify new token is valid
        payload = self.adapter.verify_token(new_token)
        self.assertIsNotNone(payload)
        
        # Check that it's a different token
        self.assertNotEqual(token, new_token)
        
        # Check that the agent ID is preserved
        self.assertEqual(payload["sub"], "test_agent")

    def test_invalidate_token(self):
        """Test token invalidation."""
        # Get a token
        token = self.adapter.get_token("test_agent")
        
        # Verify it's valid
        payload = self.adapter.verify_token(token)
        self.assertIsNotNone(payload)
        
        # Invalidate it
        success = self.adapter.invalidate_token(token)
        self.assertTrue(success)
        
        # Verify it's no longer valid
        payload = self.adapter.verify_token(token)
        self.assertIsNone(payload)
        
        # Test invalidating an already invalid token
        success = self.adapter.invalidate_token(token)
        self.assertTrue(success)  # Should return True since token is already invalid

    @patch('src.registries.registry_factory.RegistryFactory.get_tool_registry')
    def test_load_permissions_from_registry(self, mock_get_tool_registry):
        """Test loading permissions from registry."""
        # Create mock registry
        mock_registry = MagicMock()
        mock_get_tool_registry.return_value = mock_registry
        
        # Mock list_tools to return test tools
        mock_registry.list_tools.return_value = [
            {
                "id": "tool1",
                "allowed_agents": ["agent1", "agent2"]
            },
            {
                "id": "tool2",
                "allowed_agents": ["agent2"]
            },
            {
                "id": "tool3",
                "allowed_agents": ["*"]  # Wildcard permission
            }
        ]
        
        # Reset permissions to test loading
        self.adapter.permissions = {}
        
        # Test loading permissions
        self.adapter._load_permissions_from_registry()
        
        # Verify permissions are loaded correctly
        self.assertIn("agent1", self.adapter.permissions)
        self.assertIn("agent2", self.adapter.permissions)
        
        # Check specific permissions
        self.assertIn(format_tool_permission("tool1"), self.adapter.permissions["agent1"])
        self.assertIn(format_tool_permission("tool1"), self.adapter.permissions["agent2"])
        self.assertIn(format_tool_permission("tool2"), self.adapter.permissions["agent2"])


if __name__ == '__main__':
    unittest.main()
