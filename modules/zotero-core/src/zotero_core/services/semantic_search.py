"""
Semantic search service using ChromaDB.

Provides vector-based semantic search functionality for Zotero items.
ChromaDB is an optional dependency - this service gracefully handles
its absence.
"""

from typing import Any

# Check for chromadb availability at import time
try:
    import chromadb
    from chromadb.config import Settings

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None  # type: ignore


class SemanticSearchServiceError(Exception):
    """Base exception for SemanticSearchService errors."""

    pass


class SemanticSearchService:
    """
    Vector-based semantic search using ChromaDB.

    Provides semantic similarity search by storing item embeddings
    in ChromaDB and querying with natural language.

    ChromaDB is optional - if not installed, service raises ImportError.
    """

    def __init__(
        self,
        collection_name: str = "zotero_items",
        persist_directory: str | None = None,
    ):
        """
        Initialize SemanticSearchService.

        Args:
            collection_name: Name of ChromaDB collection
            persist_directory: Directory to persist database (None for in-memory)

        Raises:
            ImportError: If chromadb is not installed
            SemanticSearchServiceError: If initialization fails
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError(
                "chromadb is required for semantic search. "
                "Install it with: pip install chromadb"
            )

        try:
            # Configure ChromaDB client
            if persist_directory:
                settings = Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=persist_directory,
                )
                self.client = chromadb.PersistentClient(
                    path=persist_directory, settings=settings
                )
            else:
                self.client = chromadb.Client(settings=Settings())

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            raise SemanticSearchServiceError(
                f"Failed to initialize ChromaDB: {e}"
            ) from e

    async def add_items(self, items: list[dict[str, Any]]) -> int:
        """
        Add items to vector database.

        Args:
            items: List of item data dicts with 'key', 'title', 'abstract'

        Returns:
            Number of items added

        Raises:
            SemanticSearchServiceError: If add operation fails
        """
        if not items:
            return 0

        try:
            # Prepare batch data
            ids = []
            documents = []
            metadatas = []

            for item in items:
                # Extract key
                key = item.get("key")
                if not key:
                    continue

                # Build document text (title + abstract for better search)
                title = item.get("title", "")
                abstract = item.get("abstractNote", "") or item.get("abstract", "")
                document = f"{title}. {abstract}" if abstract else title

                ids.append(key)
                documents.append(document)
                metadatas.append(
                    {
                        "key": key,
                        "title": title,
                        "item_type": item.get("itemType", "unknown"),
                    }
                )

            if not ids:
                return 0

            # Add to collection (ChromaDB operations are synchronous)
            # We use asyncio.to_thread for async compatibility
            import asyncio

            await asyncio.to_thread(
                self.collection.add,
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )

            return len(ids)
        except Exception as e:
            raise SemanticSearchServiceError(f"Failed to add items: {e}") from e

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search by semantic similarity.

        Args:
            query: Natural language query
            top_k: Number of results to return
            filters: Optional metadata filters (e.g., {"item_type": "journalArticle"})

        Returns:
            List of dicts with 'key', 'score', and metadata

        Raises:
            SemanticSearchServiceError: If search fails
        """
        try:
            import asyncio

            # Query ChromaDB
            results = await asyncio.to_thread(
                self.collection.query,
                query_texts=[query],
                n_results=top_k,
                where=filters,
            )

            # Parse results
            if not results or not results.get("ids") or not results["ids"][0]:
                return []

            search_results = []
            for i, item_id in enumerate(results["ids"][0]):
                search_results.append(
                    {
                        "key": item_id,
                        "score": 1.0
                        - results["distances"][0][i],  # Convert distance to similarity
                        "metadata": results["metadatas"][0][i],
                        "document": results["documents"][0][i]
                        if results.get("documents")
                        else None,
                    }
                )

            return search_results
        except Exception as e:
            raise SemanticSearchServiceError(f"Semantic search failed: {e}") from e

    async def delete_items(self, keys: list[str]) -> int:
        """
        Delete items from vector database.

        Args:
            keys: List of item keys to delete

        Returns:
            Number of items deleted

        Raises:
            SemanticSearchServiceError: If delete operation fails
        """
        if not keys:
            return 0

        try:
            import asyncio

            await asyncio.to_thread(self.collection.delete, ids=keys)
            return len(keys)
        except Exception as e:
            raise SemanticSearchServiceError(f"Failed to delete items: {e}") from e

    async def clear(self) -> None:
        """
        Clear all items from the collection.

        Raises:
            SemanticSearchServiceError: If clear operation fails
        """
        try:
            import asyncio

            await asyncio.to_thread(self.collection.delete, where={})
        except Exception as e:
            raise SemanticSearchServiceError(f"Failed to clear collection: {e}") from e

    async def count(self) -> int:
        """
        Get total number of items in the collection.

        Returns:
            Number of items in collection

        Raises:
            SemanticSearchServiceError: If count operation fails
        """
        try:
            import asyncio

            count_result = await asyncio.to_thread(self.collection.count)
            return count_result
        except Exception as e:
            raise SemanticSearchServiceError(
                f"Failed to get collection count: {e}"
            ) from e
