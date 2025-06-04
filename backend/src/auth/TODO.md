# Authentication System Implementation TODO List

## Completed Tasks

- [x] Create centralized tool usage method in BaseAgent
  - [x] Add `use_tool()` method to BaseAgent class
  - [x] Implement tool instantiation and caching
  - [x] Add permission verification using registry
  - [x] Add placeholder for authentication token

- [x] Set up initial directory structure
  - [x] Create `/backend/src/auth/` directory
  - [x] Create specification document (SPEC.md)
  - [x] Create todo list (TODO.md)

## Pending Tasks

### Core Authentication Framework

- [ ] Create abstract AuthAdapter base class
  - [ ] Define `get_token()` method interface
  - [ ] Define `verify_access()` method interface
  - [ ] Define `verify_token()` method interface

- [ ] Create Auth Factory
  - [ ] Implement factory for getting appropriate auth adapter
  - [ ] Add environment-based adapter selection
  - [ ] Add configuration loading

### JWT Implementation for Local Development

- [ ] Implement LocalJwtAuthAdapter
  - [ ] Create JWT token generation logic
  - [ ] Implement token validation
  - [ ] Support permission checking
  - [ ] Add token caching for performance

- [ ] Create local permission configuration
  - [ ] Define YAML format for permissions
  - [ ] Implement configuration loading
  - [ ] Add permission verification logic

### Keycloak Integration for Production

- [ ] Create Keycloak AuthAdapter
  - [ ] Implement token acquisition from Keycloak
  - [ ] Add token validation using Keycloak API
  - [ ] Support role-based permission checking
  - [ ] Implement token refresh logic

- [ ] Create Keycloak Containerfile
  - [ ] Use Red Hat UBI base image
  - [ ] Configure for agent-tool authentication
  - [ ] Add initialization scripts

- [ ] Create Keycloak deployment configuration
  - [ ] Create OpenShift deployment templates
  - [ ] Define resource requirements
  - [ ] Configure TLS and security settings

### Tool Authentication Integration

- [ ] Modify BaseTool class
  - [ ] Add token verification
  - [ ] Implement permission checking
  - [ ] Add audit logging for tool usage

- [ ] Update existing tools
  - [ ] Ensure all tools inherit from BaseTool
  - [ ] Add authentication to tool initialization
  - [ ] Test with authentication enabled

### Agent Integration

- [ ] Update BaseAgent token management
  - [ ] Implement token acquisition and caching
  - [ ] Add token refresh logic
  - [ ] Support token invalidation

- [ ] Update agent implementations
  - [ ] Migrate direct tool usage to use_tool() method
  - [ ] Test with authentication enabled
  - [ ] Update documentation

### Testing

- [ ] Create unit tests for auth adapters
  - [ ] Test JWT adapter functionality
  - [ ] Test Keycloak adapter with mocks
  - [ ] Test permission verification

- [ ] Create integration tests
  - [ ] Test end-to-end authentication flow
  - [ ] Test performance with caching
  - [ ] Test error handling and edge cases

### Documentation

- [ ] Create user documentation
  - [ ] Document local development setup
  - [ ] Document production deployment
  - [ ] Document configuration options

- [ ] Update code documentation
  - [ ] Add docstrings to all new classes and methods
  - [ ] Document authentication flow
  - [ ] Update existing docstrings

## Installation Tasks

- [ ] Install required packages:
  ```bash
  # Activate the virtual environment
  source /path/to/venv/bin/activate
  
  # Install JWT dependencies
  pip install pyjwt cryptography
  
  # Install Keycloak client
  pip install python-keycloak
  ```

## Local Development Setup

- [ ] Create local Keycloak instance using Podman:
  ```bash
  podman run -p 8080:8080 \
    -e KEYCLOAK_ADMIN=admin \
    -e KEYCLOAK_ADMIN_PASSWORD=admin \
    registry.access.redhat.com/ubi9/keycloak:latest \
    start-dev
  ```

- [ ] Configure Keycloak for development:
  - [ ] Create "dengue-agents" realm
  - [ ] Create client for agent system
  - [ ] Define roles for tool permissions
  - [ ] Create test users/agents

## Next Steps

1. Start with implementing the core authentication framework
2. Build and test JWT adapter for local development
3. Update the BaseAgent to use the auth factory
4. Modify BaseTool to verify authentication tokens
5. Create Keycloak container for local testing
6. Implement Keycloak adapter for production
