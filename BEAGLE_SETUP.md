# Beagle Frontend WebSocket Setup Guide

## The Fix

Your WebSocket connection issues are caused by **missing `/0` database number in Redis URLs**.

### What Needs to Change

In your `docker-compose` file, update the `frontend` service:

**❌ WRONG (Current)**:
```yaml
environment:
  - REDIS_URL=${REDIS_URL:-redis://:${REDIS_PASSWORD}@beagle-redis:6379}
  - WEBSOCKET_REDIS_URL=${REDIS_URL:-redis://:${REDIS_PASSWORD}@beagle-redis:6379}
```

**✅ CORRECT (Fixed)**:
```yaml
environment:
  - REDIS_URL=redis://:${REDIS_PASSWORD}@beagle-redis:6379/0
  - WEBSOCKET_REDIS_URL=redis://:${REDIS_PASSWORD}@beagle-redis:6379/0
```

**Key change**: Added `/0` at the end of both URLs.

## Quick Fix Instructions

### Option 1: Use the Provided docker-compose.beagle.yaml

```bash
cd ~/Development/open-webui

# Stop current containers
docker compose down

# Use the corrected configuration
docker compose -f docker-compose.beagle.yaml up -d

# Wait for services to start
sleep 15

# Run diagnostics
./diagnose-websocket-beagle.sh
```

### Option 2: Manually Update Your Existing docker-compose File

1. **Open your docker-compose file**
2. **Find the `frontend` service**
3. **Update the two Redis URL lines**:
   ```yaml
   - REDIS_URL=redis://:${REDIS_PASSWORD}@beagle-redis:6379/0
   - WEBSOCKET_REDIS_URL=redis://:${REDIS_PASSWORD}@beagle-redis:6379/0
   ```
4. **Save and restart**:
   ```bash
   docker compose down
   docker compose up -d
   ```

## Environment Files

I've created environment files for you in `env/`:

**`env/postgres.env`**:
```env
POSTGRES_USER=beagle
POSTGRES_PASSWORD=beagle_password
POSTGRES_DB=beagle_db
POSTGRES_HOST_PORT=5434
```

**`env/redis.env`**:
```env
REDIS_PASSWORD=mypassword
REDIS_HOST_PORT=6379
```

**Important**: These files are in `.gitignore` for security. Update them with your actual credentials.

## Verification Steps

### 1. Check Container Status
```bash
docker ps | grep beagle
```

Should show:
- ✅ `beagle-frontend` - healthy
- ✅ `beagle-redis` - healthy
- ✅ `beagle-postgres` - healthy

### 2. Run Diagnostics
```bash
./diagnose-websocket-beagle.sh
```

Look for:
- ✅ Redis URL shows `/0` at the end
- ✅ Redis ping responds: `PONG`
- ✅ Frontend can connect to beagle-redis
- ✅ No WebSocket errors in logs

### 3. Check Browser Console
1. Open browser DevTools (F12)
2. Go to Console tab
3. Refresh the page
4. Look for:
   - ✅ No "WebSocket connection failed" errors
   - ✅ Socket.io connection successful messages

### 4. Test WebSocket Functionality
```bash
# Check if frontend has Redis environment variables
docker exec beagle-frontend env | grep REDIS

# Should show:
# REDIS_URL=redis://:mypassword@beagle-redis:6379/0
# WEBSOCKET_REDIS_URL=redis://:mypassword@beagle-redis:6379/0
```

## Why This Fixes WebSocket Errors

1. **Redis Database Selection**: Redis supports multiple databases (0-15)
2. **Default Behavior**: Without `/0`, some libraries default to database 0, others fail
3. **WebSocket Manager**: Socket.io with Redis adapter requires explicit database selection
4. **Connection String Format**: `redis://[user]:password@host:port/database`

## Troubleshooting

### "Still seeing WebSocket errors"

```bash
# Check if frontend can reach Redis
docker exec beagle-frontend nc -zv beagle-redis 6379

# Check Redis password matches
docker exec beagle-redis env | grep REDIS_PASSWORD
docker exec beagle-frontend env | grep REDIS
```

### "Redis connection refused"

```bash
# Restart Redis container
docker restart beagle-redis

# Wait for health check
sleep 10

# Restart frontend
docker restart beagle-frontend
```

### "Frontend container unhealthy"

```bash
# Check health endpoint
docker exec beagle-frontend curl -f http://localhost:8080/health

# Check frontend logs
docker logs beagle-frontend --tail 50
```

### "Environment variables not loading"

Make sure:
1. `env/postgres.env` exists and has correct values
2. `env/redis.env` exists and has correct values
3. `.env` file exists in the root directory
4. All three files are readable by Docker

## Complete Redis URL Examples

### ✅ Correct Formats
```
redis://:mypassword@beagle-redis:6379/0
redis://default:mypassword@beagle-redis:6379/0
redis://beagle-redis:6379/0  (if no password)
```

### ❌ Wrong Formats
```
redis://:mypassword@beagle-redis:6379     (missing /0)
redis://:mypassword@redis:6379/0          (wrong host - should be beagle-redis)
redis://mypassword@beagle-redis:6379/0    (username without colon)
```

## Next Steps

After fixing the Redis URLs:

1. ✅ Restart containers
2. ✅ Run diagnostics
3. ✅ Verify in browser console
4. ✅ Test real-time chat features
5. ✅ Proceed with implementing the OpenAI filter function

## Files Created

- `docker-compose.beagle.yaml` - Corrected docker-compose configuration
- `env/postgres.env` - PostgreSQL environment variables
- `env/redis.env` - Redis environment variables
- `diagnose-websocket-beagle.sh` - Diagnostic script for beagle-frontend
- `BEAGLE_SETUP.md` - This guide

## Questions?

Run the diagnostic script and share the output:
```bash
./diagnose-websocket-beagle.sh > beagle-diagnostic.txt 2>&1
cat beagle-diagnostic.txt
```
