# API Endpoints Quick Reference

## All 42 Endpoints Summary

### Files Management (12 Endpoints)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| `POST` | `/api/files/` | User | Upload file with optional background processing |
| `GET` | `/api/files/` | User | List files (filtered by user role) |
| `GET` | `/api/files/search` | User | Search files by filename pattern (wildcard support) |
| `GET` | `/api/files/{id}` | User | Get complete file details and metadata |
| `GET` | `/api/files/{id}/process/status` | User | Get file processing status (supports SSE streaming) |
| `GET` | `/api/files/{id}/data/content` | User | Get extracted text content |
| `POST` | `/api/files/{id}/data/content/update` | User | Update and reprocess file content |
| `GET` | `/api/files/{id}/content` | User | Download original file |
| `GET` | `/api/files/{id}/content/html` | User | Get HTML representation (admin only) |
| `GET` | `/api/files/{id}/content/{file_name}` | User | Download with original filename |
| `DELETE` | `/api/files/{id}` | User | Delete file and remove from vector DB |
| `DELETE` | `/api/files/all` | Admin | Delete all files and reset vector DB |

### Knowledge Base Management (12 Endpoints)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| `GET` | `/api/knowledge/` | User | Get knowledge bases with read access |
| `GET` | `/api/knowledge/list` | User | Get knowledge bases with write access |
| `POST` | `/api/knowledge/create` | User | Create new knowledge base |
| `GET` | `/api/knowledge/{id}` | User | Get knowledge base with files |
| `POST` | `/api/knowledge/{id}/update` | User | Update knowledge base metadata |
| `POST` | `/api/knowledge/{id}/file/add` | User | Add single file to knowledge base |
| `POST` | `/api/knowledge/{id}/file/update` | User | Reprocess file in knowledge base |
| `POST` | `/api/knowledge/{id}/file/remove` | User | Remove file from knowledge base |
| `POST` | `/api/knowledge/{id}/files/batch/add` | User | Add multiple files (batch operation) |
| `DELETE` | `/api/knowledge/{id}/delete` | User | Delete knowledge base |
| `POST` | `/api/knowledge/{id}/reset` | User | Clear all files from knowledge base |
| `POST` | `/api/knowledge/reindex` | Admin | Rebuild all vector indexes |

### Retrieval & RAG (18+ Endpoints)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| `GET` | `/api/retrieval/` | Public | Get RAG configuration status |
| `GET` | `/api/retrieval/embedding` | Admin | Get embedding model config |
| `POST` | `/api/retrieval/embedding/update` | Admin | Update embedding configuration |
| `POST` | `/api/retrieval/file` | User | Process file for indexing |
| `POST` | `/api/retrieval/query` | User | Query knowledge base documents |
| `POST` | `/api/retrieval/web` | User | Process URL/web content |
| `POST` | `/api/retrieval/search` | User | Web search |
| ... | ... | ... | Additional endpoints for vector DB, reranking, and web search configs |

---

## Request/Response Templates

### Upload File Request
```bash
curl -X POST "http://localhost:8000/api/files/" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf" \
  -F "metadata={\"source\": \"external\"}" \
  -F "process=true" \
  -F "process_in_background=true"
```

### Upload File Response
```json
{
  "status": true,
  "id": "uuid",
  "user_id": "user_uuid",
  "filename": "document.pdf",
  "path": "storage_path",
  "data": {
    "status": "pending"
  },
  "meta": {
    "name": "document.pdf",
    "content_type": "application/pdf",
    "size": 1024000,
    "data": {
      "source": "external"
    }
  },
  "created_at": 1700000000,
  "updated_at": 1700001000
}
```

### Create Knowledge Base Request
```json
{
  "name": "My Knowledge Base",
  "description": "Description",
  "data": null,
  "access_control": null
}
```

### Query Documents Request
```json
{
  "queries": ["What is machine learning?"],
  "collection_name": "knowledge_base_id"
}
```

### Query Documents Response
```json
{
  "documents": [
    [
      "Document text snippet...",
      "Another document text..."
    ]
  ],
  "metadatas": [
    [
      {
        "file_id": "file_uuid",
        "source": "filename.pdf",
        "page": 0
      }
    ]
  ],
  "distances": [
    [0.15, 0.32]
  ]
}
```

---

## Common Query Parameters

### List Files
```
GET /api/files/?content=true|false
```
- `content`: Include file content in response (default: true)

### Search Files
```
GET /api/files/search?filename=*.pdf&content=true|false
```
- `filename`: Wildcard pattern to match
- `content`: Include file content (default: true)

