"""
Example usage of the standalone RAG client - Aligned with Open WebUI patterns

This demonstrates how to integrate rag_client.py into your own application,
following Open WebUI's implementation patterns for context formatting and citations.
"""

import asyncio
from rag_client import (
    query_rag_for_user,
    query_rag_specific_collections,
    format_sources_for_llm,
    format_context_only,
    get_unique_sources,
    get_citation_map,
    DEFAULT_RAG_TEMPLATE
)


async def example_basic_query():
    """Example 1: Basic RAG query with XML context formatting"""
    print("=" * 80)
    print("Example 1: Basic RAG Query with LLM-Ready Context")
    print("=" * 80)

    response = await query_rag_for_user(
        query="What is toxpath?",
        user_id="d58b68d7-9bf6-41b2-a156-9b0859530b4b",
        openwebui_url="http://localhost:3000",
        api_key="sk-your-api-key-here",  # Replace with your API key
        top_k=3,
        enable_hybrid_search=True,
        format_for_llm=True  # Generate XML context automatically
    )

    print(f"\nQuery: {response.query}")
    print(f"Total Results: {response.total_results}")
    print(f"Execution Time: {response.execution_time_ms:.2f}ms")

    print(f"\nCollections Searched:")
    for col in response.collections_searched:
        print(f"  - {col['name']} ({col['id']})")

    print(f"\nTop {len(response.results)} Results with Citations:")
    for result in response.results:
        print(f"\n[{result.citation_id}] Relevance: {result.relevance_score:.3f}")
        print(f"    Collection: {result.collection_name}")
        print(f"    Source: {result.source or 'Unknown'}")
        print(f"    Text: {result.text[:150]}...")

    # Show the XML context (same format as Open WebUI)
    print("\n" + "-" * 80)
    print("XML Context for LLM (same as Open WebUI format):")
    print("-" * 80)
    print(response.context_string[:500] + "...")

    return response


async def example_full_llm_prompt():
    """Example 2: Generate complete LLM prompt with RAG template"""
    print("\n" + "=" * 80)
    print("Example 2: Full LLM Prompt with RAG Template")
    print("=" * 80)

    response = await query_rag_for_user(
        query="Explain the main concepts",
        user_id="d58b68d7-9bf6-41b2-a156-9b0859530b4b",
        openwebui_url="http://localhost:3000",
        api_key="sk-your-api-key-here",
        top_k=3,
        format_for_llm=True
    )

    # Get the full prompt that Open WebUI would send to the LLM
    full_prompt = format_sources_for_llm(response)

    print("\nFull Prompt for LLM (includes RAG template + context + query):")
    print("=" * 80)
    print(full_prompt[:800] + "...")

    # This is what you would add to your LLM messages
    print("\n" + "=" * 80)
    print("To use with your LLM:")
    print("=" * 80)
    print("""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": full_prompt}
    ]

    # The LLM will respond with inline citations like:
    # "According to the document, toxpath is used for analysis [1]."
    """)

    return response


async def example_custom_prompt():
    """Example 3: Use context with custom prompt (without default template)"""
    print("\n" + "=" * 80)
    print("Example 3: Custom Prompt with RAG Context")
    print("=" * 80)

    response = await query_rag_for_user(
        query="machine learning concepts",
        user_id="d58b68d7-9bf6-41b2-a156-9b0859530b4b",
        openwebui_url="http://localhost:3000",
        api_key="sk-your-api-key-here",
        top_k=5,
        format_for_llm=True
    )

    # Get just the context XML (without template)
    context_xml = format_context_only(response)

    # Build your own custom prompt
    custom_prompt = f"""
Using the information provided below, please explain the key concepts.

# Retrieved Information

{context_xml}

# Instructions
- Use inline citations [1], [2], etc. when referencing the sources above
- Be concise and focus on the most important points
- If information is unclear or missing, please note that

Please answer: {response.query}
"""

    print("\nCustom Prompt:")
    print("=" * 80)
    print(custom_prompt[:600] + "...")

    return response


async def example_citation_handling():
    """Example 4: Extract and display citations"""
    print("\n" + "=" * 80)
    print("Example 4: Citation Handling (for UI display)")
    print("=" * 80)

    response = await query_rag_for_user(
        query="What information is available?",
        user_id="d58b68d7-9bf6-41b2-a156-9b0859530b4b",
        openwebui_url="http://localhost:3000",
        api_key="sk-your-api-key-here",
        top_k=5
    )

    # Get citation mapping (same as Open WebUI's citation_idx_map)
    citations = get_citation_map(response)

    print(f"\nCitation Map (for displaying references to user):")
    for cit_id, source in citations.items():
        print(f"  [{cit_id}] {source}")

    # Get unique sources
    sources = get_unique_sources(response)
    print(f"\nUnique Source Documents: {sources}")

    # Simulate LLM response with citations
    simulated_llm_response = """
Based on the provided documentation, the system uses advanced algorithms
for processing [1]. The key features include real-time analysis [2] and
automated reporting capabilities [1][3].
"""

    print("\n" + "=" * 80)
    print("Simulated LLM Response with Citations:")
    print("=" * 80)
    print(simulated_llm_response)

    print("\nReferences:")
    for cit_id, source in citations.items():
        print(f"  [{cit_id}] {source}")

    return response


