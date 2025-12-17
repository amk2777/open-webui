"""
Standalone RAG Query Client for Open WebUI - Aligned with Original Implementation

This module provides a simple interface to query Open WebUI's RAG system from external applications.
It closely follows the original Open WebUI RAG implementation patterns.

Based on Open WebUI's RAG implementation:
- backend/open_webui/utils/middleware.py (lines 933-1049, 1513-1578)
- backend/open_webui/retrieval/utils.py (lines 920-1194)
- backend/open_webui/utils/task.py (lines 189-227)
- backend/open_webui/config.py (lines 2819-2839)

Dependencies:
    pip install httpx pydantic

Usage:
    from rag_client import query_rag_for_user, format_sources_for_llm

    # Query RAG
    results = await query_rag_for_user(
        query="What is machine learning?",
        user_id="user-uuid",
        openwebui_url="http://localhost:3000",
        api_key="sk-..."
    )

    # Format for LLM context (matches Open WebUI format)
    context_xml = format_sources_for_llm(results)
"""

import asyncio
from typing import List, Dict, Optional, Any, Tuple
import httpx
from pydantic import BaseModel


# ============================================================================
# DEFAULT RAG TEMPLATE (from Open WebUI config.py:2819-2839)
# ============================================================================

DEFAULT_RAG_TEMPLATE = """### Task:
Respond to the user query using the provided context, incorporating inline citations in the format [id] **only when the <source> tag includes an explicit id attribute** (e.g., <source id="1">).

### Guidelines:
- If you don't know the answer, clearly state that.
- If uncertain, ask the user for clarification.
- Respond in the same language as the user's query.
- If the context is unreadable or of poor quality, inform the user and provide the best possible answer.
- If the answer isn't present in the context but you possess the knowledge, explain this to the user and provide the answer using your own understanding.
- **Only include inline citations using [id] (e.g., [1], [2]) when the <source> tag includes an id attribute.**
- Do not cite if the <source> tag does not contain an id attribute.
- Do not use XML tags in your response.
- Ensure citations are concise and directly related to the information provided.

### Example of Citation:
If the user asks about a specific topic and the information is found in a source with a provided id attribute, the response should include the citation like in the following example:
* "According to the study, the proposed method increases efficiency by 20% [1]."

### Output:
Provide a clear and direct response to the user's query, including inline citations in the format [id] only when the <source> tag with id attribute is present in the context.

<context>
{{CONTEXT}}
</context>

Query: {{QUERY}}"""


# ============================================================================
# Data Models
# ============================================================================

class DocumentResult(BaseModel):
    """Single document result from RAG query (aligned with Open WebUI format)"""
    text: str  # Document text content
    metadata: Dict[str, Any]  # Metadata (source, file_id, etc.)
    distance: float  # Vector distance (lower = more similar)
    relevance_score: float  # 0-1 score (higher = better), derived from distance
    source: Optional[str] = None  # Source filename/identifier
    collection_id: str  # Collection UUID
    collection_name: str  # Human-readable collection name
    citation_id: Optional[int] = None  # Citation number for LLM (1, 2, 3...)


class RAGQueryResponse(BaseModel):
    """Structured response from RAG query"""
    query: str  # Original query text
    total_results: int  # Number of results returned
    results: List[DocumentResult]  # Ranked document results
    collections_searched: List[Dict[str, str]]  # Collections that were queried
    execution_time_ms: float  # Query execution time
    context_string: Optional[str] = None  # Formatted context for LLM (XML format)


# ============================================================================
# Core RAG Query Function
# ============================================================================

