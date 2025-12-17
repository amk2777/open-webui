# Debugging API Response

## Issue
Getting jq parse error when querying knowledge endpoint:
```
jq: parse error: Invalid numeric literal at line 1, column 10
```

## Step 1: Check the Raw Response (without jq)

First, let's see what the API is actually returning:

```bash
# Set your API key
export API_KEY="sk-your-key-here"

# Get raw response without jq
curl -v -X GET "http://localhost:3000/api/v1/knowledge" \
  -H "Authorization: Bearer $API_KEY"
```

The `-v` flag shows verbose output including headers and status codes.

## Step 2: Verify API Key Format

Make sure your API key is properly set:

```bash
echo $API_KEY
# Should output: sk-...
```

## Step 3: Try Different Approaches

### Option A: Save response to file first

```bash
curl -X GET "http://localhost:3000/api/v1/knowledge" \
  -H "Authorization: Bearer $API_KEY" \
  -o response.json

# Check what's in the file
cat response.json

# If it's valid JSON, parse it
cat response.json | jq .
```

### Option B: Check response headers

```bash
curl -i -X GET "http://localhost:3000/api/v1/knowledge" \
  -H "Authorization: Bearer $API_KEY"
```

This shows headers. Look for:
- `HTTP/1.1 200 OK` (success) or error codes like 401, 403
- `Content-Type: application/json` (should be JSON)

### Option C: Simple test without filtering

```bash
# Just get the response without jq filtering
curl -s -X GET "http://localhost:3000/api/v1/knowledge" \
  -H "Authorization: Bearer $API_KEY" | jq .
```

## Common Issues

### Issue 1: HTML Error Page Instead of JSON

If you see HTML like `<!DOCTYPE html>` or `<html>`, the API returned an error page.

**Solution:** Check the status code and actual error message.

### Issue 2: Authentication Error

Response might be:
```json
{"detail": "Not authenticated"}
```

**Solution:**
- Verify API key starts with `sk-`
- Make sure you're using `Bearer $API_KEY` not just `$API_KEY`
- Regenerate the API key if needed

### Issue 3: Empty or Invalid Response

**Solution:** The knowledge base might be empty or the endpoint path is wrong.

## Working Example

Once you identify the issue, this should work:

```bash
# Method 1: Get all knowledge bases
curl -s -X GET "http://localhost:3000/api/v1/knowledge" \
  -H "Authorization: Bearer $API_KEY" | jq '.'

# Method 2: Get specific fields
curl -s -X GET "http://localhost:3000/api/v1/knowledge" \
  -H "Authorization: Bearer $API_KEY" | jq '.data[]? | {name: .name, collection: .data.collection_name}'
```

Note the `?` after `.data[]` - this handles cases where data might be null/empty.

## Alternative: Use Knowledge ID Endpoint

If you know your knowledge base ID, you can query it directly:

```bash
# List all first
curl -s -X GET "http://localhost:3000/api/v1/knowledge" \
  -H "Authorization: Bearer $API_KEY" | jq '.data[] | .id'

# Then get specific one
curl -s -X GET "http://localhost:3000/api/v1/knowledge/{knowledge-id}" \
  -H "Authorization: Bearer $API_KEY" | jq '.'
```

## Next Step: Query RAG Once You Find Collection Name

Once you get the collection name (e.g., `general_knowledge`), you can query it:

```bash
curl -X POST "http://localhost:3000/api/v1/retrieval/query/doc" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "general_knowledge",
    "query": "test query",
    "k": 5,
    "hybrid": true
  }' | jq .
```
