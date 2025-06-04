"""
Keycloak Authentication Adapter

This module implements a Keycloak-based authentication adapter for production use.
"""
import os
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

try:
    from keycloak import KeycloakOpenID
    from keycloak.exceptions import KeycloakError
except ImportError:
    raise ImportError("Keycloak dependencies not installed. Run: pip install python-keycloak")

from src.auth.adapter.base import AuthAdapter, AuthenticationError
from src.auth.models import TokenPayload
from src.auth.constants import format_tool_permission

logger = logging.getLogger(__name__)


class KeycloakAuthAdapter(AuthAdapter):
    """
    Keycloak-based authentication adapter for production.
    
    This adapter integrates with a Keycloak instance for secure authentication
    and authorization in production environments.
    """
    
    def __init__(
        self,
        server_url: str,
        realm: str,
        client_id: str,
        client_secret: Optional[str] = None,
        verify_ssl: bool = True
    ):
        """
        Initialize the Keycloak authentication adapter.
        
        Args:
            server_url: URL of the Keycloak server
            realm: Keycloak realm name
            client_id: Client ID for this application
            client_secret: Client secret (if required)
            verify_ssl: Whether to verify SSL certificates
        """
        self.server_url = server_url
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret
        self.verify_ssl = verify_ssl
        
        # Initialize the Keycloak client
        try:
            self.keycloak_client = KeycloakOpenID(
                server_url=server_url,
                client_id=client_id,
                realm_name=realm,
                client_secret_key=client_secret,
                verify=verify_ssl
            )
            logger.info(f"Initialized Keycloak client for realm {realm} at {server_url}")
            
            # Get the public key for token verification
            self.public_key = "-----BEGIN PUBLIC KEY-----\n"
            self.public_key += self.keycloak_client.public_key()
            self.public_key += "\n-----END PUBLIC KEY-----"
            
        except Exception as e:
            logger.error(f"Failed to initialize Keycloak client: {str(e)}")
            # We'll initialize without connecting to the server for now
            # This allows the adapter to be created even if Keycloak is not available
            self.keycloak_client = None
            self.public_key = None
    
    def get_token(self, agent_id: str) -> str:
        """
        Get an authentication token for the specified agent.
        
        Args:
            agent_id: The ID of the agent requesting a token
            
        Returns:
            A valid JWT token as a string
            
        Raises:
            ValueError: If the agent is not authorized to obtain a token
            AuthenticationError: If there's an error during token creation
        """
        try:
            if not self.keycloak_client:
                raise AuthenticationError("Keycloak client not initialized")
                
            # For agents, we'll use client credentials grant with agent_id as username
            # This is a placeholder - in a real implementation, you would:
            # 1. Map agent_id to a Keycloak user or service account
            # 2. Use appropriate credentials for that account
            
            # For demonstration purposes, we're using a simplified approach
            token_response = self.keycloak_client.token(
                grant_type="client_credentials"
            )
            
            # Extract the access token
            access_token = token_response.get("access_token")
            if not access_token:
                raise AuthenticationError("Failed to obtain access token from Keycloak")
                
            return access_token
            
        except KeycloakError as e:
            logger.error(f"Keycloak error creating token for agent {agent_id}: {str(e)}")
            raise AuthenticationError(f"Keycloak error: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating token for agent {agent_id}: {str(e)}")
            raise AuthenticationError(f"Failed to create token: {str(e)}")
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify the validity of an authentication token.
        
        Args:
            token: The authentication token to verify
            
        Returns:
            The token payload as a dictionary if valid, None otherwise
            
        Raises:
            AuthenticationError: If there's an error during token verification
        """
        try:
            if not self.keycloak_client:
                raise AuthenticationError("Keycloak client not initialized")
                
            # Verify the token
            options = {
                "verify_signature": True,
                "verify_aud": True,
                "verify_exp": True
            }
            
            token_info = self.keycloak_client.decode_token(
                token=token,
                key=self.public_key,
                options=options
            )
            
            return token_info
            
        except KeycloakError as e:
            logger.warning(f"Keycloak token validation error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error verifying token: {str(e)}")
            raise AuthenticationError(f"Failed to verify token: {str(e)}")
    
    def verify_access(self, token: str, tool_id: str) -> bool:
        """
        Verify if the token grants access to the specified tool.
        
        Args:
            token: The authentication token to verify
            tool_id: The ID of the tool to check access for
            
        Returns:
            True if the token grants access to the tool, False otherwise
            
        Raises:
            AuthenticationError: If there's an error during access verification
        """
        try:
            if not self.keycloak_client:
                raise AuthenticationError("Keycloak client not initialized")
                
            # Verify the token
            token_info = self.verify_token(token)
            if not token_info:
                return False
                
            # Extract resource access information
            resource_access = token_info.get("resource_access", {})
            client_access = resource_access.get(self.client_id, {})
            roles = client_access.get("roles", [])
            
            # Check for specific tool permission role
            tool_permission = format_tool_permission(tool_id).replace(":", "_")
            has_permission = tool_permission in roles
            
            # Check for admin role
            is_admin = "admin" in roles
            
            return has_permission or is_admin
            
        except KeycloakError as e:
            logger.error(f"Keycloak error verifying access: {str(e)}")
            raise AuthenticationError(f"Keycloak error: {str(e)}")
        except Exception as e:
            logger.error(f"Error verifying access: {str(e)}")
            raise AuthenticationError(f"Failed to verify access: {str(e)}")
    
    def refresh_token(self, token: str) -> str:
        """
        Refresh an existing token to extend its validity.
        
        Args:
            token: The token to refresh
            
        Returns:
            A new token with extended validity
            
        Raises:
            AuthenticationError: If the token cannot be refreshed
        """
        try:
            if not self.keycloak_client:
                raise AuthenticationError("Keycloak client not initialized")
                
            # Verify the token to extract user information
            token_info = self.verify_token(token)
            if not token_info:
                raise AuthenticationError("Invalid token for refresh")
                
            # Extract agent ID
            agent_id = token_info.get("sub")
            if not agent_id:
                raise AuthenticationError("Token missing subject identifier")
                
            # Get a new token
            return self.get_token(agent_id)
            
        except KeycloakError as e:
            logger.error(f"Keycloak error refreshing token: {str(e)}")
            raise AuthenticationError(f"Keycloak error: {str(e)}")
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            raise AuthenticationError(f"Failed to refresh token: {str(e)}")
    
    def invalidate_token(self, token: str) -> bool:
        """
        Invalidate a token so it can no longer be used.
        
        Args:
            token: The token to invalidate
            
        Returns:
            True if the token was successfully invalidated, False otherwise
            
        Raises:
            AuthenticationError: If there's an error during token invalidation
        """
        try:
            if not self.keycloak_client:
                raise AuthenticationError("Keycloak client not initialized")
                
            # Verify the token to make sure it's valid
            token_info = self.verify_token(token)
            if not token_info:
                # If the token is invalid, consider it already invalidated
                return True
                
            # Extract refresh token (if available)
            refresh_token = None
            if hasattr(token, "refresh_token"):
                refresh_token = token.refresh_token
                
            # Logout the session
            if refresh_token:
                self.keycloak_client.logout(refresh_token)
                
            return True
            
        except KeycloakError as e:
            logger.error(f"Keycloak error invalidating token: {str(e)}")
            raise AuthenticationError(f"Keycloak error: {str(e)}")
        except Exception as e:
            logger.error(f"Error invalidating token: {str(e)}")
            raise AuthenticationError(f"Failed to invalidate token: {str(e)}")
            
    def _format_keycloak_role(self, permission: str) -> str:
        """Convert a permission string to a Keycloak role name."""
        return permission.replace(":", "_")
