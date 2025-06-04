# PostgreSQL Database for Dengue Agents

This document describes how to set up and configure the PostgreSQL database used for storing chat history and agent state in the dengue-agents-summit-2025 project.

## Database Details

The PostgreSQL database runs in OpenShift in the `chat-history` project and is configured with the following parameters:

- **Username**: chathistory
- **Database Name**: chat-history
- **Port**: 5432
- **Internal Service Name**: postgresql.chat-history.svc.cluster.local

## Deploying the PostgreSQL Database to OpenShift

If you need to redeploy the database, you can use the following commands:

```bash
# Create a new project (if it doesn't exist)
oc new-project chat-history

# Deploy PostgreSQL using the Red Hat template
oc new-app \
  --template=postgresql-persistent \
  --param=POSTGRESQL_USER=chathistory \
  --param=POSTGRESQL_PASSWORD=ChatHistory87b! \
  --param=POSTGRESQL_DATABASE=chat-history \
  --param=VOLUME_CAPACITY=1Gi

# Verify the deployment
oc get pods -n chat-history
oc get services -n chat-history
```

## Connecting from the Dengue Agents Application

In the application code, the database connection is configured using environment variables:

```
POSTGRESQL_USERNAME=chathistory
POSTGRESQL_PASSWORD=ChatHistory87b!
POSTGRESQL_DB=chat-history
POSTGRESQL_ROUTE=postgresql.chat-history.svc.cluster.local
POSTGRESQL_PORT=5432
```

These values are used in the SQLAlchemy database connection string in the format:
```
postgresql://{username}:{password}@{host}:{port}/{database}
```

## Database Schema

The database schema includes the following tables:

1. **Users** - Stores user information
2. **Sessions** - Stores chat sessions
3. **Messages** - Stores conversation history
4. **AgentTransitions** - Tracks agent processing events

## Security Considerations

For production deployment:
1. Use OpenShift Secrets to manage database credentials
2. Consider implementing database connection pooling
3. Set up regular database backups
4. Configure proper resource limits for the database pod
