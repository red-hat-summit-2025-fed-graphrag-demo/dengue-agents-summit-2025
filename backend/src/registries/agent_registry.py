"""
Agent Registry

A registry for managing and accessing agent definitions.
Provides functionality to load agent configurations and instantiate agent objects.
"""
import os
import json
import yaml
import logging
import importlib
from typing import Dict, List, Optional, Any, Set, Union, Type

from src.registries.base_registry import BaseRegistry
from src.registries.registry_validator import AgentRegistryValidator

logger = logging.getLogger(__name__)

class AgentRegistry(BaseRegistry):
    """
    A registry for managing agent definitions and configurations.
    
    This registry loads agent definitions from a central registry file,
    manages instantiation of agents, and provides access to agent configurations.
    """
    
    def __init__(self, registry_path: Optional[str] = None, base_dir: Optional[str] = None):
        """
        Initialize the AgentRegistry.
        
        Args:
            registry_path: Optional path to the agent registry file. If not provided,
                          defaults to 'registry.json' in the 'agents' directory.
            base_dir: Optional base directory for agent resources.
        """
        super().__init__(registry_path, base_dir)
        # Cache for instantiated agents
        self._agent_instances: Dict[str, Any] = {}
    
    def _get_default_base_dir(self) -> str:
        """
        Get the default base directory for this registry type.
        
        Returns:
            Default base directory name
        """
        return "agents"
    
    def _get_default_registry_path(self) -> str:
        """
        Get the default registry file path for this registry type.
        
        Returns:
            Default registry file path
        """
        return os.path.join(self.base_dir, "registry.json")
    
    def _get_validator(self) -> AgentRegistryValidator:
        """
        Get the validator for agent registry entries.
        
        Returns:
            An AgentRegistryValidator instance
        """
        return AgentRegistryValidator()
    
    def _load_registry(self) -> None:
        """
        Load the agent registry from the JSON file.
        """
        # Use the helper method from BaseRegistry to load JSON
        self._load_json_registry(key_field="id", items_field="agents")
    
    def get_agent_config(self, agent_id: str) -> Dict[str, Any]:
        """
        Get the configuration for an agent by ID.
        
        Args:
            agent_id: The ID of the agent
            
        Returns:
            A dictionary containing the agent configuration
            
        Raises:
            ValueError: If the agent ID is not found
        """
        # Get the base item from registry
        agent_config = self.get_item(agent_id)
        
        # Load detailed configuration if available
        config_path = agent_config.get("config_path")
        if config_path:
            full_config_path = os.path.join(self.base_dir, config_path)
            if os.path.exists(full_config_path):
                try:
                    with open(full_config_path, 'r', encoding='utf-8') as f:
                        # Based on file extension, load as YAML or JSON
                        if full_config_path.endswith('.yaml') or full_config_path.endswith('.yml'):
                            detailed_config = yaml.safe_load(f)
                        else:
                            detailed_config = json.load(f)
                        
                        # Merge detailed config, but don't overwrite registry values
                        for key, value in detailed_config.items():
                            if key not in agent_config:
                                agent_config[key] = value
                                
                except Exception as e:
                    logger.error(f"Error loading config for agent '{agent_id}': {str(e)}")
        
        return agent_config
    
    def instantiate_agent(self, agent_id: str, registry_factory=None, **kwargs) -> Any:
        """
        Instantiate an agent object by ID.
        
        Args:
            agent_id: The ID of the agent to instantiate
            registry_factory: Optional registry factory to pass to the agent
            **kwargs: Additional parameters to pass to the agent constructor
            
        Returns:
            An instance of the requested agent
            
        Raises:
            ValueError: If the agent ID is not found or cannot be instantiated
        """
        # Check cache first
        cache_key = agent_id
        if cache_key in self._agent_instances:
            return self._agent_instances[cache_key]
        
        # Get agent configuration
        agent_config = self.get_agent_config(agent_id)
        
        # Get module and class information
        module_path = agent_config.get("module_path")
        class_name = agent_config.get("class_name")
        
        if not module_path or not class_name:
            raise ValueError(f"Agent '{agent_id}' missing module_path or class_name in registry")
        
        try:
            # Import module and get class
            module = importlib.import_module(module_path)
            agent_class = getattr(module, class_name)
            
            # Prepare constructor arguments
            agent_args = {
                "agent_id": agent_id,
                "config": agent_config,
            }
            
            # Add registry_factory if provided
            if registry_factory:
                agent_args["registry_factory"] = registry_factory
                
            # Add any additional kwargs
            agent_args.update(kwargs)
            
            # Instantiate the agent
            agent_instance = agent_class(**agent_args)
            
            # Cache the instance
            self._agent_instances[cache_key] = agent_instance
            
            return agent_instance
            
        except ImportError as e:
            raise ValueError(f"Could not import module '{module_path}' for agent '{agent_id}': {str(e)}")
        except AttributeError as e:
            raise ValueError(f"Class '{class_name}' not found in module '{module_path}': {str(e)}")
        except Exception as e:
            raise ValueError(f"Error instantiating agent '{agent_id}': {str(e)}")
    
    def list_agents(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """
        List all available agents, optionally filtered to active only.
        
        Args:
            active_only: If True, only return active agents
            
        Returns:
            A list of agent configuration dictionaries
        """
        # Define a filter function based on active status
        def filter_func(item):
            if active_only:
                return item.get("active", False)
            return True
            
        # Use the base list_items method with our filter
        items = self.list_items(filter_func)
        
        # Convert to full agent configs
        return [self.get_agent_config(item["id"]) for item in items]
    
    def get_agent_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """
        Find agents with a specific capability.
        
        Args:
            capability: The capability to search for
            
        Returns:
            A list of matching agent configuration dictionaries
        """
        # First get active agents
        active_agents = self.list_agents(active_only=True)
        
        # Filter by capability
        results = []
        for agent_config in active_agents:
            capabilities = agent_config.get("capabilities", [])
            if capability in capabilities:
                results.append(agent_config)
                
        return results
    
    def register_agent(self, agent_config: Dict[str, Any]) -> None:
        """
        Register a new agent in the registry.
        
        Args:
            agent_config: A dictionary containing the agent configuration
            
        Raises:
            ValueError: If the agent configuration is invalid
        """
        # Check required fields
        required_fields = ["id", "name", "description", "module_path", "class_name"]
        for field in required_fields:
            if field not in agent_config:
                raise ValueError(f"Agent configuration missing required field: {field}")
        
        # Use the base register_item method
        agent_id = self.register_item(agent_config, id_field="id")
        logger.info(f"Registered agent '{agent_id}' in registry")
    
    def _save_registry(self) -> None:
        """
        Save the current state of the registry to the JSON file.
        Overrides the base implementation to use the agents field.
        """
        registry_data = {
            "agents": list(self._registry_items.values())
        }
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
            
            # Write the registry file
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                json.dump(registry_data, f, indent=2)
                
            logger.info(f"Saved agent registry with {len(self._registry_items)} agents")
            
        except Exception as e:
            logger.error(f"Error saving agent registry to {self.registry_path}: {str(e)}")
    
    def set_agent_active(self, agent_id: str, active: bool = True) -> None:
        """
        Set an agent's active status.
        
        Args:
            agent_id: The ID of the agent
            active: Whether the agent should be active
            
        Raises:
            ValueError: If the agent ID is not found
        """
        # Get the agent config 
        agent_config = self.get_item(agent_id)
        
        # Update active status
        agent_config["active"] = active
        
        # Update the registry
        self._registry_items[agent_id] = agent_config
        
        # Save the updated registry
        self._save_registry()
        
        logger.info(f"Set agent '{agent_id}' active status to {active}")
    
    def reload(self) -> None:
        """
        Reload the agent registry from disk.
        Useful for refreshing after external changes to the registry file.
        """
        # Call the base class reload method
        super().reload()
        # Also clear our agent instances cache
        self._agent_instances = {}