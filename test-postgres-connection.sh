#!/bin/bash

echo "Testing PostgreSQL connection..."
echo "================================"
echo ""
echo "Configuration from .env:"
echo "  Host: localhost (via docker)"
echo "  Port: ${POSTGRES_HOST_PORT:-5432}"
echo "  Database: ${POSTGRES_DB:-openwebui}"
echo "  User: ${POSTGRES_USER:-postgres}"
echo "  Password: ${POSTGRES_PASSWORD:-postgres}"
echo ""
echo "Checking if PostgreSQL port is listening..."

if command -v docker &> /dev/null; then
    echo ""
    echo "Docker containers status:"
    docker ps --filter "name=beagle-postgres" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""

    echo "Testing connection from inside Docker network:"
    docker exec beagle-postgres pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-openwebui}
    echo ""

    echo "Testing connection from host (this is what pgAdmin uses):"
    docker exec beagle-postgres psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-openwebui} -c "SELECT version();"
else
    echo "Docker command not available in this environment"
    echo "Please run this script where docker is available"
fi

echo ""
echo "================================"
echo "pgAdmin Connection Settings:"
echo "  Host: localhost"
echo "  Port: 5432 (make sure this is forwarded in VSCode)"
echo "  Database: openwebui"
echo "  Username: postgres"
echo "  Password: postgres"
echo "================================"
