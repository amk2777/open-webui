# Open WebUI Document Storage & Retrieval System - Comprehensive Analysis

## Overview
The Open WebUI document storage and retrieval system is a sophisticated 3-tier RAG (Retrieval-Augmented Generation) pipeline designed to manage, process, and retrieve documents efficiently. This system supports multiple vector databases, storage backends, and embedding models.

---

## System Architecture

### 3-Tier Architecture
```
┌─────────────────────────────────────────────────────────────┐
│ Frontend API Clients (TypeScript)                           │
│ - File Management API                                       │
│ - Knowledge Base API                                        │
│ - Retrieval/RAG API                                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ FastAPI Routers (Backend)                                   │
│ - /files (File upload, management, content access)          │
│ - /knowledge (Knowledge base management)                    │
│ - /retrieval (RAG, embedding, document processing)          │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ Core Services Layer                                         │
│ - Vector DB Factory (supports 9 backends)                   │
│ - Storage Provider (local/cloud storage abstraction)        │
│ - Document Loaders (8+ document type handlers)              │
│ - Embedding & Reranking Engines                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Files Table
```
Table: file
├── id (String, PK)                  # UUID4
├── user_id (String)                 # Owner
├── hash (Text, nullable)            # File content hash
├── filename (Text)                  # Original filename
├── path (Text, nullable)            # Storage path
├── data (JSON, nullable)            # Processing state
│   ├── status: "pending|processing|completed|failed"
│   ├── content: str                 # Extracted text content
│   └── error: str                   # Error message if failed
├── meta (JSON, nullable)            # Metadata
│   ├── name: str
│   ├── content_type: str            # MIME type
│   ├── size: int                    # File size in bytes
│   ├── collection_name: str         # Associated knowledge base
│   └── data: dict                   # User-provided metadata
├── access_control (JSON, nullable)  # Permission control
├── created_at (BigInteger)          # Epoch timestamp
└── updated_at (BigInteger)          # Epoch timestamp
```

### Knowledge Table
```
Table: knowledge
├── id (Text, PK)                    # UUID
├── user_id (Text)                   # Owner
├── name (Text)                      # Knowledge base name
├── description (Text)               # Description
├── data (JSON, nullable)            # Configuration
│   └── file_ids: list[str]         # Associated file IDs
├── meta (JSON, nullable)            # Metadata
├── access_control (JSON, nullable)  # Permission control
│   ├── None: Public access (all users)
│   ├── {}: Private (owner only)
│   └── Custom:
│       ├── read: {group_ids, user_ids}
│       └── write: {group_ids, user_ids}
├── created_at (BigInteger)          # Epoch timestamp
└── updated_at (BigInteger)          # Epoch timestamp
```

---

## Complete API Endpoints

### FILES API (`/api/files`)

#### 1. Upload File
- **POST** `/api/files/`
- **Request:**
  ```json
  {
    "file": UploadFile,
    "metadata": dict (optional),
    "process": bool (default: true),
    "process_in_background": bool (default: true)
  }
  ```
- **Response:** `FileModelResponse`
- **Auth:** Verified User
- **Description:** Upload file with optional background processing

#### 2. List Files
- **GET** `/api/files/`
- **Query Parameters:**
  - `content` (bool, default: true) - Include file content
- **Response:** `list[FileModelResponse]`
- **Auth:** Verified User
- **Description:** Get all files (user's own or all if admin)

#### 3. Search Files by Pattern
- **GET** `/api/files/search`
- **Query Parameters:**
  - `filename` (str) - Wildcard pattern (e.g., `*.txt`)
  - `content` (bool, default: true)
- **Response:** `list[FileModelResponse]`
- **Auth:** Verified User
- **Description:** Find files matching filename pattern

#### 4. Get File by ID
- **GET** `/api/files/{id}`
- **Response:** `FileModel`
- **Auth:** Verified User
- **Description:** Retrieve complete file metadata and content

#### 5. Get File Process Status
- **GET** `/api/files/{id}/process/status`
- **Query Parameters:**
  - `stream` (bool, default: false) - Stream status updates
- **Response:** `{"status": str}` or SSE stream
- **Auth:** Verified User
- **Description:** Check document processing status (supports Server-Sent Events for streaming)

#### 6. Get File Data Content
- **GET** `/api/files/{id}/data/content`
- **Response:** `{"content": str}`
- **Auth:** Verified User
- **Description:** Get extracted text content

#### 7. Update File Data Content
- **POST** `/api/files/{id}/data/content/update`
- **Request Body:**
  ```json
  {
    "content": "string"
  }
  ```
- **Response:** `{"content": str}`
- **Auth:** Verified User
- **Description:** Update and reprocess file content

#### 8. Get File Content (Download)
- **GET** `/api/files/{id}/content`
- **Query Parameters:**
  - `attachment` (bool, default: false) - Force download
- **Response:** `FileResponse` (binary)
- **Auth:** Verified User
- **Description:** Download original file

#### 9. Get File Content HTML
- **GET** `/api/files/{id}/content/html`
- **Response:** `FileResponse` (HTML)
- **Auth:** Verified User (Admin files only)
- **Description:** Get HTML representation

#### 10. Get File Content with Name
- **GET** `/api/files/{id}/content/{file_name}`
- **Response:** `FileResponse` (binary or text)
- **Auth:** Verified User
- **Description:** Download file with original name

#### 11. Delete File by ID
- **DELETE** `/api/files/{id}`
- **Response:** `{"message": "File deleted successfully"}`
- **Auth:** Verified User
- **Description:** Delete file and remove from vector DB

#### 12. Delete All Files
- **DELETE** `/api/files/all`
- **Response:** `{"message": "All files deleted successfully"}`
- **Auth:** Admin User
- **Description:** Delete all files and reset vector database

---

### KNOWLEDGE BASE API (`/api/knowledge`)

#### 1. Get Knowledge Bases
- **GET** `/api/knowledge/`
- **Response:** `list[KnowledgeUserResponse]`
- **Auth:** Verified User
- **Description:** Get knowledge bases with read access

#### 2. Get Knowledge Base List
- **GET** `/api/knowledge/list`
- **Response:** `list[KnowledgeUserResponse]`
- **Auth:** Verified User
- **Description:** Get knowledge bases with write access

#### 3. Create Knowledge Base
- **POST** `/api/knowledge/create`
- **Request Body:**
  ```json
  {
    "name": "string",
    "description": "string",
    "data": {} (optional),
    "access_control": {} (optional)
  }
  ```
- **Response:** `KnowledgeResponse`
- **Auth:** Verified User
- **Description:** Create new knowledge base

#### 4. Get Knowledge Base by ID
- **GET** `/api/knowledge/{id}`
- **Response:** `KnowledgeFilesResponse`
- **Auth:** Verified User
- **Description:** Get knowledge base with associated files

#### 5. Update Knowledge Base
- **POST** `/api/knowledge/{id}/update`
- **Request Body:** `KnowledgeForm`
- **Response:** `KnowledgeFilesResponse`
- **Auth:** Verified User
- **Description:** Update knowledge base metadata and settings

#### 6. Add File to Knowledge Base
- **POST** `/api/knowledge/{id}/file/add`
- **Request Body:**
  ```json
  {
    "file_id": "string"
  }
  ```
- **Response:** `KnowledgeFilesResponse`
- **Auth:** Verified User
- **Description:** Add single file to knowledge base

#### 7. Update File in Knowledge Base
- **POST** `/api/knowledge/{id}/file/update`
- **Request Body:**
  ```json
  {
    "file_id": "string"
  }
  ```
- **Response:** `KnowledgeFilesResponse`
- **Auth:** Verified User
- **Description:** Reprocess file in knowledge base

#### 8. Remove File from Knowledge Base
- **POST** `/api/knowledge/{id}/file/remove`
- **Request Body:**
  ```json
  {
    "file_id": "string"
  }
  ```
- **Query Parameters:**
  - `delete_file` (bool, default: true)
- **Response:** `KnowledgeFilesResponse`
- **Auth:** Verified User
- **Description:** Remove file from knowledge base (optionally delete file)

#### 9. Add Multiple Files (Batch)
- **POST** `/api/knowledge/{id}/files/batch/add`
- **Request Body:** `list[{"file_id": "string"}]`
- **Response:** `KnowledgeFilesResponse`
- **Auth:** Verified User
- **Description:** Add multiple files to knowledge base with error handling

#### 10. Delete Knowledge Base
- **DELETE** `/api/knowledge/{id}/delete`
- **Response:** `bool`
- **Auth:** Verified User
- **Description:** Delete knowledge base (removes from models that reference it)

#### 11. Reset Knowledge Base
- **POST** `/api/knowledge/{id}/reset`
- **Response:** `KnowledgeResponse`
- **Auth:** Verified User
- **Description:** Clear all files from knowledge base

#### 12. Reindex All Knowledge Bases
- **POST** `/api/knowledge/reindex`
- **Response:** `bool`
- **Auth:** Admin User
- **Description:** Rebuild all vector indexes (with error recovery)

---

### RETRIEVAL/RAG API (`/api/retrieval`)

#### 1. Get RAG Status
- **GET** `/api/retrieval/`
- **Response:**
  ```json
  {
    "status": bool,
    "chunk_size": int,
    "chunk_overlap": int,
    "template": str,
    "embedding_engine": str,
    "embedding_model": str,
    "reranking_model": str,
    "embedding_batch_size": int
  }
  ```
- **Auth:** Public

#### 2. Get Embedding Config
- **GET** `/api/retrieval/embedding`
- **Response:** Embedding configuration (OpenAI, Ollama, Azure OpenAI)
- **Auth:** Admin User

#### 3. Update Embedding Configuration
- **POST** `/api/retrieval/embedding/update`
- **Request Body:**
  ```json
  {
    "embedding_engine": "string",
    "embedding_model": "string",
    "embedding_batch_size": int,
    "openai_config": {"url": str, "key": str},
    "ollama_config": {"url": str, "key": str},
    "azure_openai_config": {"url": str, "key": str, "version": str}
  }
  ```
- **Auth:** Admin User

#### 4. Process File
- **POST** `/api/retrieval/file`
- **Request Body:**
  ```json
  {
    "file_id": "string",
    "content": "string" (optional, override file content),
    "collection_name": "string" (optional, defaults to "file-{file_id}")
  }
  ```
- **Response:** Processing result
- **Auth:** Verified User

#### 5. Query Documents
- **POST** `/api/retrieval/query`
- **Request Body:**
  ```json
  {
    "queries": ["string"],
    "collection_name": "string" (optional)
  }
  ```
- **Response:** Search results
- **Auth:** Verified User

#### 6. Process URL/Web Content
- **POST** `/api/retrieval/web`
- **Request Body:**
  ```json
  {
    "url": "string",
    "collection_name": "string" (optional)
  }
  ```
- **Response:** Processing result
- **Auth:** Verified User

#### 7. Search Web
- **POST** `/api/retrieval/search`
- **Request Body:** Search query
- **Response:** Web search results
- **Auth:** Verified User

#### Additional Endpoints (18 total):
- Vector database configuration endpoints
- Reranking model endpoints
- Collection management endpoints
- Batch processing endpoints
- Web search engine configuration endpoints

---

## Supported Technologies

### Vector Databases (9 Backends)
1. **Chroma** - Lightweight vector DB
2. **Qdrant** - Production-grade vector search
3. **Pinecone** - Managed cloud vector DB
4. **Milvus** - Scalable vector DB
5. **pgvector** - PostgreSQL extension
6. **Elasticsearch** - Full-text + vector search
7. **OpenSearch** - Open-source Elasticsearch
8. **Oracle 23ai** - Enterprise vector DB
9. **S3Vector** - Cloud-native vector storage

### Storage Backends
- **Local File System** - Development/testing
- **AWS S3** - Cloud object storage
- **Azure Blob Storage** - Microsoft cloud
- **Google Cloud Storage** - Google Cloud

### Embedding Models
- **Sentence-Transformers** (default) - Fast, lightweight
- **OpenAI** - High-quality embeddings
- **Azure OpenAI** - Enterprise OpenAI
- **Ollama** - Local LLM embeddings

### Reranking Models
- **Sentence-Transformers Cross-Encoders**
- **Jina ColBERT** - Dense retrieval
- **External Rerankers** - Custom services

### Document Loaders (8+ Types)
- PDF documents
- Office documents (DOCX, XLSX, PPTX)
- Text files (TXT, MD, CSV)
- Code files (Python, JavaScript, etc.)
- JSON documents
- HTML pages
- YouTube videos (with transcription)
- Web content

### Web Search Engines (20+)
- DuckDuckGo, Google PSE, Bing, Kagi, Mojeek
- Brave Search, Bocha, SearXNG, Yacy
- Tavily, Exa, Perplexity, Sougou
- Jina Search, SearchAPI, SerpAPI, Serper, Serply
- SerpStack, FireCrawl, Ollama Cloud

---

## Processing Pipeline

### Document Upload & Processing Flow
```
1. User uploads file via POST /api/files/
   ↓
