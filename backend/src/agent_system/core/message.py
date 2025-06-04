"""
Message models for the agent system.
"""
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

from src.agent_system.core.metadata import BaseMetadata, MetadataKeys


class MessageRole(str, Enum):
    """Message roles in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class ToolCall(BaseModel):
    """Tool call in a conversation."""
    id: str
    type: str = "function"
    function: Dict[str, Any]


class Message(BaseModel):
    """Message in a conversation."""
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def get_metadata(self, key: Union[str, MetadataKeys], default: Any = None) -> Any:
        """
        Get a metadata value using standardized keys.
        
        This method will look for the key in the standard format first,
        and if not found, attempt to find legacy versions of the key.
        
        Args:
            key: The key to lookup, either as string or MetadataKeys enum
            default: Default value to return if key not found
            
        Returns:
            The value if found, or the default
        """
        return BaseMetadata.get(self.metadata, key, default)
    
    def update_metadata(self, **kwargs) -> None:
        """
        Update message metadata using standardized keys.
        
        Args:
            **kwargs: Key-value pairs to update in metadata
        """
        self.metadata = BaseMetadata.update(self.metadata, **kwargs)
        
        # Always add timestamp on update
        if MetadataKeys.TIMESTAMP.value not in self.metadata:
            self.metadata[MetadataKeys.TIMESTAMP.value] = datetime.now().isoformat()


class UserMessage(BaseModel):
    """User message model."""
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
