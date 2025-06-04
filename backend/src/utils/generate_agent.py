#!/usr/bin/env python
"""
Agent Generator Utility

This script generates new agent files from templates, including:
1. YAML configuration file in the configs directory
2. Python implementation file in the appropriate agent_system directory
3. Registry entry in the registry.json file

The generated files are compatible with the standardized registry system,
including support for registry factories and the BaseRegistry abstract class.

Usage:
    python generate_agent.py --agent --name [type]/[name] --prompt [prompt_id] --tools [tool_id1 tool_id2 ...]

Examples:
    python generate_agent.py --agent --name assistants/summarization --prompt assistants.summarization --tools cypher_tool vector_tool
    python generate_agent.py --agent --name safety/toxicity_filter --prompt safety.toxicity_filter
    python generate_agent.py --agent --name rag/query_processor --prompt rag.query_processor --tools cypher_tool
"""
import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
import re
import shutil
import jinja2

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("agent_generator")

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "src" / "registries" / "agents" / "templates"
CONFIG_DIR = PROJECT_ROOT / "src" / "registries" / "agents" / "configs"
REGISTRY_FILE = PROJECT_ROOT / "src" / "registries" / "agents" / "registry.json"
AGENT_SYSTEM_DIR = PROJECT_ROOT / "src" / "agent_system"

# Template files
CONFIG_TEMPLATE = TEMPLATE_DIR / "agent_config_template.yaml"
IMPLEMENTATION_TEMPLATE = TEMPLATE_DIR / "agent_implementation_template.py"


def setup_jinja_env() -> jinja2.Environment:
    """Set up and return a configured Jinja2 environment."""
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader("."),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True
    )


def clean_template_content(content: str) -> str:
    """Clean template content before Jinja2 rendering.
    
    Removes template-specific comments, linter directives, and other
    artifacts that shouldn't appear in the generated files.
    """
    # Remove the template header (first docstring)
    content = content.replace(
        """Template file for agent implementation.

THIS FILE IS A TEMPLATE and contains placeholder values that will be replaced during code generation.
It is NOT meant to be valid Python on its own. Linters should ignore this file.

""", """""")
    
    # Remove noqa comments from imports and other lines
    content = re.sub(r'\s+#\s*noqa.*$', '', content, flags=re.MULTILINE)
    content = re.sub(r'^\s*#\s*(fmt: off|pylint: disable=all|flake8: noqa|type: ignore).*$', '', content, flags=re.MULTILINE)
    content = re.sub(r'#\s*pyright: ignore', '', content)
    
    # Remove any empty lines created by the above replacements
    content = re.sub(r'\n\n\n+', '\n\n', content)
    
    return content

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate agent files from templates")
    parser.add_argument("--agent", action="store_true", help="Generate a new agent")
    parser.add_argument("--name", type=str, required=True, 
                        help="Agent name in format: type/name or type/subtype/name (e.g., assistants/summarization or rag_system/query/query_writer)")
    parser.add_argument("--prompt", type=str, help="Prompt ID from the prompt registry (e.g., rag.query_generator)")
    parser.add_argument("--tools", type=str, nargs="*", help="List of tool IDs to include (e.g., cypher_tool vector_tool)")
    return parser.parse_args()

def validate_agent_name(agent_name: str) -> Tuple[str, str, str]:
    """
    Validate and parse the agent name into components.
    
    Args:
        agent_name: Agent name in format type/subtype.../name (e.g., assistants/summarization or rag_system/query/query_writer)
        
    Returns:
        Tuple of (agent_dir_path, agent_base_name, class_name)
    """
    parts = agent_name.split("/")
    if len(parts) < 2:
        raise ValueError("Agent name must be in format: type/name or type/subtype/name (e.g., assistants/summarization or rag_system/query/query_writer)")
    
    # Last part is the agent name, the rest is the directory path
    agent_base_name = parts[-1]
    agent_dir_path = "/".join(parts[:-1])
    
    # Basic type is the first part of the path
    agent_type = parts[0]
    
    # Validate main agent type
    valid_types = ["assistants", "safety", "rag_system", "routing"]
    if agent_type not in valid_types:
        logger.warning(f"Agent type '{agent_type}' is not one of the standard types: {valid_types}")
        proceed = input(f"Proceed with non-standard agent type '{agent_type}'? (y/n): ")
        if proceed.lower() != 'y':
            sys.exit(1)
    
    # Convert to snake_case if needed
    agent_base_name = re.sub(r'(?<!^)(?=[A-Z])', '_', agent_base_name).lower()
    
    # Generate class name (CamelCase)
    if agent_type == "assistants":
        class_suffix = "Assistant"
    else:
        class_suffix = "Agent"
    
    class_name = ''.join(word.capitalize() for word in agent_base_name.split('_')) + class_suffix
    
    return agent_dir_path, agent_base_name, class_name

