# RAG Client Integration Guide

This guide shows how to integrate the standalone RAG client into your own Python application.

## Overview

The `rag_client.py` module provides a simple async interface to query Open WebUI's RAG system from external applications. It handles:

- ✅ Fetching all collections a user has access to
- ✅ Querying multiple collections in parallel
- ✅ Merging and ranking results by relevance
- ✅ Returning structured responses

## Quick Start

### 1. Copy Files to Your Project

Copy these files into your project:

```bash
# Copy the client module
cp rag_client.py /path/to/your/project/

# Copy requirements (or merge into your requirements.txt)
cp rag_client_requirements.txt /path/to/your/project/
```

### 2. Install Dependencies

```bash
pip install httpx>=0.27.0 pydantic>=2.0.0
```

### 3. Use in Your Code

```python
from rag_client import query_rag_for_user

async def search_knowledge_base(user_query: str, user_id: str):
    results = await query_rag_for_user(
        query=user_query,
        user_id=user_id,
        openwebui_url="http://localhost:3000",
        api_key="sk-your-api-key-here",
        top_k=5
    )
    return results
```

## Core Function

### `query_rag_for_user()`

Main function to query all collections accessible to a user.

**Signature:**
```python
async def query_rag_for_user(
    query: str,
    user_id: str,
    openwebui_url: str,
    api_key: str,
    top_k: int = 5,
    top_k_per_collection: int = 10,
    relevance_threshold: float = 0.0,
    enable_hybrid_search: bool = True,
    timeout: float = 60.0
) -> RAGQueryResponse
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | str | Required | Search query text |
| `user_id` | str | Required | User ID (for logging/tracking) |
| `openwebui_url` | str | Required | Open WebUI base URL |
| `api_key` | str | Required | API key (starts with `sk-`) |
| `top_k` | int | 5 | Number of final results to return |
| `top_k_per_collection` | int | 10 | Results per collection before ranking |
| `relevance_threshold` | float | 0.0 | Min relevance score (0-1) |
| `enable_hybrid_search` | bool | True | Use vector + BM25 search |
| `timeout` | float | 60.0 | Request timeout (seconds) |

**Returns:**

`RAGQueryResponse` object with:
```python
class RAGQueryResponse:
    query: str                           # Original query
    total_results: int                   # Number of results
    results: List[DocumentResult]        # Ranked results
    collections_searched: List[Dict]     # Collections queried
    execution_time_ms: float             # Query time
```

**Result Structure:**

Each result in `results` list:
```python
class DocumentResult:
    text: str                    # Document text chunk
    metadata: Dict[str, Any]     # Metadata (source, page, etc.)
    distance: float              # Vector distance (lower = better)
    relevance_score: float       # 0-1 score (higher = better)
    source: Optional[str]        # Source document name
    collection_id: str           # Collection UUID
    collection_name: str         # Human-readable name
```

## Usage Examples

### Example 1: Basic Query

```python
import asyncio
from rag_client import query_rag_for_user

async def main():
    response = await query_rag_for_user(
        query="What is machine learning?",
        user_id="user-123",
        openwebui_url="http://localhost:3000",
        api_key="sk-your-key",
        top_k=3
    )

    print(f"Found {response.total_results} results")
    for result in response.results:
        print(f"- {result.source}: {result.text[:100]}...")

asyncio.run(main())
```

### Example 2: Query Specific Collections

If you know which collections to search:

```python
from rag_client import query_rag_specific_collections

response = await query_rag_specific_collections(
    query="neural networks",
    collection_ids=["uuid-1", "uuid-2"],
    openwebui_url="http://localhost:3000",
    api_key="sk-your-key",
    top_k=5
)
```

### Example 3: Format for LLM Context

```python
from rag_client import query_rag_for_user, format_results_for_llm

response = await query_rag_for_user(
    query="Explain the concept",
    user_id="user-123",
    openwebui_url="http://localhost:3000",
    api_key="sk-your-key",
    top_k=3
)

# Format for LLM prompt
context = format_results_for_llm(response)

# Use in your LLM prompt
prompt = f"""
Based on the following information:

{context}

Please answer: {response.query}
"""
```

### Example 4: With Relevance Filtering

```python
response = await query_rag_for_user(
    query="deep learning",
    user_id="user-123",
    openwebui_url="http://localhost:3000",
    api_key="sk-your-key",
    top_k=10,
    relevance_threshold=0.7  # Only return results >70% relevant
)

# All results will have relevance_score >= 0.7
for result in response.results:
    print(f"Relevance: {result.relevance_score:.2%}")
```

### Example 5: Error Handling

```python
try:
    response = await query_rag_for_user(
        query="test",
        user_id="user-123",
        openwebui_url="http://localhost:3000",
        api_key="sk-your-key",
        timeout=5.0
    )
except ValueError as e:
    # No collections accessible
    print(f"No knowledge bases available: {e}")
except httpx.HTTPError as e:
    # API request failed
    print(f"API error: {e}")
except Exception as e:
    # Other errors
    print(f"Unexpected error: {e}")
```

## Integration Patterns

### Pattern 1: FastAPI Endpoint

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from rag_client import query_rag_for_user

app = FastAPI()

class QueryRequest(BaseModel):
    query: str
    user_id: str

@app.post("/search")
async def search(request: QueryRequest):
    try:
        response = await query_rag_for_user(
            query=request.query,
            user_id=request.user_id,
            openwebui_url="http://localhost:3000",
            api_key="sk-your-key",
            top_k=5
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Pattern 2: LangChain Integration

```python
from langchain.schema import Document
from rag_client import query_rag_for_user

