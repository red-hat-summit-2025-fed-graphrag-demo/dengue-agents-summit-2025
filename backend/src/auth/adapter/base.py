"""
Base Authentication Adapter

This module defines the abstract base class for all authentication adapters.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union


class AuthAdapter(ABC):
    """
    Abstract base class for authentication adapters.
    
    All concrete authentication implementations must inherit from this class
    and implement its abstract methods. This ensures a consistent interface
    regardless of the underlying authentication provider.
    """
    
    @abstractmethod
    def get_token(self, agent_id: str) -> str:
        """
        Get an authentication token for the specified agent.
        
        Args:
            agent_id: The ID of the agent requesting a token
            
        Returns:
            A valid authentication token as a string
            
        Raises:
            ValueError: If the agent is not authorized to obtain a token
            AuthenticationError: If there's an error during token creation
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass


class AuthenticationError(Exception):
    """Exception raised for authentication-related errors."""
    pass
