# Keycloak Authentication System

This directory contains the configuration for the Keycloak authentication system used for agent-tool authorization in production environments.

## Local Development Setup

For local development and testing, you can run Keycloak in a container using Podman:

```bash
# From this directory
podman build -t dengue-agents-keycloak -f Containerfile .
podman run -p 8080:8080 dengue-agents-keycloak
```

Alternatively, use the provided `run_keycloak.sh` script:

```bash
./run_keycloak.sh
```

Once running, you can access the Keycloak admin console at:
http://localhost:8080/admin/

Login with:
- Username: `admin`
- Password: `admin`

## Configuration for Agent-Tool Authentication

After Keycloak is running, you need to:

1. Create a new realm called `dengue-agents`
2. Create a client for the agent system:
   - Client ID: `agent-system`
   - Client Protocol: `openid-connect`
   - Access Type: `confidential`
   - Service Accounts Enabled: `ON`

3. Create roles for tool permissions:
   - For each tool, create a role named `tool_TOOLNAME_use`
   - Example: `tool_schema_tool_use`

4. Create groups for agents:
   - Create a group for each agent type
   - Assign appropriate roles to each group

5. Create users for agents:
   - Create a user for each agent
   - Assign to appropriate groups

## Production Deployment

For production deployment on OpenShift:

1. Use the Red Hat SSO Operator (based on Keycloak)
2. Configure secure TLS endpoints
3. Use OpenShift secrets for credentials
4. Set up proper RBAC

## Environment Variables

The following environment variables can be set to configure Keycloak authentication:

- `AUTH_PROVIDER=KEYCLOAK` - Set to use Keycloak authentication
- `KEYCLOAK_SERVER_URL` - URL of the Keycloak server
- `KEYCLOAK_REALM` - Realm name
- `KEYCLOAK_CLIENT_ID` - Client ID
- `KEYCLOAK_CLIENT_SECRET` - Client secret
- `KEYCLOAK_VERIFY_SSL` - Whether to verify SSL certificates (`true`/`false`)
