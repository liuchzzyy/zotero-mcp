"""
Keyword-based search service using Zotero API.

Provides search functionality for items, tags, and collections
using Zotero's native search capabilities.
"""

from typing import Any

from zotero_core.clients.zotero_client import ZoteroClient, ZoteroClientError
from zotero_core.models import SearchItemsInput, SearchResultItem, SearchResults


class SearchServiceError(Exception):
    """Base exception for SearchService errors."""

    pass


class SearchService:
    """
    Keyword-based search service using Zotero API.

    Provides methods for searching items, tags, and collections
    with proper error handling and type conversion.
    """

    def __init__(self, client: ZoteroClient):
        """
        Initialize SearchService.

        Args:
            client: ZoteroClient instance
        """
        self.client = client

    async def search_items(self, input_data: SearchItemsInput) -> SearchResults:
        """
        Search items by keyword.

        Args:
            input_data: Search parameters including query, mode, filters

        Returns:
            SearchResults with matching items

        Raises:
            SearchServiceError: If search fails
        """
        try:
            # Call Zotero API search
            items_data = await self.client.search_items(
                query=input_data.query,
                limit=input_data.limit,
                start=input_data.offset,
                mode=input_data.mode.value,
                item_type=input_data.item_type,
                tags=input_data.tags,
            )

            # Convert to Item models
            search_items = []
            for item_data in items_data:
                try:
                    normalized = self._normalize_search_result(item_data)
                    item = self._dict_to_search_result_item(normalized)
                    search_items.append(item)
                except (ValueError, KeyError):
                    # Skip invalid items
                    continue

            return SearchResults(
                query=input_data.query,
                total=len(search_items),
                count=len(search_items),
                items=search_items,
                has_more=len(search_items) >= input_data.limit,
            )
        except ZoteroClientError as e:
            raise SearchServiceError(f"Keyword search failed: {e}") from e

    async def search_tags(self, query: str, limit: int = 100) -> list[str]:
        """
        Search for tags matching a query.

        Args:
            query: Tag name or partial name to search for
            limit: Maximum number of tags to return

        Returns:
            List of matching tag names

        Raises:
            SearchServiceError: If search fails
        """
        try:
            all_tags = await self.client.get_tags()

            # Normalize tags to strings (handle both dict and string formats)
            normalized_tags = []
            for tag in all_tags:
                if isinstance(tag, dict):
                    tag_name = tag.get("tag", "")
                    if tag_name:
                        normalized_tags.append(tag_name)
                elif isinstance(tag, str) and tag:
                    normalized_tags.append(tag)

            # Filter tags by query (case-insensitive substring match)
            query_lower = query.lower()
            matching_tags = [
                tag for tag in normalized_tags if query_lower in tag.lower()
            ][:limit]

            return matching_tags
        except ZoteroClientError as e:
            raise SearchServiceError(f"Tag search failed: {e}") from e

    def _normalize_search_result(self, item_data: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize search result data from Zotero API.

        Handles both nested (data field) and flat formats.

        Args:
            item_data: Raw item data from Zotero API

        Returns:
            Normalized item data dict

        Raises:
            ValueError: If required fields are missing
        """
        # Check for nested structure (data field)
        if "data" in item_data and isinstance(item_data["data"], dict):
            data = item_data["data"]
        else:
            data = item_data

        # Validate required fields
        if "key" not in data:
            raise ValueError("Item data missing required 'key' field")

        # Extract creators as formatted string
        creators = data.get("creators", [])
        if creators:
            authors = [
                c.get("lastName", c.get("firstName", ""))
                for c in creators
                if c.get("creatorType") == "author"
            ]
            authors_str = ", ".join([a for a in authors if a])
        else:
            authors_str = None

        # Extract year from date
        date = data.get("date", "")
        year = None
        if date:
            # Try to extract 4-digit year
            import re

            year_match = re.search(r"\b(19|20)\d{2}\b", date)
            if year_match:
                year = int(year_match.group())

        # Extract tags
        tags_data = data.get("tags", [])
        if tags_data and isinstance(tags_data[0], dict):
            tags = [t.get("tag", "") for t in tags_data if t.get("tag")]
        elif isinstance(tags_data, list):
            tags = tags_data
        else:
            tags = []

        # Build normalized dict
        return {
            "key": data["key"],
            "title": data.get("title", "Untitled"),
            "item_type": data.get("itemType", "unknown"),
            "authors": authors_str,
            "date": date,
            "year": year,
            "abstract": data.get("abstractNote"),
            "tags": tags,
            "doi": data.get("DOI"),
            "url": data.get("url"),
            "date_added": data.get("dateAdded"),
            "collections": data.get("collections", []),
            "raw_data": item_data,
        }

    def _dict_to_search_result_item(
        self, data: dict[str, Any]
    ) -> SearchResultItem:
        """
        Convert normalized dict to SearchResultItem model.

        Args:
            data: Normalized item data

        Returns:
            SearchResultItem instance
        """
        return SearchResultItem(**data)
