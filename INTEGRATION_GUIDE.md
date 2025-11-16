# Document Storage & Retrieval Integration Guide

This guide explains how to integrate Open WebUI's document storage and retrieval system with your existing OpenWebUI pipeline or external applications.

---

## Quick Start: Integration Patterns

### Pattern 1: Use Existing API Endpoints (Recommended)

The simplest approach is to use the existing REST API endpoints. All endpoints are designed to be integrated into external pipelines.

#### Upload Documents
```bash
curl -X POST "http://localhost:8000/api/files/" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf" \
  -F "metadata={\"source\": \"external_system\"}" \
  -F "process=true" \
  -F "process_in_background=false"
```

#### Create Knowledge Base
```bash
curl -X POST "http://localhost:8000/api/knowledge/create" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Pipeline KB",
    "description": "Documents for my pipeline",
    "access_control": null
  }'
```

#### Query Documents
```bash
curl -X POST "http://localhost:8000/api/retrieval/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "queries": ["What is machine learning?"],
    "collection_name": "my_knowledge_base_id"
  }'
```

---

### Pattern 2: Direct Python Integration

For tight integration with Python-based pipelines:

#### Step 1: Import Core Components
```python
from open_webui.models.files import Files, FileForm
from open_webui.models.knowledge import Knowledges, KnowledgeForm
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT
from open_webui.storage.provider import Storage
from open_webui.retrieval.utils import get_embedding_function, query_collection
```

#### Step 2: Create Knowledge Base
```python
from open_webui.models.knowledge import Knowledges, KnowledgeForm

# Create knowledge base
kb_form = KnowledgeForm(
    name="My Pipeline Knowledge Base",
    description="Documents indexed by external pipeline",
    data=None,
    access_control=None  # Public
)

knowledge_base = Knowledges.insert_new_knowledge(
    user_id="system",
    form_data=kb_form
)

kb_id = knowledge_base.id
print(f"Created KB: {kb_id}")
```

#### Step 3: Add Documents
```python
import uuid
import time
from pathlib import Path

# Upload file to storage
file_path = "/path/to/document.pdf"
with open(file_path, "rb") as f:
    contents, stored_path = Storage.upload_file(
        f,
        f"document_{uuid.uuid4()}.pdf",
        metadata={
            "source": "external_pipeline",
            "custom_field": "value"
        }
    )

# Create file record in database
file_id = str(uuid.uuid4())
file_form = FileForm(
    id=file_id,
    filename="document.pdf",
    path=stored_path,
    data={"status": "pending"},
    meta={
        "name": "document.pdf",
        "content_type": "application/pdf",
        "size": len(contents),
        "collection_name": kb_id,
        "data": {"source": "external_pipeline"}
    }
)

file = Files.insert_new_file(
    user_id="system",
    form_data=file_form
)

# Add file to knowledge base
data = knowledge_base.data or {}
file_ids = data.get("file_ids", [])
file_ids.append(file_id)
data["file_ids"] = file_ids

Knowledges.update_knowledge_data_by_id(kb_id, data)

print(f"Added file: {file_id}")
```

#### Step 4: Process Document for Indexing
```python
from open_webui.routers.retrieval import ProcessFileForm, process_file
from fastapi import Request

# Create a minimal request object if not in FastAPI context
class MinimalRequest:
    def __init__(self, app_state):
        self.app = type('obj', (object,), {'state': app_state})()

# Process the file (extract, embed, index)
# In FastAPI route: pass real request
# In standalone script: create mock request
process_file(
    request,  # FastAPI Request object
    ProcessFileForm(
        file_id=file_id,
        collection_name=kb_id
    ),
    user=user  # or mock user
)

print(f"Processing file: {file_id}")
```

