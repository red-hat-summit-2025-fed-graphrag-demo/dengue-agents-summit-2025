"""
Configuration class for the agent system.
"""
from typing import Dict, Any, Optional, List


class AgentSystemConfig:
    """
    Configuration for the agent system.
    
    This class holds system-wide configuration settings for the agent system.
    """
    def __init__(
        self,
        config_dir: Optional[str] = None,
        enable_safety_agents: bool = True,
        enable_streaming: bool = True,
        agent_transitions: Optional[Dict[str, float]] = None,
        custom_settings: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the agent system configuration.
        
        Args:
            config_dir: Optional directory for configuration files
            enable_safety_agents: Whether to enable safety agents
            enable_streaming: Whether to enable streaming responses
            agent_transitions: Optional delay times between agent transitions
            custom_settings: Additional custom settings
        """
        self.config_dir = config_dir
        self.enable_safety_agents = enable_safety_agents
        self.enable_streaming = enable_streaming
        self.agent_transitions = agent_transitions or {}
        self.custom_settings = custom_settings or {}

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a custom setting value.
        
        Args:
            key: The setting key
            default: Default value if setting is not found
            
        Returns:
            The setting value or default
        """
        return self.custom_settings.get(key, default)
        
    def set_setting(self, key: str, value: Any) -> None:
        """
        Set a custom setting value.
        
        Args:
            key: The setting key
            value: The setting value
        """
        self.custom_settings[key] = value
        
    def add_agent_transition_delay(self, from_agent: str, to_agent: str, delay_seconds: float) -> None:
        """
        Add a delay between agent transitions.
        
        Args:
            from_agent: The source agent ID
            to_agent: The destination agent ID
            delay_seconds: Delay in seconds
        """
        transition_key = f"{from_agent}:{to_agent}"
        self.agent_transitions[transition_key] = delay_seconds
        
    def get_agent_transition_delay(self, from_agent: str, to_agent: str) -> float:
        """
        Get the delay for a specific agent transition.
        
        Args:
            from_agent: The source agent ID
            to_agent: The destination agent ID
            
        Returns:
            Delay in seconds
        """
        transition_key = f"{from_agent}:{to_agent}"
        return self.agent_transitions.get(transition_key, 0.0)
