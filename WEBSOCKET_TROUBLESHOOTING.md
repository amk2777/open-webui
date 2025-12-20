# WebSocket Connection Troubleshooting Guide

## Common Error

```
WebSocket connection to 'ws://localhost:62149/ws/socket.io/?EIO=4&transport=websocket' failed
```

## Root Cause

This error occurs when Open WebUI cannot establish WebSocket connections, typically due to Redis configuration issues. WebSocket support in Open WebUI requires Redis for pub/sub messaging between server instances.

## Fixed Issues

### 1. Redis URL Host Mismatch ✅
**Problem**: `.env.example` used `@redis` but the service name is `beagle-redis`

**Before**:
```bash
REDIS_URL=redis://default:mypassword@redis:6379/0  # Wrong host!
```

**After**:
```yaml
# In docker-compose.min.yaml
REDIS_URL=redis://:${REDIS_PASSWORD}@beagle-redis:6379/0
```

### 2. Redis URL Format Inconsistency ✅
**Problem**: Mixed username/password formats between `.env` and `docker-compose`

**Fixed**: Standardized to password-only auth (no username required)
```
redis://:mypassword@beagle-redis:6379/0
```

### 3. Database Number Missing ✅
**Problem**: Redis URL didn't include `/0` database number

**Fixed**: Added `/0` to specify Redis database 0

## Configuration

### Correct Redis URL Format

```
redis://[username]:password@host:port/database
```

For this setup:
- **Username**: (empty) - Redis doesn't require username by default
- **Password**: `${REDIS_PASSWORD}` from `.env`
- **Host**: `beagle-redis` (container name in Docker network)
- **Port**: `6379` (internal Redis port)
- **Database**: `0` (default Redis database)

### Example `.env` Configuration

```bash
# Minimal Redis configuration
REDIS_HOST_PORT=6379
REDIS_PASSWORD=mypassword

# Do NOT set REDIS_URL - it's auto-constructed in docker-compose
```

### Docker Compose Configuration

```yaml
environment:
  - REDIS_URL=redis://:${REDIS_PASSWORD}@beagle-redis:6379/0
  - ENABLE_WEBSOCKET_SUPPORT=true
  - WEBSOCKET_MANAGER=redis
  - WEBSOCKET_REDIS_URL=redis://:${REDIS_PASSWORD}@beagle-redis:6379/0
```

## How to Fix

### Step 1: Update Your `.env` File

Make sure your `.env` file has:

```bash
REDIS_HOST_PORT=6379
REDIS_PASSWORD=mypassword
```

**Remove** or **comment out** any `REDIS_URL` variable:
```bash
# REDIS_URL=...  # Let docker-compose handle this
```

### Step 2: Restart Containers

```bash
cd ~/Development/open-webui

# Stop containers
docker compose -f docker-compose.min.yaml down

# Start containers
docker compose -f docker-compose.min.yaml up -d

# Wait for services to be healthy
sleep 10

# Check logs
docker logs open-webui -f
```

### Step 3: Verify WebSocket Connection

1. **Open Browser DevTools** (F12)
2. **Go to Console tab**
3. **Look for**:
   - ✅ No WebSocket errors
   - ✅ `socket.io` connected messages

### Step 4: Run Diagnostics

```bash
./diagnose-websocket.sh
```

This will check:
- Redis connectivity from open-webui
- Environment variables
- Redis pub/sub channels
- Open WebUI logs

## Verification Checklist

- [ ] Redis container is running and healthy
- [ ] `REDIS_PASSWORD` is set in `.env`
- [ ] No `REDIS_URL` override in `.env` (let docker-compose handle it)
- [ ] Open WebUI can ping Redis: `docker exec open-webui sh -c 'nc -zv beagle-redis 6379'`
- [ ] WebSocket environment variables are set correctly
- [ ] No WebSocket errors in browser console

## Common Issues

### Issue 1: "Connection Refused"

**Symptom**: WebSocket fails with "connection refused"

**Solution**:
```bash
# Check if Redis is running
docker ps | grep beagle-redis

# Check Redis logs
docker logs beagle-redis

# Restart Redis
docker restart beagle-redis
```

### Issue 2: "Authentication Failed"

**Symptom**: Redis authentication errors in logs

**Solution**:
```bash
# Verify password matches
docker exec beagle-redis env | grep REDIS_PASSWORD
docker exec open-webui env | grep REDIS

# Should both show same password
```

### Issue 3: "Host Not Found"

**Symptom**: Cannot resolve `beagle-redis`

**Solution**:
```bash
# Check if containers are on same network
docker network inspect open-webui_default

# Verify service name in docker-compose.min.yaml
grep "container_name: beagle-redis" docker-compose.min.yaml
```

### Issue 4: "Port Already in Use"

**Symptom**: Cannot start containers, port conflict

**Solution**:
```bash
# Check what's using port 6379
sudo lsof -i :6379

# Stop conflicting service or change REDIS_HOST_PORT in .env
```

## Testing Redis Connection

### From Open WebUI Container

```bash
# Test network connectivity
docker exec open-webui nc -zv beagle-redis 6379

# Test Redis ping (if redis-cli is available)
docker exec open-webui redis-cli -h beagle-redis -p 6379 -a mypassword ping
```

### From Redis Container

```bash
# Check if Redis is accepting connections
docker exec beagle-redis redis-cli -a mypassword ping

# List connected clients
docker exec beagle-redis redis-cli -a mypassword CLIENT LIST

# Check pub/sub channels (used by WebSockets)
docker exec beagle-redis redis-cli -a mypassword PUBSUB CHANNELS
```

## Expected Behavior

When WebSockets are working correctly:

1. **Browser Console**: No WebSocket connection errors
2. **Open WebUI Logs**: `socketio` connection messages
3. **Redis Logs**: Client connections from open-webui
4. **Features**: Real-time chat updates, collaborative features work

## Still Having Issues?

Run the diagnostic script and share the output:

```bash
./diagnose-websocket.sh > websocket-debug.txt 2>&1
```

Then review `websocket-debug.txt` for:
- Redis connection failures
- Authentication errors
- Network connectivity issues
- Environment variable mismatches
