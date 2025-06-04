"""
Workflow validation tool.

This script validates workflow definitions and checks that all required agents
are available. Use it to ensure workflows are correctly configured.
"""

import os
import sys
import json
import argparse
import asyncio
import logging
from typing import Dict, List, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the project root to the Python path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(parent_dir)

from src.agent_system.core.workflow_manager import WorkflowManager
from src.agent_system.core.workflow_executor_adapter import (
    AgentRegistryAdapter, 
    EnhancedWorkflowExecutor
)
from src.registries.agent_registry import AgentRegistry


async def validate_workflow(workflow_path: str) -> Tuple[bool, List[str]]:
    """
    Validate a workflow definition file.
    
    Args:
        workflow_path: Path to the workflow definition file
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Check if file exists
    if not os.path.isfile(workflow_path):
        errors.append(f"Workflow file not found: {workflow_path}")
        return False, errors
    
    # Check if file is valid JSON
    try:
        with open(workflow_path, 'r') as f:
            workflow_data = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in workflow file: {e}")
        return False, errors
    
    # Check if workflow has required fields
    if 'steps' not in workflow_data:
        errors.append("Workflow is missing 'steps' field")
    elif not isinstance(workflow_data['steps'], list):
        errors.append("Workflow 'steps' must be a list")
    
    # Check if workflow has an ID
    if 'id' not in workflow_data:
        workflow_id = os.path.basename(workflow_path).replace('.json', '')
        logger.warning(f"Workflow is missing 'id' field. Using filename: {workflow_id}")
    else:
        workflow_id = workflow_data['id']
    
    # If we have validation errors at this point, return early
    if errors:
        return False, errors
    
    # Check if all agents are available
    try:
        # Initialize the agent registry
        agent_registry = AgentRegistry()
        available_agents = {agent['id'] for agent in agent_registry.list_agents()}
        
        # Check each step
        for i, step in enumerate(workflow_data['steps']):
            if step is None:
                # None is valid for dynamic placeholders
                continue
                
            if isinstance(step, str):
                # Simple agent ID
                if step not in available_agents:
                    errors.append(f"Agent '{step}' at step {i} is not registered")
            elif isinstance(step, dict):
                # Complex directive
                if 'sub_workflow' in step:
                    # Sub-workflow reference
                    sub_workflow_id = step['sub_workflow']
                    # We would need to validate the sub-workflow here in a full implementation
                    logger.info(f"Found sub-workflow reference to '{sub_workflow_id}' (not validated)")
                elif 'loop' in step:
                    # Loop directive
                    loop_data = step['loop']
                    if 'steps' not in loop_data:
                        errors.append(f"Loop directive at step {i} is missing 'steps' field")
                    elif not isinstance(loop_data['steps'], list):
                        errors.append(f"Loop directive 'steps' at step {i} must be a list")
                    else:
                        # Check loop steps
                        for j, loop_step in enumerate(loop_data['steps']):
                            if isinstance(loop_step, str) and loop_step not in available_agents:
                                errors.append(f"Agent '{loop_step}' in loop at step {i}.{j} is not registered")
                else:
                    errors.append(f"Unknown directive at step {i}: {step}")
            else:
                errors.append(f"Invalid step type at step {i}: {type(step)}")
    
    except Exception as e:
        errors.append(f"Error validating agents: {str(e)}")
    
    return len(errors) == 0, errors


async def validate_all_workflows(workflows_dir: str) -> Dict[str, Any]:
    """
    Validate all workflow definitions in a directory.
    
    Args:
        workflows_dir: Directory containing workflow definition files
        
    Returns:
        Dictionary with validation results
    """
    if not os.path.isdir(workflows_dir):
        return {"error": f"Workflow directory not found: {workflows_dir}"}
    
    results = {}
    
    for filename in os.listdir(workflows_dir):
        if filename.endswith('.json'):
            workflow_path = os.path.join(workflows_dir, filename)
            is_valid, errors = await validate_workflow(workflow_path)
            
            # Try to get workflow ID from file if possible
            try:
                with open(workflow_path, 'r') as f:
                    workflow_data = json.load(f)
                    workflow_id = workflow_data.get('id', filename.replace('.json', ''))
            except:
                workflow_id = filename.replace('.json', '')
            
            results[workflow_id] = {
                "filename": filename,
                "valid": is_valid,
                "errors": errors
            }
    
    return results


async def main():
    """Main entry point for the workflow validation tool."""
    parser = argparse.ArgumentParser(
        description="Validate workflow definition files"
    )
    parser.add_argument(
        'workflow_dir',
        nargs='?',
        default=os.path.join(parent_dir, 'backend/src/registries/workflows'),
        help="Directory containing workflow definitions"
    )
    parser.add_argument(
        '--workflow',
        help="Validate a specific workflow file"
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help="Output results as JSON"
    )
    
    args = parser.parse_args()
    
    # Validate workflows
    if args.workflow:
        is_valid, errors = await validate_workflow(args.workflow)
        if args.json:
            print(json.dumps({
                "valid": is_valid,
                "errors": errors
            }, indent=2))
        else:
            if is_valid:
                print(f"Workflow is valid: {args.workflow}")
            else:
                print(f"Workflow validation failed: {args.workflow}")
                for error in errors:
                    print(f"  - {error}")
    else:
        results = await validate_all_workflows(args.workflow_dir)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"Validation results for workflows in: {args.workflow_dir}")
            for workflow_id, result in results.items():
                status = "VALID" if result["valid"] else "INVALID"
                print(f"{status}: {workflow_id} ({result['filename']})")
                if not result["valid"]:
                    for error in result["errors"]:
                        print(f"  - {error}")


if __name__ == "__main__":
    asyncio.run(main())