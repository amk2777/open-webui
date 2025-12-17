# Testing RAG Query Endpoints in Open WebUI

This guide shows how to test Open WebUI's RAG query endpoints directly without creating a separate service.

## Prerequisites

Your Open WebUI is running at: `http://localhost:3000`

## Step 1: Enable API Keys (if not already enabled)

### Option A: Via Environment Variable (Recommended for Docker)

Add to your Docker Compose file or environment:

```bash
ENABLE_API_KEYS=true
```

Then restart Open WebUI:
```bash
docker-compose down
docker-compose up -d
```

### Option B: Via Admin UI (if available)

1. Login as admin user
2. Go to Admin Panel → Settings → Authentication
3. Enable "API Keys" feature

## Step 2: Generate an API Key

### Option A: Via Web UI

1. Login to Open WebUI at http://localhost:3000
2. Go to Settings → Account
3. Look for "API Keys" section
4. Click "Generate API Key" or "Create API Key"
5. Copy the generated key (starts with `sk-`)

### Option B: Via API (if you have a session token)

First, login and get your JWT token:

```bash
# Login to get JWT token
curl -X POST "http://localhost:3000/api/v1/auths/signin" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "your-password"
  }'
```

This returns:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "id": "user-id",
  ...
}
```

Then generate API key:
```bash
# Generate API key using JWT token
curl -X POST "http://localhost:3000/api/v1/auths/api_key" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "api_key": "sk-1234567890abcdef..."
}
```

## Step 3: Test RAG Query Endpoints

Once you have your API key (starting with `sk-`), you can query the RAG system:

### Test 1: Query a Single Collection

```bash
curl -X POST "http://localhost:3000/api/v1/retrieval/query/doc" \
  -H "Authorization: Bearer sk-YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "your_collection_name",
    "query": "What is machine learning?",
    "k": 5,
    "hybrid": true
  }'
```

**Expected Response:**
```json
{
  "ids": ["doc1_chunk1", "doc2_chunk3", ...],
  "documents": ["Machine learning is...", "ML algorithms...", ...],
  "metadatas": [
    {"source": "ml_intro.pdf", "page": 1},
    {"source": "ai_basics.pdf", "page": 5}
  ],
  "distances": [0.15, 0.23, 0.34, ...]
}
```

### Test 2: Query Multiple Collections

```bash
curl -X POST "http://localhost:3000/api/v1/retrieval/query/collection" \
  -H "Authorization: Bearer sk-YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_names": ["collection1", "collection2"],
    "query": "What is deep learning?",
    "k": 3,
    "hybrid": true
  }'
```

### Test 3: Query with Advanced Options

```bash
curl -X POST "http://localhost:3000/api/v1/retrieval/query/doc" \
  -H "Authorization: Bearer sk-YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "my_docs",
    "query": "neural networks",
    "k": 10,
    "k_reranker": 5,
    "r": 0.7,
    "hybrid": true
  }'
```

**Parameters:**
- `collection_name` (string, required): Name of the collection to query
- `query` (string, required): Search query text
- `k` (int, optional): Number of results to retrieve (default: from config)
- `k_reranker` (int, optional): Number of results after reranking
- `r` (float, optional): Relevance threshold (0.0-1.0)
- `hybrid` (bool, optional): Enable hybrid search (vector + BM25)

## Step 4: Find Your Collection Names

If you don't know your collection names, you can list them:

```bash
# List all knowledge bases (collections)
curl -X GET "http://localhost:3000/api/v1/knowledge" \
  -H "Authorization: Bearer sk-YOUR_API_KEY_HERE"
```

This returns all knowledge bases with their collection names:
```json
{
  "data": [
    {
      "id": "kb-uuid-1",
      "name": "My Documents",
      "description": "Company documents",
      "data": {
        "collection_name": "my_documents_collection"
      }
    }
  ]
}
```

## Testing Inside Docker Container

If you need to test from inside a Docker container in the same network:

```bash
# If Open WebUI backend is in same Docker network
curl -X POST "http://open-webui:8080/api/v1/retrieval/query/doc" \
  -H "Authorization: Bearer sk-YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "test_collection",
    "query": "test query",
    "k": 5
  }'
