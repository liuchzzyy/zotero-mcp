"""
Example: Using HybridSearchService with RRF fusion.

This example demonstrates how to use the zotero-core search services
to perform keyword, semantic, and hybrid search operations.
"""

import asyncio

from zotero_core.clients import ZoteroClient
from zotero_core.models import SearchItemsInput, SearchMode
from zotero_core.services import (
    CHROMADB_AVAILABLE,
    HybridSearchService,
    SearchService,
    SemanticSearchService,
)


async def main():
    """Demonstrate search functionality."""
    # Initialize Zotero client (replace with your credentials)
    client = ZoteroClient(
        library_id="your_library_id",
        api_key="your_api_key",
        library_type="user",
    )

    # 1. Keyword Search (always available)
    print("\n=== Keyword Search ===")
    search_service = SearchService(client=client)

    keyword_input = SearchItemsInput(
        query="machine learning",
        mode=SearchMode.TITLE_CREATOR_YEAR,
        limit=10,
    )

    results = await search_service.search_items(keyword_input)
    print(f"Found {results.total} items")
    for item in results.items[:3]:
        print(f"  - {item.title} by {item.authors or 'Unknown'}")

    # 2. Semantic Search (requires ChromaDB)
    if CHROMADB_AVAILABLE:
        print("\n=== Semantic Search ===")
        semantic_service = SemanticSearchService(
            collection_name="zotero_items",
            persist_directory="./chroma_db",
        )

        # Perform semantic search
        semantic_results = await semantic_service.search(
            query="artificial intelligence and deep neural networks",
            top_k=5,
        )

        print(f"Found {len(semantic_results)} semantically similar items")
        for result in semantic_results[:3]:
            print(f"  - {result['metadata'].get('title', 'Untitled')}")
            print(f"    Score: {result['score']:.3f}")
    else:
        print("\n=== Semantic Search ===")
        print("ChromaDB not installed. Semantic search unavailable.")
        print("Install with: pip install chromadb")

    # 3. Hybrid Search (RRF fusion)
    print("\n=== Hybrid Search (RRF Fusion) ===")

    if CHROMADB_AVAILABLE:
        semantic_service = SemanticSearchService(
            collection_name="zotero_items",
            persist_directory="./chroma_db",
        )
        hybrid_service = HybridSearchService(
            keyword_search=search_service,
            semantic_search=semantic_service,
            rrf_k=60,
        )
    else:
        # Falls back to keyword-only
        hybrid_service = HybridSearchService(
            keyword_search=search_service,
            semantic_search=None,
            rrf_k=60,
        )

    # Perform hybrid search
    hybrid_results = await hybrid_service.search(
        query="neural networks for computer vision",
        mode="hybrid",  # options: "keyword", "semantic", "hybrid"
        top_k=5,
    )

    print(f"Found {hybrid_results.total} items")
    for item in hybrid_results.items[:3]:
        print(f"  - {item.title}")
        if item.keyword_score:
            print(f"    Keyword Score: {item.keyword_score:.4f}")
        if item.semantic_score:
            print(f"    Semantic Score: {item.semantic_score:.4f}")
        if item.relevance_score:
            print(f"    Combined Score: {item.relevance_score:.4f}")
        print(f"    Rank: {item.rank}")

    # 4. Tag Search
    print("\n=== Tag Search ===")
    tags = await search_service.search_tags("ml", limit=10)
    print(f"Found {len(tags)} matching tags:")
    for tag in tags[:5]:
        print(f"  - {tag}")


if __name__ == "__main__":
    print("Zotero Core Search Example")
    print("=" * 50)

    # Note: Replace with actual credentials to run
    print("\nNote: This example requires valid Zotero credentials.")
    print("Replace 'your_library_id' and 'your_api_key' with actual values.")

    # Uncomment to run with real credentials:
    # asyncio.run(main())
