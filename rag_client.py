"""
Standalone RAG Query Client for Open WebUI

This module provides a simple interface to query Open WebUI's RAG system.
Can be easily integrated into any Python project.

Dependencies:
    pip install httpx pydantic

Usage:
    from rag_client import query_rag_for_user

    results = await query_rag_for_user(
        query="What is machine learning?",
        user_id="user-uuid",
        openwebui_url="http://localhost:3000",
        api_key="sk-..."
    )
"""

import asyncio
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import httpx
from pydantic import BaseModel


# ============================================================================
# Data Models
# ============================================================================

class DocumentResult(BaseModel):
    """Single document result from RAG query"""
    text: str
    metadata: Dict[str, Any]
    distance: float  # Lower is better (more similar)
    relevance_score: float  # 0-1, higher is better
    source: Optional[str] = None
    collection_id: str
    collection_name: str


class RAGQueryResponse(BaseModel):
    """Structured response from RAG query"""
    query: str
    total_results: int
    results: List[DocumentResult]
    collections_searched: List[Dict[str, str]]
    execution_time_ms: float


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
    timeout: float = 60.0
) -> RAGQueryResponse:
    """
    Query all RAG collections accessible to a user and return ranked results.

    This function:
    1. Fetches all knowledge bases the user has access to
    2. Queries each collection in parallel
    3. Merges and ranks results by relevance
    4. Returns top K most relevant documents

    Args:
        query: Search query text
        user_id: User ID (currently used for logging, auth is via API key)
        openwebui_url: Base URL of Open WebUI instance (e.g., "http://localhost:3000")
        api_key: Open WebUI API key (starts with "sk-")
        top_k: Number of final results to return (default: 5)
        top_k_per_collection: Results to fetch per collection before ranking (default: 10)
        relevance_threshold: Minimum relevance score (0-1) to include (default: 0.0)
        enable_hybrid_search: Use hybrid search (vector + BM25) (default: True)
        timeout: Request timeout in seconds (default: 60.0)

    Returns:
        RAGQueryResponse with ranked results

    Raises:
        httpx.HTTPError: If API requests fail
        ValueError: If no collections are accessible
    """
    import time
    start_time = time.time()

    async with httpx.AsyncClient(timeout=timeout) as client:
        # Step 1: Get all collections user has access to
        collections = await _get_user_collections(
            client=client,
            openwebui_url=openwebui_url,
            api_key=api_key
        )

        if not collections:
            raise ValueError(f"No knowledge bases accessible for user {user_id}")

        # Step 2: Query all collections in parallel
        query_tasks = [
            _query_single_collection(
                client=client,
                openwebui_url=openwebui_url,
                api_key=api_key,
                collection_id=col["id"],
                collection_name=col["name"],
                query=query,
                k=top_k_per_collection,
                hybrid=enable_hybrid_search
            )
            for col in collections
        ]

        collection_results = await asyncio.gather(*query_tasks, return_exceptions=True)

        # Step 3: Merge and rank results
        all_results = []
        for idx, result in enumerate(collection_results):
            if isinstance(result, Exception):
                # Log error but continue with other collections
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

        execution_time = (time.time() - start_time) * 1000  # Convert to ms

        return RAGQueryResponse(
            query=query,
            total_results=len(filtered_results),
            results=filtered_results,
            collections_searched=[
                {"id": col["id"], "name": col["name"]}
                for col in collections
            ],
            execution_time_ms=execution_time
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

    Returns:
        List of dicts with 'id' and 'name' keys
    """
    url = f"{openwebui_url}/api/v1/knowledge/list"
    headers = {"Authorization": f"Bearer {api_key}"}

    response = await client.get(url, headers=headers)
    response.raise_for_status()

    knowledge_bases = response.json()

    # Extract id and name for each knowledge base
    return [
        {
            "id": kb["id"],
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
    hybrid: bool
) -> List[DocumentResult]:
    """
    Query a single collection and return results.

    Returns:
        List of DocumentResult objects
    """
    url = f"{openwebui_url}/api/v1/retrieval/query/doc"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "collection_name": collection_id,  # Note: uses UUID, not human name
        "query": query,
        "k": k,
        "hybrid": hybrid
    }

    try:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        # Parse results
        results = []
        documents = data.get("documents", [])
        metadatas = data.get("metadatas", [])
        distances = data.get("distances", [])

        for idx, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
            # Convert distance to relevance score (0-1, higher is better)
            # Distance is typically 0-2 for cosine distance
            relevance_score = max(0.0, 1.0 - (distance / 2.0))

            results.append(DocumentResult(
                text=doc,
                metadata=metadata,
                distance=distance,
                relevance_score=relevance_score,
                source=metadata.get("source") or metadata.get("file_name"),
                collection_id=collection_id,
                collection_name=collection_name
            ))

        return results

    except httpx.HTTPError as e:
        # Re-raise with more context
        raise Exception(f"Failed to query collection {collection_name}: {str(e)}") from e


# ============================================================================
# Alternative: Query with Collection Filtering
# ============================================================================

async def query_rag_specific_collections(
    query: str,
    collection_ids: List[str],
    openwebui_url: str,
    api_key: str,
    top_k: int = 5,
    top_k_per_collection: int = 10,
    enable_hybrid_search: bool = True,
    timeout: float = 60.0
) -> RAGQueryResponse:
    """
    Query specific collections by ID (useful when you know which collections to search).

    Args:
        query: Search query text
        collection_ids: List of collection IDs (UUIDs) to search
        openwebui_url: Base URL of Open WebUI instance
        api_key: Open WebUI API key
        top_k: Number of final results to return
        top_k_per_collection: Results per collection before ranking
        enable_hybrid_search: Use hybrid search
        timeout: Request timeout in seconds

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
                collection_name=f"Collection-{col_id[:8]}",  # Short name
                query=query,
                k=top_k_per_collection,
                hybrid=enable_hybrid_search
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

        execution_time = (time.time() - start_time) * 1000

        return RAGQueryResponse(
            query=query,
            total_results=len(final_results),
            results=final_results,
            collections_searched=[
                {"id": col_id, "name": f"Collection-{col_id[:8]}"}
                for col_id in collection_ids
            ],
            execution_time_ms=execution_time
        )


# ============================================================================
# Convenience Functions
# ============================================================================

def format_results_for_llm(response: RAGQueryResponse) -> str:
    """
    Format RAG results as context for an LLM.

    Returns:
        Formatted string with numbered results
    """
    if not response.results:
        return "No relevant information found."

    context_parts = [
        f"Found {response.total_results} relevant documents for query: '{response.query}'\n"
    ]

    for idx, result in enumerate(response.results, 1):
        source_info = f" (from {result.source})" if result.source else ""
        context_parts.append(
            f"\n[{idx}] Relevance: {result.relevance_score:.2f}{source_info}\n"
            f"{result.text}\n"
        )

    return "\n".join(context_parts)


def get_unique_sources(response: RAGQueryResponse) -> List[str]:
    """Get list of unique source documents referenced in results."""
    sources = set()
    for result in response.results:
        if result.source:
            sources.add(result.source)
    return sorted(list(sources))
