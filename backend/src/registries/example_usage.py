"""
Example script demonstrating how to use the registry system.

This script shows how to:
1. Access prompts from the Prompt Registry
2. Access tools from the Tool Registry
3. Access agents from the Agent Registry
"""
import asyncio
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the registry factory
from src.registries import RegistryFactory

async def demo_prompt_registry():
    """
    Demonstrate how to use the Prompt Registry.
    """
    print("\n---- Prompt Registry Demo ----")
    
    # Get the prompt registry
    prompt_registry = RegistryFactory.get_prompt_registry()
    
    # List all available prompts
    prompts = prompt_registry.list_prompts()
    print(f"Found {len(prompts)} prompts:")
    for prompt in prompts:
        print(f"  - {prompt['id']}: {prompt['name']}")
    
    # Get a specific prompt by ID
    try:
        router_prompt = prompt_registry.get_prompt(
            "router.task_classifier", 
            query="What are the symptoms of dengue fever?"
        )
        print("\nTask classifier prompt (truncated):")
        print(router_prompt[:200] + "...")
    except ValueError as e:
        print(f"Error: {str(e)}")
    
    # Get prompts by tag
    rag_prompts = prompt_registry.get_prompt_by_tags("rag")
    print(f"\nFound {len(rag_prompts)} RAG prompts:")
    for prompt in rag_prompts:
        print(f"  - {prompt['id']}: {prompt['name']}")

async def demo_tool_registry():
    """
    Demonstrate how to use the Tool Registry.
    """
    print("\n---- Tool Registry Demo ----")
    
    # Get the tool registry
    tool_registry = RegistryFactory.get_tool_registry()
    
    # List all tools
    tools = tool_registry.list_tools()
    print(f"Found {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool['id']}: {tool['name']}")
    
    # Get a specific tool configuration
    try:
        cypher_tool_config = tool_registry.get_tool_config("cypher_tool")
        print("\nCypher Tool Configuration:")
        print(f"  Name: {cypher_tool_config['name']}")
        print(f"  Description: {cypher_tool_config['description']}")
        print(f"  Module: {cypher_tool_config['module_path']}.{cypher_tool_config['class_name']}")
        
        # Show capabilities if available
        if "capabilities" in cypher_tool_config:
            print("\n  Capabilities:")
            for capability in cypher_tool_config["capabilities"]:
                print(f"    - {capability}")
    except ValueError as e:
        print(f"Error: {str(e)}")
    
    # Check and update agent access
    try:
        # Grant access
        tool_registry.grant_agent_access("citation_agent", "cypher_tool")
        print("\nGranted 'citation_agent' access to 'cypher_tool'")
        
        # Check access
        has_access = tool_registry.check_agent_access("citation_agent", "cypher_tool")
        print(f"'citation_agent' has access to 'cypher_tool': {has_access}")
        
        # Revoke access
        tool_registry.revoke_agent_access("citation_agent", "cypher_tool")
        print("Revoked 'citation_agent' access to 'cypher_tool'")
        
        # Check access again
        has_access = tool_registry.check_agent_access("citation_agent", "cypher_tool")
        print(f"'citation_agent' has access to 'cypher_tool': {has_access}")
    except ValueError as e:
        print(f"Error: {str(e)}")

async def demo_agent_registry():
    """
    Demonstrate how to use the Agent Registry.
    """
    print("\n---- Agent Registry Demo ----")
    
    # Get the agent registry
    agent_registry = RegistryFactory.get_agent_registry()
    
    # List all agents
    agents = agent_registry.list_agents()
    print(f"Found {len(agents)} agents:")
    for agent in agents:
        status = "active" if agent.get("active", False) else "inactive"
        print(f"  - {agent['id']}: {agent['name']} ({status})")
    
    # Get a specific agent configuration
    try:
        citation_agent_config = agent_registry.get_agent_config("citation_agent")
        print("\nCitation Agent Configuration:")
        print(f"  Name: {citation_agent_config['name']}")
        print(f"  Description: {citation_agent_config['description']}")
        
        # Show LLM configuration if available
        if "llm" in citation_agent_config:
            llm_config = citation_agent_config["llm"]
            print(f"\n  LLM: {llm_config['provider']} / {llm_config['model']}")
            print(f"  Parameters: {llm_config['parameters']}")
        
        # Show tools if available
        if "tools" in citation_agent_config:
            print("\n  Tools:")
            for tool in citation_agent_config["tools"]:
                print(f"    - {tool['id']}")
    except ValueError as e:
        print(f"Error: {str(e)}")

async def main():
    """
    Run the demo for all registries.
    """
    print("=== Registry System Demo ===")
    
    # Demo each registry
    await demo_prompt_registry()
    await demo_tool_registry()
    await demo_agent_registry()
    
    print("\n=== Demo Complete ===")

if __name__ == "__main__":
    asyncio.run(main())