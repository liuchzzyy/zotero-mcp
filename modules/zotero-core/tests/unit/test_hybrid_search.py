"""
Unit tests for HybridSearchService with RRF fusion.

Tests the hybrid search service that combines keyword and semantic
search using Reciprocal Rank Fusion (RRF) algorithm.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zotero_core.clients.zotero_client import ZoteroClient, ZoteroClientError
from zotero_core.models import (
    SearchItemsInput,
    SearchMode,
    SearchResults,
    SearchResultItem,
)
from zotero_core.services.hybrid_search import (
    HybridSearchService,
    HybridSearchServiceError,
)
from zotero_core.services.search_service import (
    SearchService,
    SearchServiceError,
)
from zotero_core.services.semantic_search import (
    CHROMADB_AVAILABLE,
    SemanticSearchService,
    SemanticSearchServiceError,
)


@pytest.fixture
def mock_client():
    """Create a mock ZoteroClient."""
    client = MagicMock(spec=ZoteroClient)
    return client


@pytest.fixture
def search_service(mock_client):
    """Create a SearchService with mocked client."""
    with patch(
        "zotero_core.services.search_service.ZoteroClient", return_value=mock_client
    ):
        service = SearchService(client=mock_client)
        return service


@pytest.fixture
def mock_semantic_service():
    """Create a mock SemanticSearchService."""
    service = MagicMock(spec=SemanticSearchService)
    return service


@pytest.fixture
def sample_search_results():
    """Sample search results from Zotero API."""
    return [
        {
            "key": "ITEM1",
            "version": 1,
            "data": {
                "key": "ITEM1",
                "title": "Machine Learning for Healthcare",
                "itemType": "journalArticle",
                "creators": [
                    {
                        "firstName": "John",
                        "lastName": "Smith",
                        "creatorType": "author",
                    }
                ],
                "date": "2024",
                "abstractNote": "A paper about ML in healthcare.",
                "tags": [{"tag": "ml"}, {"tag": "healthcare"}],
            },
        },
        {
            "key": "ITEM2",
            "version": 2,
            "data": {
                "key": "ITEM2",
                "title": "Deep Learning Advances",
                "itemType": "journalArticle",
                "creators": [
                    {
                        "firstName": "Jane",
                        "lastName": "Doe",
                        "creatorType": "author",
                    }
                ],
                "date": "2023",
                "abstractNote": "Recent advances in deep learning.",
                "tags": [{"tag": "dl"}, {"tag": "ai"}],
            },
        },
        {
            "key": "ITEM3",
            "version": 3,
            "data": {
                "key": "ITEM3",
                "title": "Natural Language Processing",
                "itemType": "journalArticle",
                "creators": [
                    {
                        "firstName": "Bob",
                        "lastName": "Johnson",
                        "creatorType": "author",
                    }
                ],
                "date": "2024",
                "abstractNote": "NLP techniques and applications.",
                "tags": [{"tag": "nlp"}, {"tag": "ai"}],
            },
        },
    ]


@pytest.fixture
def sample_semantic_results():
    """Sample semantic search results."""
    return [
        {
            "key": "ITEM3",
            "score": 0.95,
            "metadata": {"title": "Natural Language Processing", "item_type": "journalArticle"},
            "document": "Natural Language Processing. NLP techniques.",
        },
        {
            "key": "ITEM1",
            "score": 0.85,
            "metadata": {
                "title": "Machine Learning for Healthcare",
                "item_type": "journalArticle",
            },
            "document": "Machine Learning for Healthcare. ML in healthcare.",
        },
        {
            "key": "ITEM4",
            "score": 0.75,
            "metadata": {"title": "Computer Vision Basics", "item_type": "journalArticle"},
            "document": "Computer Vision Basics. Introduction to CV.",
        },
    ]


class TestSearchService:
    """Tests for SearchService (keyword search)."""

    @pytest.mark.asyncio
    async def test_search_items_success(
        self, search_service, mock_client, sample_search_results
    ):
        """Test successful keyword search."""
        mock_client.search_items = AsyncMock(return_value=sample_search_results)

        input_data = SearchItemsInput(
            query="machine learning",
            mode=SearchMode.TITLE_CREATOR_YEAR,
            limit=10,
        )

        results = await search_service.search_items(input_data)

        assert results.query == "machine learning"
        assert len(results.items) == 3
        assert results.items[0].key == "ITEM1"
        assert results.items[0].title == "Machine Learning for Healthcare"
        assert "Smith" in results.items[0].authors
        mock_client.search_items.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_items_with_filters(
        self, search_service, mock_client, sample_search_results
    ):
        """Test keyword search with tag and type filters."""
        mock_client.search_items = AsyncMock(return_value=sample_search_results)

        input_data = SearchItemsInput(
            query="ai",
            mode=SearchMode.EVERYTHING,
            item_type="-attachment",
            tags=["ml"],
            limit=5,
        )

        results = await search_service.search_items(input_data)

        assert len(results.items) == 3
        mock_client.search_items.assert_called_once_with(
            query="ai",
            limit=5,
            start=0,
            mode="everything",
            item_type="-attachment",
            tags=["ml"],
        )

    @pytest.mark.asyncio
    async def test_search_items_empty_results(
        self, search_service, mock_client
    ):
        """Test keyword search with no results."""
        mock_client.search_items = AsyncMock(return_value=[])

        input_data = SearchItemsInput(query="nonexistent", limit=10)

        results = await search_service.search_items(input_data)

        assert len(results.items) == 0
        assert results.total == 0

    @pytest.mark.asyncio
    async def test_search_items_client_error(
        self, search_service, mock_client
    ):
        """Test handling of client error."""
        mock_client.search_items = AsyncMock(
            side_effect=ZoteroClientError("API error")
        )

        input_data = SearchItemsInput(query="test", limit=10)

        with pytest.raises(SearchServiceError, match="Keyword search failed"):
            await search_service.search_items(input_data)

    @pytest.mark.asyncio
    async def test_search_tags(self, search_service, mock_client):
        """Test tag search."""
        # Mock pyzotero's tag format (list of dicts with 'tag' field)
        # After ZoteroClient.get_tags() processing, this becomes a list of strings
        mock_client.get_tags = AsyncMock(
            return_value=["machine-learning", "healthcare", "ai"]
        )

        tags = await search_service.search_tags("machine", limit=10)

        assert len(tags) == 1
        assert tags[0] == "machine-learning"
        mock_client.get_tags.assert_called_once()


class TestSemanticSearchService:
    """Tests for SemanticSearchService."""

    def test_init_without_chromadb(self):
        """Test that initialization fails without chromadb."""
        with patch("zotero_core.services.semantic_search.CHROMADB_AVAILABLE", False):
            from zotero_core.services.semantic_search import (
                SemanticSearchService,
            )

            with pytest.raises(ImportError, match="chromadb is required"):
                SemanticSearchService()

    @pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="chromadb not installed")
    @pytest.mark.asyncio
    async def test_add_items(self):
        """Test adding items to vector database."""
        service = SemanticSearchService(collection_name="test_collection")

        items = [
            {
                "key": "ITEM1",
                "title": "Test Paper",
                "itemType": "journalArticle",
                "abstractNote": "Test abstract",
            }
        ]

        count = await service.add_items(items)

        assert count == 1

        # Cleanup
        await service.clear()

    @pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="chromadb not installed")
    @pytest.mark.asyncio
    async def test_search_semantic(self):
        """Test semantic search."""
        service = SemanticSearchService(collection_name="test_search")

        # Add test items
        items = [
            {
                "key": "ITEM1",
                "title": "Machine Learning",
                "itemType": "journalArticle",
                "abstractNote": "Introduction to ML algorithms",
            },
            {
                "key": "ITEM2",
                "title": "Healthcare Analytics",
                "itemType": "journalArticle",
                "abstractNote": "Data analysis in healthcare",
            },
        ]

        await service.add_items(items)

        # Search
        results = await service.search("artificial intelligence", top_k=2)

        assert len(results) > 0

        # Cleanup
        await service.clear()

    @pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="chromadb not installed")
    @pytest.mark.asyncio
    async def test_delete_items(self):
        """Test deleting items from vector database."""
        service = SemanticSearchService(collection_name="test_delete")

        # Add items
        items = [
            {
                "key": "ITEM1",
                "title": "Test",
                "itemType": "journalArticle",
                "abstractNote": "Test",
            }
        ]
        await service.add_items(items)

        # Delete
        count = await service.delete_items(["ITEM1"])

        assert count == 1

        # Cleanup
        await service.clear()

    @pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="chromadb not installed")
    @pytest.mark.asyncio
    async def test_count_items(self):
        """Test counting items in collection."""
        service = SemanticSearchService(collection_name="test_count")

        # Add items
        items = [
            {
                "key": f"ITEM{i}",
                "title": f"Test {i}",
                "itemType": "journalArticle",
                "abstractNote": "Test",
            }
            for i in range(3)
        ]
        await service.add_items(items)

        # Count
        count = await service.count()

        assert count == 3

        # Cleanup
        await service.clear()


class TestHybridSearchService:
    """Tests for HybridSearchService with RRF fusion."""

    @pytest.fixture
    def hybrid_service(self, search_service, mock_semantic_service):
        """Create a HybridSearchService."""
        return HybridSearchService(
            keyword_search=search_service,
            semantic_search=mock_semantic_service,
            rrf_k=60,
        )

    @pytest.mark.asyncio
    async def test_keyword_mode(
        self, hybrid_service, search_service, mock_client, sample_search_results
    ):
        """Test keyword-only search mode."""
        mock_client.search_items = AsyncMock(return_value=sample_search_results)

        results = await hybrid_service.search(
            query="machine learning",
            mode="keyword",
            top_k=10,
        )

        assert len(results.items) == 3
        assert results.items[0].keyword_score is not None
        assert results.items[0].relevance_score is not None
        assert results.items[0].rank == 1

    @pytest.mark.asyncio
    async def test_semantic_mode(self, hybrid_service, mock_semantic_service):
        """Test semantic-only search mode."""
        mock_semantic_service.search = AsyncMock(
            return_value=[
                {
                    "key": "ITEM1",
                    "score": 0.9,
                    "metadata": {"title": "Test", "item_type": "journalArticle"},
                    "document": "Test",
                }
            ]
        )

        results = await hybrid_service.search(
            query="test query",
            mode="semantic",
            top_k=10,
        )

        assert len(results.items) == 1
        assert results.items[0].semantic_score == 0.9
        assert results.items[0].relevance_score == 0.9

    @pytest.mark.asyncio
    async def test_semantic_mode_unavailable(
        self, search_service, mock_client, sample_search_results
    ):
        """Test semantic mode without semantic search service."""
        mock_client.search_items = AsyncMock(return_value=sample_search_results)

        # Create service without semantic search
        service = HybridSearchService(
            keyword_search=search_service, semantic_search=None
        )

        with pytest.raises(HybridSearchServiceError, match="Semantic search unavailable"):
            await service.search(query="test", mode="semantic", top_k=10)

    @pytest.mark.asyncio
    async def test_hybrid_mode_rrf_fusion(
        self,
        hybrid_service,
        search_service,
        mock_client,
        mock_semantic_service,
        sample_search_results,
        sample_semantic_results,
    ):
        """Test hybrid mode with RRF fusion."""
        # Setup mocks
        mock_client.search_items = AsyncMock(return_value=sample_search_results)
        mock_semantic_service.search = AsyncMock(return_value=sample_semantic_results)

        # Execute hybrid search
        results = await hybrid_service.search(
            query="machine learning and nlp",
            mode="hybrid",
            top_k=5,
        )

        # Verify fusion
        assert len(results.items) > 0

        # Check that items have both scores if they appear in both lists
        for item in results.items:
            # ITEM1 and ITEM3 appear in both keyword and semantic results
            if item.key in ["ITEM1", "ITEM3"]:
                assert item.keyword_score is not None
                assert item.semantic_score is not None
                assert item.relevance_score is not None
                # RRF combined score should be sum of individual scores
                expected = item.keyword_score + item.semantic_score
                assert abs(item.relevance_score - expected) < 0.001

        # ITEM4 only in semantic results
        item4 = next((item for item in results.items if item.key == "ITEM4"), None)
        if item4:
            assert item4.keyword_score is None
            assert item4.semantic_score is not None

        # ITEM2 only in keyword results
        item2 = next((item for item in results.items if item.key == "ITEM2"), None)
        if item2:
            assert item2.keyword_score is not None
            item2.semantic_score is None or item2.semantic_score >= 0

    @pytest.mark.asyncio
    async def test_rrf_ranking(
        self,
        hybrid_service,
        search_service,
        mock_client,
        mock_semantic_service,
    ):
        """Test RRF ranking behavior."""
        # Create results with clear ranking differences
        keyword_data = [
            {
                "key": f"K{i}",
                "version": i,
                "data": {
                    "key": f"K{i}",
                    "title": f"Keyword Result {i}",
                    "itemType": "journalArticle",
                    "creators": [],
                    "date": "2024",
                },
            }
            for i in range(1, 6)  # K1 to K5
        ]

        semantic_data = [
            {
                "key": f"S{i}",
                "score": 1.0 - (i * 0.1),
                "metadata": {"title": f"Semantic {i}", "item_type": "journalArticle"},
                "document": f"Semantic {i}",
            }
            for i in range(1, 6)  # S1 to S5
        ]

        # Overlap: K2/S3, K3/S2
        keyword_data[1]["data"]["key"] = "OVERLAP1"
        keyword_data[2]["data"]["key"] = "OVERLAP2"
        semantic_data[2]["key"] = "OVERLAP1"  # S3 is OVERLAP1
        semantic_data[1]["key"] = "OVERLAP2"  # S2 is OVERLAP2

        mock_client.search_items = AsyncMock(return_value=keyword_data)
        mock_semantic_service.search = AsyncMock(return_value=semantic_data)

        results = await hybrid_service.search(
            query="test", mode="hybrid", top_k=10
        )

        # Verify ranking
        # OVERLAP items should be ranked higher (appear in both lists)
        overlap_items = [item for item in results.items if item.key.startswith("OVERLAP")]
        assert len(overlap_items) == 2

        # Overlap items should have both scores
        for item in overlap_items:
            assert item.keyword_score is not None
            assert item.semantic_score is not None
            assert item.relevance_score is not None

    @pytest.mark.asyncio
    async def test_rrf_constants(
        self,
        search_service,
        mock_client,
        mock_semantic_service,
        sample_search_results,
        sample_semantic_results,
    ):
        """Test RRF with different k constants."""
        mock_client.search_items = AsyncMock(return_value=sample_search_results)
        mock_semantic_service.search = AsyncMock(return_value=sample_semantic_results)

        # Test with different k values
        for k in [30, 60, 100]:
            service = HybridSearchService(
                keyword_search=search_service,
                semantic_search=mock_semantic_service,
                rrf_k=k,
            )

            results = await service.search(query="test", mode="hybrid", top_k=5)

            assert results.query == "test"
            assert len(results.items) > 0

    @pytest.mark.asyncio
    async def test_hybrid_fallback_to_keyword(
        self, search_service, mock_client, sample_search_results
    ):
        """Test hybrid mode fallback when semantic search fails."""
        mock_client.search_items = AsyncMock(return_value=sample_search_results)

        # Create semantic service that fails
        failing_semantic = MagicMock(spec=SemanticSearchService)
        failing_semantic.search = AsyncMock(
            side_effect=SemanticSearchServiceError("ChromaDB error")
        )

        service = HybridSearchService(
            keyword_search=search_service,
            semantic_search=failing_semantic,
        )

        # Should fall back to keyword-only
        results = await service.search(query="test", mode="hybrid", top_k=5)

        assert len(results.items) > 0
        # All items should only have keyword scores
        for item in results.items:
            assert item.keyword_score is not None

    @pytest.mark.asyncio
    async def test_empty_results_handling(
        self,
        hybrid_service,
        search_service,
        mock_client,
        mock_semantic_service,
    ):
        """Test handling of empty search results."""
        mock_client.search_items = AsyncMock(return_value=[])
        mock_semantic_service.search = AsyncMock(return_value=[])

        results = await hybrid_service.search(query="nonexistent", mode="hybrid", top_k=5)

        assert len(results.items) == 0
        assert results.total == 0

    @pytest.mark.asyncio
    async def test_hybrid_search_with_filters(
        self,
        hybrid_service,
        search_service,
        mock_client,
        mock_semantic_service,
        sample_search_results,
        sample_semantic_results,
    ):
        """Test hybrid search with filters applied."""
        mock_client.search_items = AsyncMock(return_value=sample_search_results)
        mock_semantic_service.search = AsyncMock(return_value=sample_semantic_results)

        results = await hybrid_service.search(
            query="test",
            mode="hybrid",
            top_k=5,
            item_type="-attachment",
            tags=["ml"],
            keyword_mode="everything",
        )

        # Verify filters were passed to keyword search
        mock_client.search_items.assert_called()
        call_kwargs = mock_client.search_items.call_args.kwargs
        assert call_kwargs["item_type"] == "-attachment"
        assert call_kwargs["tags"] == ["ml"]
        assert call_kwargs["mode"] == "everything"


class TestRRFAlgorithm:
    """Direct tests of RRF algorithm."""

    def test_rrf_fusion_basic(self):
        """Test basic RRF fusion logic."""
        # Create service
        service = MagicMock()
        service.keyword_search = MagicMock()
        service.semantic_search = MagicMock()
        service.rrf_k = 60

        # Create mock results
        keyword_results = SearchResults(
            query="test",
            total=3,
            count=3,
            items=[
                SearchResultItem(key="A", title="Item A"),
                SearchResultItem(key="B", title="Item B"),
                SearchResultItem(key="C", title="Item C"),
            ],
            has_more=False,
        )

        semantic_results = SearchResults(
            query="test",
            total=3,
            count=3,
            items=[
                SearchResultItem(key="B", title="Item B"),
                SearchResultItem(key="A", title="Item A"),
                SearchResultItem(key="D", title="Item D"),
            ],
            has_more=False,
        )

        # Apply RRF
        fused = HybridSearchService._rrf_fusion(
            service, keyword_results, semantic_results, top_k=5
        )

        # Verify fusion
        assert len(fused) == 4  # A, B, C, D (D only in semantic)

        # Extract keys
        keys = [item.key for item in fused]
        assert "A" in keys
        assert "B" in keys
        assert "C" in keys
        assert "D" in keys

        # A and B appear in both lists, should have higher combined scores
        item_a = next(item for item in fused if item.key == "A")
        item_c = next(item for item in fused if item.key == "C")
        item_d = next(item for item in fused if item.key == "D")

        # A (rank 1 in keyword, rank 2 in semantic) should beat C (rank 3 keyword only)
        assert item_a.relevance_score > item_c.relevance_score

        # D should only have semantic score
        assert item_d.semantic_score is not None
        assert item_d.keyword_score is None or item_d.keyword_score == 0

    def test_rrf_fusion_no_semantic(self):
        """Test RRF fusion with only keyword results."""
        service = MagicMock()
        service.keyword_search = MagicMock()
        service.semantic_search = None
        service.rrf_k = 60

        keyword_results = SearchResults(
            query="test",
            total=2,
            count=2,
            items=[
                SearchResultItem(key="A", title="Item A"),
                SearchResultItem(key="B", title="Item B"),
            ],
            has_more=False,
        )

        fused = HybridSearchService._rrf_fusion(
            service, keyword_results, None, top_k=5
        )

        assert len(fused) == 2
        # Items should only have keyword scores
        for item in fused:
            assert item.semantic_score is None or item.semantic_score == 0
            assert item.keyword_score is not None

    def test_rrf_fusion_top_k_truncation(self):
        """Test that RRF fusion respects top_k parameter."""
        service = MagicMock()
        service.keyword_search = MagicMock()
        service.semantic_search = MagicMock()
        service.rrf_k = 60

        # Create 10 results
        keyword_results = SearchResults(
            query="test",
            total=10,
            count=10,
            items=[SearchResultItem(key=f"K{i}", title=f"Item {i}") for i in range(10)],
            has_more=False,
        )

        semantic_results = SearchResults(
            query="test",
            total=10,
            count=10,
            items=[SearchResultItem(key=f"S{i}", title=f"Item {i}") for i in range(10)],
            has_more=False,
        )

        fused = HybridSearchService._rrf_fusion(
            service, keyword_results, semantic_results, top_k=5
        )

        assert len(fused) == 5
