#!/bin/bash

echo "========================================="
echo "WebSocket & Redis Configuration Diagnostics"
echo "========================================="
echo ""

# Check open-webui logs for WebSocket/Redis errors
echo "1. Checking open-webui logs for WebSocket/Redis errors..."
echo "---------------------------------------------"
docker logs open-webui --tail 50 | grep -i -E "(websocket|redis|socket\.io|connection)" || echo "  No WebSocket/Redis related logs found"
echo "---------------------------------------------"
echo ""

# Check Redis connectivity from open-webui container
echo "2. Testing Redis connection from open-webui container..."
docker exec open-webui sh -c 'command -v redis-cli >/dev/null 2>&1 && redis-cli -h beagle-redis -p 6379 -a ${REDIS_PASSWORD:-mypassword} ping || echo "redis-cli not available in container"' 2>&1
echo ""

# Check environment variables in open-webui
echo "3. Checking WebSocket-related environment variables in open-webui..."
docker exec open-webui env | grep -E "(WEBSOCKET|REDIS_URL)" | sort
echo ""

# Check Redis container status
echo "4. Checking Redis container status..."
docker ps --filter "name=beagle-redis" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Test Redis connection
echo "5. Testing Redis from beagle-redis container..."
docker exec beagle-redis redis-cli -a "${REDIS_PASSWORD:-mypassword}" ping
echo ""

# Check Redis connection info
echo "6. Checking Redis client connections..."
docker exec beagle-redis redis-cli -a "${REDIS_PASSWORD:-mypassword}" CLIENT LIST | head -10
echo ""

# Check if Redis has any pub/sub channels (used by WebSockets)
echo "7. Checking Redis pub/sub channels..."
docker exec beagle-redis redis-cli -a "${REDIS_PASSWORD:-mypassword}" PUBSUB CHANNELS
echo ""

# Check open-webui environment for socket.io
echo "8. Checking full open-webui logs (last 100 lines)..."
echo "---------------------------------------------"
docker logs open-webui --tail 100
echo "---------------------------------------------"
echo ""

echo "========================================="
echo "Common Issues & Solutions:"
echo "========================================="
echo "1. REDIS_URL format mismatch"
echo "   - Check if REDIS_URL uses correct format"
echo "   - Should be: redis://[username]:password@host:port[/db]"
echo ""
echo "2. Redis authentication failure"
echo "   - Verify REDIS_PASSWORD matches in .env and docker-compose"
echo ""
echo "3. Container networking"
echo "   - Ensure open-webui can reach beagle-redis"
echo "   - Use service name 'beagle-redis' not 'redis'"
echo ""
echo "4. Missing WebSocket dependencies"
echo "   - Check if python-socketio is installed in open-webui"
echo "========================================="