def get_model_defaults(agent_type: str) -> Dict[str, str]:
    """
    Get default model settings based on agent type.
    
    Args:
        agent_type: Type of agent (e.g., assistants, safety)
        
    Returns:
        Dictionary of default model settings
    """
    if agent_type == "safety":
        return {
            "model_type": "guardian",
            "model_name": "granite3-guardian-2b"
        }
    else:
        return {
            "model_type": "instruct",
            "model_name": "granite-3-1-8b-instruct-w4a16"
        }

def generate_agent_id(agent_type: str, agent_name: str) -> str:
    """Generate a standardized agent ID."""
    if agent_type == "assistants":
        return f"{agent_name}_assistant"
    elif agent_type == "rag_system":
        return f"rag_{agent_name}_agent"
    else:
        return f"{agent_name}_agent"

def generate_config_file(agent_type: str, agent_base_name: str, class_name: str, prompt_id: Optional[str] = None, tools: Optional[List[str]] = None) -> str:
    """
    Generate the agent config YAML file using Jinja2 templating.
    
    Args:
        agent_type: Type of agent directory path (e.g., assistants, rag_system/query)
        agent_base_name: Base name of the agent
        class_name: Class name for the agent
        prompt_id: Optional specific prompt ID to use
        tools: Optional list of tool IDs to include
        
    Returns:
        Path to the generated config file
    """
    # Generate agent ID and name based on type
    agent_id = generate_agent_id(agent_type.split('/')[0], agent_base_name)
    agent_name = ' '.join(word.capitalize() for word in agent_base_name.split('_'))
    
    # Set appropriate names and default prompt ID based on agent type
    primary_type = agent_type.split('/')[0]
    if primary_type == "assistants":
        agent_name = f"{agent_name} Assistant"
        default_prompt_id = f"assistants.{agent_base_name}"
        agent_type_tag = f"{agent_base_name}_assistant_agent"
    elif primary_type == "safety":
        agent_name = f"{agent_name} Safety Agent"
        default_prompt_id = f"safety.{agent_base_name}"
        agent_type_tag = "safety"
    elif primary_type == "rag_system":
        agent_name = f"{agent_name} RAG Agent"
        default_prompt_id = f"rag.{agent_base_name}"
        agent_type_tag = "rag"
    else:
        agent_name = f"{agent_name} Agent"
        default_prompt_id = f"{primary_type}.{agent_base_name}"
        agent_type_tag = primary_type
    
    # Use provided prompt_id or default
    actual_prompt_id = prompt_id or default_prompt_id
    
    # Get appropriate model defaults
    model_defaults = get_model_defaults(primary_type)
    
    # Setup Jinja2 environment
    env = setup_jinja_env()
    
    # Load the template from file
    with open(CONFIG_TEMPLATE, 'r') as f:
        template_content = f.read()
    
    # Create a template from the string
    template = env.from_string(template_content)
    
    # Prepare context for rendering
    context = {
        "agent_id": agent_id,
        "agent_name": agent_name,
        "agent_description": f"A specialized agent for {agent_base_name.replace('_', ' ')} functionality",
        "agent_type": agent_type_tag,
        "model_type": model_defaults["model_type"],
        "model_name": model_defaults["model_name"],
        "prompt_id": actual_prompt_id,
        "tools": [dict(id=tool_id, parameters={}) for tool_id in (tools or [])]
    }
    
    # Render the template
    rendered_content = template.render(**context)
    
    # Create output file
    output_file = CONFIG_DIR / f"{agent_id}.yaml"
    with open(output_file, 'w') as f:
        f.write(rendered_content)
    
    logger.info(f"Generated config file: {output_file}")
    return str(output_file)

