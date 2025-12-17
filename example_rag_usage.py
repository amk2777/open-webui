"""
Example usage of the standalone RAG client.

This demonstrates how to integrate rag_client.py into your own application.
"""

import asyncio
from rag_client import (
    query_rag_for_user,
    query_rag_specific_collections,
    format_results_for_llm,
    get_unique_sources
)


async def example_basic_query():
    """Example 1: Basic query across all user's collections"""
    print("=" * 80)
    print("Example 1: Basic RAG Query")
    print("=" * 80)

    response = await query_rag_for_user(
        query="What is toxpath?",
        user_id="d58b68d7-9bf6-41b2-a156-9b0859530b4b",  # Your user ID
        openwebui_url="http://localhost:3000",
        api_key="sk-your-api-key-here",  # Replace with your API key
        top_k=3,
        enable_hybrid_search=True
    )

    print(f"\nQuery: {response.query}")
    print(f"Total Results: {response.total_results}")
    print(f"Execution Time: {response.execution_time_ms:.2f}ms")
    print(f"\nCollections Searched:")
    for col in response.collections_searched:
        print(f"  - {col['name']} ({col['id']})")

    print(f"\nTop {len(response.results)} Results:")
    for idx, result in enumerate(response.results, 1):
        print(f"\n[{idx}] Relevance: {result.relevance_score:.3f}")
        print(f"    Collection: {result.collection_name}")
        print(f"    Source: {result.source or 'Unknown'}")
        print(f"    Text: {result.text[:200]}...")

    return response


async def example_specific_collections():
    """Example 2: Query specific collections"""
    print("\n" + "=" * 80)
    print("Example 2: Query Specific Collections")
    print("=" * 80)

    response = await query_rag_specific_collections(
        query="What information is available?",
        collection_ids=[
            "f248a97e-ec6c-41d2-974c-e4ecddd8df77"  # Your collection ID
        ],
        openwebui_url="http://localhost:3000",
        api_key="sk-your-api-key-here",
        top_k=5
    )

    print(f"\nQuery: {response.query}")
    print(f"Results: {response.total_results}")

    return response


async def example_format_for_llm():
    """Example 3: Format results for LLM context"""
    print("\n" + "=" * 80)
    print("Example 3: Format Results for LLM")
    print("=" * 80)

    response = await query_rag_for_user(
        query="Explain the main topics",
        user_id="d58b68d7-9bf6-41b2-a156-9b0859530b4b",
        openwebui_url="http://localhost:3000",
        api_key="sk-your-api-key-here",
        top_k=3
    )

    # Format for use as LLM context
    llm_context = format_results_for_llm(response)
    print("\nFormatted for LLM:")
    print(llm_context)

    # Get unique sources
    sources = get_unique_sources(response)
    print(f"\nUnique Sources: {sources}")

    return response


async def example_with_filters():
    """Example 4: Query with relevance threshold"""
    print("\n" + "=" * 80)
    print("Example 4: Query with Relevance Threshold")
    print("=" * 80)

    response = await query_rag_for_user(
        query="machine learning concepts",
        user_id="d58b68d7-9bf6-41b2-a156-9b0859530b4b",
        openwebui_url="http://localhost:3000",
        api_key="sk-your-api-key-here",
        top_k=10,
        relevance_threshold=0.7,  # Only return results with >70% relevance
        enable_hybrid_search=True
    )

    print(f"\nQuery: {response.query}")
    print(f"Results (relevance > 0.7): {response.total_results}")

    for result in response.results:
        print(f"\n  Relevance: {result.relevance_score:.3f} | {result.source}")

    return response


async def example_error_handling():
    """Example 5: Error handling"""
    print("\n" + "=" * 80)
    print("Example 5: Error Handling")
    print("=" * 80)

    try:
        response = await query_rag_for_user(
            query="test",
            user_id="invalid-user",
            openwebui_url="http://localhost:3000",
            api_key="invalid-key",
            top_k=3,
            timeout=5.0  # Short timeout
        )
    except ValueError as e:
        print(f"\nValueError caught: {e}")
    except Exception as e:
        print(f"\nError caught: {type(e).__name__}: {e}")


async def example_integration_with_your_app():
    """
    Example 6: How to integrate into your application

    This shows a typical pattern for using the RAG client in your own app.
    """
    print("\n" + "=" * 80)
    print("Example 6: Application Integration Pattern")
    print("=" * 80)

    # Configuration (typically from environment variables or config file)
    config = {
        "openwebui_url": "http://localhost:3000",
        "api_key": "sk-your-api-key-here"
    }

    # Simulate a user query in your application
    user_query = "What is in the documents?"
    user_id = "d58b68d7-9bf6-41b2-a156-9b0859530b4b"

    try:
        # 1. Query RAG system
        rag_response = await query_rag_for_user(
            query=user_query,
            user_id=user_id,
            openwebui_url=config["openwebui_url"],
            api_key=config["api_key"],
            top_k=5
        )

        # 2. Check if we got results
        if rag_response.total_results == 0:
            print("\nNo relevant information found in knowledge base.")
            return None

        # 3. Format results for your application
        context = format_results_for_llm(rag_response)

        # 4. Use in your application (e.g., send to LLM with context)
        print(f"\nContext retrieved ({rag_response.total_results} documents):")
        print(context[:500] + "...")

        # 5. Track sources for citations
        sources = get_unique_sources(rag_response)
        print(f"\nSources: {', '.join(sources)}")

        return rag_response

    except Exception as e:
        print(f"\nError querying RAG: {e}")
        # Handle error in your application (log, return default, etc.)
        return None


async def main():
    """Run all examples"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "RAG CLIENT USAGE EXAMPLES" + " " * 33 + "║")
    print("╚" + "═" * 78 + "╝")

    # Update these before running:
    print("\n⚠️  BEFORE RUNNING: Update the API key and user ID in the examples above!")
    print("    - Replace 'sk-your-api-key-here' with your actual API key")
    print("    - Replace user_id with your actual user ID")
    print("\n")

    # Run examples (comment out the ones you don't want to run)
    try:
        await example_basic_query()
        # await example_specific_collections()
        # await example_format_for_llm()
        # await example_with_filters()
        # await example_error_handling()
        # await example_integration_with_your_app()
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("\nMake sure:")
        print("  1. Open WebUI is running at http://localhost:3000")
        print("  2. You've updated the API key in the examples")
        print("  3. You have knowledge bases with documents")


if __name__ == "__main__":
    asyncio.run(main())
