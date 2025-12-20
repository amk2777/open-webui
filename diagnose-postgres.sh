#!/bin/bash

echo "========================================="
echo "PostgreSQL Connection Diagnostics"
echo "========================================="
echo ""

# Check if container is running
echo "1. Checking if beagle-postgres container is running..."
docker ps --filter "name=beagle-postgres" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Check container logs for errors
echo "2. Checking PostgreSQL logs (last 30 lines)..."
echo "---------------------------------------------"
docker logs beagle-postgres --tail 30
echo "---------------------------------------------"
echo ""

# Check what port is actually exposed
echo "3. Checking exposed ports..."
docker port beagle-postgres
echo ""

# Try to connect as postgres superuser
echo "4. Trying to connect as postgres user..."
docker exec beagle-postgres psql -U postgres -l 2>&1 | head -10
echo ""

# List all database roles/users
echo "5. Attempting to list all database roles..."
docker exec beagle-postgres psql -U postgres -c "\du" 2>&1 || \
  docker exec beagle-postgres psql -U beagle -c "\du" 2>&1 || \
  echo "  ✗ Could not list database roles with either postgres or beagle user"
echo ""

# Check PostgreSQL configuration
echo "6. Checking pg_hba.conf (authentication settings)..."
docker exec beagle-postgres cat /var/lib/postgresql/data/pg_hba.conf 2>&1 | grep -v "^#" | grep -v "^$"
echo ""

# Check what databases exist
echo "7. Attempting to list databases..."
docker exec beagle-postgres psql -U postgres -c "\l" 2>&1 || \
  docker exec beagle-postgres psql -U beagle -c "\l" 2>&1 || \
  echo "  ✗ Could not list databases"
echo ""

# Check environment variables in container
echo "8. Checking PostgreSQL environment variables in container..."
docker exec beagle-postgres env | grep POSTGRES
echo ""

echo "========================================="
echo "Diagnostic complete!"
echo ""
echo "Next steps:"
echo "  - If you see errors in the logs, that indicates the problem"
echo "  - If no 'beagle' user exists, run ./reset-postgres.sh"
echo "  - If the port mapping shows 5434, use that port in pgAdmin"
echo "========================================="
