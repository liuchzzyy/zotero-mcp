"""Maintenance operations for Zotero library hygiene tasks."""

from __future__ import annotations

from typing import Any

from zotero_mcp.services.data_access import DataAccessService
from zotero_mcp.utils.formatting.tags import (
    normalize_input_tags,
    normalize_tag_names,
    to_tag_objects,
)


class LibraryMaintenanceService:
    """Service layer for clean-empty and clean-tags workflows."""

    _SKIPPED_CHILD_TYPES = {"attachment", "note", "annotation"}

    def __init__(self, data_service: DataAccessService | None = None):
        self.data_service = data_service or DataAccessService()

    async def _resolve_collections(
        self, collection_name: str | None
    ) -> tuple[list[dict], str | None]:
        if not collection_name:
            return await self.data_service.get_collections(), None

        matches = await self.data_service.find_collection_by_name(
            collection_name, exact_match=True
        )
        if not matches:
            return [], f"Collection not found: {collection_name}"
        return matches, None

    async def clean_empty_items(
        self,
        collection_name: str | None,
        scan_limit: int,
        treated_limit: int,
        dry_run: bool,
    ) -> dict[str, Any]:
        collections, error = await self._resolve_collections(collection_name)
        if error:
            return {"error": error}

        candidates: list[tuple[str, str, str]] = []
        total_scanned = 0

        for col in collections:
            col_key = col.get("key", "")
            col_name = col.get("data", {}).get("name", col.get("name", "Unknown"))
            offset = 0

            while len(candidates) < treated_limit:
                items = await self.data_service.get_collection_items(
                    col_key, limit=scan_limit, start=offset
                )
                if not items:
                    break

                for item in items:
                    total_scanned += 1

                    if item.item_type in self._SKIPPED_CHILD_TYPES:
                        continue

                    title = item.title or ""
                    if title.strip() and title.strip() != "Untitled":
                        continue

                    try:
                        children = await self.data_service.get_item_children(item.key)
                    except Exception:
                        continue

                    if children:
                        continue

                    candidates.append((item.key, title or "(empty)", col_name))
                    if len(candidates) >= treated_limit:
                        break

                if len(items) < scan_limit:
                    break
                offset += scan_limit

            if len(candidates) >= treated_limit:
                break

        if dry_run:
            return {
                "total_scanned": total_scanned,
                "empty_items_found": len(candidates),
                "candidates": [
                    {"key": key, "title": title, "collection": col_name}
                    for key, title, col_name in candidates
                ],
                "dry_run": True,
            }

        deleted = 0
        failed = 0
        failures: list[dict[str, str]] = []
        for key, _, _ in candidates:
            try:
                await self.data_service.delete_item(key)
                deleted += 1
            except Exception as exc:
                failed += 1
                failures.append({"key": key, "error": str(exc)})

        return {
            "total_scanned": total_scanned,
            "empty_items_found": len(candidates),
            "deleted": deleted,
            "failed": failed,
            "failures": failures,
        }

    async def purge_tags(
        self,
        tags: list[str],
        collection_name: str | None,
        batch_size: int,
        scan_limit: int | None,
        update_limit: int | None,
        dry_run: bool,
    ) -> dict[str, Any]:
        """Purge specific tags across the library or a named collection."""
        target_tags = set(normalize_input_tags(tags))
        if not target_tags:
            return {"error": "At least one non-empty tag is required for purge"}

        collections, error = await self._resolve_collections(collection_name)
        if error:
            return {"error": error}

        items_updated: list[dict[str, Any]] = []
        total_scanned = 0
        total_tags_removed = 0

        for col in collections:
            if update_limit is not None and len(items_updated) >= update_limit:
                break
            if scan_limit is not None and total_scanned >= scan_limit:
                break

            col_key = col.get("key", "")
            col_name = col.get("data", {}).get("name", col.get("name", "Unknown"))
            offset = 0

            while True:
                if update_limit is not None and len(items_updated) >= update_limit:
                    break
                if scan_limit is not None and total_scanned >= scan_limit:
                    break

                remaining_scan = (
                    scan_limit - total_scanned
                    if scan_limit is not None
                    else batch_size
                )
                current_batch = min(batch_size, remaining_scan)
                if current_batch <= 0:
                    break

                items = await self.data_service.get_collection_items(
                    col_key, limit=current_batch, start=offset
                )
                if not items:
                    break

                for item in items:
                    if scan_limit is not None and total_scanned >= scan_limit:
                        break
                    if update_limit is not None and len(items_updated) >= update_limit:
                        break

                    total_scanned += 1

                    full_item = await self.data_service.get_item(item.key)
                    item_data = full_item.get("data", {})
                    existing_tags = normalize_tag_names(item_data.get("tags", []))
                    if not existing_tags:
                        continue

                    kept_tags = [
                        tag_name
                        for tag_name in existing_tags
                        if tag_name not in target_tags
                    ]
                    removed_tags = [
                        tag_name
                        for tag_name in existing_tags
                        if tag_name in target_tags
                    ]

                    if not removed_tags:
                        continue

                    removed_count = len(removed_tags)
                    total_tags_removed += removed_count
                    items_updated.append(
                        {
                            "item_key": item.key,
                            "title": item.title or "(no title)",
                            "collection": col_name,
                            "removed": removed_count,
                            "removed_tags": sorted(set(removed_tags)),
                            "kept": len(kept_tags),
                        }
                    )

                    if not dry_run:
                        full_item["data"]["tags"] = to_tag_objects(kept_tags)
                        await self.data_service.update_item(full_item)

                if len(items) < current_batch:
                    break
                offset += current_batch

        return {
            "tags": sorted(target_tags),
            "collection": collection_name,
            "total_items_scanned": total_scanned,
            "items_updated": len(items_updated),
            "total_tags_removed": total_tags_removed,
            "details": items_updated,
            "dry_run": dry_run,
        }