#### Step 5: Query Documents
```python
from open_webui.retrieval.utils import get_embedding_function, query_collection
from open_webui.config import RAG_EMBEDDING_MODEL, RAG_EMBEDDING_ENGINE

# Get embedding function
embedding_fn = get_embedding_function(
    engine=RAG_EMBEDDING_ENGINE,
    embedding_model=RAG_EMBEDDING_MODEL
)

# Create query embedding
query = "What are the main topics?"
query_embedding = embedding_fn([query])[0]

# Query vector database
results = query_collection(
    collection_name=kb_id,
    query=query,
    embedding_function=embedding_fn,
    top_k=5
)

# Results include: documents, metadatas, distances
for i, doc in enumerate(results['documents'][0]):
    print(f"Result {i}: {doc}")
    print(f"  Score: {results['distances'][0][i]}")
    print(f"  Source: {results['metadatas'][0][i]}")
```

---

### Pattern 3: Custom Pipeline with Vector DB Direct Access

For low-level control over document processing:

#### Direct Vector DB Operations
```python
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT
from open_webui.retrieval.loaders.main import Loader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# 1. Load documents
loader = Loader()
documents = loader.load_file("path/to/file.pdf")

# 2. Split into chunks
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1024,
    chunk_overlap=100
)
chunks = splitter.split_documents(documents)

# 3. Generate embeddings
embedding_fn = get_embedding_function()
embeddings = embedding_fn([doc.page_content for doc in chunks])

# 4. Add to vector DB
VECTOR_DB_CLIENT.add(
    collection_name="custom_collection",
    documents=[doc.page_content for doc in chunks],
    metadatas=[{
        "file_id": "file_id",
        "source": doc.metadata.get("source"),
        "page": doc.metadata.get("page", 0)
    } for doc in chunks],
    ids=[f"doc_{i}" for i in range(len(chunks))],
    embeddings=embeddings
)

# 5. Query
query_embedding = embedding_fn(["query text"])[0]
results = VECTOR_DB_CLIENT.query(
    collection_name="custom_collection",
    query_embeddings=[query_embedding],
    n_results=5
)
```

---

## Integration Scenario: LLM Pipeline Integration

### Scenario: Using Document Storage with LLM Generation

```python
from open_webui.retrieval.utils import (
    query_collection,
    get_embedding_function,
    get_reranking_function
)
from open_webui.models.knowledge import Knowledges

async def generate_with_context(query: str, kb_id: str):
    """Generate response using documents from knowledge base"""

    # 1. Get knowledge base
    kb = Knowledges.get_knowledge_by_id(kb_id)
    if not kb:
        raise ValueError(f"Knowledge base {kb_id} not found")

    # 2. Retrieve relevant documents
    embedding_fn = get_embedding_function()

    results = query_collection(
        collection_name=kb_id,
        query=query,
        embedding_function=embedding_fn,
        top_k=10
    )

    # 3. Optional: Rerank results
    reranking_fn = get_reranking_function()
    if reranking_fn:
        reranked = reranking_fn(
            query=query,
            documents=results['documents'][0]
        )
        # Use top-5 reranked results
        documents = reranked[:5]
    else:
        documents = results['documents'][0][:5]

    # 4. Create context
    context = "\n\n".join(documents)

    # 5. Format prompt
    system_prompt = f"""You are an assistant. Use the following context to answer the user's question.

Context:
{context}

Instructions:
- Answer based on the provided context
- Be concise and accurate
- If the context doesn't contain relevant information, say so
"""

    # 6. Call your LLM
    response = await call_llm(system_prompt, query)

    return {
        "response": response,
        "sources": results['metadatas'][0][:5],
        "documents": documents
    }
```

---

## Integration Scenario: Continuous Document Pipeline

### Scenario: Auto-Index New Documents

