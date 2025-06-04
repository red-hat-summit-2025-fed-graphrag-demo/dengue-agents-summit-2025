#!/bin/bash
# Script to build and run Keycloak for local development

# Build the Keycloak container image
echo "Building Keycloak container image..."
podman build -t dengue-agents-keycloak -f Containerfile .

# Run the Keycloak container
echo "Starting Keycloak on http://localhost:8080"
echo "Admin console: http://localhost:8080/admin/"
echo "Username: admin"
echo "Password: admin"
echo "Press Ctrl+C to stop the container"

podman run --rm -p 8080:8080 dengue-agents-keycloak
