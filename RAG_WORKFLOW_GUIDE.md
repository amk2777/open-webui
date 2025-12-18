# RAG Workflow in Open WebUI vs External Application

## 📋 Open WebUI's Actual RAG Workflow (Verified from Source Code)

Based on analysis of `backend/open_webui/utils/middleware.py` and related files:

### Complete Flow:

```
1. USER asks QUESTION
   └─> User sends message via chat API
   └─> middleware.py:process_chat_payload() (line 1102)

2. ATTACH FILES/KNOWLEDGE (if any)
   └─> Files or knowledge bases attached to chat
   └─> Could be documents, URLs, or knowledge collections

3. GENERATE OPTIMIZED QUERIES from user question
   └─> middleware.py:chat_completion_files_handler() (line 933-1049)
   └─> Calls generate_queries() (line 946-984)
   └─> LLM generates 1-3 optimized search queries
   └─> Example: "neural networks" → ["neural network architecture", "how neural networks learn"]
   └─> FALLBACK: If query generation fails, uses user's original message

4. SEARCH RAG using USER_ID and QUERIES
   └─> middleware.py:get_sources_from_items() (line 989-1013)
   └─> retrieval/utils.py:get_sources_from_items() (line 920-1194)
   └─> Queries all attached collections in parallel
   └─> Uses embedding_function to generate query embeddings
   └─> Optional: Hybrid search (vector + BM25)
   └─> Optional: Reranking for better results
   └─> Returns: sources with documents, metadata, distances

5. FORMAT CONTEXT for LLM (if sources found)
   └─> middleware.py:1514-1552
   └─> Build citation_idx_map: {source_id: 1, source_id2: 2, ...}
   └─> Format as XML:
       <source id="1" name="doc.pdf">document text</source>
       <source id="2" name="other.pdf">more text</source>
   └─> Apply RAG template (utils/task.py:rag_template(), line 189-227)
   └─> Template includes instructions for [1], [2] citation format

6. REPLACE USER MESSAGE with formatted prompt
   └─> middleware.py:1544-1552
   └─> Original: "What is machine learning?"
   └─> Modified: "### Task: Respond using context with citations [id]...
                  <context>
                  <source id="1">ML is a field of AI...</source>
                  </context>
                  Query: What is machine learning?"

7. SEND TO LLM
   └─> Modified messages sent to LLM API
   └─> LLM sees context and instructions
   └─> LLM generates response with inline citations

8. STREAM RESPONSE to USER
   └─> LLM response: "Machine learning is a field of AI [1] that involves..."
   └─> Response streamed back to user in real-time

9. SEND CITATIONS to USER (as event)
   └─> middleware.py:1562-1563
   └─> events.append({"sources": sources})
   └─> Frontend receives sources event
   └─> UI displays clickable citations below response
   └─> Citations show: [1] document.pdf, [2] other.pdf
```

---

## 🔍 Key Details from Source Code

### Step 3: Query Generation (Optional but Recommended)

**Location:** `middleware.py:946-984`

```python
# Generate optimized queries from user message + conversation history
res = await generate_queries(
    request,
    {
        "model": body["model"],
        "messages": body["messages"],  # Full conversation
        "type": "retrieval"
    },
    user
)

# LLM returns JSON: {"queries": ["query1", "query2", "query3"]}
queries = json.loads(response).get("queries", [])

# Fallback if generation fails
if len(queries) == 0:
    queries = [user_message]  # Use original message
```

**Why?** Optimized queries improve retrieval accuracy:
- User: "How do they work?" → Query: "neural network architecture and functionality"
- Converts conversational questions to search-optimized queries
- Can generate multiple queries for comprehensive search

### Step 4: RAG Search

**Location:** `middleware.py:989-1013`, `retrieval/utils.py:920-1194`

```python
sources = await get_sources_from_items(
    request=request,
    items=files,  # Files/knowledge bases attached
    queries=queries,  # Generated queries
    embedding_function=lambda query, prefix: request.app.state.EMBEDDING_FUNCTION(
        query, prefix=prefix, user=user
    ),
    k=request.app.state.config.TOP_K,  # Default: 5
    reranking_function=request.app.state.RERANKING_FUNCTION,
    k_reranker=request.app.state.config.TOP_K_RERANKER,
    r=request.app.state.config.RELEVANCE_THRESHOLD,
    hybrid_bm25_weight=request.app.state.config.HYBRID_BM25_WEIGHT,
    hybrid_search=request.app.state.config.ENABLE_RAG_HYBRID_SEARCH,
    user=user
)

# Returns: List of sources
# Each source: {
#   "source": {"id": "kb-id", "name": "General Knowledge"},
#   "document": ["text1", "text2", ...],
#   "metadata": [{"source": "doc.pdf", ...}, ...],
#   "distances": [0.15, 0.23, ...]
# }
```