```python
import asyncio
from pathlib import Path
from open_webui.models.files import Files, FileForm
from open_webui.models.knowledge import Knowledges
from open_webui.storage.provider import Storage
from open_webui.routers.retrieval import ProcessFileForm, process_file
import uuid
import time

class DocumentPipeline:
    def __init__(self, kb_id: str, watch_dir: str):
        self.kb_id = kb_id
        self.watch_dir = Path(watch_dir)
        self.processed_files = set()

    async def watch_directory(self):
        """Watch directory for new documents"""
        while True:
            for file_path in self.watch_dir.glob("**/*"):
                if file_path.is_file() and file_path.name not in self.processed_files:
                    await self.process_new_file(file_path)
            await asyncio.sleep(5)  # Check every 5 seconds

    async def process_new_file(self, file_path: Path):
        """Process new file and add to knowledge base"""
        try:
            file_id = str(uuid.uuid4())

            # Upload to storage
            with open(file_path, "rb") as f:
                contents, stored_path = Storage.upload_file(
                    f,
                    f"{file_id}_{file_path.name}",
                    metadata={"source": "watch_directory"}
                )

            # Create file record
            file_form = FileForm(
                id=file_id,
                filename=file_path.name,
                path=stored_path,
                data={"status": "pending"},
                meta={
                    "name": file_path.name,
                    "content_type": "application/pdf",
                    "size": len(contents),
                    "collection_name": self.kb_id
                }
            )

            file = Files.insert_new_file("system", file_form)

            # Add to knowledge base
            kb = Knowledges.get_knowledge_by_id(self.kb_id)
            data = kb.data or {}
            file_ids = data.get("file_ids", [])
            file_ids.append(file_id)
            Knowledges.update_knowledge_data_by_id(self.kb_id, {"file_ids": file_ids})

            # Process for indexing
            # Note: Need to pass FastAPI Request object
            # In production, call via API or create proper request context

            self.processed_files.add(file_path.name)
            print(f"Processed: {file_path.name}")

        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")

# Usage
async def main():
    pipeline = DocumentPipeline(
        kb_id="knowledge_base_uuid",
        watch_dir="/path/to/documents"
    )
    await pipeline.watch_directory()

# asyncio.run(main())
```

---

## Configuration for Integration

### Essential Configuration (in `.env` or `config.py`)

```python
# Vector Database
VECTOR_DB=chroma  # or qdrant, pinecone, milvus, etc.
VECTOR_DB_PATH=./data/vector_db

# Embedding
RAG_EMBEDDING_ENGINE=""  # "" for local, "openai", "ollama", "azure_openai"
RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RAG_EMBEDDING_BATCH_SIZE=32

# Document Processing
CHUNK_SIZE=1024
CHUNK_OVERLAP=100
ALLOWED_FILE_EXTENSIONS=["pdf", "txt", "docx", "xlsx", "pptx", "md", "json"]

# Storage
UPLOAD_DIR=./data/uploads
# Or cloud storage:
# AWS_S3_BUCKET=my-bucket
# AWS_S3_REGION=us-east-1
# AZURE_STORAGE_CONNECTION_STRING=...
# GCS_BUCKET=my-gcs-bucket

# Optional: Reranking
RAG_RERANKING_MODEL=None
# or: jinaai/jina-colbert-v2

# RAG Template (system prompt)
RAG_TEMPLATE="Relevant Documents: {context}\n\nQuery: {query}"
```

---

## Access Control Integration

### Integrating with User/Group System

```python
from open_webui.models.files import Files
from open_webui.models.knowledge import Knowledges
from open_webui.utils.access_control import has_access

# Public knowledge base
kb_form = KnowledgeForm(
    name="Public KB",
    description="...",
    access_control=None  # Public
)

# Private knowledge base
kb_form = KnowledgeForm(
    name="Private KB",
    description="...",
    access_control={}  # Private (owner only)
)

# Knowledge base shared with specific users/groups
kb_form = KnowledgeForm(
    name="Shared KB",
    description="...",
    access_control={
        "read": {
            "group_ids": ["group_uuid"],
            "user_ids": ["user_uuid"]
        },
        "write": {
            "group_ids": ["group_uuid"],
            "user_ids": []
        }
    }
)

kb = Knowledges.insert_new_knowledge("owner_user_id", kb_form)

# Check access
can_read = has_access(
    user_id="user_uuid",
    permission="read",
    access_control=kb.access_control
)
```

---

## Error Handling & Best Practices

### Error Handling Pattern
```python
from open_webui.constants import ERROR_MESSAGES
from fastapi import HTTPException, status

try:
    file = Files.get_file_by_id(file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Process file

except Exception as e:
    log.error(f"Error processing file: {e}")
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ERROR_MESSAGES.DEFAULT(str(e))
    )
```

