"""
Simple Hello Tool

A simple tool that doesn't require authentication and returns a greeting.
Used for testing the authentication system.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SimpleHelloTool:
    """
    A tool that doesn't require authentication to use.
    
    This tool simply returns a greeting message without checking for authentication.
    It's used for testing the authentication system.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the simple hello tool.
        
        Args:
            config: Tool configuration (optional)
        """
        self.config = config or {}
        logger.info("Initialized SimpleHelloTool")
        
    def execute(self, name: str = "World", **kwargs) -> Dict[str, Any]:
        """
        Execute the simple hello functionality.
        
        Args:
            name: Name to include in the greeting (default: "World")
            **kwargs: Additional parameters
            
        Returns:
            A response dictionary with greeting
        """
        logger.info(f"SimpleHelloTool executed with name: {name}")
        
        # Return a simple greeting
        return {
            "greeting": f"Hello, {name}!",
            "authenticated": False,
            "message": "This message came from a tool that doesn't require authentication"
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