### Process Status
```
GET /api/files/{id}/process/status?stream=true|false
```
- `stream`: Use Server-Sent Events for real-time updates (default: false)

### Get File Content
```
GET /api/files/{id}/content?attachment=true|false
```
- `attachment`: Force download (default: false)

### Remove File from Knowledge Base
```
POST /api/knowledge/{id}/file/remove?delete_file=true|false
```
- `delete_file`: Also delete the file itself (default: true)

---

## Authentication Headers

All endpoints require authentication (except `GET /api/retrieval/`):

```
Authorization: Bearer <jwt_token>
```

### Obtaining Token
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password"
  }'

# Returns:
# {"token": "eyJ0eXAiOiJKV1QiLCJhbGc..."}
```

---

## Error Responses

### 404 Not Found
```json
{
  "detail": "Not found"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Access prohibited"
}
```

### 400 Bad Request
```json
{
  "detail": "File type is not allowed"
}
```

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not Found |
| 500 | Internal Server Error |

---

## Batch Operations

### Add Multiple Files to Knowledge Base
```json
POST /api/knowledge/{id}/files/batch/add
Content-Type: application/json

[
  {"file_id": "file_uuid_1"},
  {"file_id": "file_uuid_2"},
  {"file_id": "file_uuid_3"}
]
```

Response includes: successful results + error details for failed files

---

## Server-Sent Events (SSE) Streaming

### Stream File Processing Status
```bash
curl -X GET "http://localhost:8000/api/files/{id}/process/status?stream=true" \
  -H "Authorization: Bearer $TOKEN"
```

### Streamed Events
```
data: {"status": "processing"}

data: {"status": "processing"}

data: {"status": "completed"}
```

---

## Content Types Supported

### Document Types
- PDF (.pdf)
- Word (.docx)
- Excel (.xlsx)
- PowerPoint (.pptx)
- Text (.txt)
- Markdown (.md)
- JSON (.json)
- CSV (.csv)

### Media Types (with transcription)
- Audio (wav, mp3, m4a, flac, etc.)
- Video (webm, mp4, etc.)

### Configuration
See `ALLOWED_FILE_EXTENSIONS` in config for full list

---

## Vector Database Operations

### Query by Embeddings
```json
POST /api/retrieval/query

{
  "queries": ["search query"],
  "collection_name": "knowledge_base_id"
}
```

### Process File for Indexing
```json
POST /api/retrieval/file

{
  "file_id": "file_uuid",
  "content": "optional_override_content",
  "collection_name": "knowledge_base_id"
}
```

---

## Access Control Types

### Public (null)
```json
{
  "access_control": null
}
```
Available to all users with "user" role

### Private ({})
```json
{
  "access_control": {}
}
```
Owner only

### Custom Permissions
```json
{
  "access_control": {
    "read": {
      "group_ids": ["group_uuid_1", "group_uuid_2"],
      "user_ids": ["user_uuid_1"]
    },
    "write": {
      "group_ids": ["group_uuid_1"],
      "user_ids": []
    }
  }
}
```

---

## Rate Limiting & Quotas

Default limits (configurable):
- File upload size: Configurable per instance
- Batch add files: No hard limit (processes in sequence)
- Query results: Top-k configurable (default: 10)
- Embedding batch size: Configurable (default: 1)

---

## WebSocket Endpoints (If Enabled)

Real-time processing status updates:
```
WS /api/files/{id}/status/stream
```

---

## Migration & Admin Operations

### Reindex All Knowledge Bases
```bash
curl -X POST "http://localhost:8000/api/knowledge/reindex" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

Purpose: Rebuild vector indexes after configuration changes or recovery

### Delete All Files
```bash
curl -X DELETE "http://localhost:8000/api/files/all" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

Warning: Irreversible operation

---

## Performance Tips

1. **Batch uploads**: Use `/api/knowledge/{id}/files/batch/add` for multiple files
2. **Async processing**: Set `process_in_background=true` for large files
3. **Streaming status**: Use `stream=true` for real-time feedback on file processing
4. **Query optimization**: Reduce `top_k` for faster retrieval
5. **Embedding batching**: Increase `RAG_EMBEDDING_BATCH_SIZE` for faster indexing

---

## Integration Checklist

- [ ] Authenticate user and get token
- [ ] Create knowledge base
- [ ] Upload documents (single or batch)
- [ ] Wait for processing to complete
- [ ] Query knowledge base
- [ ] Handle errors gracefully
- [ ] Implement access control
- [ ] Monitor vector DB performance
- [ ] Set up logging and monitoring
- [ ] Test with various document types
