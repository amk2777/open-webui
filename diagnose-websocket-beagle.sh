#!/bin/bash

echo "========================================="
echo "WebSocket & Redis Diagnostics (Beagle)"
echo "========================================="
echo ""

FRONTEND_CONTAINER="beagle-frontend"
REDIS_CONTAINER="beagle-redis"

# Check frontend container status
echo "1. Checking ${FRONTEND_CONTAINER} container status..."
docker ps --filter "name=${FRONTEND_CONTAINER}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Check frontend logs for WebSocket/Redis errors
echo "2. Checking ${FRONTEND_CONTAINER} logs for WebSocket/Redis errors..."
echo "---------------------------------------------"
docker logs ${FRONTEND_CONTAINER} --tail 100 | grep -i -E "(websocket|redis|socket\.io|connection|error)" || echo "  No WebSocket/Redis errors found (could be good!)"
echo "---------------------------------------------"
echo ""

# Check environment variables in frontend
echo "3. Checking WebSocket-related environment variables in ${FRONTEND_CONTAINER}..."
docker exec ${FRONTEND_CONTAINER} env | grep -E "(WEBSOCKET|REDIS_URL)" | sort
echo ""

# Check Redis container status
echo "4. Checking ${REDIS_CONTAINER} container status..."
docker ps --filter "name=${REDIS_CONTAINER}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Test Redis connection from frontend
echo "5. Testing Redis connection from ${FRONTEND_CONTAINER}..."
docker exec ${FRONTEND_CONTAINER} sh -c 'nc -zv beagle-redis 6379 2>&1' || echo "  ⚠ Network connectivity test failed"
echo ""

# Test Redis ping
echo "6. Testing Redis ping from ${REDIS_CONTAINER}..."
docker exec ${REDIS_CONTAINER} redis-cli -a "${REDIS_PASSWORD:-mypassword}" ping
echo ""

# Check Redis connection info
echo "7. Checking Redis client connections..."
CONN_COUNT=$(docker exec ${REDIS_CONTAINER} redis-cli -a "${REDIS_PASSWORD:-mypassword}" CLIENT LIST 2>/dev/null | wc -l)
echo "  Total Redis connections: ${CONN_COUNT}"
docker exec ${REDIS_CONTAINER} redis-cli -a "${REDIS_PASSWORD:-mypassword}" CLIENT LIST | grep -i "name=" || echo "  No named clients found"
echo ""

# Check if Redis has any pub/sub channels (used by WebSockets)
echo "8. Checking Redis pub/sub channels (WebSocket uses these)..."
CHANNELS=$(docker exec ${REDIS_CONTAINER} redis-cli -a "${REDIS_PASSWORD:-mypassword}" PUBSUB CHANNELS)
if [ -z "$CHANNELS" ]; then
    echo "  No active pub/sub channels (WebSocket may not be connected yet)"
else
    echo "$CHANNELS"
fi
echo ""

# Check frontend health
echo "9. Checking ${FRONTEND_CONTAINER} health status..."
docker inspect ${FRONTEND_CONTAINER} --format='{{.State.Health.Status}}' 2>/dev/null || echo "  No health check configured"
echo ""

# Check latest frontend logs
echo "10. Latest ${FRONTEND_CONTAINER} logs (last 30 lines)..."
echo "---------------------------------------------"
docker logs ${FRONTEND_CONTAINER} --tail 30
echo "---------------------------------------------"
echo ""

# Test if frontend can resolve beagle-redis hostname
echo "11. Testing DNS resolution from ${FRONTEND_CONTAINER}..."
docker exec ${FRONTEND_CONTAINER} sh -c 'getent hosts beagle-redis 2>&1' || echo "  ⚠ DNS resolution failed"
echo ""

echo "========================================="
echo "Configuration Summary:"
echo "========================================="
echo "Redis URL should be:"
echo "  redis://:mypassword@beagle-redis:6379/0"
echo ""
echo "Check if the /0 database number is present!"
echo ""
echo "Common Issues:"
echo "  1. Missing /0 in REDIS_URL"
echo "  2. Wrong container name (use 'beagle-redis' not 'redis')"
echo "  3. Password mismatch"
echo "  4. Network connectivity issues"
echo "========================================="