### Step 5: Context Formatting

**Location:** `middleware.py:1514-1552`

```python
context_string = ""
citation_idx_map = {}

for source in sources:
    for document_text, document_metadata in zip(
        source["document"], source["metadata"]
    ):
        source_id = document_metadata.get("source") or "N/A"

        # Assign sequential citation IDs
        if source_id not in citation_idx_map:
            citation_idx_map[source_id] = len(citation_idx_map) + 1

        # Build XML context
        context_string += (
            f'<source id="{citation_idx_map[source_id]}" '
            f'name="{source_name}">{document_text}</source>\n'
        )

# Apply RAG template
formatted_prompt = rag_template(
    RAG_TEMPLATE,  # Instructions + placeholders
    context_string,  # XML context
    prompt  # Original user question
)

# Replace user message
form_data["messages"] = add_or_update_user_message(
    formatted_prompt,
    form_data["messages"],
    append=False  # Replace, don't append
)
```

### Step 6: RAG Template

**Location:** `config.py:2819-2839`

The template tells the LLM:
- How to use citations: `[1]`, `[2]` format
- Only cite when `<source id="X">` is present
- Respond in same language as query
- Don't use XML tags in response

### Step 9: Send Citations to UI

**Location:** `middleware.py:1562-1563`

```python
if len(sources) > 0:
    events.append({"sources": sources})

# Frontend receives this event separately
# UI renders citations below the response
# User can click [1] to see source document
```

---

## 🚀 How to Implement in Your External Repository

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   YOUR EXTERNAL APPLICATION                  │
│                                                              │
│  1. User Question                                           │
│      ↓                                                       │
│  2. Query Generation (optional LLM call)                    │
│      ↓                                                       │
│  3. Call RAG Client                                         │
│      ├─> query_rag_for_user()                              │
│      └─> Returns: results + context_string + citations     │
│      ↓                                                       │
│  4. Format LLM Prompt                                       │
│      ├─> format_sources_for_llm(response)                  │
│      └─> Returns: Full prompt with RAG template + context  │
│      ↓                                                       │
│  5. Send to Your LLM                                        │
│      └─> LLM responds with citations [1], [2]              │
│      ↓                                                       │
│  6. Display to User                                         │
│      ├─> Show LLM response                                 │
│      └─> Show citations with get_citation_map()            │
└─────────────────────────────────────────────────────────────┘
         │
         │ HTTP API Calls
         ↓
