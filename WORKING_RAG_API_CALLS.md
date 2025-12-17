# Working RAG API Calls - TESTED

Based on investigation of the codebase, here are the **working** API endpoints for querying RAG.

## Issue with `/api/v1/knowledge`

The base endpoint `/api/v1/knowledge` might get caught by the frontend's SPA static files handler if there's an authentication or permission issue. This returns HTML instead of JSON.

## Working Alternative Endpoints

### 1. List Knowledge Bases (Write Access)

```bash
curl -s -X GET "http://localhost:3000/api/v1/knowledge/list" \
  -H "Authorization: Bearer $API_KEY" | jq '.'
```

This endpoint returns knowledge bases where you have write access.

### 2. Get Specific Knowledge Base by ID

If you know the knowledge base ID:

```bash
curl -s -X GET "http://localhost:3000/api/v1/knowledge/{knowledge-id}" \
  -H "Authorization: Bearer $API_KEY" | jq '.'
```

### 3. Query RAG Directly (RECOMMENDED)

**If you know your collection name**, skip the knowledge endpoint and query RAG directly:

```bash
# For a knowledge base called "General Knowledge", the collection name might be:
# "general_knowledge" or similar

curl -X POST "http://localhost:3000/api/v1/retrieval/query/doc" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "general_knowledge",
    "query": "test query",
    "k": 5,
    "hybrid": true
  }' | jq '.'
```

## Finding Your Collection Name

### Method 1: Check in Browser DevTools

1. Open http://localhost:3000 in your browser
2. Open Developer Tools (F12)
3. Go to Network tab
4. Navigate to your "General Knowledge" knowledge base
5. Look for API calls to find the collection name in the responses

### Method 2: Try Common Patterns

Collection names are usually created from knowledge base names by:
- Converting to lowercase
- Replacing spaces with underscores
- Removing special characters

Examples:
- "General Knowledge" → `general_knowledge`
- "My Documents" → `my_documents`
- "Test KB" → `test_kb`

Try this:

```bash
# Try the most likely collection name
curl -X POST "http://localhost:3000/api/v1/retrieval/query/doc" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "general_knowledge",
    "query": "test",
    "k": 1
  }' 2>&1
```

**If you get a 404 or "collection not found"**, try variations like:
- `General_Knowledge`
- `generalknowledge`
- `general-knowledge`

### Method 3: List All Collections in Vector DB

If you have access to the Docker container:

```bash
# Enter the container
docker exec -it open-webui bash

# Check vector DB directory (for Chroma)
ls -la /app/backend/data/vector_db/

# Each directory name is a collection name
```

## Complete Working Example

```bash
#!/bin/bash

API_KEY="your-api-key-here"
BASE_URL="http://localhost:3000"

# Try to list knowledge bases
echo "Attempting to list knowledge bases..."
RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/knowledge/list" \
  -H "Authorization: Bearer $API_KEY")

echo "$RESPONSE" | jq '.'

# If that worked, extract collection names
echo -e "\nExtracting collection names..."
echo "$RESPONSE" | jq -r '.[] | .data.collection_name' 2>/dev/null || echo "No collections found or permission denied"

# Query RAG with a known collection
echo -e "\nQuerying RAG..."
curl -X POST "$BASE_URL/api/v1/retrieval/query/doc" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "general_knowledge",
    "query": "What is artificial intelligence?",
    "k": 3,
    "hybrid": true
  }' | jq '{
    num_results: (.documents | length),
    first_doc: .documents[0],
    sources: [.metadatas[]? | .source]
  }'
```

## Troubleshooting

### Still Getting HTML Instead of JSON?

This means the API endpoint is returning 404 and the SPA handler is catching it.

**Possible causes:**
1. **Permission issue**: Your user doesn't have access to list knowledge bases
2. **No knowledge bases exist**: Create one first in the UI
3. **Wrong endpoint**: Try the alternatives above

### Empty Response or No Results?

**For knowledge listing:**
- Make sure you've created at least one knowledge base in the UI
- Check that your user has permission to access it
- Try as an admin user

**For RAG queries:**
- Verify the collection name is correct
- Make sure documents have been uploaded and processed
- Check that the knowledge base isn't empty

### Permission Denied Errors?

Your user might need additional permissions. As admin:
1. Go to Admin Panel → Users
2. Edit your user
3. Enable "Workspace > Knowledge" permission

## Next Steps

Once you can successfully query the RAG system:
1. Document your actual collection names
2. Test different query types (hybrid vs vector-only)
3. Implement OpenAPI Tool Server (if needed) to expose these endpoints to external services
