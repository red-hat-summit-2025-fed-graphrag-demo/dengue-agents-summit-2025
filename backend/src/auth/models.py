"""
Authentication Models

This module defines data models for authentication tokens and related structures.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class TokenPayload:
    """
    Data model representing the payload of an authentication token.
    
    This class defines the standard structure for authentication token payloads
    across different authentication providers.
    """
    # Required fields
    agent_id: str
    permissions: List[str]
    issued_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    # Optional fields
    token_id: Optional[str] = None
    issuer: str = "dengue-agents-auth"
    token_type: str = "bearer"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if the token is expired."""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at
    
    def has_permission(self, permission: str) -> bool:
        """Check if the token has a specific permission."""
        return permission in self.permissions
    
    def has_tool_permission(self, tool_id: str) -> bool:
        """Check if the token has permission to use a specific tool."""
        tool_permission = f"tool:{tool_id}:use"
        return self.has_permission(tool_permission)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the token payload to a dictionary for encoding."""
        result = {
            "sub": self.agent_id,
            "permissions": self.permissions,
            "iat": int(self.issued_at.timestamp()),
            "iss": self.issuer,
            "typ": self.token_type,
        }
        
        if self.token_id:
            result["jti"] = self.token_id
            
        if self.expires_at:
            result["exp"] = int(self.expires_at.timestamp())
            
        if self.metadata:
            result["metadata"] = self.metadata
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TokenPayload':
        """Create a TokenPayload from a dictionary (decoded token)."""
        agent_id = data.get("sub")
        permissions = data.get("permissions", [])
        
        # Convert timestamps to datetime objects
        issued_at = datetime.fromtimestamp(data.get("iat", 0))
        expires_at = None
        if "exp" in data:
            expires_at = datetime.fromtimestamp(data.get("exp"))
            
        token_id = data.get("jti")
        issuer = data.get("iss", "dengue-agents-auth")
        token_type = data.get("typ", "bearer")
        metadata = data.get("metadata", {})
        
        return cls(
            agent_id=agent_id,
            permissions=permissions,
            issued_at=issued_at,
            expires_at=expires_at,
            token_id=token_id,
            issuer=issuer,
            token_type=token_type,
            metadata=metadata
        )