### Best Practices

1. **Always validate user permissions**
   ```python
   if not (file.user_id == user.id or user.role == "admin"):
       raise HTTPException(status_code=403, detail="Access denied")
   ```

2. **Use background tasks for long operations**
   ```python
   background_tasks.add_task(process_file, file_id, collection_name)
   ```

3. **Handle embedding errors gracefully**
   ```python
   try:
       embeddings = embedding_fn(texts)
   except Exception as e:
       # Fall back to alternative embedding or skip
       log.warning(f"Embedding failed: {e}")
   ```

4. **Monitor vector DB performance**
   ```python
   # Check collection size
   if VECTOR_DB_CLIENT.count(collection_name) > 1_000_000:
       log.warning("Collection size exceeding 1M documents")
   ```

5. **Implement proper logging**
   ```python
   import logging
   log = logging.getLogger(__name__)
   log.info(f"Processing file: {file_id}")
   ```

---

## API Client Examples

### Python Client (using httpx)
```python
import httpx
import asyncio

class DocumentClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token
        self.client = httpx.AsyncClient()

    async def upload_document(self, file_path: str, kb_id: str):
        """Upload document to knowledge base"""
        with open(file_path, "rb") as f:
            response = await self.client.post(
                f"{self.base_url}/api/files/",
                headers={"Authorization": f"Bearer {self.token}"},
                files={"file": f},
                data={
                    "process": "true",
                    "metadata": f'{{"kb_id": "{kb_id}"}}'
                }
            )
        return response.json()

    async def query(self, question: str, kb_id: str):
        """Query knowledge base"""
        response = await self.client.post(
            f"{self.base_url}/api/retrieval/query",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "queries": [question],
                "collection_name": kb_id
            }
        )
        return response.json()

# Usage
async def main():
    client = DocumentClient(
        "http://localhost:8000",
        "your_auth_token"
    )

    # Upload
    result = await client.upload_document("document.pdf", "kb_uuid")
    print(result)

    # Query
    results = await client.query("What is X?", "kb_uuid")
    print(results)

# asyncio.run(main())
```

### JavaScript/TypeScript Client
```typescript
import axios from 'axios';

class DocumentClient {
  constructor(private baseUrl: string, private token: string) {}

  async uploadDocument(file: File, kbId: string) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('process', 'true');
    formData.append('metadata', JSON.stringify({ kb_id: kbId }));

    const response = await axios.post(
      `${this.baseUrl}/api/files/`,
      formData,
      {
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'multipart/form-data'
        }
      }
    );
    return response.data;
  }

  async query(question: string, kbId: string) {
    const response = await axios.post(
      `${this.baseUrl}/api/retrieval/query`,
      {
        queries: [question],
        collection_name: kbId
      },
      {
        headers: {
          'Authorization': `Bearer ${this.token}`
        }
      }
    );
    return response.data;
  }
}

// Usage
const client = new DocumentClient('http://localhost:8000', 'token');
client.uploadDocument(file, 'kb_uuid').then(console.log);
```

---

## Troubleshooting Common Issues

| Issue | Solution |
|-------|----------|
| Files not being indexed | Check VECTOR_DB configuration, verify file type is allowed |
| Slow embeddings | Increase RAG_EMBEDDING_BATCH_SIZE, use faster model |
| Poor retrieval results | Try reranking, adjust CHUNK_SIZE, verify embeddings |
| Access denied errors | Check access_control settings, verify user permissions |
| Storage errors | Verify storage provider config (S3, Azure, GCS) |
| OOM errors during processing | Reduce CHUNK_SIZE or RAG_EMBEDDING_BATCH_SIZE |

---

## Next Steps

1. Review `DOCUMENT_STORAGE_ANALYSIS.md` for complete API reference
2. Choose integration pattern (REST API, Python, or Direct DB)
3. Configure vector database and storage backend
4. Implement document upload workflow
5. Test retrieval and querying
6. Integrate with your LLM pipeline
7. Deploy and monitor