2. File stored in Storage Provider (S3/Local/etc)
   ↓
3. FileModel created in database
   ↓
4. Background task triggered (if enabled)
   ↓
5. Document Loader extracts content based on file type
   ↓
6. Content validation and cleaning
   ↓
7. Text splitting using RecursiveCharacterTextSplitter
   ↓
8. Embedding generation
   ├── Embedding model selected
   ├── Batch processing (configurable batch size)
   └── Result: Dense vectors
   ↓
9. Vector database indexing
   ├── Collection name: "file-{file_id}"
   ├── Metadata includes: file_id, content, user_id
   └── Filtering enabled for access control
   ↓
10. File status updated: "completed"
```

### Retrieval/Query Flow
```
1. User submits query via POST /api/retrieval/query
   ↓
2. Query embedding generated
   ↓
3. Vector similarity search
   ├── Dense vector matching
   └── Returns top-k results (default: 10)
   ↓
4. Optional: BM25 full-text search hybrid
   ├── Combines dense + sparse results
   └── Re-ranks combined results
   ↓
5. Optional: Reranking using CrossEncoder
   ├── Higher-quality relevance scoring
   └── Final ranking
   ↓
6. Results returned with:
   ├── Document content
   ├── Relevance score
   ├── Source file metadata
   └── Access control validation
