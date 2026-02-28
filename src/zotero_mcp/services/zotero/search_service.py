"""
Search Service.

Handles search operations for Zotero items using API and Local DB.
"""

import logging
from typing import Literal

from zotero_mcp.clients.zotero import (
    LocalDatabaseClient,
    ZoteroAPIClient,
)
from zotero_mcp.models.common import SearchResultItem
from zotero_mcp.services.zotero.result_mapper import (
    api_item_to_search_result,
    zotero_item_to_search_result,
)
from zotero_mcp.utils.formatting.tags import normalize_input_tags, normalize_tag_names

logger = logging.getLogger(__name__)


class SearchService:
    """
    Service for searching Zotero items.
    """

    def __init__(
        self,
        api_client: ZoteroAPIClient,
        local_client: LocalDatabaseClient | None = None,
    ):
        """
        Initialize SearchService.

        Args:
            api_client: Zotero API client
            local_client: Local database client (optional)
        """
        self.api_client = api_client
        self.local_client = local_client

    async def search_items(
        self,
        query: str,
        limit: int = 25,
        offset: int = 0,
        qmode: Literal["titleCreatorYear", "everything"] = "titleCreatorYear",
    ) -> list[SearchResultItem]:
        """
        Search items in the library.

        Uses local database if available for faster results.

        Args:
            query: Search query
            limit: Maximum results
            offset: Pagination offset
            qmode: Search mode

        Returns:
            List of search results
        """
        # Try local database first for speed
        if self.local_client and qmode == "everything":
            try:
                items = self.local_client.search_items(query, limit=limit + offset)
                if offset >= len(items):
                    return []
                return [
                    zotero_item_to_search_result(item)
                    for item in items[offset : offset + limit]
                ]
            except Exception as e:
                logger.warning(f"Local search failed, falling back to API: {e}")

        # Fall back to API
        items = await self.api_client.search_items(
            query=query,
            qmode=qmode,
            limit=limit,
            start=offset,
        )
        if isinstance(items, int):
            logger.warning(f"Search API returned HTTP status {items}")
            return []
        return [api_item_to_search_result(item) for item in items]

    async def get_recent_items(
        self,
        limit: int = 10,
        days: int = 7,
    ) -> list[SearchResultItem]:
        """
        Get recently added items.

        Args:
            limit: Maximum results
            days: Days to look back

        Returns:
            List of recent items
        """
        items = await self.api_client.get_recent_items(limit=limit, days=days)
        if isinstance(items, int):
            logger.warning(f"Recent items API returned HTTP status {items}")
            return []
        return [api_item_to_search_result(item) for item in items]

    async def search_by_tag(
        self,
        tags: list[str],
        exclude_tags: list[str] | None = None,
        limit: int = 25,
    ) -> list[SearchResultItem]:
        """
        Search items by tags.

        Args:
            tags: Required tags (AND logic)
            exclude_tags: Tags to exclude
            limit: Maximum results

        Returns:
            Matching items
        """
        include_tags = normalize_input_tags(tags)
        exclude = set(normalize_input_tags(exclude_tags))
        if not include_tags:
            return []

        api_limit = max(100, limit)
        items = await self.api_client.get_items_by_tag(include_tags[0], limit=api_limit)
        if isinstance(items, int):
            logger.warning(f"Tag search API returned HTTP status {items}")
            return []

        filtered: list[dict] = []
        for item in items:
            item_tags = set(normalize_tag_names(item.get("data", {}).get("tags", [])))
            if any(tag not in item_tags for tag in include_tags):
                continue
            if exclude and any(tag in item_tags for tag in exclude):
                continue
            filtered.append(item)

        return [api_item_to_search_result(item) for item in filtered[:limit]]
