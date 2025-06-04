# Registry System

The Registry System provides a modular, configurable way to manage prompts, tools, and agents in the Dengue Knowledge Graph agent system. It separates configuration from code, making it easier to modify and extend the system without code changes.

## Overview

The system consists of three main components:

1. **Prompt Registry**: Manages prompt templates stored as YAML files
2. **Tool Registry**: Manages tool definitions and access control
3. **Agent Registry**: Defines agents with their capabilities, associated tools, and LLM configurations

These registries are accessed through a factory pattern, ensuring consistent access throughout the application.

## Prompt Registry

The Prompt Registry stores prompts as individual YAML files organized by purpose/domain. This allows for version control, easy editing, and metadata for filtering/searching.

### Directory Structure

```
/backend/src/registries/prompts/
  ├── router/
  │   ├── task_classifier.yaml
  │   └── ...
  ├── rag/
  │   ├── retrieval_prompt.yaml
  │   ├── synthesis_prompt.yaml
  │   └── ...
  ├── safety/
  │   ├── content_moderation.yaml
  │   └── ...
  └── ...
```

### Prompt Format

Each prompt file has a consistent YAML structure:

```yaml
id: "router.task_classifier"
name: "Task Classification Prompt"
description: "Classifies user queries into categories"
version: "1.0.0"
tags: ["router", "classification", "task"]
created_at: "2025-04-29"
updated_at: "2025-04-29"
author: "Dengue Project Team"
models: [""]
prompt: |
  You are a task classification agent...
  User query: {{query}}
  Response as JSON: {"category": "CATEGORY_NAME"}
```

### Usage

```python
from src.registries import RegistryFactory

# Get the prompt registry
prompt_registry = RegistryFactory.get_prompt_registry()

# Get a prompt by ID and format it with variables
formatted_prompt = prompt_registry.get_prompt(
    "router.task_classifier", 
    query="What are the symptoms of dengue fever?"
)

# Get prompts by tag
router_prompts = prompt_registry.get_prompt_by_tags("router")
```

## Tool Registry

The Tool Registry defines available tools and their access controls. It manages tool configurations, instantiation, and permission management.

### Directory Structure

```
/backend/src/registries/tools/
  ├── registry.json  # Main registry file
  ├── schemas/       # JSON schema definitions for tools
  │   ├── cypher_tool.json
  │   └── ...
  └── metadata/      # Additional tool metadata
      ├── cypher_tool.yaml
      └── ...
```

### Tool Configuration

The main registry file (`registry.json`) contains basic tool definitions:

```json
{
  "tools": [
    {
      "id": "cypher_tool",
      "name": "Cypher Query Tool",
      "description": "Executes Cypher queries against the Neo4j knowledge graph",
      "module_path": "src.tools.cypher_tool",
      "class_name": "CypherTool",
      "schema_path": "schemas/cypher_tool.json",
      "metadata_path": "metadata/cypher_tool.yaml",
      "allowed_agents": [],
      "requires_permissions": ["database_read"]
    }
  ]
}
```

Additional metadata is stored in YAML files:

```yaml
# metadata/cypher_tool.yaml
description: |
  The Cypher Tool allows agents to query the Neo4j knowledge graph using Cypher.

usage_examples:
  - description: "Basic node count"
    code: |
      result = await cypher_tool.execute_query("MATCH (n) RETURN count(n) as count")
```

### Usage

```python
from src.registries import RegistryFactory

# Get the tool registry
tool_registry = RegistryFactory.get_tool_registry()

# Get a tool configuration
cypher_tool_config = tool_registry.get_tool_config("cypher_tool")

# Instantiate a tool
cypher_tool = tool_registry.instantiate_tool("cypher_tool")

# Control agent access to tools
tool_registry.grant_agent_access("citation_agent", "cypher_tool")
tool_registry.revoke_agent_access("citation_agent", "cypher_tool")
```

## Agent Registry