async def query_rag_for_user(
    query: str,
    user_id: str,
    openwebui_url: str,
    api_key: str,
    top_k: int = 5,
    top_k_per_collection: int = 10,
    relevance_threshold: float = 0.0,
    enable_hybrid_search: bool = True,
    enable_reranking: bool = False,
    timeout: float = 60.0,
    format_for_llm: bool = True
) -> RAGQueryResponse:
    """
    Query all RAG collections accessible to a user and return ranked results.

    This implementation follows Open WebUI's RAG query pattern:
    1. Fetch all knowledge bases (collections) user has access to
    2. Query each collection in parallel using the same query
    3. Merge and rank results by relevance (distance-based scoring)
    4. Optionally format results as XML context string for LLM

    QUERY GENERATION NOTE:
    -----------------------
    In Open WebUI's full implementation (middleware.py:946-984), the query
    is optionally generated from the user's message using an LLM call to
    create optimized search queries. This happens via:

        generate_queries(request, {
            "model": body["model"],
            "messages": body["messages"],
            "type": "retrieval"
        }, user)

    The LLM can return multiple refined queries for better retrieval, or
    fall back to using the user's message directly.

    For this standalone client, we use the query directly (same as the fallback).
    If you want to implement query generation in your application:
    1. Call your LLM with the user's conversation history
    2. Ask it to generate optimized search queries
    3. Pass those queries to this function

    Example prompt for query generation:
        "Given the conversation history, generate 1-3 optimized search queries
         to find relevant information to answer the user's question.
         Return as JSON: {'queries': ['query1', 'query2', ...]}"

    Args:
        query: Search query text (can be user message or LLM-generated query)
        user_id: User ID (used for logging, auth is via API key)
        openwebui_url: Base URL of Open WebUI (e.g., "http://localhost:3000")
        api_key: Open WebUI API key (starts with "sk-")
        top_k: Final number of results to return (default: 5)
        top_k_per_collection: Results per collection before ranking (default: 10)
        relevance_threshold: Min relevance score 0-1 (default: 0.0)
        enable_hybrid_search: Use vector + BM25 hybrid search (default: True)
        enable_reranking: Use reranking model if available (default: False)
        timeout: Request timeout in seconds (default: 60.0)
        format_for_llm: Generate XML context string (default: True)

    Returns:
        RAGQueryResponse with ranked results and optional formatted context

    Raises:
        httpx.HTTPError: If API requests fail
        ValueError: If no collections are accessible
    """
    import time
    start_time = time.time()

    async with httpx.AsyncClient(timeout=timeout) as client:
        # Step 1: Get all collections user has access to
        # Matches: middleware.py get_sources_from_items() pattern
        collections = await _get_user_collections(
            client=client,
            openwebui_url=openwebui_url,
            api_key=api_key
        )

        if not collections:
            raise ValueError(f"No knowledge bases accessible for user {user_id}")

        # Step 2: Query all collections in parallel
        # Matches: middleware.py:1144-1167 query pattern
        query_tasks = [
            _query_single_collection(
                client=client,
                openwebui_url=openwebui_url,
                api_key=api_key,
                collection_id=col["id"],
                collection_name=col["name"],
                query=query,
                k=top_k_per_collection,
                hybrid=enable_hybrid_search,
                enable_reranking=enable_reranking
            )
            for col in collections
        ]

        collection_results = await asyncio.gather(*query_tasks, return_exceptions=True)

        # Step 3: Merge and rank results
        # Matches: retrieval/utils.py:1178-1194 sources building pattern
        all_results = []
        for idx, result in enumerate(collection_results):
            if isinstance(result, Exception):
                # Log error but continue (matches Open WebUI error handling)
                print(f"Error querying collection {collections[idx]['name']}: {result}")
                continue
            all_results.extend(result)

        # Sort by relevance score (higher is better)
        all_results.sort(key=lambda x: x.relevance_score, reverse=True)

        # Apply relevance threshold and limit to top_k
        filtered_results = [
            r for r in all_results
            if r.relevance_score >= relevance_threshold
        ][:top_k]

        # Step 4: Assign citation IDs (matches middleware.py:1516-1531)
        citation_idx_map = {}
        for result in filtered_results:
            source_id = result.source or result.metadata.get("source") or "N/A"
            if source_id not in citation_idx_map:
                citation_idx_map[source_id] = len(citation_idx_map) + 1
            result.citation_id = citation_idx_map[source_id]

        # Step 5: Optionally format context for LLM (matches middleware.py:1515-1552)
        context_string = None
        if format_for_llm and filtered_results:
            context_string = _format_context_for_llm(filtered_results)

        execution_time = (time.time() - start_time) * 1000  # Convert to ms

        return RAGQueryResponse(
            query=query,
            total_results=len(filtered_results),
            results=filtered_results,
            collections_searched=[
                {"id": col["id"], "name": col["name"]}
                for col in collections
            ],
            execution_time_ms=execution_time,
            context_string=context_string
        )


