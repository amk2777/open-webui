#!/bin/bash

echo "========================================="
echo "Redis Connection Test & Diagnostics"
echo "========================================="
echo ""

# Check if container is running
echo "1. Checking if beagle-redis container is running..."
docker ps --filter "name=beagle-redis" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Check port mapping
echo "2. Checking Redis port mapping..."
docker port beagle-redis
echo ""

# Check environment variables
echo "3. Checking Redis environment variables..."
docker exec beagle-redis env | grep REDIS
echo ""

# Test Redis connection from inside container
echo "4. Testing Redis connection (ping)..."
docker exec beagle-redis redis-cli -a "${REDIS_PASSWORD:-mypassword}" ping
echo ""

# Get Redis info
echo "5. Getting Redis server info..."
docker exec beagle-redis redis-cli -a "${REDIS_PASSWORD:-mypassword}" INFO server | head -20
echo ""

# Check Redis keys (to see if data exists)
echo "6. Checking if Redis has any keys..."
KEY_COUNT=$(docker exec beagle-redis redis-cli -a "${REDIS_PASSWORD:-mypassword}" DBSIZE)
echo "  Keys in database: $KEY_COUNT"
echo ""

# List some keys if they exist
if [[ "$KEY_COUNT" != *"0"* ]]; then
    echo "7. Listing first 10 keys:"
    docker exec beagle-redis redis-cli -a "${REDIS_PASSWORD:-mypassword}" KEYS "*" | head -10
    echo ""
fi

# Check if open-webui is connected to Redis
echo "8. Checking active Redis connections..."
docker exec beagle-redis redis-cli -a "${REDIS_PASSWORD:-mypassword}" CLIENT LIST | grep -c "name=" || echo "  No named clients connected"
echo ""

# Check Redis logs
echo "9. Checking Redis logs (last 20 lines)..."
echo "---------------------------------------------"
docker logs beagle-redis --tail 20
echo "---------------------------------------------"
echo ""

echo "========================================="
echo "Another Redis Desktop Manager Settings:"
echo "========================================="
echo "  Name: Beagle Redis"
echo "  Host: 127.0.0.1 (or localhost)"
echo "  Port: ${REDIS_HOST_PORT:-6379}"
echo "  Auth: ${REDIS_PASSWORD:-mypassword}"
echo "  Username: (leave empty, or try 'default')"
echo "  Database: 0"
echo ""
echo "IMPORTANT: Make sure VSCode is forwarding port ${REDIS_HOST_PORT:-6379}"
echo "========================================="
