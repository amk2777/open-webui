# Fix: Enable API Keys in Docker

## Problem
Error when trying to generate API key:
```
{"detail":"API key creation is not allowed in the environment."}
```

## Solution

I've updated your `docker-compose.yaml` to enable API keys. Now you need to restart the container.

### Step 1: Restart the Open WebUI Container

```bash
# Stop and restart the open-webui container
docker-compose restart open-webui

# OR if you want to recreate the container
docker-compose down
docker-compose up -d
```

Wait about 10-20 seconds for the container to fully start.

### Step 2: Verify API Keys are Enabled

You can check two ways:

**Option A: Via UI**
1. Go to http://localhost:3000
2. Login
3. Go to Settings → Account
4. You should now see an "API Keys" section

**Option B: Via API**
```bash
# Get your JWT token first
export JWT_TOKEN=$(curl -s -X POST "http://localhost:3000/api/v1/auths/signin" \
  -H "Content-Type: application/json" \
  -d '{"email":"your-email","password":"your-password"}' | jq -r '.token')

# Now try to generate an API key
curl -X POST "http://localhost:3000/api/v1/auths/api_key" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### Step 3: Expected Response

If it works, you'll get:
```json
{
  "api_key": "sk-1234567890abcdef..."
}
```

Save this API key! It starts with `sk-`.

### Step 4: Test RAG Query with API Key

```bash
# Save your API key
export API_KEY="sk-paste-your-api-key-here"

# List available collections
curl -X GET "http://localhost:3000/api/v1/knowledge" \
  -H "Authorization: Bearer $API_KEY" | jq .

# Query a collection (replace collection_name with actual name)
curl -X POST "http://localhost:3000/api/v1/retrieval/query/doc" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "your_collection_name",
    "query": "test query",
    "k": 5,
    "hybrid": true
  }' | jq .
```

## What Changed

Added to `docker-compose.yaml`:
```yaml
environment:
  - 'ENABLE_API_KEYS=true'
  - 'USER_PERMISSIONS_FEATURES_API_KEYS=true'
```

**Two flags are required:**
1. `ENABLE_API_KEYS=true` - Enables the API key feature globally
2. `USER_PERMISSIONS_FEATURES_API_KEYS=true` - Gives users permission to create/use API keys

Without BOTH flags, you'll get: "API key creation is not allowed in the environment."

## Troubleshooting

### Still getting "not allowed" error after restart?

1. Make sure the container actually restarted:
   ```bash
   docker ps | grep open-webui
   ```
   Check the "STATUS" column - should say "Up X seconds/minutes"

2. Check the logs:
   ```bash
   docker logs open-webui | grep -i "api_key"
   ```

3. Try recreating the container completely:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### "API Keys" section not showing in UI?

Your user might not have permission. Try:
1. Login as admin
2. Go to Admin Panel → Users
3. Edit your user
4. Enable "API Keys" permission under Features

## Next Steps

Once you have a working API key:
1. Test the RAG query endpoints (see QUICK_START_RAG_API.md)
2. Implement OpenAPI Tool Server integration (if needed)
3. Call the API from your external application