async def get_langchain_documents(query: str, user_id: str):
    """Convert RAG results to LangChain documents"""
    response = await query_rag_for_user(
        query=query,
        user_id=user_id,
        openwebui_url="http://localhost:3000",
        api_key="sk-your-key"
    )

    return [
        Document(
            page_content=result.text,
            metadata={
                "source": result.source,
                "relevance": result.relevance_score,
                "collection": result.collection_name
            }
        )
        for result in response.results
    ]
```

### Pattern 3: Background Task / Job Queue

```python
from celery import Celery
from rag_client import query_rag_for_user
import asyncio

app = Celery('tasks', broker='redis://localhost:6379')

@app.task
def search_knowledge_base(query: str, user_id: str):
    """Celery task for async RAG queries"""
    loop = asyncio.get_event_loop()
    response = loop.run_until_complete(
        query_rag_for_user(
            query=query,
            user_id=user_id,
            openwebui_url="http://localhost:3000",
            api_key="sk-your-key"
        )
    )
    return response.dict()
```

### Pattern 4: Caching Results

```python
from functools import lru_cache
import hashlib
import json
from rag_client import query_rag_for_user

# Simple in-memory cache
_cache = {}

async def cached_query_rag(query: str, user_id: str, **kwargs):
    """Query RAG with caching"""
    cache_key = hashlib.md5(
        f"{query}:{user_id}:{json.dumps(kwargs)}".encode()
    ).hexdigest()

    if cache_key in _cache:
        return _cache[cache_key]

    response = await query_rag_for_user(
        query=query,
        user_id=user_id,
        **kwargs
    )

    _cache[cache_key] = response
    return response
```

## Configuration

### Environment Variables

Create a `.env` file or use environment variables:

```bash
OPENWEBUI_URL=http://localhost:3000
OPENWEBUI_API_KEY=sk-your-api-key-here
RAG_DEFAULT_TOP_K=5
RAG_DEFAULT_THRESHOLD=0.0
RAG_TIMEOUT=60.0
```

### Configuration Class

```python
from pydantic_settings import BaseSettings

class RAGConfig(BaseSettings):
    openwebui_url: str
    openwebui_api_key: str
    default_top_k: int = 5
    relevance_threshold: float = 0.0
    timeout: float = 60.0

    class Config:
        env_prefix = "RAG_"
        env_file = ".env"

# Usage
config = RAGConfig()

response = await query_rag_for_user(
    query="test",
    user_id="user-123",
    openwebui_url=config.openwebui_url,
    api_key=config.openwebui_api_key,
    top_k=config.default_top_k
)
```

## Testing

### Unit Test Example

```python
import pytest
from unittest.mock import AsyncMock, patch
from rag_client import query_rag_for_user, DocumentResult

@pytest.mark.asyncio
async def test_query_rag():
    with patch('rag_client._get_user_collections') as mock_collections, \
         patch('rag_client._query_single_collection') as mock_query:

        # Mock collections
        mock_collections.return_value = [
            {"id": "col-1", "name": "Test Collection"}
        ]

        # Mock query results
        mock_query.return_value = [
            DocumentResult(
                text="Test document",
                metadata={"source": "test.pdf"},
                distance=0.1,
                relevance_score=0.95,
                source="test.pdf",
                collection_id="col-1",
                collection_name="Test Collection"
            )
        ]

        response = await query_rag_for_user(
            query="test",
            user_id="user-123",
            openwebui_url="http://localhost:3000",
            api_key="sk-test"
        )

        assert response.total_results == 1
        assert response.results[0].text == "Test document"
```

## Troubleshooting

### Issue: No results returned

**Possible causes:**
1. No documents in collections
2. Relevance threshold too high
3. Query doesn't match document content

**Solutions:**
```python
# Lower threshold
response = await query_rag_for_user(
    query="...",
    relevance_threshold=0.0,  # Accept all results
    top_k=10
)

# Try without hybrid search
response = await query_rag_for_user(
    query="...",
    enable_hybrid_search=False
)
```

### Issue: Timeout errors

**Solution:**
```python
response = await query_rag_for_user(
    query="...",
    timeout=120.0,  # Increase timeout to 2 minutes
    top_k_per_collection=5  # Reduce results per collection
)
```

### Issue: Authentication errors

**Check:**
1. API key is correct and starts with `sk-`
2. API keys are enabled in Open WebUI
3. User has permission to access collections

## Performance Tips

1. **Parallel Queries**: The client queries all collections in parallel automatically

2. **Limit Per-Collection Results**: Reduce `top_k_per_collection` if querying many collections:
   ```python
   response = await query_rag_for_user(
       query="...",
       top_k=5,
       top_k_per_collection=5  # Fetch fewer from each collection
   )
   ```

3. **Use Specific Collections**: If you know which collections to search:
   ```python
   from rag_client import query_rag_specific_collections

   response = await query_rag_specific_collections(
       query="...",
       collection_ids=["known-col-id"],
       top_k=5
   )
   ```

4. **Cache Results**: Implement caching for repeated queries (see Pattern 4 above)

## Additional Helper Functions

### `format_results_for_llm(response)`

Formats results as text for LLM context.

```python
from rag_client import format_results_for_llm

context = format_results_for_llm(response)
# Returns formatted string with numbered results
```

### `get_unique_sources(response)`

Extracts unique source documents.

```python
from rag_client import get_unique_sources

sources = get_unique_sources(response)
# Returns: ["document1.pdf", "document2.pdf", ...]
```

## Complete Example Application

See `example_rag_usage.py` for complete working examples including:
- Basic queries
- Specific collection queries
- LLM context formatting
- Error handling
- Integration patterns

## Support

For issues or questions:
1. Check the examples in `example_rag_usage.py`
2. Review the troubleshooting section above
3. Check Open WebUI API documentation
4. Verify Open WebUI is running and accessible

## License

This client module follows the same license as Open WebUI.
