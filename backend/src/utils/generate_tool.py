#!/usr/bin/env python
"""
Tool Generator

This script generates new tool files from templates:
1. Creates a tool configuration file
2. Creates a tool implementation file
3. Updates the tool registry

The generated files are compatible with the standardized registry system,
including support for registry factories and the BaseRegistry abstract class.
This ensures tools can be properly registered and permissions enforced.

This script uses Jinja2 for templating, providing more robust and maintainable
template rendering with support for conditionals, loops, and better escaping.

Usage:
  python -m src.utils.generate_tool --tool --name <tool_name> [--agents <agent_id1> <agent_id2> ...]
"""

import argparse
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import jinja2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("tool_generator")


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate tool files from templates")
    parser.add_argument("--tool", action="store_true", help="Generate a new tool")
    parser.add_argument("--name", type=str, help="Tool name (e.g., 'database_tool')")
    parser.add_argument(
        "--agents", 
        nargs="+", 
        help="Agent IDs allowed to use this tool"
    )
    return parser.parse_args()


def snake_to_camel(name: str) -> str:
    """Convert snake_case to CamelCase."""
    components = name.split("_")
    return "".join(x.title() for x in components)


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
    content = re.sub(r'"""[\s\S]*?THIS IS A TEMPLATE FILE[\s\S]*?"""', '"""', content, count=1)
    
    # Remove template-specific directives
    content = re.sub(r"# pylint: disable=all\n", "", content)
    content = re.sub(r"# flake8: noqa\n", "", content)
    content = re.sub(r"# type: ignore\n", "", content)
    content = re.sub(r"# pyright: ignore\n", "", content)
    content = re.sub(r"#\s*noqa: E999\n", "", content)
    
    # Remove any empty lines created by the above replacements
    content = re.sub(r'\n\n\n+', '\n\n', content)
    
    return content


# Note: We no longer need a separate load_template function as we load
# templates directly through Jinja2's environment


def generate_config_file(
    template_path: str, 
    output_path: str, 
    tool_id: str, 
    tool_name: str, 
    allowed_agents: Optional[List[str]] = None
) -> None:
    """Generate a tool configuration file from template using Jinja2."""
    # Setup Jinja2 environment
    env = setup_jinja_env()
    
    # Load the template from file
    with open(template_path, 'r') as f:
        template_content = f.read()
    
    # Create a template from the string
    template = env.from_string(template_content)
    
    # Prepare context for rendering
    context = {
        "tool_id": tool_id,
        "tool_name": tool_name,
        "tool_description": f"A specialized tool for {tool_id} functionality",
        "type": "utility",
        "allowed_agents": allowed_agents or []
    }
    
    # Render the template
    rendered_content = template.render(**context)
    
    # Write to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(rendered_content)
    
    logger.info(f"Generated config file: {output_path}")


def generate_implementation_file(
    template_path: str, 
    output_path: str, 
    tool_id: str, 
    class_name: str
) -> None:
    """Generate a tool implementation file from template."""
    # Load template
    template = load_template(template_path)
    
    # Clean template
    content = clean_template_content(template)
    
    # Replace class name
    content = content.replace("ToolClassName", class_name)
    content = content.replace("Tool Description", f"{class_name} Tool")
    content = content.replace("tool functionality description", f"{tool_id} operations")
    
    # Write to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(content)
    
    logger.info(f"Generated implementation file: {output_path}")