def generate_implementation_file(agent_type: str, agent_base_name: str, class_name: str, prompt_id: Optional[str] = None) -> str:
    """
    Generate the agent implementation Python file.
    
    Args:
        agent_type: Type of agent directory path (e.g., assistants, rag_system/query)
        agent_base_name: Base name of the agent
        class_name: Class name for the agent
        prompt_id: Optional specific prompt ID to use
        
    Returns:
        Path to the generated implementation file
    """
    # Ensure the target directory exists (handle nested paths)
    target_dir = AGENT_SYSTEM_DIR
    for path_part in agent_type.split('/'):
        target_dir = target_dir / path_part
        if not target_dir.exists():
            logger.info(f"Creating directory: {target_dir}")
            target_dir.mkdir(exist_ok=True)
    
    # Create __init__.py files in all directories if they don't exist
    current_dir = AGENT_SYSTEM_DIR
    for path_part in agent_type.split('/'):
        current_dir = current_dir / path_part
        init_file = current_dir / "__init__.py"
        if not init_file.exists():
            logger.info(f"Creating __init__.py file in: {current_dir}")
            with open(init_file, 'w') as f:
                f.write('"""Agent module."""\n')
    
    agent_id = generate_agent_id(agent_type.split('/')[0], agent_base_name)
    agent_name = ' '.join(word.capitalize() for word in agent_base_name.split('_'))
    
    # Determine appropriate agent attributes based on primary type (first path component)
    primary_type = agent_type.split('/')[0]
    if primary_type == "assistants":
        agent_name = f"{agent_name} Assistant"
        default_prompt_id = f"assistants.{agent_base_name}"
        model_type = "instruct"
    elif primary_type == "safety":
        agent_name = f"{agent_name} Safety Agent"
        default_prompt_id = f"safety.{agent_base_name}"
        model_type = "guardian"
    elif primary_type == "rag_system":
        agent_name = f"{agent_name} RAG Agent"
        default_prompt_id = f"rag.{agent_base_name}"
        model_type = "instruct"
    else:
        agent_name = f"{agent_name} Agent"
        default_prompt_id = f"{primary_type}.{agent_base_name}"
        model_type = "instruct"
    
    # Use provided prompt_id or default
    actual_prompt_id = prompt_id or default_prompt_id
    
    # Setup Jinja2 environment
    env = setup_jinja_env()
    
    # Load the template from file
    with open(IMPLEMENTATION_TEMPLATE, 'r') as f:
        template_content = f.read()
        
    # Clean the template content before rendering
    template_content = clean_template_content(template_content)
    
    # Create a template from the cleaned string
    template = env.from_string(template_content)
    
    # Prepare context for rendering with all required variables
    agent_description = f"A specialized agent for {agent_base_name.replace('_', ' ')} functionality"
    
    context = {
        "class_name": class_name,
        "agent_name": agent_name,
        "agent_description": agent_description,
        "prompt_id": actual_prompt_id,
        "model_type": model_type,
    }
    
    # Render the template with the context
    rendered_content = template.render(**context)
    
    # Create output file
    if primary_type == "assistants" and not agent_base_name.endswith("assistant"):
        output_file = target_dir / f"{agent_base_name}_assistant.py"
    else:
        output_file = target_dir / f"{agent_base_name}_agent.py"
    
    with open(output_file, 'w') as f:
        f.write(rendered_content)
    
    logger.info(f"Generated implementation file: {output_file}")
    return str(output_file)

