#!/usr/bin/env python
"""
Workflow Generator

This script generates new workflow files from templates:
1. Creates a workflow JSON file with the specified structure
2. Supports different workflow types (simple, loop, etc.)

Usage:
  python -m src.utils.generate_workflow --workflow --id <WORKFLOW_ID> --name <workflow_name> --agents <agent_id1> <agent_id2>
"""

import argparse
import json
import logging
import os
import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("workflow_generator")


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate workflow files from templates")
    parser.add_argument("--workflow", action="store_true", help="Generate a new workflow")
    parser.add_argument("--id", type=str, help="Workflow ID (e.g., 'CUSTOM_WORKFLOW')")
    parser.add_argument("--name", type=str, help="Workflow name (e.g., 'Custom Workflow')")
    parser.add_argument("--agents", nargs="+", help="Agent IDs to include in the workflow", default=[])
    parser.add_argument("--type", type=str, choices=["simple", "loop", "sandwich"], 
                        default="simple", help="Workflow type")
    parser.add_argument("--description", type=str, help="Workflow description")
    parser.add_argument("--inactive", action="store_true", help="Set workflow as inactive (not used in testing)")
    return parser.parse_args()


def load_template(template_path: str) -> Dict[str, Any]:
    """Load a template file."""
    logger.info(f"Loading template: {template_path}")
    with open(template_path, "r") as f:
        return json.load(f)


def generate_workflow_file(
    template: Dict[str, Any],
    output_path: str,
    workflow_id: str,
    workflow_name: str,
    description: str,
    agents: List[str],
    inactive: bool
) -> None:
    """Generate a workflow file from template."""
    # Get current date
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Update workflow data with provided values
    workflow = template.copy()
    workflow["id"] = workflow_id
    workflow["name"] = workflow_name
    workflow["description"] = description or f"Workflow for {workflow_name.lower()}"
    
    # Only add inactive field if workflow is inactive
    if inactive:
        workflow["inactive"] = True
    
    # Update dates
    workflow["metadata"]["created_at"] = today
    workflow["metadata"]["updated_at"] = today
    workflow["metadata"]["notes"] = f"Standard workflow with {len(agents)} agent(s)"
    
    # Update agents/steps
    if agents:
        workflow["steps"] = agents
    
    # Write to file
    with open(output_path, "w") as f:
        json.dump(workflow, f, indent=2)
    
    logger.info(f"Generated workflow file: {output_path}")


def generate_sandwich_workflow(
    template: Dict[str, Any],
    output_path: str,
    workflow_id: str,
    workflow_name: str,
    description: str,
    agents: List[str],
    inactive: bool
) -> None:
    """Generate a compliance sandwich workflow."""
    # Get current date
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Create sandwich workflow
    workflow = template.copy()
    workflow["id"] = workflow_id
    workflow["name"] = workflow_name
    workflow["description"] = description or "Standard workflow with safety checks before and after processing"
    
    # Only add inactive field if workflow is inactive
    if inactive:
        workflow["inactive"] = True
    
    # Create sandwich pattern
    steps = ["injection_check_agent", "policy_check_agent"]
    
    # Add central agent(s)
    if agents:
        for agent in agents:
            steps.append(agent)
    else:
        steps.append(None)  # Placeholder to be replaced at runtime
        
    # Add final compliance check
    steps.append("content_compliance_agent")
    
    workflow["steps"] = steps
    
    # Update metadata
    workflow["metadata"]["created_at"] = today
    workflow["metadata"]["updated_at"] = today
    workflow["metadata"]["notes"] = "Sandwich pattern with safety checks before and after processing"
    
    # Write to file
    with open(output_path, "w") as f:
        json.dump(workflow, f, indent=2)
    
    logger.info(f"Generated sandwich workflow file: {output_path}")


def generate_loop_workflow(
    template: Dict[str, Any],
    output_path: str,
    workflow_id: str,
    workflow_name: str,
    description: str,
    agents: List[str],
    inactive: bool
) -> None:
    """Generate a workflow with loop directive."""
    # Get current date
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Create base workflow
    workflow = template.copy()
    workflow["id"] = workflow_id
    workflow["name"] = workflow_name
    workflow["description"] = description or "Workflow with loop for iterative processing"
    
    # Only add inactive field if workflow is inactive
    if inactive:
        workflow["inactive"] = True
    
    # Create steps with loop
    if len(agents) >= 2:
        loop_agents = agents
    else:
        loop_agents = ["query_generator", "query_executor", "result_evaluator"]
        
    loop_directive = {
        "loop": {
            "condition_key": "needs_more_results",
            "steps": loop_agents,
            "max_iterations": 5
        }
    }
    
    workflow["steps"] = [loop_directive]
    
    # Update metadata
    workflow["metadata"]["created_at"] = today
    workflow["metadata"]["updated_at"] = today
    workflow["metadata"]["notes"] = "Contains loop directive for iterative processing"
    
    # Write to file
    with open(output_path, "w") as f:
        json.dump(workflow, f, indent=2)
    
    logger.info(f"Generated loop workflow file: {output_path}")


def generate_workflow(
    workflow_id: str,
    workflow_name: str,
    workflow_type: str = "simple",
    description: str = None,
    agents: List[str] = None,
    inactive: bool = False
) -> None:
    """Generate workflow files based on type."""
    # Setup paths
    backend_dir = Path(__file__).resolve().parents[2]
    templates_dir = backend_dir / "src" / "registries" / "workflows" / "templates"
    workflows_dir = backend_dir / "src" / "registries" / "workflows"
    
    # Format workflow ID
    workflow_id = workflow_id.upper()
    if not workflow_id.endswith("_WORKFLOW"):
        workflow_id += "_WORKFLOW"
        
    # Log info
    logger.info(f"Generating new workflow: {workflow_name} (ID: {workflow_id}, Type: {workflow_type})")
    
    # Set template and output paths
    template_path = templates_dir / "workflow_template.json"
    output_path = workflows_dir / f"{workflow_id}.json"
    
    # Load base template
    template = load_template(str(template_path))
    
    # Generate appropriate workflow type
    if workflow_type == "sandwich":
        generate_sandwich_workflow(
            template,
            str(output_path),
            workflow_id,
            workflow_name,
            description,
            agents or [],
            inactive
        )
    elif workflow_type == "loop":
        generate_loop_workflow(
            template,
            str(output_path),
            workflow_id,
            workflow_name,
            description,
            agents or [],
            inactive
        )
    else:  # simple
        generate_workflow_file(
            template,
            str(output_path),
            workflow_id,
            workflow_name,
            description or f"Simple workflow for {workflow_name.lower()}",
            agents or [],
            inactive
        )
    
    # Print completion message
    logger.info("\nWorkflow generation complete!")
    logger.info(f"Workflow file: {output_path}")
    logger.info("\nNext steps:")
    logger.info("1. Review and update the workflow file as needed")
    logger.info("2. Test the workflow with the WorkflowManager")
    if workflow_type == "sandwich":
        logger.info("3. If using a placeholder (null) step, ensure it's replaced at runtime")
    elif workflow_type == "loop":
        logger.info("3. Review the loop condition and max iterations settings")


def main() -> None:
    """Main entry point."""
    args = parse_arguments()
    
    if args.workflow and args.id and args.name:
        inactive = args.inactive
        generate_workflow(
            args.id, 
            args.name,
            args.type,
            args.description,
            args.agents,
            inactive
        )
    else:
        logger.error("Invalid arguments. Use --workflow --id <ID> --name <name>")


if __name__ == "__main__":
    main()
