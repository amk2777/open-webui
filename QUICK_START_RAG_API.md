# Quick Start: Testing RAG API in Docker

Your Open WebUI is running in Docker with these ports:
- **Frontend/UI**: http://localhost:3000
- **Backend API** (inside container): port 8080
- **External API access**: http://localhost:3000/api/...

## Step 1: Get an API Key

### Option A: Generate via UI (Easiest)
1. Open http://localhost:3000 in your browser
2. Login with your credentials
3. Click your profile → Settings → Account
4. Scroll to "API Keys" section
5. Click "Create API Key" or "Generate API Key"
6. Copy the key (starts with `sk-`)

### Option B: Generate via curl
```bash
# First, login to get a JWT token
curl -X POST "http://localhost:3000/api/v1/auths/signin" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "your-password"
  }' | jq -r '.token'

# Save the token, then generate API key
export JWT_TOKEN="paste-your-token-here"

curl -X POST "http://localhost:3000/api/v1/auths/api_key" \
  -H "Authorization: Bearer $JWT_TOKEN" | jq -r '.api_key'
```

## Step 2: Find Your Collection Name

```bash
# Save your API key
export API_KEY="sk-paste-your-api-key-here"

# List all knowledge bases to find collection names
curl -X GET "http://localhost:3000/api/v1/knowledge" \
  -H "Authorization: Bearer $API_KEY" | jq '.data[] | {name: .name, collection: .data.collection_name}'
```

## Step 3: Query the RAG System

```bash
# Simple query
curl -X POST "http://localhost:3000/api/v1/retrieval/query/doc" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "your_collection_name_here",
    "query": "What is machine learning?",
    "k": 5
  }' | jq .

# With hybrid search (vector + keyword)
curl -X POST "http://localhost:3000/api/v1/retrieval/query/doc" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "your_collection_name_here",
    "query": "neural networks",
    "k": 5,
    "hybrid": true
  }' | jq .
```

## Step 4: Test from Inside Docker

If you need to call the API from another container in the same Docker network:

```bash
# From another container in the same network
curl -X POST "http://open-webui:8080/api/v1/retrieval/query/doc" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "your_collection_name_here",
    "query": "test query",
    "k": 5
  }'
```

Note: Use `http://open-webui:8080` (internal Docker network) instead of `http://localhost:3000`.

## Troubleshooting

### "API Keys not enabled" error

Add to your `.env` or `docker-compose.yaml`:
```yaml
environment:
  - ENABLE_API_KEYS=true
```

Then restart:
```bash
docker-compose restart open-webui
```

### "Collection not found" error

1. Make sure you've uploaded and processed documents in Open WebUI
2. Check the exact collection name using the knowledge endpoint
3. Collection names are case-sensitive

### "No results" / Empty documents array

1. Try removing the `r` (relevance threshold) parameter
2. Increase `k` to get more results
3. Try `"hybrid": false` to test vector-only search

## Complete Working Example

```bash
#!/bin/bash

# Configuration
API_KEY="sk-your-api-key-here"
BASE_URL="http://localhost:3000"

# Find collections
echo "Finding collections..."
curl -s -X GET "$BASE_URL/api/v1/knowledge" \
  -H "Authorization: Bearer $API_KEY" | jq '.data[] | {name: .name, collection: .data.collection_name}'

# Query RAG
echo -e "\nQuerying RAG..."
curl -s -X POST "$BASE_URL/api/v1/retrieval/query/doc" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "test_collection",
    "query": "What is AI?",
    "k": 3,
    "hybrid": true
  }' | jq '{
    num_results: (.documents | length),
    documents: .documents,
    sources: [.metadatas[] | .source]
  }'
```

Save this as `test_rag.sh`, make it executable (`chmod +x test_rag.sh`), and run it.

## Next Steps

Once this works, you can:
1. Create an OpenAPI Tool Server to expose these endpoints
2. Call these APIs from your external application directly
3. Build SDKs/clients in your preferred language

See `TESTING_RAG_ENDPOINTS.md` for more detailed documentation.
