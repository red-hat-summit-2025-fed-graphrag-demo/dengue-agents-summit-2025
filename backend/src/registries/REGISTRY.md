# Registry System Documentation

## Overview

The Dengue Agents platform uses a standardized registry system to manage and access various components:

- **Tool Registry**: Manages tools that perform specific operations
- **Agent Registry**: Manages agents that execute tasks using tools
- **Prompt Registry**: Manages prompts used by agents
- **Workflow Registry**: Manages workflows that coordinate agent execution

All registry entries follow a standardized format defined in [REGISTRY_STANDARD.md](./REGISTRY_STANDARD.md), which ensures consistent access patterns and validation.

## Registry Architecture

### BaseRegistry

The `BaseRegistry` class defines a common interface for all registry types. It provides:

- Standard methods for loading, accessing, and managing registered resources
- Validation of registry entries against a standard schema
- Backward compatibility for non-compliant entries
- Consistent error handling and logging

### Registry Implementations

Each registry type extends `BaseRegistry` and implements specific functionality:

1. **ToolRegistry**: 
   - Manages tool configurations in a central JSON file
   - Controls access to tools based on agent permissions
   - Allows dynamic loading and instantiation of tool implementations

2. **AgentRegistry**:
   - Manages agent configurations in a central JSON file
   - Links agents to their prompt templates and model configurations
   - Supports instantiation of agent objects with appropriate dependencies

3. **PromptRegistry**:
   - Manages prompt templates as individual YAML files
   - Supports variable substitution in prompts
   - Provides metadata about prompts for agent configuration

4. **WorkflowRegistry**:
   - Manages workflow definitions that coordinate agent execution
   - Supports dependency validation between workflow steps
   - Provides workflow instantiation and execution

### RegistryFactory

The `RegistryFactory` provides centralized access to all registry instances, ensuring:

- Singleton instances for each registry type
- Consistent access patterns across the system
- Proper initialization of interdependent registries

## Validation System

The validation system ensures that all registry entries comply with the standardized format:

- **ValidationSeverity**: Defines severity levels (ERROR, WARNING, INFO)
- **ValidationResult**: Collects and reports validation issues
- **RegistryValidator**: Base class for all validators with common validation logic
- **Specialized Validators**: Implement type-specific validation for each registry type

## Permission System

The permission system controls which agents can access which tools:

- Each tool defines an `allowed_agents` field
- Special value `"*"` indicates all agents can access the tool
- Empty list indicates no agent can access the tool
- The `has_permission()` utility checks if an agent can access a tool

## Usage Examples

### Accessing a Registry

```python
from src.registries.registry_factory import RegistryFactory

# Get registry instances
tool_registry = RegistryFactory.get_tool_registry()
agent_registry = RegistryFactory.get_agent_registry()
prompt_registry = RegistryFactory.get_prompt_registry()

# List available items
tools = tool_registry.list_tools()
agents = agent_registry.list_agents()
prompts = prompt_registry.list_prompts()

# Get specific items
tool_config = tool_registry.get_tool_config("example_tool")
agent_config = agent_registry.get_agent_config("example_agent")
prompt_text = prompt_registry.get_prompt("example.prompt", variable="value")
```

### Checking Permissions

```python
from src.registries.permission_utils import has_permission

# Check if an agent can access a tool
agent_id = "example_agent"
tool_id = "example_tool"
can_access = has_permission(agent_id, tool_id)

# Or using the registry directly
can_access = tool_registry.agent_can_use_tool(agent_id, tool_id)
```

### Registering New Items

```python
# Register a new tool
new_tool = {
    "id": "new_tool",
    "name": "New Tool",
    "description": "A new tool",
    "version": "1.0.0",
    "active": True,
    "module_path": "src.tools.new_tool",
    "class_name": "NewTool",
    "config_path": "configs/new_tool.yaml",
    "allowed_agents": ["agent1", "agent2"]
}
tool_registry.register_tool(new_tool)

# Register a new agent
new_agent = {
    "id": "new_agent",
    "name": "New Agent",
    "description": "A new agent",
    "version": "1.0.0",
    "active": True,
    "module_path": "src.agent_system.new_agent",
    "class_name": "NewAgent",
    "config_path": "configs/new_agent.yaml",
    "prompt_id": "new.prompt",
    "model_config": {
        "model_type": "instruct",
        "max_tokens": 1024,
        "temperature": 0.7
    }
}
agent_registry.register_agent(new_agent)

# Register a new prompt
prompt_id = "new.prompt"
prompt_text = "This is a new prompt template."
prompt_metadata = {
    "name": "New Prompt",
    "description": "A new prompt",
    "version": "1.0.0",
    "active": True
}
prompt_registry.register_prompt(prompt_id, prompt_text, prompt_metadata)
```

## Best Practices

1. **Use RegistryFactory**: Always access registries through the RegistryFactory.
2. **Check Permissions**: Always verify permissions before allowing an agent to use a tool.
3. **Validate New Entries**: Ensure new registry entries follow the standardized format.
4. **Handle Validation Issues**: Log and address validation warnings to maintain standard compliance.
5. **Update Registry Documentation**: When adding new registry features, update this documentation.
