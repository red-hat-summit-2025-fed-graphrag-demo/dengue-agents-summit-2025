"""
Auth Hello Tool

A simple tool that requires authentication and returns a greeting.
Used for testing the authentication system.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AuthHelloTool:
    """
    A tool that requires authentication to use.
    
    This tool validates the authentication token before returning a greeting message.
    It's used for testing the authentication system.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the auth hello tool.
        
        Args:
            config: Tool configuration (optional)
        """
        self.config = config or {}
        logger.info("Initialized AuthHelloTool")
        
    def execute(self, name: str = "World", auth_token: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Execute the auth hello functionality.
        
        Args:
            name: Name to include in the greeting (default: "World")
            auth_token: Authentication token (required)
            **kwargs: Additional parameters
            
        Returns:
            A response dictionary with greeting and authentication status
            
        Raises:
            ValueError: If no authentication token is provided
        """
        # Check for authentication token
        if not auth_token:
            logger.warning("Authentication token missing for AuthHelloTool")
            raise ValueError("Authentication token is required for this tool")
            
        logger.info(f"AuthHelloTool executed with auth token and name: {name}")
        
        # Return a simple greeting with authentication info
        return {
            "greeting": f"Hello, {name}! (Authenticated)",
            "authenticated": True,
            "message": "This message came from a tool that requires authentication"
        }
    
    def __call__(self, **kwargs) -> Dict[str, Any]:
        """
        Make the tool callable directly.
        
        Args:
            **kwargs: Parameters to pass to execute
            
        Returns:
            Result from execute method
        """
        return self.execute(**kwargs)
