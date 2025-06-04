"""
Tool Registry

A registry for managing and accessing tools that can be used by agents.
Provides functionality to load tool definitions, instantiate tools, and control access.

This registry implements the BaseRegistry abstract class to ensure
a consistent interface with other registries in the system.
"""
import os
import json
import yaml
import logging
import importlib
from typing import Dict, List, Optional, Any, Set, Union, Type

from src.registries.base_registry import BaseRegistry
from src.registries.registry_validator import ToolRegistryValidator

logger = logging.getLogger(__name__)

# Permission constants
ALL_AGENTS = "*"
NO_AGENTS = []

# Default registry path if not specified
DEFAULT_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "tools", "registry.json")

class ToolRegistry(BaseRegistry):
    """
    A registry for managing tools and their configurations.
    
    This registry loads tool definitions from a central registry file,
    manages instantiation of tools, and controls which agents have access
    to which tools. Inherits from BaseRegistry to ensure a consistent interface.
    """
    
    def __init__(self, registry_path: str = DEFAULT_REGISTRY_PATH):
        """
        Initialize a tool registry.
        
        Args:
            registry_path: Path to the tool registry JSON file
        """
        # Initialize the BaseRegistry
        super().__init__(registry_path=registry_path)
        
        # Add tool-specific instance cache
        self._tool_instances = {}  # Cache of instantiated tools
        
        # Load the registry using BaseRegistry methods
        self.load()
        
        # Legacy references for backward compatibility
        self.tools = self._registry_items
    
    def _get_default_base_dir(self) -> str:
        """Get the default base directory for tool files."""
        return "tools"
    
    def _get_default_registry_path(self) -> str:
        """Get the default registry file path."""
        return DEFAULT_REGISTRY_PATH
        
    def _get_validator(self) -> ToolRegistryValidator:
        """Get the validator for tool registry entries."""
        return ToolRegistryValidator()
    
    def _load_registry(self) -> None:
        """Load the tool registry from the JSON file."""
        # Use BaseRegistry's JSON loading method
        self._load_json_registry(key_field="id", items_field="tools")
        
        # Additional validation specific to tools
        for tool_id, tool_data in list(self._registry_items.items()):
            # Validate required fields
            if not tool_data.get("module_path") or not tool_data.get("class_name"):
                logger.warning(f"Tool '{tool_id}' is missing required module_path or class_name - skipping")
                self._registry_items.pop(tool_id, None)
                continue
                
            # Ensure allowed_agents is a list
            if "allowed_agents" not in tool_data:
                tool_data["allowed_agents"] = []
            elif not isinstance(tool_data["allowed_agents"], list):
                tool_data["allowed_agents"] = [tool_data["allowed_agents"]]
    
    def get_tool_config(self, tool_id: str) -> Dict[str, Any]:
        """
        Get the configuration for a tool by ID.
        
        Args:
            tool_id: The ID of the tool
            
        Returns:
            A dictionary containing the tool configuration
            
        Raises:
            ValueError: If the tool ID is not found
        """
        try:
            # Use BaseRegistry's get_item method
            tool_config = self.get_item(tool_id)
        except ValueError:
            raise ValueError(f"Tool '{tool_id}' not found in registry")
        
        # Load additional metadata if available
        metadata_path = tool_config.get("metadata_path")
        if metadata_path:
            full_metadata_path = os.path.join(self.base_dir, metadata_path)
            if os.path.exists(full_metadata_path):
                try:
                    with open(full_metadata_path, 'r', encoding='utf-8') as f:
                        metadata = yaml.safe_load(f)
                        # Merge metadata into tool config
                        tool_config.update(metadata)
                except Exception as e:
                    logger.error(f"Error loading metadata for tool '{tool_id}': {str(e)}")
        
        return tool_config
    
    def instantiate_tool(self, tool_id: str, **kwargs) -> Any:
        """
        Instantiate a tool object by ID.
        
        Args:
            tool_id: The ID of the tool to instantiate
            **kwargs: Additional parameters to pass to the tool constructor
            
        Returns:
            An instance of the requested tool
            
        Raises:
            ValueError: If the tool ID is not found or cannot be instantiated
        """
        # Check cache first
        cache_key = tool_id
        if cache_key in self._tool_instances:
            return self._tool_instances[cache_key]
        
        # Get tool configuration
        tool_config = self.get_tool_config(tool_id)
        
        # Get module and class information
        module_path = tool_config.get("module_path")
        class_name = tool_config.get("class_name")
        
        if not module_path or not class_name:
            raise ValueError(f"Tool '{tool_id}' missing module_path or class_name in registry")
        
        try:
            # Import module and get class
            module = importlib.import_module(module_path)
            tool_class = getattr(module, class_name)
            
            # Instantiate the tool with any provided kwargs
            tool_instance = tool_class(**kwargs)
            
            # Cache the instance
            self._tool_instances[cache_key] = tool_instance
            
            return tool_instance
            
        except ImportError as e:
            raise ValueError(f"Could not import module '{module_path}' for tool '{tool_id}': {str(e)}")
        except AttributeError as e:
            raise ValueError(f"Class '{class_name}' not found in module '{module_path}': {str(e)}")
        except Exception as e:
            raise ValueError(f"Error instantiating tool '{tool_id}': {str(e)}")
    
    def agent_can_use_tool(self, agent_id: str, tool_id: str) -> bool:
        """
        Check if an agent has permission to use a specific tool.
        
        Args:
            agent_id: The ID of the agent
            tool_id: The ID of the tool
            
        Returns:
            True if the agent can use the tool, False otherwise
        """
        try:
            # Get the tool configuration
            tool_config = self.get_tool_config(tool_id)
            
            # Check if the tool is active
            if not tool_config.get("active", False):
                logger.warning(f"Tool '{tool_id}' is not active")
                return False
            
            # Get the list of allowed agents
            allowed_agents = tool_config.get("allowed_agents", [])
            
            # Special case: "*" means all agents are allowed
            if ALL_AGENTS in allowed_agents:
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
    
    # Alias for backward compatibility
    check_agent_access = agent_can_use_tool
    
    def get_allowed_tools_for_agent(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get a list of tool configurations that an agent is allowed to use.
        
        Args:
            agent_id: The ID of the agent
            
        Returns:
            List of tool configurations the agent can use
        """
        # Get all active tools
        all_tools = self.list_tools(active_only=True)
        
        # Filter to tools this agent can use
        allowed_tools = []
        for tool in all_tools:
            tool_id = tool["id"]
            allowed_agents = tool.get("allowed_agents", [])
            
            # Check if the agent is allowed
            if ALL_AGENTS in allowed_agents or agent_id in allowed_agents:
                allowed_tools.append(tool)
        
        return allowed_tools
    
    def grant_agent_access(self, agent_id: str, tool_id: str) -> None:
        """
        Grant an agent access to use a specific tool.
        
        Args:
            agent_id: The ID of the agent
            tool_id: The ID of the tool
            
        Raises:
            ValueError: If the tool ID is not found
        """
        if tool_id not in self.tools:
            raise ValueError(f"Tool '{tool_id}' not found in registry")
        
        # Update the tool configuration
        if "allowed_agents" not in self.tools[tool_id]:
            self.tools[tool_id]["allowed_agents"] = []
            
        if agent_id not in self.tools[tool_id]["allowed_agents"]:
            self.tools[tool_id]["allowed_agents"].append(agent_id)
            
        # Save the updated registry
        self._save_registry()
    
    def update_tool_permissions(self, tool_id: str, allowed_agents: List[str]) -> bool:
        """
        Update the permissions for a tool.
        
        Args:
            tool_id: The ID of the tool
            allowed_agents: New list of allowed agent IDs
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the tool configuration
            if tool_id not in self.tools:
                raise ValueError(f"Tool '{tool_id}' not found in registry")
                
            # Update the allowed agents
            self.tools[tool_id]["allowed_agents"] = allowed_agents
            
            # Save the updated registry
            self._save_registry()
            
            logger.info(f"Updated permissions for tool '{tool_id}'")
            return True
            
        except Exception as e:
            # Error handling
            logger.error(f"Error updating permissions for tool '{tool_id}': {str(e)}")
            return False
    
    def revoke_agent_access(self, agent_id: str, tool_id: str) -> None:
        """
        Revoke an agent's access to use a specific tool.
        
        Args:
            agent_id: The ID of the agent
            tool_id: The ID of the tool
            
        Raises:
            ValueError: If the tool ID is not found
        """
        if tool_id not in self.tools:
            raise ValueError(f"Tool '{tool_id}' not found in registry")
        
        # Update the tool configuration
        if "allowed_agents" in self.tools[tool_id] and agent_id in self.tools[tool_id]["allowed_agents"]:
            self.tools[tool_id]["allowed_agents"].remove(agent_id)
            
        # Save the updated registry
        self._save_registry()
    
    def list_tools(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all available tools, optionally filtered by agent access.
        
        Args:
            agent_id: Optional agent ID to filter tools by access
            
        Returns:
            A list of tool configuration dictionaries
        """
        if agent_id:
            # Create a filter function that checks agent access
            def has_access(tool_config: Dict[str, Any]) -> bool:
                return self.check_agent_access(agent_id, tool_config.get("id", ""))
            
            # Use BaseRegistry's list_items with our access filter
            return self.list_items(filter_func=has_access)
        else:
            # No filtering, return all items
            return self.list_items()
    
    def register_tool(self, tool_config: Dict[str, Any]) -> str:
        """
        Register a new tool in the registry.
        
        Args:
            tool_config: The tool configuration dictionary
            
        Returns:
            The ID of the registered tool
            
        Raises:
            ValueError: If tool_config is missing required fields
        """
        # Validate required fields
        if "id" not in tool_config:
            raise ValueError("Tool configuration missing required 'id' field")
            
        if "module_path" not in tool_config or "class_name" not in tool_config:
            raise ValueError("Tool configuration missing required 'module_path' or 'class_name' fields")
        
        # Ensure allowed_agents is a list
        if "allowed_agents" not in tool_config:
            tool_config["allowed_agents"] = []
        elif not isinstance(tool_config["allowed_agents"], list):
            tool_config["allowed_agents"] = [tool_config["allowed_agents"]]
        
        # Use BaseRegistry register_item method
        tool_id = tool_config["id"]
        tool_id = self.register_item(tool_config.copy())
        
        # If we already have an instance, remove it so it gets recreated when needed
        if tool_id in self._tool_instances:
            del self._tool_instances[tool_id]
    
        try:
            # Import module and get class
            module = importlib.import_module(module_path)
            tool_class = getattr(module, class_name)
            
            # Instantiate the tool with any provided kwargs
            tool_instance = tool_class(**kwargs)
            
            # Cache the instance
            self._tool_instances[cache_key] = tool_instance
            
            return tool_instance
            
        except ImportError as e:
            raise ValueError(f"Could not import module '{module_path}' for tool '{tool_id}': {str(e)}")
        except AttributeError as e:
            raise ValueError(f"Class '{class_name}' not found in module '{module_path}': {str(e)}")
        except Exception as e:
            raise ValueError(f"Error instantiating tool '{tool_id}': {str(e)}")
    
    def check_agent_access(self, agent_id: str, tool_id: str) -> bool:
        """
        Check if an agent has access to use a specific tool.
        
        Args:
            agent_id: The ID of the agent
            tool_id: The ID of the tool
            
        Returns:
            True if the agent has access, False otherwise
        """
        if tool_id not in self.tools:
            return False
        
        tool_config = self.tools[tool_id]
        allowed_agents = tool_config.get("allowed_agents", [])
        
        # If allowed_agents is empty, no agents have access yet
        if not allowed_agents:
            return False
        
        # Special case: ["*"] means all agents have access
        if "*" in allowed_agents:
            return True
                
        return agent_id in allowed_agents

    def grant_agent_access(self, agent_id: str, tool_id: str) -> None:
        """
        Grant an agent access to use a specific tool.
        
        Args:
            agent_id: The ID of the agent
            tool_id: The ID of the tool
            
        Raises:
            ValueError: If the tool ID is not found
        """
        if tool_id not in self.tools:
            raise ValueError(f"Tool '{tool_id}' not found in registry")
        
        # Update the tool configuration
        if "allowed_agents" not in self.tools[tool_id]:
            self.tools[tool_id]["allowed_agents"] = []
            
        if agent_id not in self.tools[tool_id]["allowed_agents"]:
            self.tools[tool_id]["allowed_agents"].append(agent_id)
            
        # Save the updated registry
        self._save_registry()
        logger.info(f"Granted access to tool '{tool_id}' for agent '{agent_id}'")

    def revoke_agent_access(self, agent_id: str, tool_id: str) -> None:
        """
        Revoke an agent's access to use a specific tool.
        
        Args:
            agent_id: The ID of the agent
            tool_id: The ID of the tool
            
        Raises:
            ValueError: If the tool ID is not found
        """
        if tool_id not in self.tools:
            raise ValueError(f"Tool '{tool_id}' not found in registry")
        
        # Update the tool configuration
        if "allowed_agents" in self.tools[tool_id] and agent_id in self.tools[tool_id]["allowed_agents"]:
            self.tools[tool_id]["allowed_agents"].remove(agent_id)
            
        # Save the updated registry
        self._save_registry()
        logger.info(f"Revoked access to tool '{tool_id}' for agent '{agent_id}'")

    def list_tools(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all available tools, optionally filtered by agent access.
        
        Args:
            agent_id: Optional agent ID to filter tools by access
            
        Returns:
            A list of tool configuration dictionaries
        """
        if agent_id:
            # Create a filter function that checks agent access
            def has_access(tool_config: Dict[str, Any]) -> bool:
                return self.check_agent_access(agent_id, tool_config.get("id", ""))
            
            # Use BaseRegistry's list_items with our access filter
            return self.list_items(filter_func=has_access)
        else:
            # No filtering, return all items
            return self.list_items()

    def register_tool(self, tool_config: Dict[str, Any]) -> str:
        """
        Register a new tool in the registry.
        
        Args:
            tool_config: The tool configuration dictionary
            
        Returns:
            The ID of the registered tool
            
        Raises:
            ValueError: If tool_config is missing required fields
        """
        # Validate required fields
        if "id" not in tool_config:
            raise ValueError("Tool configuration missing required 'id' field")
            
        if "module_path" not in tool_config or "class_name" not in tool_config:
            raise ValueError("Tool configuration missing required 'module_path' or 'class_name' fields")
        
        # Ensure allowed_agents is a list
        if "allowed_agents" not in tool_config:
            tool_config["allowed_agents"] = []
        elif not isinstance(tool_config["allowed_agents"], list):
            tool_config["allowed_agents"] = [tool_config["allowed_agents"]]
        
        # Use BaseRegistry register_item method
        tool_id = tool_config["id"]
        tool_id = self.register_item(tool_config.copy())
        
        # If we already have an instance, remove it so it gets recreated when needed
        if tool_id in self._tool_instances:
            del self._tool_instances[tool_id]
        
        logger.info(f"Registered tool '{tool_id}' in registry")
        return tool_id
        
    def load(self) -> None:
        """
        Load the tool registry from disk.
        """
        # If file doesn't exist, initialize an empty registry
        if not os.path.exists(self.registry_path):
            logger.info(f"Tool registry file not found at {self.registry_path}, creating new one")
            self._initialize_empty_registry()
            return
            
        try:
            # Use BaseRegistry's _load_json_registry method to load the registry
            self._load_json_registry(key_field="id", items_field="tools")
            # Update legacy reference for backward compatibility
            self.tools = self._registry_items
            logger.info(f"Loaded tool registry with {len(self.tools)} tools from {self.registry_path}")
        except Exception as e:
            logger.error(f"Error loading tool registry from {self.registry_path}: {str(e)}")
            # Initialize empty registry on error
            self._initialize_empty_registry()

    def _initialize_empty_registry(self) -> None:
        """
        Initialize an empty registry and save it to disk.
        """
        self._registry_items = {}
        self.tools = self._registry_items
        self._save_registry()

    def reload(self) -> None:
        """
        Reload the tool registry from disk.
        """
        # Clear instances first
        self._tool_instances = {}
        
        # Use BaseRegistry's reload method
        super().reload()
        
        # Update legacy reference for backward compatibility
        self.tools = self._registry_items

    def unregister_tool(self, tool_id: str) -> None:
        """
        Remove a tool from the registry.
        
        Args:
            tool_id: The ID of the tool to remove
            
        Raises:
            ValueError: If the tool ID doesn't exist
        """
        # Check if tool exists using BaseRegistry methods
        if not self.has_item(tool_id):
            raise ValueError(f"Tool ID '{tool_id}' does not exist in registry")
            
        # Remove any cached instance
        if tool_id in self._tool_instances:
            del self._tool_instances[tool_id]
            
        # Use BaseRegistry to unregister the item
        self.unregister_item(tool_id)
        
        logger.info(f"Unregistered tool '{tool_id}' from registry")