```

---

## Key Configuration Parameters

### Chunking Configuration
- `CHUNK_SIZE`: Document chunk size (default: 1024)
- `CHUNK_OVERLAP`: Overlap between chunks (default: 100)

### Embedding Configuration
- `RAG_EMBEDDING_ENGINE`: Engine type (default: "", openai, ollama, azure_openai)
- `RAG_EMBEDDING_MODEL`: Model name (default: sentence-transformers/all-MiniLM-L6-v2)
- `RAG_EMBEDDING_BATCH_SIZE`: Batch size for embeddings (default: 1)
- `RAG_EMBEDDING_MODEL_AUTO_UPDATE`: Auto-update models (default: false)
- `RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE`: Allow remote code (default: false)

### Reranking Configuration
- `RAG_RERANKING_MODEL`: Reranking model (optional)
- `RAG_RERANKING_MODEL_AUTO_UPDATE`: Auto-update (default: false)
- `RAG_RERANKING_MODEL_TRUST_REMOTE_CODE`: Allow remote code (default: false)

### Vector Database Configuration
- `VECTOR_DB`: Selected vector DB (chroma, qdrant, pinecone, etc.)
- `VECTOR_DB_PATH`: Local path for Chroma (default: ./data/vector_db)
- Backend-specific configuration in `config.py`

### Content Extraction
- `CONTENT_EXTRACTION_ENGINE`: Engine for text extraction
  - "" (empty): LangChain loaders
  - "external": External service
  - "image" content type for images
- `ALLOWED_FILE_EXTENSIONS`: Whitelist of allowed file types

### RAG Template
- `RAG_TEMPLATE`: System prompt template for RAG integration

---

## File Models & Data Structures

### FileModel
```python
{
  "id": "uuid4",
  "user_id": "user_id",
  "hash": "sha256_hash_optional",
  "filename": "original_name.pdf",
  "path": "storage_path",
  "data": {
    "status": "pending|processing|completed|failed",
    "content": "extracted_text_content",
    "error": "error_message_if_failed"
  },
  "meta": {
    "name": "filename",
    "content_type": "application/pdf",
    "size": 1024000,
    "data": {
      "user_custom_field": "value"
    }
  },
  "access_control": null,  # null=public, {}=private, custom
  "created_at": 1700000000,
  "updated_at": 1700001000
}
```

### KnowledgeModel
```python
{
  "id": "uuid",
  "user_id": "user_id",
  "name": "Knowledge Base Name",
  "description": "Description of the knowledge base",
  "data": {
    "file_ids": ["file_id_1", "file_id_2"]
  },
  "meta": {},
  "access_control": {
    "read": {
      "group_ids": ["group_1"],
      "user_ids": ["user_1"]
    },
    "write": {
      "group_ids": ["group_1"],
      "user_ids": ["user_1"]
    }
  },
  "created_at": 1700000000,
  "updated_at": 1700001000
}
```

---

## Access Control

### File Access Control
- Owner (user_id) has full access
- Admins have full access
- Knowledge base members can access files through knowledge bases
- Access checked via: `has_access_to_file(file_id, access_type, user)`

### Knowledge Base Access Control
- **Public** (`access_control: null`): All users with "user" role
- **Private** (`access_control: {}`): Owner only
- **Custom** (`access_control: {...}`): Specific groups/users
  ```json
  {
    "read": {
      "group_ids": ["group_1"],
      "user_ids": ["user_1"]
    },
    "write": {
      "group_ids": ["group_2"],
      "user_ids": ["user_2"]
    }
  }
  ```

---

## Integration Points for External Pipelines

### 1. Direct Vector Database Access
```python
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT

