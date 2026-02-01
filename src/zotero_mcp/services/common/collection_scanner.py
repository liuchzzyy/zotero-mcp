"""
Shared collection scanning utilities for batch operations.

Provides a common pattern for scanning collections with pagination,
skip conditions, and progress tracking.
"""

from collections.abc import Callable
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def scan_collections(
    item_service: Any,
    collection_key: str | None,
    scan_limit: int,
    treated_limit: int,
    process_fn: Callable[[list[Any]], dict[str, int]],
    progress_callback: Callable | None = None,
) -> dict[str, int]:
    """
    Scan collections and process items in batches.

    Args:
        item_service: Item service instance
        collection_key: Optional single collection key to scan
        scan_limit: Items to fetch per batch
        treated_limit: Max items to process (excludes skipped)
        process_fn: Function to process each batch, returns stats dict
        progress_callback: Optional callback for progress updates

    Returns:
        Dict with scanning statistics
    """
    total_scanned = 0
    total_processed = 0

    if collection_key:
        collection_keys = [collection_key]
    else:
        logger.info("Scanning all collections in name order...")
        collections = await item_service.get_sorted_collections()
        collection_keys = [coll["key"] for coll in collections]

    for coll_key in collection_keys:
        if total_processed >= treated_limit:
            logger.info(f"Reached treated_limit ({treated_limit}), stopping scan")
            break

        result = await _scan_single_collection(
            item_service=item_service,
            coll_key=coll_key,
            scan_limit=scan_limit,
            treated_limit=treated_limit,
            total_processed=total_processed,
            process_fn=process_fn,
        )

        total_scanned += result["scanned"]
        total_processed += result["processed"]

        if progress_callback:
            await progress_callback(total_scanned, total_processed)

        logger.info(
            f"  Collection progress: {total_processed} processed "
            f"(scanned: {total_scanned})"
        )

    return {"scanned": total_scanned, "processed": total_processed}


async def _scan_single_collection(
    item_service: Any,
    coll_key: str,
    scan_limit: int,
    treated_limit: int,
    total_processed: int,
    process_fn: Callable[[list[Any]], dict[str, int]],
) -> dict[str, int]:
    """Scan a single collection with pagination."""
    scanned = 0
    processed = 0
    offset = 0

    while total_processed + processed < treated_limit:
        items = await item_service.get_collection_items(
            coll_key, limit=scan_limit, start=offset
        )
        if not items:
            break

        scanned += len(items)

        # Process batch and get stats
        stats = process_fn(items)
        processed += stats.get("processed", 0)

        if len(items) < scan_limit:
            break

        offset += scan_limit

    return {"scanned": scanned, "processed": processed}
