# Agent System Test Suite

This directory contains test scripts for validating the agent system functionality, from individual components to complete workflows.

## Test Philosophy

The test suite follows these core principles:

1. **Start with Critical Dependencies**: Test connectivity to required endpoints first to ensure failures in workflows are due to implementation issues, not connectivity problems.

2. **Isolate Components**: Test individual components before testing their interactions.

3. **Simple → Complex**: Start with the simplest workflows and build up to more complex scenarios.

4. **Complete Validation**: Test the full path through the system, ensuring data flows correctly from input to output.

## Test Files

### Critical Dependency Tests

- **`test_endpoints.py`** - Tests connectivity to all required external endpoints (LLM APIs, Knowledge Graph API)
- **`test_llm_connection.py`** - Tests detailed LLM API connectivity and response validation
- **`test_graph_connection.py`** - Tests Neo4j graph database connectivity and basic queries

### Workflow Tests

- **`test_basic_workflow.py`** - Tests the simplest end-to-end workflow through the system:
  - Safety checks → Router → Assistant → Compliance check

### Combined Test Runner

- **`run_all_tests.py`** - Master script that runs all tests in the appropriate order

## Running the Tests

### Run All Tests

```bash
python run_all_tests.py
```

### Run Specific Tests

```bash
# Test only endpoints
python test_endpoints.py

# Test only graph database
python test_graph_connection.py

# Test only LLM connections
python test_llm_connection.py

# Test only basic workflow
python test_basic_workflow.py
```

### Skip Specific Tests in Full Suite

```bash
# Skip endpoint tests
python run_all_tests.py --skip-endpoints

# Skip graph database tests
python run_all_tests.py --skip-graph

# Skip LLM tests
python run_all_tests.py --skip-llm

# Skip workflow tests
python run_all_tests.py --skip-workflow
```

## Test Requirements

To run the tests, you need:

1. Python 3.8+ with required packages (see requirements.txt)
2. Environment variables configured (see .env.example)
3. Access to required APIs and services:
   - Granite API endpoints (Instruct, Guardian)
   - Mixtral API endpoint
   - Neo4j graph database
   - Knowledge Graph API

## Troubleshooting

If tests fail, check the following:

1. **API Connectivity**: Ensure all required API endpoints are accessible and that API keys are valid
2. **Network Access**: Check for any firewall or proxy issues that might block connections
3. **Environment Configuration**: Verify that all required environment variables are set correctly
4. **Service Status**: Ensure that external services are running and responding to requests

## Adding New Tests

When adding new tests:

1. Follow the existing pattern of test scripts
2. Start with dependency validation
3. Add detailed logging and error messages
4. Make tests self-contained when possible
5. Update the master test runner if necessary
