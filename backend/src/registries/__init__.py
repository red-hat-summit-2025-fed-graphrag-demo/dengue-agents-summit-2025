"""
Registry System

A system for managing prompts, tools, and agents in a modular way.
Provides access to the various registries through a factory pattern.
"""
from .prompt_registry import PromptRegistry
from .tool_registry import ToolRegistry
from .agent_registry import AgentRegistry
from .base_registry import BaseRegistry
from .registry_factory import RegistryFactory

# Direct imports for backward compatibility
__all__ = [
    'PromptRegistry',
    'ToolRegistry',
    'AgentRegistry',
    'BaseRegistry',
    'RegistryFactory',
]

# For backward compatibility, keep the same instance access pattern
# but redirect to the new implementation
def get_prompt_registry() -> PromptRegistry:
    """Get the prompt registry."""
    return RegistryFactory.get_prompt_registry()

def get_tool_registry() -> ToolRegistry:
    """Get the tool registry."""
    return RegistryFactory.get_tool_registry()

def get_agent_registry() -> AgentRegistry:
    """Get the agent registry."""
    return RegistryFactory.get_agent_registry()

def reload_all_registries() -> None:
    """Reload all registries."""
    RegistryFactory.reload_all()