# ============================================================================
# Helper Functions
# ============================================================================

async def _get_user_collections(
    client: httpx.AsyncClient,
    openwebui_url: str,
    api_key: str
) -> List[Dict[str, str]]:
    """
    Get all knowledge bases (collections) accessible to the user.

    Matches: middleware.py get_sources_from_items() collection fetching

    Returns:
        List of dicts with 'id', 'name', and 'description' keys
    """
    url = f"{openwebui_url}/api/v1/knowledge/list"
    headers = {"Authorization": f"Bearer {api_key}"}

    response = await client.get(url, headers=headers)
    response.raise_for_status()

    knowledge_bases = response.json()

    return [
        {
            "id": kb["id"],  # This is the collection UUID used in queries
            "name": kb.get("name", "Unknown"),
            "description": kb.get("description", "")
        }
        for kb in knowledge_bases
    ]


async def _query_single_collection(
    client: httpx.AsyncClient,
    openwebui_url: str,
    api_key: str,
    collection_id: str,
    collection_name: str,
    query: str,
    k: int,
    hybrid: bool,
    enable_reranking: bool = False
) -> List[DocumentResult]:
    """
    Query a single collection and return results.

    Matches: middleware.py:1144-1167 query_collection_with_hybrid_search pattern

    Returns:
        List of DocumentResult objects
    """
    url = f"{openwebui_url}/api/v1/retrieval/query/doc"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "collection_name": collection_id,  # Uses UUID, not human name
        "query": query,
        "k": k,
        "hybrid": hybrid
    }

    # Add reranking if enabled (matches Open WebUI pattern)
    if enable_reranking:
        payload["k_reranker"] = min(k, 10)  # Typically rerank fewer results

    try:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        # Parse results (matches retrieval/utils.py:1178-1194)
        results = []
        documents = data.get("documents", [])
        metadatas = data.get("metadatas", [])
        distances = data.get("distances", [])

        for idx, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
            # Convert distance to relevance score (0-1, higher is better)
            # Distance is typically 0-2 for cosine distance
            # Matches Open WebUI's distance handling
            relevance_score = max(0.0, 1.0 - (distance / 2.0))

            results.append(DocumentResult(
                text=doc,
                metadata=metadata,
                distance=distance,
                relevance_score=relevance_score,
                source=metadata.get("source") or metadata.get("file_name") or metadata.get("name"),
                collection_id=collection_id,
                collection_name=collection_name
            ))

        return results

    except httpx.HTTPError as e:
        raise Exception(f"Failed to query collection {collection_name}: {str(e)}") from e


def _format_context_for_llm(results: List[DocumentResult]) -> str:
    """
    Format results as XML context string for LLM consumption.

    Matches: middleware.py:1515-1539 context_string formatting

    Format:
        <source id="1" name="filename.pdf">document text</source>
        <source id="2" name="other.pdf">more text</source>

    The citation IDs should already be assigned to each result.

    Returns:
        XML-formatted context string
    """
    context_parts = []

    for result in results:
        # Build source tag attributes
        source_tag = f'<source id="{result.citation_id}"'

        # Add name attribute if source is available
        if result.source:
            source_tag += f' name="{result.source}"'

        # Close opening tag and add content
        source_tag += f'>{result.text}</source>'

        context_parts.append(source_tag)

    return "\n".join(context_parts)


def format_sources_for_llm(
    response: RAGQueryResponse,
    rag_template: Optional[str] = None
) -> str:
    """
    Format RAG query response using the RAG template (full LLM prompt).

    Matches: utils/task.py:189-227 rag_template() function and
             middleware.py:1544-1552 template application

    This creates the complete prompt that would be sent to the LLM,
    including the RAG template instructions, context, and query.

    Args:
        response: RAG query response with results
        rag_template: Custom RAG template (defaults to Open WebUI's template)

    Returns:
        Formatted string ready to be added to LLM messages
    """
    if rag_template is None:
        rag_template = DEFAULT_RAG_TEMPLATE

    # Get or generate context string
    context = response.context_string
    if context is None:
        context = _format_context_for_llm(response.results) if response.results else ""

    # Replace template placeholders (matches task.py:218-222)
    result = rag_template.replace("[context]", context)
    result = result.replace("{{CONTEXT}}", context)
    result = result.replace("[query]", response.query)
    result = result.replace("{{QUERY}}", response.query)

    return result


