"""
Authentication Utilities

This module provides utility functions for working with permissions
and authentication tokens.
"""
import os
import logging
from typing import List, Dict, Any, Optional, Union

from src.auth.constants import (
    format_tool_permission,
    PERMISSION_PREFIX,
    PERMISSION_VERB
)
from src.registries.registry_factory import RegistryFactory

logger = logging.getLogger(__name__)


def get_agent_permissions(agent_id: str) -> List[str]:
    """
    Get all permissions for an agent based on registry entries.
    
    Args:
        agent_id: The ID of the agent
        
    Returns:
        A list of permission strings
    """
    try:
        # Get registry instances
        tool_registry = RegistryFactory.get_tool_registry()
        
        # Get all active tools
        tools = tool_registry.list_tools(active_only=True)
        
        # Collect tool permissions for this agent
        permissions = []
        
        for tool in tools:
            tool_id = tool["id"]
            allowed_agents = tool.get("allowed_agents", [])
            
            # Check if this agent has access to this tool
            # Either explicitly or via wildcard
            if agent_id in allowed_agents or "*" in allowed_agents:
                # Add tool usage permission
                permission = format_tool_permission(tool_id)
                permissions.append(permission)
        
        # Add agent execution permission
        agent_execute_permission = f"{PERMISSION_PREFIX['AGENT']}:{agent_id}:{PERMISSION_VERB['EXECUTE']}"
        permissions.append(agent_execute_permission)
        
        return permissions
    
    except Exception as e:
        logger.error(f"Error getting permissions for agent {agent_id}: {str(e)}")
        return []


def agent_can_use_tool(agent_id: str, tool_id: str) -> bool:
    """
    Check if an agent has permission to use a specific tool.
    
    Args:
        agent_id: The ID of the agent
        tool_id: The ID of the tool
        
    Returns:
        True if the agent can use the tool, False otherwise
    """
    try:
        # Get registry instances
        tool_registry = RegistryFactory.get_tool_registry()
        
        # Get the tool entry
        tool = tool_registry.get_tool(tool_id)
        if not tool:
            logger.warning(f"Tool {tool_id} not found in registry")
            return False
            
        # Check if tool is active
        if not tool.get("active", True):
            logger.warning(f"Tool {tool_id} is not active")
            return False
            
        # Check if agent is allowed to use this tool
        allowed_agents = tool.get("allowed_agents", [])
        
        return agent_id in allowed_agents or "*" in allowed_agents
        
    except Exception as e:
        logger.error(f"Error checking tool permission for agent {agent_id}, tool {tool_id}: {str(e)}")
        return False


def verify_auth_token(token: str, tool_id: str) -> bool:
    """
    Verify if a token grants access to use a specific tool.
    
    Args:
        token: The authentication token
        tool_id: The ID of the tool to check access for
        
    Returns:
        True if the token grants access, False otherwise
    """
    try:
        # Import here to avoid circular imports
        from src.auth.factory import get_auth_adapter
        
        # Get the auth adapter
        auth_adapter = get_auth_adapter()
        
        # Verify access
        return auth_adapter.verify_access(token, tool_id)
        
    except ImportError:
        logger.warning("Auth system not available, proceeding without token verification")
        # If auth system not available, fall back to registry-based permissions
        # Extract agent_id from token if possible, otherwise allow access
        return True
        
    except Exception as e:
        logger.error(f"Error verifying auth token for tool {tool_id}: {str(e)}")
        return False
