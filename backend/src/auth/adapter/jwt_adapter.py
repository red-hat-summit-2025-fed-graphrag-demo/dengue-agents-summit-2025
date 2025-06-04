"""
JWT Authentication Adapter

This module implements a simple JWT-based authentication adapter for local development.
"""
import os
import json
import time
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

try:
    import jwt
except ImportError:
    raise ImportError("JWT dependencies not installed. Run: pip install pyjwt cryptography")

from src.auth.adapter.base import AuthAdapter, AuthenticationError
from src.auth.models import TokenPayload
from src.auth.constants import format_tool_permission, PERMISSION_PREFIX
from src.registries.registry_factory import RegistryFactory

logger = logging.getLogger(__name__)


class LocalJwtAuthAdapter(AuthAdapter):
    """
    JWT-based authentication adapter for local development.
    
    This adapter provides a simple JWT-based authentication mechanism
    for local development without requiring external services.
    """
    
    def __init__(
        self,
        secret_key: Optional[str] = None,
        token_expiry_seconds: int = 3600,
        token_refresh_seconds: int = 86400,
        issuer: str = "dengue-agents-auth",
        token_algorithm: str = "HS256",
        permissions_file: Optional[str] = None
    ):
        """
        Initialize the JWT authentication adapter.
        
        Args:
            secret_key: Secret key for signing tokens, defaults to env variable or a random key
            token_expiry_seconds: Token expiry time in seconds (default: 1 hour)
            token_refresh_seconds: Refresh token expiry time in seconds (default: 24 hours)
            issuer: Token issuer identifier
            token_algorithm: JWT algorithm to use for signing
            permissions_file: Optional path to a JSON file containing permissions
        """
        # Set the secret key
        self.secret_key = secret_key
        if not self.secret_key:
            self.secret_key = os.environ.get("JWT_SECRET_KEY", str(uuid.uuid4()))
            
        # Set token configuration
        self.token_expiry_seconds = token_expiry_seconds
        self.token_refresh_seconds = token_refresh_seconds
        self.issuer = issuer
        self.token_algorithm = token_algorithm
        
        # Load permissions
        self.permissions = {}
        if permissions_file and os.path.exists(permissions_file):
            try:
                with open(permissions_file, 'r') as f:
                    self.permissions = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load permissions file: {str(e)}")
                
        # If no permissions file provided, use the registry to determine permissions
        if not self.permissions:
            self._load_permissions_from_registry()
            
        # Cache for issued tokens to support invalidation
        self._token_cache = {}
            
    def _load_permissions_from_registry(self) -> None:
        """Load permissions from the tool registry."""
        try:
            # Get the tool registry
            tool_registry = RegistryFactory.get_tool_registry()
            
            # Get all active tools
            tools = tool_registry.list_tools(active_only=True)
            
            # Build the permissions dictionary from tool registry
            # We'll map agent_id -> list of tool permissions
            self.permissions = {}
            
            for tool in tools:
                tool_id = tool["id"]
                # Get the allowed_agents for this tool
                allowed_agents = tool.get("allowed_agents", [])
                
                # Handle wildcard permission
                if "*" in allowed_agents:
                    # Assign this tool permission to all agents
                    # We'll create agent entries as we encounter them
                    pass
                else:
                    # Assign specific permissions to specific agents
                    for agent_id in allowed_agents:
                        if agent_id not in self.permissions:
                            self.permissions[agent_id] = []
                            
                        # Add the tool permission
                        tool_permission = format_tool_permission(tool_id)
                        if tool_permission not in self.permissions[agent_id]:
                            self.permissions[agent_id].append(tool_permission)
                            
            logger.info(f"Loaded permissions for {len(self.permissions)} agents from registry")
                
        except Exception as e:
            logger.error(f"Failed to load permissions from registry: {str(e)}")
            # Initialize with empty permissions
            self.permissions = {}
            
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
            # Get permissions for this agent
            agent_permissions = self._get_agent_permissions(agent_id)
            
            # Create token payload
            issued_at = datetime.now()
            expires_at = issued_at + timedelta(seconds=self.token_expiry_seconds)
            token_id = str(uuid.uuid4())
            
            payload = TokenPayload(
                agent_id=agent_id,
                permissions=agent_permissions,
                issued_at=issued_at,
                expires_at=expires_at,
                token_id=token_id,
                issuer=self.issuer
            )
            
            # Convert to dictionary for JWT encoding
            token_dict = payload.to_dict()
            
            # Encode the token
            token = jwt.encode(
                token_dict,
                self.secret_key,
                algorithm=self.token_algorithm
            )
            
            # Cache the token for later invalidation
            self._token_cache[token_id] = token
            
            return token
            
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
            # Decode the token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.token_algorithm],
                options={"verify_signature": True}
            )
            
            # Check if token has been invalidated
            token_id = payload.get("jti")
            if token_id and token_id not in self._token_cache:
                logger.warning(f"Token {token_id} has been invalidated")
                return None
                
            # Convert to TokenPayload object for validation
            token_payload = TokenPayload.from_dict(payload)
            
            # Check if token is expired
            if token_payload.is_expired():
                logger.warning(f"Token for agent {token_payload.agent_id} has expired")
                return None
                
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
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
            # Verify the token
            payload = self.verify_token(token)
            if not payload:
                return False
                
            # Convert to TokenPayload for convenience
            token_payload = TokenPayload.from_dict(payload)
            
            # Check tool permission
            tool_permission = format_tool_permission(tool_id)
            has_permission = token_payload.has_permission(tool_permission)
            
            # Also check for wildcard permissions
            wildcard_admin = f"{PERMISSION_PREFIX['ADMIN']}:*:*"
            wildcard_tool = f"{PERMISSION_PREFIX['TOOL']}:*:*"
            
            return (has_permission or 
                    wildcard_admin in token_payload.permissions or
                    wildcard_tool in token_payload.permissions)
            
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
            # Verify the token without checking expiration
            try:
                payload = jwt.decode(
                    token,
                    self.secret_key,
                    algorithms=[self.token_algorithm],
                    options={"verify_signature": True, "verify_exp": False}
                )
            except jwt.InvalidTokenError as e:
                logger.warning(f"Invalid token for refresh: {str(e)}")
                raise AuthenticationError(f"Invalid token for refresh: {str(e)}")
                
            # Extract agent ID and permissions
            agent_id = payload.get("sub")
            if not agent_id:
                raise AuthenticationError("Token missing agent ID")
                
            # Remove old token from cache
            token_id = payload.get("jti")
            if token_id and token_id in self._token_cache:
                del self._token_cache[token_id]
                
            # Create a new token
            return self.get_token(agent_id)
            
        except AuthenticationError:
            # Re-raise authentication errors
            raise
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
            # Verify the token signature without checking expiration
            try:
                payload = jwt.decode(
                    token,
                    self.secret_key,
                    algorithms=[self.token_algorithm],
                    options={"verify_signature": True, "verify_exp": False}
                )
            except jwt.InvalidTokenError:
                # If the token is invalid, consider it already invalidated
                return True
                
            # Remove from cache
            token_id = payload.get("jti")
            if token_id and token_id in self._token_cache:
                del self._token_cache[token_id]
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error invalidating token: {str(e)}")
            raise AuthenticationError(f"Failed to invalidate token: {str(e)}")
    
    def _get_agent_permissions(self, agent_id: str) -> List[str]:
        """
        Get the permissions for an agent.
        
        Args:
            agent_id: The ID of the agent
            
        Returns:
            A list of permission strings
        """
        # Check if we have specific permissions for this agent
        if agent_id in self.permissions:
            return self.permissions[agent_id]
            
        # Otherwise, check the registry again (might have been updated)
        self._load_permissions_from_registry()
        
        # Try again
        if agent_id in self.permissions:
            return self.permissions[agent_id]
            
        # Return empty permissions if agent not found
        logger.warning(f"No permissions found for agent {agent_id}")
        return []
