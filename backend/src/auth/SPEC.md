# Authentication and Authorization System Specification

## Overview

This document outlines the design and implementation of a centralized authentication and authorization system for agent-tool interactions. The system follows these key design principles:

1. **Centralized Authentication**: All tool usage must go through the BaseAgent's authentication mechanisms
2. **Permission-Based Authorization**: Agents can only use tools they have explicit permission to access
3. **Modular Design**: Authentication providers can be swapped based on environment (development vs. production)
4. **Minimal Dependency**: Local development requires minimal external dependencies
5. **Production Ready**: Solution must be compatible with OpenShift for production deployment

## Architectural Components

### 1. BaseAgent Enhancements

We've already implemented initial modifications to the BaseAgent class to support centralized tool usage:

- Added `use_tool()` method that all agents must use to access tools
- Implemented permission checking via the existing registry system
- Added tool instantiation and caching for performance
- Created placeholders for authentication token management

### 2. Auth Adapter System

We will implement a modular authentication adapter system consisting of:

- `AuthAdapter` abstract base class defining the authentication interface
- Concrete implementations for different environments:
  - `LocalJwtAuthAdapter` for development (simple JWT tokens)
  - `KeycloakAuthAdapter` for production (Keycloak integration)
- Factory pattern to create the appropriate adapter based on configuration

### 3. Token Management

- Tokens will identify both the agent and its permissions
- Tokens will be passed to tools during instantiation and execution
- Tools will verify token validity before execution
- Token lifecycle will be managed by the authentication provider

### 4. Keycloak Integration

For production, we'll use Keycloak as our authentication provider:

- Deploy Keycloak using Podman with Red Hat UBI base image
- Configure realms, clients, and roles for agent-tool permissions
- Implement Python client for Keycloak integration
- Define RBAC (Role-Based Access Control) for tools

## Implementation Details

### Directory Structure

```
backend/src/
├── auth/
│   ├── __init__.py
│   ├── adapter/
│   │   ├── __init__.py
│   │   ├── base.py             # AuthAdapter abstract base class
│   │   ├── jwt_adapter.py      # JWT adapter for local development
│   │   └── keycloak_adapter.py # Keycloak adapter for production
│   ├── factory.py              # Auth adapter factory
│   ├── models.py               # Data models for auth tokens
│   ├── constants.py            # Auth-related constants
│   └── utils.py                # Utility functions
├── agent_system/
│   └── core/
│       └── base_agent.py       # Already modified for centralized tool usage
└── tools/
    └── base_tool.py            # To be modified for token verification
```

### Authentication Flow

1. Agent requests to use a tool via `use_tool()` method
2. BaseAgent obtains an authentication token from the current AuthAdapter
3. BaseAgent verifies permissions using the registry system
4. BaseAgent passes the token to the tool during execution
5. Tool verifies the token before performing its operation
6. Results are returned to the agent

### Token Structure

JWT tokens will have the following structure:

```json
{
  "iss": "dengue-agents-auth",
  "sub": "<agent_id>",
  "iat": 1589188251,
  "exp": 1589191851,
  "permissions": [
    "tool:schema_tool:use",
    "tool:dengue_data_tool:use"
  ]
}
```

### Keycloak Configuration

For Keycloak deployment, we will:

1. Use Red Hat UBI 9 as the base image
2. Configure a dedicated realm for agent-tool interactions
3. Create clients representing the agent system
4. Define roles corresponding to tool permissions
5. Map agents to appropriate roles

## Local Development Setup

For local development:

1. Simple JWT-based authentication requiring minimal dependencies
2. Permissions stored in a local configuration file
3. No need for external services during development

## Production Deployment

For production on OpenShift:

1. Deploy Keycloak using provided templates
2. Configure TLS for secure communication
3. Use OpenShift secrets for credential management
4. Integrate with existing identity providers if needed

## Security Considerations

1. **Token Security**: All tokens must be securely generated and verified
2. **Least Privilege**: Agents should have access only to the tools they need
3. **Token Expiration**: Tokens should have a limited lifetime
4. **Rate Limiting**: Consider implementing rate limiting for tool usage
5. **Audit Logging**: All tool usage must be logged for audit purposes

## Compatibility

- Python 3.11+ compatibility
- OCI-compliant containers
- Red Hat UBI base images
- OpenShift deployment support