def format_context_only(response: RAGQueryResponse) -> str:
    """
    Get just the XML context string (without template).

    Useful if you want to insert context into your own custom prompt.

    Returns:
        XML-formatted context: <source id="1">...</source>
    """
    if response.context_string:
        return response.context_string
    return _format_context_for_llm(response.results) if response.results else ""


def get_unique_sources(response: RAGQueryResponse) -> List[str]:
    """
    Extract unique source documents referenced in results.

    Matches: middleware.py:1019-1036 unique_ids extraction

    Returns:
        Sorted list of unique source filenames/identifiers
    """
    sources = set()
    for result in response.results:
        if result.source:
            sources.add(result.source)
    return sorted(list(sources))


def get_citation_map(response: RAGQueryResponse) -> Dict[int, str]:
    """
    Get mapping of citation IDs to source names.

    Useful for displaying citations to users or generating reference lists.

    Returns:
        Dict mapping citation_id -> source_name
        Example: {1: "document.pdf", 2: "other.pdf"}
    """
    citation_map = {}
    for result in response.results:
        if result.citation_id and result.source:
            citation_map[result.citation_id] = result.source
    return citation_map


# ============================================================================
# Alternative: Query Specific Collections
# ============================================================================

async def query_rag_specific_collections(
    query: str,
    collection_ids: List[str],
    openwebui_url: str,
    api_key: str,
    top_k: int = 5,
    top_k_per_collection: int = 10,
    enable_hybrid_search: bool = True,
    enable_reranking: bool = False,
    timeout: float = 60.0,
    format_for_llm: bool = True
) -> RAGQueryResponse:
    """
    Query specific collections by ID (when you know which ones to search).

    Args:
        query: Search query text
        collection_ids: List of collection UUIDs to search
        openwebui_url: Base URL of Open WebUI
        api_key: API key
        top_k: Final number of results
        top_k_per_collection: Results per collection
        enable_hybrid_search: Use hybrid search
        enable_reranking: Use reranking
        timeout: Request timeout
        format_for_llm: Generate XML context

    Returns:
        RAGQueryResponse with ranked results
    """
    import time
    start_time = time.time()

    async with httpx.AsyncClient(timeout=timeout) as client:
        # Query specified collections in parallel
        query_tasks = [
            _query_single_collection(
                client=client,
                openwebui_url=openwebui_url,
                api_key=api_key,
                collection_id=col_id,
                collection_name=f"Collection-{col_id[:8]}",
                query=query,
                k=top_k_per_collection,
                hybrid=enable_hybrid_search,
                enable_reranking=enable_reranking
            )
            for col_id in collection_ids
        ]

        collection_results = await asyncio.gather(*query_tasks, return_exceptions=True)

        # Merge and rank
        all_results = []
        for result in collection_results:
            if not isinstance(result, Exception):
                all_results.extend(result)

        all_results.sort(key=lambda x: x.relevance_score, reverse=True)
        final_results = all_results[:top_k]

        # Assign citation IDs
        citation_idx_map = {}
        for result in final_results:
            source_id = result.source or "N/A"
            if source_id not in citation_idx_map:
                citation_idx_map[source_id] = len(citation_idx_map) + 1
            result.citation_id = citation_idx_map[source_id]

        # Format context
        context_string = None
        if format_for_llm and final_results:
            context_string = _format_context_for_llm(final_results)

        execution_time = (time.time() - start_time) * 1000

        return RAGQueryResponse(
            query=query,
            total_results=len(final_results),
            results=final_results,
            collections_searched=[
                {"id": col_id, "name": f"Collection-{col_id[:8]}"}
                for col_id in collection_ids
            ],
            execution_time_ms=execution_time,
            context_string=context_string
        )