def update_registry(
    registry_path: str, 
    tool_id: str, 
    tool_name: str, 
    module_path: str, 
    class_name: str, 
    config_path: str,
    allowed_agents: Optional[List[str]] = None
) -> None:
    """Update the tool registry with the new tool.
    
    This method is compatible with the BaseRegistry approach and includes
    permissions management via allowed_agents list.
    
    Uses the RegistryFactory to access the tool registry instance.
    """
    try:
        # Import here to avoid circular imports
        from src.registries.registry_factory import RegistryFactory
        
        # Get the tool registry from the factory
        tool_registry = RegistryFactory.get_tool_registry()
        
        # Check if tool already exists
        if tool_registry.has_item(tool_id):
            logger.warning(f"Tool with ID '{tool_id}' already exists in registry. Skipping update.")
            return
            
        # Prepare the new tool with standardized fields
        new_tool = {
            "id": tool_id,
            "name": tool_name,
            "description": f"A specialized tool for {tool_id} functionality",
            "module_path": module_path,
            "class_name": class_name,
            "config_path": config_path,
            "active": True,
        }
        
        # Add allowed_agents if specified
        if allowed_agents:
            new_tool["allowed_agents"] = allowed_agents
        
        # Register the tool using the registry's register_tool method
        tool_registry.register_tool(new_tool)
        
        logger.info(f"Added tool '{tool_id}' to registry using RegistryFactory")
        
    except ImportError:
        # Fall back to direct file manipulation if RegistryFactory is not available
        logger.warning("RegistryFactory not available, falling back to direct file manipulation")
        
        # Load the registry
        with open(registry_path, "r") as f:
            registry = json.load(f)
        
        # Ensure standard structure
        if "tools" not in registry:
            registry["tools"] = []
        
        # Check if the tool already exists
        for tool in registry["tools"]:
            if tool["id"] == tool_id:
                logger.warning(f"Tool with ID '{tool_id}' already exists in registry. Skipping update.")
                return
        
        # Prepare the tool entry
        new_tool = {
            "id": tool_id,
            "name": tool_name,
            "description": f"A specialized tool for {tool_id} functionality",
            "module_path": module_path,
            "class_name": class_name,
            "config_path": config_path,
            "active": True,
        }
        
        # Add allowed_agents if specified
        if allowed_agents:
            new_tool["allowed_agents"] = allowed_agents
        
        # Add to registry
        registry["tools"].append(new_tool)
        
        # Save updated registry
        with open(registry_path, "w") as f:
            json.dump(registry, f, indent=2)
            
        logger.info(f"Added tool '{tool_id}' to registry using direct file manipulation")
    except Exception as e:
        logger.error(f"Error updating tool registry: {str(e)} with new tool: {tool_id}")