The Agent Registry defines agents with their capabilities, LLM configurations, and associated tools.

### Directory Structure

```
/backend/src/registries/agents/
  ├── registry.json  # Main registry file 
  └── configs/       # Individual agent configurations
      ├── router_agent.yaml
      ├── citation_agent.yaml
      └── ...
```

### Agent Configuration

The main registry file (`registry.json`) contains basic agent definitions:

```json
{
  "agents": [
    {
      "id": "citation_agent",
      "name": "Citation Agent",
      "description": "Retrieves and formats citations for responses",
      "module_path": "src.agent_system.rag_system.citation_agent",
      "class_name": "CitationAgent",
      "config_path": "configs/citation_agent.yaml",
      "active": true
    }
  ]
}
```

Detailed configurations are stored in YAML files:

```yaml
# configs/citation_agent.yaml
name: "Citation Agent"
description: "Handles citation retrieval and formatting for the RAG system"
version: "1.0.0"

llm:
  provider: ""
  model: ""
  parameters:
    temperature: 0.1
    max_tokens: 1500

tools:
  - id: "cypher_tool"
    parameters:
      include_citations: true

prompts:
  - id: "citation.retrieval"
    description: "Prompt for retrieving relevant citations"
```

### Usage

```python
from src.registries import RegistryFactory

# Get the agent registry
agent_registry = RegistryFactory.get_agent_registry()

# Get an agent configuration
citation_agent_config = agent_registry.get_agent_config("citation_agent")

# Instantiate an agent
citation_agent = agent_registry.instantiate_agent("citation_agent", registry_factory=RegistryFactory)

# List active agents
active_agents = agent_registry.list_agents(active_only=True)

# Set agent active status
agent_registry.set_agent_active("citation_agent", active=True)
```

## Registry Factory

The Registry Factory provides singleton access to the registries, ensuring consistent access throughout the application.

### Usage

```python
from src.registries import RegistryFactory

# Get the various registries
prompt_registry = RegistryFactory.get_prompt_registry()
tool_registry = RegistryFactory.get_tool_registry()
agent_registry = RegistryFactory.get_agent_registry()

# Reload all registries
RegistryFactory.reload_all()
```

## Example: Creating a New Agent

To create a new agent:

1. Implement the agent class
2. Add the agent to the registry
3. Create a configuration file
4. Grant the agent access to required tools

```python
# 1. Implement the agent class
class MyNewAgent:
    def __init__(self, agent_id, config, registry_factory=None):
        self.agent_id = agent_id
        self.config = config
        
        # Get registries
        if registry_factory:
            self.prompt_registry = registry_factory.get_prompt_registry()
            self.tool_registry = registry_factory.get_tool_registry()
            
            # Get required tools
            self.my_tool = self.tool_registry.instantiate_tool("my_tool")
            
            # Get required prompts
            self.my_prompt = self.prompt_registry.get_prompt("my.prompt")

# 2. Add the agent to the registry
agent_config = {
    "id": "my_new_agent",
    "name": "My New Agent",
    "description": "Does something useful",
    "module_path": "src.agent_system.my_module",
    "class_name": "MyNewAgent",
    "config_path": "configs/my_new_agent.yaml",
    "active": True
}

agent_registry = RegistryFactory.get_agent_registry()
agent_registry.register_agent(agent_config)

# 3. Create a configuration file (my_new_agent.yaml)

# 4. Grant the agent access to required tools
tool_registry = RegistryFactory.get_tool_registry()
tool_registry.grant_agent_access("my_new_agent", "my_tool")
```

## Best Practices

1. **Modular Prompts**: Keep prompts focused on a single task; compose complex workflows from multiple prompts
2. **Versioning**: Use the version field to track changes to prompts and configurations
3. **Documentation**: Include clear descriptions and usage examples in metadata
4. **Minimal Permissions**: Grant agents access only to the tools they need
5. **Testing**: Test prompts with different inputs before deployment