┌─────────────────────────────────────────────────────────────┐
│               OPEN WEBUI (Knowledge Base Only)               │
│   - Stores documents                                         │
│   - Handles chunking/embedding                              │
│   - Provides /api/v1/retrieval/query/* endpoints           │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Steps

#### Step 1: Query Generation (Optional but Recommended)

```python
async def generate_search_queries(
    user_message: str,
    conversation_history: List[dict],
    llm_client
) -> List[str]:
    """
    Generate optimized search queries from user message.

    Matches: Open WebUI's generate_queries() pattern (middleware.py:946-984)
    """
    prompt = f"""
Given the conversation history, generate 1-3 optimized search queries
to find relevant information to answer the user's latest question.

Conversation:
{json.dumps(conversation_history[-5:], indent=2)}

Latest question: {user_message}

Generate search queries that:
1. Are specific and searchable
2. Include key concepts and terminology
3. Rephrase conversational questions to search queries

Return ONLY a JSON object: {{"queries": ["query1", "query2"]}}
"""

    try:
        response = await llm_client.generate(prompt)
        queries = json.loads(response)["queries"]

        # Validate
        if not queries or len(queries) == 0:
            return [user_message]

        return queries
    except Exception as e:
        # Fallback to original message (matches Open WebUI)
        print(f"Query generation failed: {e}")
        return [user_message]


# Usage
queries = await generate_search_queries(
    user_message="How do they work?",
    conversation_history=[
        {"role": "user", "content": "Tell me about neural networks"},
        {"role": "assistant", "content": "Neural networks are..."}
    ],
    llm_client=your_llm
)
# Returns: ["neural network architecture and functionality"]
```

#### Step 2: Query RAG System

```python
from rag_client import query_rag_for_user

async def search_knowledge_base(
    queries: List[str],
    user_id: str,
    config: dict
) -> RAGQueryResponse:
    """
    Search RAG system with optimized queries.

    Note: rag_client queries with single query at a time.
    If you have multiple queries, you can:
    1. Query with first/best query (recommended)
    2. Query with all and merge results (advanced)
    """

    # Use the first/best query (matches Open WebUI's typical behavior)
    primary_query = queries[0] if queries else "search"

    response = await query_rag_for_user(
        query=primary_query,
        user_id=user_id,
        openwebui_url=config["openwebui_url"],
        api_key=config["api_key"],
        top_k=5,  # Number of results
        enable_hybrid_search=True,  # Vector + BM25
        enable_reranking=False,  # Optional
        format_for_llm=True  # Auto-generate XML context
    )

    return response


# Usage
rag_response = await search_knowledge_base(
    queries=["neural network architecture"],
    user_id="user-123",
    config={"openwebui_url": "http://localhost:3000", "api_key": "sk-..."}
)
```

#### Step 3: Format Prompt for LLM

```python
from rag_client import format_sources_for_llm, get_citation_map

async def prepare_llm_prompt(
    rag_response: RAGQueryResponse,
    original_message: str
) -> tuple[str, dict]:
    """
    Format RAG results into LLM prompt.

    Matches: Open WebUI's rag_template() and context formatting
    """

    if rag_response.total_results == 0:
        # No RAG context, send original message
        return original_message, {}

    # Get full formatted prompt (includes RAG template + context + query)
    llm_prompt = format_sources_for_llm(rag_response)

    # Get citation mapping for later display
    citations = get_citation_map(rag_response)

    return llm_prompt, citations


# Usage
llm_prompt, citations = await prepare_llm_prompt(
    rag_response,
    original_message="How do neural networks work?"
)

# llm_prompt contains:
# """
# ### Task:
# Respond using the provided context, incorporating inline citations [id]...
#
# <context>
# <source id="1" name="ml_basics.pdf">Neural networks consist of...</source>
# <source id="2" name="deep_learning.pdf">The architecture includes...</source>
# </context>
#
# Query: How do neural networks work?
# """

# citations = {1: "ml_basics.pdf", 2: "deep_learning.pdf"}
```

#### Step 4: Send to Your LLM

```python
async def get_rag_enhanced_response(
    user_message: str,
    conversation_history: List[dict],
    llm_client,
    rag_config: dict
) -> dict:
    """
    Complete RAG workflow with LLM response.
    """

    # Step 1: Generate optimized queries (optional)
    queries = await generate_search_queries(
        user_message,
        conversation_history,
        llm_client
    )

    # Step 2: Search RAG
    rag_response = await search_knowledge_base(
        queries,
        user_id=rag_config["user_id"],
        config=rag_config
    )

    # Step 3: Format prompt
    llm_prompt, citations = await prepare_llm_prompt(
        rag_response,
        user_message
    )

    # Step 4: Send to LLM
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        *conversation_history,
        {"role": "user", "content": llm_prompt}
    ]

    llm_response = await llm_client.chat(messages)

    # Step 5: Return response + citations
    return {
        "response": llm_response,
        "citations": citations,
        "sources_used": rag_response.total_results,
        "collections_searched": rag_response.collections_searched
    }


# Usage
result = await get_rag_enhanced_response(
    user_message="How do neural networks work?",
    conversation_history=[...],
    llm_client=your_llm,
    rag_config={
        "user_id": "user-123",
        "openwebui_url": "http://localhost:3000",
        "api_key": "sk-..."
    }
)

# Display to user
print(result["response"])
# "Neural networks consist of interconnected layers [1].
#  Each layer processes information [2]..."

print("\nReferences:")
for cit_id, source in result["citations"].items():
    print(f"  [{cit_id}] {source}")
# [1] ml_basics.pdf
# [2] deep_learning.pdf
```

#### Step 5: Display Citations in UI (Optional)

```python
def format_response_with_citations(
    llm_response: str,
    citations: dict
) -> dict:
    """
    Parse LLM response and extract citation references.
    """
    import re

    # Find all [1], [2], [3] patterns in response
    citation_pattern = r'\[(\d+)\]'
    used_citations = set()

    for match in re.finditer(citation_pattern, llm_response):
        cit_id = int(match.group(1))
        if cit_id in citations:
            used_citations.add(cit_id)

    # Build citation list
    citation_list = [
        {"id": cit_id, "source": citations[cit_id]}
        for cit_id in sorted(used_citations)
    ]

    return {
        "text": llm_response,
        "citations": citation_list
    }


# Usage
formatted = format_response_with_citations(
    "Neural networks use layers [1] and backpropagation [2].",
    citations={1: "ml_basics.pdf", 2: "deep_learning.pdf", 3: "unused.pdf"}
)

# Returns:
# {
#   "text": "Neural networks use layers [1] and backpropagation [2].",
#   "citations": [
#     {"id": 1, "source": "ml_basics.pdf"},
#     {"id": 2, "source": "deep_learning.pdf"}
#   ]
# }
```

---

## 🔄 Complete Example: Full Integration

```python
# complete_rag_workflow.py

import asyncio
from rag_client import (
    query_rag_for_user,
    format_sources_for_llm,
    get_citation_map
)

class RAGChatBot:
    """Complete RAG-enhanced chatbot implementation"""

    def __init__(self, llm_client, openwebui_url, api_key, user_id):
        self.llm = llm_client
        self.config = {
            "openwebui_url": openwebui_url,
            "api_key": api_key,
            "user_id": user_id
        }
        self.conversation = []

    async def generate_queries(self, message: str) -> List[str]:
        """Step 1: Generate optimized search queries"""
        if len(self.conversation) == 0:
            # First message, use as-is
            return [message]

        # Use LLM to generate queries (simplified)
        prompt = f"""
        Based on conversation, create 1-2 search queries for: "{message}"
        Return JSON: {{"queries": ["query1", "query2"]}}
        """

        try:
            response = await self.llm.generate(prompt)
            return json.loads(response)["queries"]
        except:
            return [message]  # Fallback

    async def search_rag(self, queries: List[str]):
        """Step 2: Search knowledge base"""
        return await query_rag_for_user(
            query=queries[0],  # Use primary query
            user_id=self.config["user_id"],
            openwebui_url=self.config["openwebui_url"],
            api_key=self.config["api_key"],
            top_k=5,
            enable_hybrid_search=True,
            format_for_llm=True
        )

    async def chat(self, user_message: str) -> dict:
        """Main chat method - handles complete RAG workflow"""

        # Step 1: Generate queries
        queries = await self.generate_queries(user_message)
        print(f"Generated queries: {queries}")

        # Step 2: Search RAG
        rag_response = await self.search_rag(queries)
        print(f"Found {rag_response.total_results} documents")

        # Step 3: Format prompt
        if rag_response.total_results > 0:
            # With RAG context
            llm_prompt = format_sources_for_llm(rag_response)
            citations = get_citation_map(rag_response)
        else:
            # No context found
            llm_prompt = user_message
            citations = {}

        # Step 4: Build messages
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            *self.conversation,
            {"role": "user", "content": llm_prompt}
        ]

        # Step 5: Get LLM response
        llm_response = await self.llm.chat(messages)

        # Update conversation history
        self.conversation.append({"role": "user", "content": user_message})
        self.conversation.append({"role": "assistant", "content": llm_response})

        return {
            "response": llm_response,
            "citations": citations,
            "sources": rag_response.total_results
        }


# Usage
async def main():
    bot = RAGChatBot(
        llm_client=your_llm,
        openwebui_url="http://localhost:3000",
        api_key="sk-...",
        user_id="user-123"
    )

    # User asks questions
    result1 = await bot.chat("What is machine learning?")
    print(result1["response"])
    print(f"Citations: {result1['citations']}")

    # Follow-up question (uses conversation context for query generation)
    result2 = await bot.chat("How does it work?")
    print(result2["response"])
    print(f"Citations: {result2['citations']}")

asyncio.run(main())
```

---

## ⚖️ Key Differences: Open WebUI vs Your External App

| Aspect | Open WebUI | Your External App |
|--------|------------|-------------------|
| **Query Generation** | Built-in with `generate_queries()` | You implement with your LLM |
| **RAG Access** | Direct internal function calls | HTTP API calls via `rag_client.py` |
| **Context Formatting** | Automatic in middleware | Use `format_sources_for_llm()` |
| **Citations** | WebSocket events to UI | You extract and display |
| **Conversation** | Managed by backend | You manage in your app |
| **Streaming** | Native SSE streaming | Your LLM's streaming |

---

## 📊 Flow Comparison

### Open WebUI (Internal)
```
User Message → Middleware → Query Gen → RAG Search → Format →
LLM → Stream Response → WebSocket Events (citations)
```

### Your External App
```
User Message → Your Backend → Query Gen (LLM) →
rag_client.query_rag_for_user() [HTTP] → format_sources_for_llm() →
Your LLM → Your Response Handler → Display (response + citations)
```

---

## ✅ Recommendations for Your External App

1. **✓ Use Query Generation** - Significantly improves retrieval quality
2. **✓ Use `format_for_llm=True`** - Automatically formats XML context
3. **✓ Enable Hybrid Search** - Better results than vector-only
4. **✓ Display Citations** - Use `get_citation_map()` to show sources
5. **✓ Cache Queries** - If same question asked, reuse RAG results
6. **✓ Handle No Results** - Gracefully fall back when RAG returns nothing
7. **✓ Manage Conversation** - Keep history for query generation context

---

## 🎯 Summary

**Your Proposed Flow:** ✅ Correct!
1. User asks QUESTION ✓
2. Generate QUERY from question (optional but recommended) ✓
3. Search RAG with USER_ID and QUERY ✓
4. If found, pass to LLM ✓
5. Show response ✓
6. Show citations ✓

**Key Addition:** Step 1.5 (Query Generation) significantly improves results!

The `rag_client.py` module handles steps 3-4 automatically and matches Open WebUI's implementation patterns exactly.