# Query vectors
results = VECTOR_DB_CLIENT.query(
    collection_name="knowledge_base_id",
    queries=["query_embedding"],
    top_k=10
)

# Add vectors
VECTOR_DB_CLIENT.add(
    collection_name="custom_collection",
    documents=document_list,
    metadatas=metadata_list,
    ids=id_list
)

# Delete collection
VECTOR_DB_CLIENT.delete_collection(collection_name="collection_id")
```

### 2. Document Loader Access
```python
from open_webui.retrieval.loaders.main import Loader

loader = Loader()
documents = loader.load_file(file_path)
```

### 3. Embedding Function
```python
from open_webui.retrieval.utils import get_embedding_function

embedding_fn = get_embedding_function(
    engine=request.app.state.config.RAG_EMBEDDING_ENGINE,
    embedding_model=request.app.state.config.RAG_EMBEDDING_MODEL
)

embeddings = embedding_fn(texts)
```

### 4. Storage Provider Access
```python
from open_webui.storage.provider import Storage

# Upload file
contents, file_path = Storage.upload_file(
    file_obj,
    filename,
    metadata_dict
)

# Get file
file_path = Storage.get_file(stored_path)

# Delete file
Storage.delete_file(file_path)
```

### 5. Database Models
```python
from open_webui.models.files import Files
from open_webui.models.knowledge import Knowledges

