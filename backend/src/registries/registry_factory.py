"""
Registry Factory

A centralized factory for accessing all registry instances.
This ensures consistent access to registries throughout the application.

This factory implements the singleton pattern to provide single instances
of each registry, improving performance and ensuring consistent state.
"""
import logging
from typing import Dict, Optional, Any, Type

from .base_registry import BaseRegistry
from .prompt_registry import PromptRegistry
from .tool_registry import ToolRegistry
from .agent_registry import AgentRegistry

logger = logging.getLogger(__name__)

class RegistryFactory:
    """
    Factory for accessing the various registries.
    
    This class provides singleton access to the prompt, tool, agent,
    and other registries, ensuring consistent access throughout the application.
    
    Usage:
        # Get a registry instance
        prompt_registry = RegistryFactory.get_registry(PromptRegistry)
        
        # Or use convenience methods
        tool_registry = RegistryFactory.get_tool_registry()
    """
    
    # Registry cache for singleton instances
    _registry_instances: Dict[Type[BaseRegistry], BaseRegistry] = {}
    
    @classmethod
    def get_registry(cls, registry_class: Type[BaseRegistry], **kwargs) -> BaseRegistry:
        """
        Get a registry instance by its class.
        
        Args:
            registry_class: The registry class to get an instance of
            **kwargs: Additional parameters to pass to the registry constructor
            
        Returns:
            An instance of the specified registry
        """
        if registry_class not in cls._registry_instances:
            logger.debug(f"Creating new instance of {registry_class.__name__}")
            cls._registry_instances[registry_class] = registry_class(**kwargs)
        return cls._registry_instances[registry_class]
    
    @classmethod
    def get_prompt_registry(cls) -> PromptRegistry:
        """
        Get the prompt registry instance.
        
        Returns:
            The prompt registry instance
        """
        return cls.get_registry(PromptRegistry)
    
    @classmethod
    def get_tool_registry(cls) -> ToolRegistry:
        """
        Get the tool registry instance.
        
        Returns:
            The tool registry instance
        """
        return cls.get_registry(ToolRegistry)
    
    @classmethod
    def get_agent_registry(cls) -> AgentRegistry:
        """
        Get the agent registry instance.
        
        Returns:
            The agent registry instance
        """
        return cls.get_registry(AgentRegistry)
    
    @classmethod
    def reload_all(cls) -> None:
        """
        Reload all registered registries.
        
        This is useful for refreshing after external changes to registry files.
        """
        for registry_class, registry_instance in cls._registry_instances.items():
            logger.info(f"Reloading {registry_class.__name__}")
            registry_instance.reload()
    
    @classmethod
    def reset(cls) -> None:
        """
        Reset the factory, clearing all cached registry instances.
        
        This is primarily useful for testing or when needing to reinitialize
        with different parameters.
        """
        cls._registry_instances.clear()