```

**Note:** Replace `open-webui` with the actual service name in your Docker network, and use port `8080` (backend) instead of `3000` (frontend).

## Common Errors and Solutions

### Error: 401 Unauthorized

**Cause:** Invalid or missing API key

**Solution:**
1. Check API keys are enabled (`ENABLE_API_KEYS=true`)
2. Verify your API key starts with `sk-`
3. Make sure you're using the correct format: `Authorization: Bearer sk-...`
4. Regenerate the API key if needed

### Error: 403 Forbidden

**Cause:** User doesn't have API key permissions

**Solution:**
1. Check user has `features.api_keys` permission
2. Admins have this by default
3. For regular users, admin needs to grant permission

### Error: 404 Collection Not Found

**Cause:** Collection name doesn't exist

**Solution:**
1. List all collections using the knowledge endpoint
2. Check spelling of collection name
3. Make sure documents have been processed and indexed

### Error: Empty Results

**Cause:** No relevant documents found or relevance threshold too high

**Solution:**
1. Lower the `r` (relevance) parameter or remove it
2. Increase `k` to get more results
3. Try with `hybrid: false` to test pure vector search
4. Verify documents are actually in the collection

## Using from External Applications

### Python Example

```python
import httpx
import asyncio

async def query_rag(collection_name: str, query: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:3000/api/v1/retrieval/query/doc",
            headers={
                "Authorization": "Bearer sk-YOUR_API_KEY_HERE",
                "Content-Type": "application/json"
            },
            json={
                "collection_name": collection_name,
                "query": query,
                "k": 5,
                "hybrid": True
            }
        )
        response.raise_for_status()
        return response.json()

# Usage
result = asyncio.run(query_rag("my_docs", "What is AI?"))
print(f"Found {len(result['documents'])} documents")
for doc in result['documents']:
    print(f"- {doc[:100]}...")
```

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

async function queryRAG(collectionName, query) {
  const response = await axios.post(
    'http://localhost:3000/api/v1/retrieval/query/doc',
    {
      collection_name: collectionName,
      query: query,
      k: 5,
      hybrid: true
    },
    {
      headers: {
        'Authorization': 'Bearer sk-YOUR_API_KEY_HERE',
        'Content-Type': 'application/json'
      }
    }
  );
  return response.data;
}

// Usage
queryRAG('my_docs', 'What is AI?')
  .then(result => {
    console.log(`Found ${result.documents.length} documents`);
    result.documents.forEach(doc => {
      console.log(`- ${doc.substring(0, 100)}...`);
    });
  });
```

## Complete API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/retrieval/query/doc` | POST | Query single collection |
| `/api/v1/retrieval/query/collection` | POST | Query multiple collections |
| `/api/v1/retrieval/process/file` | POST | Process and index a file |
| `/api/v1/retrieval/process/text` | POST | Process and index raw text |
| `/api/v1/retrieval/process/web` | POST | Process web URL |
| `/api/v1/knowledge` | GET | List all knowledge bases |
| `/api/v1/knowledge/{id}` | GET | Get knowledge base details |
| `/api/v1/auths/api_key` | POST | Generate API key |
| `/api/v1/auths/api_key` | GET | Get existing API key |
| `/api/v1/auths/api_key` | DELETE | Delete API key |

## Next Steps: OpenAPI Tool Server

Once the basic curl tests work, you can expose these endpoints as an OpenAPI Tool Server to make them discoverable and usable by other services. See `OPENAPI_TOOL_SERVER.md` for instructions.

## Notes

- All RAG configuration (chunk size, embedding model, vector DB) is managed in Open WebUI
- No separate service needed - call these endpoints directly
- API keys can be scoped per user for security
- Hybrid search combines vector similarity with BM25 keyword search
- Reranking improves result quality but adds latency