# File operations
file = Files.get_file_by_id(file_id)
files = Files.get_files_by_user_id(user_id)
Files.update_file_data_by_id(file_id, {"status": "completed"})

# Knowledge operations
kb = Knowledges.get_knowledge_by_id(kb_id)
Knowledges.update_knowledge_data_by_id(kb_id, {"file_ids": [...]})
```

---

## Code File Reference

### Core Files
| File | Purpose |
|------|---------|
| `/backend/open_webui/routers/files.py` | File management API (12 endpoints) |
| `/backend/open_webui/routers/knowledge.py` | Knowledge base API (12 endpoints) |
| `/backend/open_webui/routers/retrieval.py` | RAG/retrieval API (18+ endpoints) |
| `/backend/open_webui/models/files.py` | File database model & ORM |
| `/backend/open_webui/models/knowledge.py` | Knowledge database model & ORM |

### Vector Database
| File | Purpose |
|------|---------|
| `/backend/open_webui/retrieval/vector/factory.py` | Vector DB factory & client |
| `/backend/open_webui/retrieval/vector/main.py` | Abstract interface |
| `/backend/open_webui/retrieval/vector/type.py` | Enums for DB types |
| `/backend/open_webui/retrieval/vector/dbs/` | 9 backend implementations |

### Document Processing
| File | Purpose |
|------|---------|
| `/backend/open_webui/retrieval/loaders/main.py` | Main document loader |
| `/backend/open_webui/retrieval/loaders/` | Specialized loaders (PDF, DOCX, etc.) |
| `/backend/open_webui/retrieval/utils.py` | Utility functions (embedding, reranking) |

### Storage
| File | Purpose |
|------|---------|
| `/backend/open_webui/storage/provider.py` | Multi-cloud storage abstraction |

### Frontend
| File | Purpose |
|------|---------|
| `/src/lib/apis/files/index.ts` | File API client (TypeScript) |
| `/src/lib/apis/knowledge/index.ts` | Knowledge base API client |
| `/src/lib/apis/retrieval/index.ts` | Retrieval API client |

---

## Database Migrations

Document storage system uses migrations for schema management:

```
backend/open_webui/migrations/versions/
├── 6a39f3d8e55c_add_knowledge_table.py
├── c0fbf31ca0db_update_file_table.py
├── 7826ab40b532_update_file_table.py
└── c29facfe716b_update_file_table_path.py
```

---

## Error Handling

Standard error responses:
```json
{
  "detail": "Error message"
}
```

Common error messages:
- `NOT_FOUND`: File/knowledge base not found
- `UNAUTHORIZED`: User not authenticated
- `ACCESS_PROHIBITED`: User lacks required permissions
- `FILE_NOT_PROCESSED`: File hasn't been processed yet
- `FILE_EXISTS`: Knowledge base name already exists

---

## Summary of All Endpoints

**Total: 42 API Endpoints**
- **Files**: 12 endpoints
- **Knowledge Bases**: 12 endpoints
- **Retrieval/RAG**: 18+ endpoints

All endpoints maintain authentication and access control through:
- `get_verified_user`: Standard user authentication
- `get_admin_user`: Admin-only operations
- `has_access_to_file()`: File-level access control
- `has_access()`: Knowledge base access control
- `has_permission()`: Feature-level permissions

---

## Integration Checklist for External Pipelines

- [ ] Configure vector database backend (chroma, qdrant, etc.)
- [ ] Set embedding model and engine
- [ ] Configure storage provider (local/S3/Azure/GCS)
- [ ] Import necessary models and routers
- [ ] Implement file upload workflow
- [ ] Set up knowledge base organization
- [ ] Configure access control rules
- [ ] Test document processing pipeline
- [ ] Verify vector indexing
- [ ] Test retrieval/query functionality
- [ ] Implement error handling and logging
- [ ] Monitor processing performance
- [ ] Set up database backups
- [ ] Configure rate limiting if needed
- [ ] Test with different document types
