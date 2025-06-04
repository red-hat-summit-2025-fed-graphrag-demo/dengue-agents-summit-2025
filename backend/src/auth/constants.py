"""
Authentication Constants

This module defines constants used throughout the authentication system.
"""
from enum import Enum, auto


class AuthProvider(Enum):
    """Enum for supported authentication providers."""
    LOCAL_JWT = auto()    # Simple JWT-based auth for development
    KEYCLOAK = auto()     # Keycloak-based auth for production


class TokenType(Enum):
    """Enum for token types."""
    BEARER = "bearer"       # Standard Bearer token
    ACCESS = "access"       # Access token
    REFRESH = "refresh"     # Refresh token


# Default authentication configuration
DEFAULT_AUTH_CONFIG = {
    "provider": AuthProvider.LOCAL_JWT,
    "secret_key": "dengue-agents-development-secret",
    "token_expiry_seconds": 3600,  # 1 hour
    "token_refresh_seconds": 86400,  # 24 hours
    "issuer": "dengue-agents-auth"
}

# Keycloak-specific configuration
KEYCLOAK_CONFIG = {
    "server_url": "http://localhost:8080/",
    "realm": "dengue-agents",
    "client_id": "agent-system",
    "client_secret": None,  # Set from environment for security
    "verify_ssl": True
}

# Permission prefixes
PERMISSION_PREFIX = {
    "TOOL": "tool",           # Tool-related permissions (e.g., tool:schema_tool:use)
    "AGENT": "agent",         # Agent-related permissions (e.g., agent:execute)
    "ADMIN": "admin"          # Administrative permissions (e.g., admin:manage)
}

# Permission verbs
PERMISSION_VERB = {
    "USE": "use",             # Permission to use a tool
    "READ": "read",           # Permission to read data
    "WRITE": "write",         # Permission to write data
    "EXECUTE": "execute",     # Permission to execute
    "MANAGE": "manage"        # Permission to manage
}


def format_tool_permission(tool_id: str, verb: str = PERMISSION_VERB["USE"]) -> str:
    """
    Format a permission string for a tool.
    
    Args:
        tool_id: The ID of the tool
        verb: The permission verb (default: "use")
        
    Returns:
        A formatted permission string (e.g., "tool:schema_tool:use")
    """
    return f"{PERMISSION_PREFIX['TOOL']}:{tool_id}:{verb}"