def update_registry(agent_type: str, agent_base_name: str, class_name: str) -> None:
    """
    Update the agent registry JSON file to include the new agent.
    This is compatible with the BaseRegistry-derived AgentRegistry class.
    
    Args:
        agent_type: Type of agent directory path (e.g., assistants, rag_system/query)
        agent_base_name: Base name of the agent
        class_name: Class name for the agent
    """
    agent_id = generate_agent_id(agent_type.split('/')[0], agent_base_name)
    agent_name = ' '.join(word.capitalize() for word in agent_base_name.split('_'))
    
    # Get primary agent type
    primary_type = agent_type.split('/')[0]
    
    if primary_type == "assistants":
        agent_name = f"{agent_name} Assistant"
        module_path_suffix = f"{agent_base_name}_assistant"
    else:
        agent_name = f"{agent_name} Agent"
        module_path_suffix = f"{agent_base_name}_agent"
    
    # Build a module path that includes all the subdirectories
    module_path = f"src.agent_system.{agent_type.replace('/', '.')}.{module_path_suffix}"
    
    try:
        # Import here to avoid circular imports
        from src.registries.registry_factory import RegistryFactory
        
        # Get the agent registry from the factory
        agent_registry = RegistryFactory.get_agent_registry()
        
        # Check if agent already exists
        if agent_registry.has_item(agent_id):
            logger.warning(f"Agent with ID '{agent_id}' already exists in registry. Skipping update.")
            return
    
        # Create new agent entry with standardized fields
        agent_description = f"A specialized agent for {agent_base_name.replace('_', ' ')} functionality"
        new_agent = {
            "id": agent_id,
            "name": agent_name,
            "description": agent_description,
            "module_path": module_path,
            "class_name": class_name,
            "config_path": f"configs/{agent_id}.yaml",
            "active": True,
            "model_config": {
                "model_type": "instruct",
                "max_tokens": 1024,
                "temperature": 0.7,
                "top_p": 0.95
            }
        }
        
        # Register the agent using the registry's register_agent method
        agent_registry.register_agent(new_agent)
        
        logger.info(f"Added agent '{agent_id}' to registry using RegistryFactory")
        
    except ImportError:
        # Fall back to direct file manipulation if RegistryFactory is not available
        logger.warning("RegistryFactory not available, falling back to direct file manipulation")
        
        # Load the registry
        with open(REGISTRY_FILE, 'r') as f:
            registry = json.load(f)
            
        # Ensure we have the standard structure
        if "agents" not in registry:
            registry["agents"] = []
        
        # Check if agent already exists
        for agent in registry["agents"]:
            if agent["id"] == agent_id:
                logger.warning(f"Agent with ID '{agent_id}' already exists in registry. Skipping update.")
                return
        
        # Create new agent entry with standardized fields
        agent_description = f"A specialized agent for {agent_base_name.replace('_', ' ')} functionality"
        new_agent = {
            "id": agent_id,
            "name": agent_name,
            "description": agent_description,
            "module_path": module_path,
            "class_name": class_name,
            "config_path": f"configs/{agent_id}.yaml",
            "active": True,
            "model_config": {
                "model_type": "instruct",
                "max_tokens": 1024,
                "temperature": 0.7,
                "top_p": 0.95
            }
        }
        
        # Add to registry
        registry["agents"].append(new_agent)
        
        # Save updated registry
        with open(REGISTRY_FILE, 'w') as f:
            json.dump(registry, f, indent=2)
            
        logger.info(f"Added agent '{agent_id}' to registry using direct file manipulation")
    except Exception as e:
        logger.error(f"Error updating agent registry: {str(e)} with new agent: {agent_id}")

def main():
    """Main entry point for the script."""
    args = parse_args()
    
    if args.agent:
        # Validate templates exist
        for template_file in [CONFIG_TEMPLATE, IMPLEMENTATION_TEMPLATE]:
            if not template_file.exists():
                logger.error(f"Template file not found: {template_file}")
                sys.exit(1)
        
        # Parse and validate agent name
        try:
            agent_type, agent_base_name, class_name = validate_agent_name(args.name)
        except ValueError as e:
            logger.error(str(e))
            sys.exit(1)
        
        logger.info(f"Generating new agent: {class_name} (Type: {agent_type}, Base: {agent_base_name})")
        
        # Extract tools list if provided
        tools = args.tools if args.tools else None
        
        # Generate files
        config_file = generate_config_file(agent_type, agent_base_name, class_name, args.prompt, tools)
        implementation_file = generate_implementation_file(agent_type, agent_base_name, class_name, args.prompt)
        update_registry(agent_type, agent_base_name, class_name)
        
        # Success message
        logger.info("\nAgent generation complete!")
        logger.info(f"Config file: {config_file}")
        logger.info(f"Implementation file: {implementation_file}")
        logger.info(f"Registry updated in: {REGISTRY_FILE}")
        logger.info("\nNext steps:")
        logger.info("1. Review and update the configuration in the YAML file")
        logger.info("2. Implement agent-specific logic in the Python file")
        logger.info("3. Create necessary prompt in the prompt registry")
    
if __name__ == "__main__":
    main()