async def example_query_generation_pattern():
    """
    Example 5: Query Generation Pattern (as used in Open WebUI)

    Note: This shows how to implement query generation in your app.
    The standalone client uses queries directly, but you can pre-process
    them using an LLM call as Open WebUI does.
    """
    print("\n" + "=" * 80)
    print("Example 5: Query Generation Pattern (Advanced)")
    print("=" * 80)

    # Simulate a conversation history
    conversation_history = [
        {"role": "user", "content": "I'm interested in machine learning"},
        {"role": "assistant", "content": "I'd be happy to help with machine learning!"},
        {"role": "user", "content": "Can you explain how neural networks work?"}
    ]

    user_message = conversation_history[-1]["content"]

    print("\nUser's Original Question:")
    print(f'  "{user_message}"')

    # In a real application, you would call your LLM here to generate optimized queries
    # This is what Open WebUI does with generate_queries()

    print("\n" + "-" * 80)
    print("QUERY GENERATION STEP (implement this in your app):")
    print("-" * 80)
    print("""
    # Pseudo-code for query generation:

    query_gen_prompt = f'''
    Given the conversation history:
    {conversation_history}

    Generate 1-3 optimized search queries to find relevant information
    to answer the user's latest question.

    Return as JSON: {{"queries": ["query1", "query2", ...]}}
    '''

    # Call your LLM
    llm_response = await your_llm.generate(query_gen_prompt)
    generated_queries = parse_json(llm_response)["queries"]

    # Examples of generated queries:
    # - "neural network architecture explanation"
    # - "how do neural networks learn"
    # - "neural network basics tutorial"
    """)

    # For this example, we'll use hand-crafted optimized queries
    optimized_queries = [
        "neural network architecture and how it works",
        "neural network learning process backpropagation"
    ]

    print("\nGenerated Optimized Queries:")
    for i, q in enumerate(optimized_queries, 1):
        print(f'  {i}. "{q}"')

    # Now query RAG with the optimized queries
    # (In practice, you might query with multiple and merge results)
    print("\nQuerying RAG with optimized query...")

    response = await query_rag_for_user(
        query=optimized_queries[0],  # Use best query
        user_id="d58b68d7-9bf6-41b2-a156-9b0859530b4b",
        openwebui_url="http://localhost:3000",
        api_key="sk-your-api-key-here",
        top_k=5
    )

    print(f"\nResults: {response.total_results} documents found")
    print(f"Using query: '{response.query}'")

    return response


async def example_integration_pattern():
    """
    Example 6: Complete Integration Pattern for Your Application

    Shows the full flow: conversation → query generation → RAG → LLM response
    """
    print("\n" + "=" * 80)
    print("Example 6: Complete Application Integration Pattern")
    print("=" * 80)

    # Configuration
    config = {
        "openwebui_url": "http://localhost:3000",
        "api_key": "sk-your-api-key-here",
        "user_id": "d58b68d7-9bf6-41b2-a156-9b0859530b4b"
    }

    # Step 1: User asks a question
    user_query = "What are the key features?"
    print(f"\n[User Question] {user_query}")

    # Step 2: Query RAG system
    print("\n[RAG Query] Searching knowledge base...")

    try:
        rag_response = await query_rag_for_user(
            query=user_query,
            user_id=config["user_id"],
            openwebui_url=config["openwebui_url"],
            api_key=config["api_key"],
            top_k=5,
            format_for_llm=True
        )

        print(f"✓ Found {rag_response.total_results} relevant documents")

        # Step 3: Get citation mapping for later use
        citations = get_citation_map(rag_response)

        # Step 4: Format prompt for LLM (with RAG template)
        llm_prompt = format_sources_for_llm(rag_response)

        print("\n[LLM Prompt] Generated prompt with context:")
        print(f"  - Context length: {len(rag_response.context_string or '')} chars")
        print(f"  - Citations available: {list(citations.keys())}")

        # Step 5: Call your LLM (pseudo-code)
        print("\n[LLM Call] Sending to language model...")
        print("""
        # Pseudo-code:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": llm_prompt}
        ]

        llm_response = await your_llm.chat(messages)
        # LLM returns answer with citations: "The key features include X [1] and Y [2]."
        """)

        # Step 6: Parse and display response with references
        print("\n[Response] Final answer:")
        simulated_response = f"""
The key features include:
1. Advanced analytics capabilities [{list(citations.keys())[0] if citations else 1}]
2. Real-time processing [{list(citations.keys())[1] if len(citations) > 1 else 1}]
3. Automated reporting tools [{list(citations.keys())[0] if citations else 1}]
"""
        print(simulated_response)

        print("References:")
        for cit_id, source in citations.items():
            print(f"  [{cit_id}] {source}")

        return rag_response

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n[Fallback] Responding without RAG context...")
        return None


async def main():
    """Run all examples"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 15 + "RAG CLIENT - OPEN WEBUI ALIGNED EXAMPLES" + " " * 22 + "║")
    print("╚" + "═" * 78 + "╝")

    print("\n⚠️  BEFORE RUNNING: Update the API key in the examples!")
    print("    Replace 'sk-your-api-key-here' with your actual API key")
    print("    Generated from: http://localhost:3000 → Settings → Account → API Keys")
    print("\n")

    # Run examples (comment out the ones you don't want)
    try:
        await example_basic_query()
        # await example_full_llm_prompt()
        # await example_custom_prompt()
        # await example_citation_handling()
        # await example_query_generation_pattern()
        # await example_integration_pattern()

        print("\n\n" + "=" * 80)
        print("📚 For more details, see:")
        print("  - rag_client.py - Full implementation with comments")
        print("  - RAG_CLIENT_INTEGRATION.md - Integration guide")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("\nMake sure:")
        print("  1. Open WebUI is running at http://localhost:3000")
        print("  2. You've updated the API key in the examples")
        print("  3. You have knowledge bases with documents uploaded")
        print("  4. API keys are enabled (ENABLE_API_KEYS=true)")


if __name__ == "__main__":
    asyncio.run(main())
