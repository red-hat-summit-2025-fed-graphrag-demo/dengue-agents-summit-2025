#!/usr/bin/env python
"""
Verify agent configurations after standardization.
"""
import sys
import os

# Add current directory to path
sys.path.append('.')

from src.registries.agent_registry import AgentRegistry

def main():
    """Check all agent configurations."""
    print("Loading agent registry...")
    registry = AgentRegistry()
    
    print(f"Found {len(registry.agents)} agents in registry:")
    print(", ".join(registry.agents.keys()))
    print("\n" + "="*50 + "\n")
    
    for agent_id in registry.agents.keys():
        try:
            config = registry.get_agent_config(agent_id)
            print(f"Agent: {agent_id}")
            print(f"  Name: {config.get('name')}")
            print(f"  Description: {config.get('description')}")
            print(f"  Enabled: {config.get('enabled', config.get('active', False))}")
            print(f"  Version: {config.get('version', 'Not specified')}")
            
            # Check model config
            if "model_config" in config:
                mc = config["model_config"]
                print(f"  Model Config: {mc.get('model_type')} (max_tokens={mc.get('max_tokens')}, temp={mc.get('temperature')})")
            else:
                print("  Model Config: Not found")
                
            # Check prompts
            if "prompts" in config:
                print(f"  Prompts:")
                for prompt_type, prompt_info in config["prompts"].items():
                    print(f"    - {prompt_type}: {prompt_info.get('id')}")
            elif "prompt_id" in config:
                print(f"  Prompt ID: {config['prompt_id']}")
            else:
                print("  Prompts: Not found")
                
            print()
        except Exception as e:
            print(f"Error loading {agent_id}: {str(e)}")
    
    print("="*50)
    print("Configuration verification complete.")

if __name__ == "__main__":
    main()
