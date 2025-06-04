"""
Permission Utilities

Provides utilities for verifying permissions between agents and tools.
Ensures consistent permission checks throughout the system.
"""
import logging
from typing import Dict, List, Any, Optional, Union
import os

from src.registries.registry_factory import RegistryFactory

logger = logging.getLogger(__name__)

def has_permission(agent_id: str, tool_id: str) -> bool:
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
        
        # Get the tool configuration
        tool_config = tool_registry.get_tool_config(tool_id)
        
        # Check if the tool is active
        if not tool_config.get("active", False):
            logger.warning(f"Tool '{tool_id}' is not active")
            return False
        
        # Get the list of allowed agents
        allowed_agents = tool_config.get("allowed_agents", [])
        
        # Special case: "*" means all agents are allowed
        if "*" in allowed_agents:
            return True
        
        # Check if the agent is in the allowed list
        return agent_id in allowed_agents
        
    except ValueError as e:
        # Tool not found
        logger.error(f"Error checking permission: {str(e)}")
        return False
    except Exception as e:
        # Other errors
        logger.error(f"Unexpected error checking permission: {str(e)}")
        return False

def get_agent_allowed_tools(agent_id: str) -> List[str]:
    """
    Get a list of tool IDs that an agent is allowed to use.
    
    Args:
        agent_id: The ID of the agent
        
    Returns:
        List of tool IDs the agent can use
    """
    try:
        # Get registry instances
        tool_registry = RegistryFactory.get_tool_registry()
        
        # Get all active tools
        all_tools = tool_registry.list_tools(active_only=True)
        
        # Filter to tools this agent can use
        allowed_tools = []
        for tool in all_tools:
            tool_id = tool["id"]
            allowed_agents = tool.get("allowed_agents", [])
            
            # Check if the agent is allowed
            if "*" in allowed_agents or agent_id in allowed_agents:
                allowed_tools.append(tool_id)
        
        return allowed_tools
        
    except Exception as e:
        # Error handling
        logger.error(f"Error getting allowed tools for agent '{agent_id}': {str(e)}")
        return []

def is_agent_allowed(agent_id: str, allowed_agents: List[str]) -> bool:
    """
    Check if an agent is in a list of allowed agents.
    
    Args:
        agent_id: The ID of the agent
        allowed_agents: List of allowed agent IDs
        
    Returns:
        True if the agent is allowed, False otherwise
    """
    # Special case: "*" means all agents are allowed
    if "*" in allowed_agents:
        return True
    
    # Empty list means no agents are allowed
    if not allowed_agents:
        return False
    
    # Check if the agent is in the allowed list
    return agent_id in allowed_agents

def update_tool_permissions(tool_id: str, allowed_agents: List[str]) -> bool:
    """
    Update the permissions for a tool.
    
    Args:
        tool_id: The ID of the tool
        allowed_agents: New list of allowed agent IDs
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get registry instances
        tool_registry = RegistryFactory.get_tool_registry()
        
        # Get the tool configuration
        tool_config = tool_registry.get_tool_config(tool_id)
        
        # Update the allowed agents
        tool_config["allowed_agents"] = allowed_agents
        
        # Save the updated tool
        tool_registry.register_tool(tool_config)
        
        logger.info(f"Updated permissions for tool '{tool_id}'")
        return True
        
    except Exception as e:
        # Error handling
        logger.error(f"Error updating permissions for tool '{tool_id}': {str(e)}")
        return False

def get_permission_matrix() -> Dict[str, List[str]]:
    """
    Generate a permission matrix showing which agents can access which tools.
    
    Returns:
        Dictionary mapping agent IDs to lists of allowed tool IDs
    """
    try:
        # Get registry instances
        tool_registry = RegistryFactory.get_tool_registry()
        agent_registry = RegistryFactory.get_agent_registry()
        
        # Get all active agents
        agents = agent_registry.list_agents(active_only=True)
        
        # Initialize the matrix
        matrix = {}
        
        # For each agent, find all tools they can use
        for agent in agents:
            agent_id = agent["id"]
            allowed_tools = get_agent_allowed_tools(agent_id)
            matrix[agent_id] = allowed_tools
        
        return matrix
        
    except Exception as e:
        # Error handling
        logger.error(f"Error generating permission matrix: {str(e)}")
        return {}
