# Registry Format Standardization

This document defines the standard formats for all registry types in the system.

## Common Metadata Fields

All registry items should include these common fields:

| Field        | Type     | Required | Description                                       |
|--------------|----------|----------|---------------------------------------------------|
| `id`         | String   | Yes      | Unique identifier (namespace.name format)         |
| `name`       | String   | Yes      | Human-readable name                               |
| `description`| String   | Yes      | Brief description of the item's purpose           |
| `version`    | String   | No       | Semantic version (e.g., "1.0.0")                 |
| `tags`       | String[] | No       | Categorization tags                               |
| `created_at` | String   | No       | Creation date in ISO format (YYYY-MM-DD)          |
| `updated_at` | String   | No       | Last update date in ISO format (YYYY-MM-DD)       |
| `author`     | String   | No       | Creator information                               |
| `active`     | Boolean  | Yes      | Whether the item is currently active              |

## Registry-Specific Fields

### Prompt Registry

**Format:** YAML (individual files)

Additional fields:
- `prompt`: String - The actual prompt content
- `models`: String[] - List of compatible model identifiers

Example:
```yaml
id: "category.prompt_id"
name: "Example Prompt"
description: "Description of the prompt"
version: "1.0.0"
tags: ["tag1", "tag2"]
created_at: "2025-05-01"
updated_at: "2025-05-10"
author: "Dengue Project Team"
active: true
models: ["model1", "model2"]
prompt: |
  The actual prompt content goes here.
  Can be multi-line with formatting.
```

### Tool Registry

**Format:** JSON (single registry file)

Additional fields:
- `module_path`: String - Path to the module containing the tool implementation
- `class_name`: String - Name of the class implementing the tool
- `config_path`: String - Path to the tool configuration file
- `allowed_agents`: String[] - List of agent IDs allowed to use this tool (or ["*"] for all)

Example:
```json
{
  "tools": [
    {
      "id": "tool_id",
      "name": "Tool Name",
      "description": "Tool description",
      "version": "1.0.0",
      "tags": ["tag1", "tag2"],
      "created_at": "2025-05-01",
      "updated_at": "2025-05-10",
      "author": "Dengue Project Team",
      "active": true,
      "module_path": "src.tools.example_tool",
      "class_name": "ExampleTool",
      "config_path": "configs/example_tool.yaml",
      "allowed_agents": ["agent1", "agent2"]
    }
  ]
}
```

### Agent Registry

**Format:** JSON (single registry file)

Additional fields:
- `module_path`: String - Path to the module containing the agent implementation
- `class_name`: String - Name of the class implementing the agent
- `config_path`: String - Path to the agent configuration file
- `prompt_id`: String - ID of the primary prompt used by this agent
- `model_config`: Object - Configuration for the model used by this agent
  - `model_type`: String - Type of model (e.g., "instruct", "chat")
  - `max_tokens`: Number - Maximum tokens to generate
  - `temperature`: Number - Temperature parameter for generation
  - `top_p`: Number - Top-p parameter for generation (optional)
- `tools`: String[] - List of tool IDs this agent can use (optional)

Example:
```json
{
  "agents": [
    {
      "id": "agent_id",
      "name": "Agent Name",
      "description": "Agent description",
      "version": "1.0.0",
      "tags": ["tag1", "tag2"],
      "created_at": "2025-05-01",
      "updated_at": "2025-05-10",
      "author": "Dengue Project Team",
      "active": true,
      "module_path": "src.agent_system.example_agent",
      "class_name": "ExampleAgent",
      "config_path": "configs/example_agent.yaml",
      "prompt_id": "category.prompt_id",
      "model_config": {
        "model_type": "instruct",
        "max_tokens": 1024,
        "temperature": 0.7,
        "top_p": 0.95
      },
      "tools": ["tool1", "tool2"]
    }
  ]
}
```

## Implementation Notes

1. **Backward Compatibility**: When reading registry files, be prepared to handle missing fields by providing defaults.
2. **Migration**: Existing registry items should be gradually updated to conform to this standard.
3. **Validation**: Registry loaders should validate entries against these standards.
4. **Error Handling**: When encountering non-conforming entries, log warnings but try to continue operation.
