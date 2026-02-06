"""
Hybrid search service combining keyword and semantic search with RRF fusion.

Provides intelligent search that combines traditional keyword matching
with semantic similarity using Reciprocal Rank Fusion (RRF).
"""

from typing import Any, Literal

from zotero_core.models import (
    SearchItemsInput,
    SearchResultItem,
    SearchResults,
)
from zotero_core.services.search_service import SearchService, SearchServiceError
from zotero_core.services.semantic_search import (
    CHROMADB_AVAILABLE,
    SemanticSearchService,
    SemanticSearchServiceError,
)


class HybridSearchServiceError(Exception):
    """Base exception for HybridSearchService errors."""

    pass


class HybridSearchService:
    """
    Hybrid search combining keyword and semantic search with RRF.

    Uses Reciprocal Rank Fusion to combine results from keyword search
    (Zotero API) and semantic search (ChromaDB) for improved relevance.

    Attributes:
        keyword_search: Keyword search service
        semantic_search: Semantic search service (optional)
        rrf_k: RRF constant (default 60, higher = more rank smoothing)
    """

    def __init__(
        self,
        keyword_search: SearchService,
        semantic_search: SemanticSearchService | None = None,
        rrf_k: int = 60,
    ):
        """
        Initialize HybridSearchService.

        Args:
            keyword_search: Keyword search service (required)
            semantic_search: Semantic search service (optional)
            rrf_k: RRF constant for rank fusion
        """
        self.keyword_search = keyword_search
        self.semantic_search = semantic_search
        self.rrf_k = rrf_k

        # Warn if semantic search unavailable
        if not CHROMADB_AVAILABLE or semantic_search is None:
            import warnings

            warnings.warn(
                "Semantic search unavailable. Hybrid mode will fall back to keyword search.",
                UserWarning,
                stacklevel=2,
            )

    async def search(
        self,
        query: str,
        mode: Literal["keyword", "semantic", "hybrid"] = "hybrid",
        top_k: int = 10,
        keyword_mode: str = "titleCreatorYear",
        item_type: str = "-attachment",
        tags: list[str] | None = None,
    ) -> SearchResults:
        """
        Execute search with specified mode.

        Args:
            query: Search query
            mode: Search mode ("keyword", "semantic", or "hybrid")
            top_k: Number of results to return
            keyword_mode: Search mode for keyword component
            item_type: Item type filter
            tags: Tag filters

        Returns:
            SearchResults with ranked items

        Raises:
            HybridSearchServiceError: If search fails
        """
        try:
            if mode == "keyword":
                return await self._keyword_search(
                    query,
                    top_k,
                    keyword_mode,
                    item_type,
                    tags,
                )
            elif mode == "semantic":
                return await self._semantic_search(query, top_k)
            else:  # hybrid
                return await self._hybrid_search_rrf(
                    query,
                    top_k,
                    keyword_mode,
                    item_type,
                    tags,
                )
        except (SearchServiceError, SemanticSearchServiceError) as e:
            raise HybridSearchServiceError(f"Search failed: {e}") from e

    async def _keyword_search(
        self,
        query: str,
        top_k: int,
        keyword_mode: str,
        item_type: str,
        tags: list[str] | None,
    ) -> SearchResults:
        """
        Perform keyword-only search.

        Args:
            query: Search query
            top_k: Number of results
            keyword_mode: Keyword search mode
            item_type: Item type filter
            tags: Tag filters

        Returns:
            SearchResults with keyword scores
        """
        input_data = SearchItemsInput(
            query=query,
            mode=keyword_mode,  # type: ignore
            item_type=item_type,
            tags=tags,
            limit=top_k,
            offset=0,
        )

        results = await self.keyword_search.search_items(input_data)

        # Add keyword scores (simple inverse rank)
        for rank, item in enumerate(results.items, 1):
            item.keyword_score = 1.0 / rank
            item.relevance_score = item.keyword_score
            item.rank = rank

        return results

    async def _semantic_search(self, query: str, top_k: int) -> SearchResults:
        """
        Perform semantic-only search.

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            SearchResults with semantic scores

        Raises:
            HybridSearchServiceError: If semantic search unavailable
        """
        if not self.semantic_search:
            raise HybridSearchServiceError(
                "Semantic search unavailable. Please install chromadb."
            )

        # Query semantic search
        semantic_results = await self.semantic_search.search(query, top_k=top_k)

        # Convert to SearchResultItem
        items = []
        for rank, result in enumerate(semantic_results, 1):
            metadata = result.get("metadata", {})
            item = SearchResultItem(
                key=result["key"],
                title=metadata.get("title", "Untitled"),
                item_type=metadata.get("item_type", "unknown"),
                semantic_score=result["score"],
                relevance_score=result["score"],
                rank=rank,
                snippet=result.get("document"),
            )
            items.append(item)

        return SearchResults(
            query=query,
            total=len(items),
            count=len(items),
            items=items,
            has_more=False,
        )

    async def _hybrid_search_rrf(
        self,
        query: str,
        top_k: int,
        keyword_mode: str,
        item_type: str,
        tags: list[str] | None,
    ) -> SearchResults:
        """
        Perform hybrid search with RRF fusion.

        Fetches more results from each source, applies RRF algorithm,
        and returns top_k fused results.

        Args:
            query: Search query
            top_k: Number of results to return
            keyword_mode: Keyword search mode
            item_type: Item type filter
            tags: Tag filters

        Returns:
            SearchResults with fused rankings
        """
        # Fetch more results for fusion (2x top_k from each source)
        fetch_k = top_k * 2

        # Get keyword results
        keyword_results = await self._keyword_search(
            query, fetch_k, keyword_mode, item_type, tags
        )

        # Get semantic results (if available)
        semantic_results: SearchResults | None = None
        if self.semantic_search:
            import contextlib

            with contextlib.suppress(SemanticSearchServiceError):
                semantic_results = await self._semantic_search(query, fetch_k)

        # Apply RRF fusion
        fused_items = self._rrf_fusion(keyword_results, semantic_results, top_k)

        # Update ranks
        for rank, item in enumerate(fused_items, 1):
            item.rank = rank

        return SearchResults(
            query=query,
            total=len(fused_items),
            count=len(fused_items),
            items=fused_items,
            has_more=keyword_results.has_more,
        )

    def _rrf_fusion(
        self,
        keyword_results: SearchResults,
        semantic_results: SearchResults | None,
        top_k: int,
    ) -> list[SearchResultItem]:
        """
        Apply Reciprocal Rank Fusion to combine results.

        RRF formula: score(item) = sum(1 / (k + rank)) for each list

        Args:
            keyword_results: Keyword search results
            semantic_results: Semantic search results (optional)
            top_k: Number of top results to return

        Returns:
            Fused and ranked list of items
        """
        scores: dict[str, dict[str, Any]] = {}

        # Process keyword results
        for rank, item in enumerate(keyword_results.items, 1):
            key = item.key
            if key not in scores:
                scores[key] = {
                    "item": item,
                    "keyword_score": 0.0,
                    "semantic_score": 0.0,
                    "keyword_rank": rank,
                    "semantic_rank": None,
                }

            # Add keyword RRF score
            scores[key]["keyword_score"] += 1 / (self.rrf_k + rank)
            scores[key]["keyword_rank"] = rank

        # Process semantic results
        if semantic_results:
            for rank, item in enumerate(semantic_results.items, 1):
                key = item.key
                if key not in scores:
                    scores[key] = {
                        "item": item,
                        "keyword_score": 0.0,
                        "semantic_score": 0.0,
                        "keyword_rank": None,
                        "semantic_rank": rank,
                    }

                # Add semantic RRF score
                scores[key]["semantic_score"] += 1 / (self.rrf_k + rank)
                scores[key]["semantic_rank"] = rank

        # Calculate combined scores and sort
        fused = []
        for _key, data in scores.items():
            item = data["item"]

            # Store individual scores
            item.keyword_score = (
                data["keyword_score"] if data["keyword_score"] > 0 else None
            )
            item.semantic_score = (
                data["semantic_score"] if data["semantic_score"] > 0 else None
            )

            # Combined score (simple sum for RRF)
            item.relevance_score = data["keyword_score"] + data["semantic_score"]

            fused.append(item)

        # Sort by combined score (descending)
        fused.sort(key=lambda x: x.relevance_score or 0.0, reverse=True)

        # Return top_k
        return fused[:top_k]
