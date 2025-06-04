"""
Authentication Example Tool

This tool demonstrates how to implement authentication verification
in a tool that requires authorization.
"""
import logging
from typing import Dict, Any, Optional

# Import auth utilities for token verification
from src.auth.utils import verify_auth_token

logger = logging.getLogger(__name__)


class AuthExampleTool:
    """
    Example tool demonstrating authentication integration.
    
    This tool implements proper authentication checks and
    provides a template for other tools to follow.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the auth example tool.
        
        Args:
            config: Tool configuration (optional)
        """
        self.config = config or {}
        logger.info("Initialized AuthExampleTool with authentication support")
        
    def execute(self, message: str, auth_token: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool functionality with authentication checks.
        
        Args:
            message: The message to process
            auth_token: Authentication token (optional)
            **kwargs: Additional parameters
            
        Returns:
            A response dictionary with authentication status
            
        Raises:
            PermissionError: If authentication fails
        """
        # Check authentication if token is provided
        authenticated = False
        
        if auth_token:
            # Verify the token grants access to this tool
            authenticated = verify_auth_token(auth_token, "auth_example_tool")
            
            if not authenticated:
                logger.warning("Authentication failed for AuthExampleTool")
                raise PermissionError("Invalid authentication token for auth_example_tool")
            
            logger.info("Authentication successful for AuthExampleTool")
        else:
            logger.info("No authentication token provided, proceeding with limited functionality")
        
        # Process the request
        # For a real tool, this would implement actual functionality
        response = {
            "message": f"Processed message: {message}",
            "authenticated": authenticated,
            "auth_status": "authenticated" if authenticated else "anonymous"
        }
        
        return response
    
    def __call__(self, **kwargs) -> Dict[str, Any]:
        """
        Make the tool callable directly.
        
        Args:
            **kwargs: Parameters to pass to execute
            
        Returns:
            Result from execute method
        """
        return self.execute(**kwargs)