def generate_tool(name: str, allowed_agents: Optional[List[str]] = None) -> None:
    """Generate all files for a new tool."""
    # Validate and clean the tool name
    tool_id = name.lower().strip().replace(' ', '_').replace('-', '_')
    tool_name = tool_id.replace('_', ' ').title()
    class_name = f"{snake_to_camel(tool_id)}Tool"
    
    # Set up paths
    project_root = Path(__file__).parent.parent.parent
    registry_dir = project_root / "src" / "registries" / "tools"
    templates_dir = registry_dir / "templates"
    configs_dir = registry_dir / "configs"
    tools_dir = project_root / "src" / "tools"
    
    # Create directories if they don't exist
    os.makedirs(registry_dir, exist_ok=True)
    os.makedirs(templates_dir, exist_ok=True)
    os.makedirs(configs_dir, exist_ok=True)
    os.makedirs(tools_dir, exist_ok=True)
    
    # Ensure registry file exists
    registry_path = registry_dir / "registry.json"
    if not os.path.exists(registry_path):
        with open(registry_path, "w") as f:
            json.dump({"tools": []}, f, indent=2)
    
    # Template paths
    config_template_path = templates_dir / "tool_config_template.yaml"
    implementation_template_path = templates_dir / "tool_implementation_template.py"
    
    # Create template files if they don't exist
    sample_config_content = (
        "# Tool Configuration Template\n"
        "id: {{ tool_id }}                      # Unique identifier for the tool\n"
        "name: {{ Tool Name }}                 # Human-readable name\n"
        "description: {{ Tool description }}     # Brief description of tool purpose\n"
        "type: {{ type }}                      # Tool type: utility, api, database, etc.\n\n"
        "allowed_agents:                              # [OPTIONAL] List of agent IDs allowed to use this tool\n"
        "  - \"{{ agent_id_1 }}\"\n"
        "  # - Add more agent IDs as needed\n\n"
        "# Add any additional tool-specific configuration below\n"
    )

    if not os.path.exists(config_template_path):
        with open(config_template_path, "w") as f:
            f.write(sample_config_content)
    
    sample_implementation_content = (
        "\"\"\"\n"
        "Tool implementation template for new tools.\n\n"
        "THIS IS A TEMPLATE FILE and contains placeholder values that will be replaced during code generation.\n"
        "It is NOT meant to be used directly. Linters should ignore this file.\n"
        "\"\"\"\n"
        "from typing import Any, Dict, List, Optional, Union\n\n"
        "from src.tools.core.base_tool import BaseTool\n"
        "from src.tools.core.tool_response import ToolResponse\n\n\n"
        "class {{ ClassName }}(BaseTool):  # noqa: E999\n"
        "    \"\"\"\n"
        "    {{ ToolName }} Tool\n\n"
        "    This tool handles {{ tool_id }} operations.\n"
        "    \"\"\"\n\n"
        "    def __init__(self, config: Dict[str, Any]) -> None:\n"
        "        \"\"\"\n"
        "        Initialize the {{ ToolName }}.\n\n"
        "        Args:\n"
        "            config: Tool configuration dictionary\n"
        "        \"\"\"\n"
        "        super().__init__(config)\n"
        "        # Add any additional initialization here\n\n"
        "    async def execute(self, params: Dict[str, Any]) -> ToolResponse:\n"
        "        \"\"\"\n"
        "        Execute the tool with the given parameters.\n\n"
        "        Args:\n"
        "            params: Input parameters for the tool\n\n"
        "        Returns:\n"
        "            ToolResponse object containing the results\n"
        "        \"\"\"\n"
        "        try:\n"
        "            # TODO: Implement tool-specific logic here\n"
        "            result = f\"Executed {{ tool_id }} with {params}\"\n"
        "            return ToolResponse(success=True, data=result)\n"
        "        except Exception as e:\n"
        "            return ToolResponse(success=False, error=str(e))\n"
    )

    if not os.path.exists(implementation_template_path):
        with open(implementation_template_path, "w") as f:
            f.write(sample_implementation_content)
    
    # Generate output paths
    config_path = configs_dir / f"{tool_id}.yaml"
    implementation_path = tools_dir / f"{tool_id}.py"
    
    # Generate the config file
    generate_config_file(
        template_path=config_template_path,
        output_path=config_path,
        tool_id=tool_id,
        tool_name=tool_name,
        allowed_agents=allowed_agents
    )
    
    # Generate the implementation file using Jinja2
    env = setup_jinja_env()
    
    # Load the template from file
    with open(implementation_template_path, 'r') as f:
        template_content = f.read()
    
    # Clean the template content
    template_content = clean_template_content(template_content)
    
    # Create a template from the string
    template = env.from_string(template_content)
    
    # Prepare context for rendering
    context = {
        "ClassName": class_name,
        "ToolName": tool_name,
        "tool_id": tool_id
    }
    
    # Render the template
    rendered_content = template.render(**context)
    
    # Write to file
    with open(implementation_path, "w") as f:
        f.write(rendered_content)
    
    logger.info(f"Generated implementation file: {implementation_path}")
    
    # Update the registry
    relative_config_path = f"configs/{tool_id}.yaml"
    module_path = f"src.tools.{tool_id}"
    
    update_registry(
        registry_path=registry_path,
        tool_id=tool_id,
        tool_name=tool_name,
        module_path=module_path,
        class_name=class_name,
        config_path=relative_config_path,
        allowed_agents=allowed_agents  # Pass the allowed_agents parameter to update_registry
    )
    
    # Print completion message
    logger.info("\nTool generation complete!")
    logger.info(f"Config file: {config_path}")
    logger.info(f"Implementation file: {implementation_path}")
    logger.info(f"Registry updated in: {registry_path}")
    logger.info("\nNext steps:")
    logger.info("1. Review and update the configuration in the YAML file")
    logger.info("2. Implement tool-specific logic in the Python file")


def main() -> None:
    """Main entry point."""
    args = parse_arguments()
    
    if args.tool and args.name:
        generate_tool(args.name, args.agents)
    else:
        logger.error("Invalid arguments. Use --tool --name <tool_name>")


if __name__ == "__main__":
    main()
