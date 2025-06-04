# Agent Workflow Registry

This directory contains declarative definitions of agent workflows.  Workflows describe the sequence and control flow of agents for different use cases.  By externalizing workflows you gain:

- **Configurable Pipelines**: Add, remove, or reorder agents without code changes.
- **Nesting & Reuse**: Sub-workflows let you compose complex pipelines from simpler ones.
- **Looping & Conditional Logic**: Define loops to repeat steps based on metadata flags.

## File Structure

Each workflow is defined in its own JSON file named `<WORKFLOW_ID>.json` under this folder.

```
workflows/
├── BASIC_TEST_WORKFLOW.json
├── GRAPH_RAG_WORKFLOW.json
├── COMPLIANCE_SANDWICH_WORKFLOW.json
└── README.md       ← this document
```

## Workflow Schema

```json
{
  "steps": [ <step1>, <step2>, ... ]
}
```

- **steps**: an ordered list where each element is one of:
  1. **Agent ID** (string): runs a single agent, e.g.:
     ```json
     "simple_test_agent"
     ```
  2. **Sub-workflow** (object): inline reference to another workflow
     ```json
     { "sub_workflow": "OTHER_WORKFLOW_ID" }
     ```
  3. **Loop directive** (object): repeat a block until a metadata key flips
     ```json
     {
       "loop": {
         "condition_key": "needs_more_results",
         "steps": ["query_generator","query_runner","result_evaluator"],
         "max_iterations": 5               
       }
     }
     ```

> **Note**: Loops are optional and supported by the `WorkflowManager` executor.  If your use case doesn’t need dynamic repetition, omit loop directives.

## Getting Started

1. Instantiate:
   ```python
   from src.agent_system.core.workflow_manager import WorkflowManager
   
   registry_dir = os.path.join(BASE_DIR, 'src/registries/workflows')
   wf_mgr = WorkflowManager(registry_dir)
   ```

2. List workflows:
   ```python
   wf_mgr._workflows.keys()  # set of available WORKFLOW_IDs
   ```

3. Inspect steps:
   ```python
   raw_steps = wf_mgr.get_steps('BASIC_TEST_WORKFLOW')
   flat = wf_mgr.flatten_steps('BASIC_TEST_WORKFLOW')
   ```

4. Execution is driven by your `AgentManager`.  You can pass the desired `workflow_id` to route through agents dynamically.

## Example: BASIC_TEST_WORKFLOW.json
A minimal workflow that runs the `simple_test_agent`, used for sanity-checks and smoke tests.
```json
{
  "steps": [
    "simple_test_agent"
  ]
}
```

## Adding New Workflows

1. Copy `BASIC_TEST_WORKFLOW.json` to `<MY_WORKFLOW_ID>.json`.
2. Update `steps` array to your desired agent sequence.
3. Use `sub_workflow` or `loop` directives to compose or repeat.
4. No code changes required—just add your JSON, and restart the service.
