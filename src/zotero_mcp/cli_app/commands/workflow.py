"""Workflow command group."""

from __future__ import annotations

import argparse
import asyncio
import sys

from zotero_mcp.cli_app.common import (
    add_output_arg,
    add_scan_limit_arg,
    add_treated_limit_arg,
)
from zotero_mcp.cli_app.output import emit
from zotero_mcp.utils.config import load_config


def register(subparsers: argparse._SubParsersAction) -> None:
    workflow = subparsers.add_parser("workflow", help="Batch workflow commands")
    workflow_sub = workflow.add_subparsers(dest="subcommand", required=True)

    scan = workflow_sub.add_parser(
        "scan", help="Scan library and analyze items without AI notes"
    )
    add_scan_limit_arg(scan, default=100)
    add_treated_limit_arg(
        scan, default=20, help_text="Maximum total items to process (default: 20)"
    )
    scan.add_argument(
        "--target-collection",
        required=True,
        help="Move items to this collection after analysis (required)",
    )
    scan.add_argument(
        "--dry-run", action="store_true", help="Preview without processing"
    )
    scan.add_argument(
        "--llm-provider",
        choices=["auto", "claude-cli", "deepseek", "openai", "gemini"],
        default="auto",
        help="LLM provider for analysis (default: auto)",
    )
    scan.add_argument(
        "--source-collection",
        default="00_INBOXS",
        help="Collection to scan first (default: 00_INBOXS)",
    )
    scan.add_argument(
        "--multimodal",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable multi-modal analysis (default: enabled)",
    )
    add_output_arg(scan)

    metadata = workflow_sub.add_parser(
        "metadata-update", help="Update item metadata from external APIs"
    )
    metadata.add_argument("--collection", help="Limit to specific collection (by key)")
    add_scan_limit_arg(metadata, default=500)
    add_treated_limit_arg(metadata)
    metadata.add_argument("--item-key", help="Update a specific item by key")
    metadata.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview metadata updates without applying changes",
    )
    add_output_arg(metadata)

    dedup = workflow_sub.add_parser(
        "deduplicate", help="Find and remove duplicate items"
    )
    dedup.add_argument("--collection", help="Limit to specific collection (by key)")
    add_scan_limit_arg(dedup, default=500)
    add_treated_limit_arg(
        dedup,
        default=100,
        help_text="Maximum total number of items to scan (default: 100)",
    )
    dedup.add_argument(
        "--dry-run", action="store_true", help="Preview duplicates without deleting"
    )
    add_output_arg(dedup)

    clean_empty = workflow_sub.add_parser(
        "clean-empty", help="Find and delete empty items (no title, no attachments)"
    )
    clean_empty.add_argument(
        "--collection", help="Limit to specific collection (by name)"
    )
    add_scan_limit_arg(clean_empty, default=500)
    add_treated_limit_arg(
        clean_empty,
        default=100,
        help_text="Maximum total number of items to delete (default: 100)",
    )
    clean_empty.add_argument(
        "--dry-run", action="store_true", help="Preview empty items without deleting"
    )
    add_output_arg(clean_empty)

    clean_tags = workflow_sub.add_parser(
        "clean-tags", help="Remove all tags except those starting with a prefix"
    )
    clean_tags.add_argument(
        "--collection", help="Limit to specific collection (by name)"
    )
    clean_tags.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of items to process per batch (default: 50)",
    )
    clean_tags.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum total number of items to process",
    )
    clean_tags.add_argument(
        "--keep-prefix",
        default="AI",
        help="Keep tags starting with this prefix (default: 'AI')",
    )
    clean_tags.add_argument(
        "--dry-run", action="store_true", help="Preview changes without updating"
    )
    add_output_arg(clean_tags)


def run(args: argparse.Namespace) -> int:
    load_config()
    sub = args.subcommand

    if sub == "scan":
        from zotero_mcp.services.scanner import GlobalScanner

        scanner = GlobalScanner()
        result = asyncio.run(
            scanner.scan_and_process(
                scan_limit=args.scan_limit,
                treated_limit=args.treated_limit,
                target_collection=args.target_collection,
                dry_run=args.dry_run,
                llm_provider=args.llm_provider,
                source_collection=args.source_collection,
                include_multimodal=args.multimodal,
            )
        )
        emit(args, result)
        return 1 if result.get("error") else 0

    if sub == "metadata-update":
        from zotero_mcp.services.data_access import DataAccessService
        from zotero_mcp.services.zotero.metadata_update_service import (
            MetadataUpdateService,
        )

        async def _run() -> dict:
            data_service = DataAccessService()
            update_service = MetadataUpdateService(
                data_service.item_service, data_service.metadata_service
            )
            if args.item_key:
                return await update_service.update_item_metadata(
                    args.item_key, dry_run=args.dry_run
                )
            return await update_service.update_all_items(
                collection_key=args.collection,
                scan_limit=args.scan_limit,
                treated_limit=args.treated_limit,
                dry_run=args.dry_run,
            )

        result = asyncio.run(_run())
        emit(args, result)
        return 0

    if sub == "deduplicate":
        from zotero_mcp.services.data_access import DataAccessService
        from zotero_mcp.services.zotero.duplicate_service import (
            DuplicateDetectionService,
        )

        async def _run() -> dict:
            data_service = DataAccessService()
            service = DuplicateDetectionService(data_service.item_service)
            return await service.find_and_remove_duplicates(
                collection_key=args.collection,
                scan_limit=args.scan_limit,
                treated_limit=args.treated_limit,
                dry_run=args.dry_run,
            )

        result = asyncio.run(_run())
        emit(args, result)
        return 0

    if sub == "clean-empty":
        from zotero_mcp.services.data_access import DataAccessService

        async def _run() -> dict:
            data_service = DataAccessService()
            if args.collection:
                matches = await data_service.find_collection_by_name(
                    args.collection, exact_match=True
                )
                if not matches:
                    return {"error": f"Collection not found: {args.collection}"}
                collections = matches
            else:
                collections = await data_service.get_collections()

            candidates: list[tuple[str, str, str]] = []
            total_scanned = 0

            for col in collections:
                col_key = col.get("key", "")
                col_name = col.get("data", {}).get("name", col.get("name", "Unknown"))
                offset = 0

                while len(candidates) < args.treated_limit:
                    items = await data_service.get_collection_items(
                        col_key, limit=args.scan_limit, start=offset
                    )
                    if not items:
                        break
                    for item in items:
                        total_scanned += 1
                        if item.item_type in ("attachment", "note"):
                            continue
                        title = item.title or ""
                        if title.strip() and title.strip() != "Untitled":
                            continue
                        try:
                            children = await data_service.get_item_children(item.key)
                        except Exception:
                            continue
                        if children:
                            continue
                        candidates.append((item.key, title or "(empty)", col_name))
                        if len(candidates) >= args.treated_limit:
                            break
                    if len(items) < args.scan_limit:
                        break
                    offset += args.scan_limit
                if len(candidates) >= args.treated_limit:
                    break

            if args.dry_run:
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
                    await data_service.delete_item(key)
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

        result = asyncio.run(_run())
        emit(args, result)
        return 1 if result.get("error") else 0

    if sub == "clean-tags":
        from zotero_mcp.clients.zotero.api_client import get_zotero_client
        from zotero_mcp.services.data_access import DataAccessService

        async def _run() -> dict:
            api_client = get_zotero_client()
            data_service = DataAccessService()

            if args.collection:
                matches = await data_service.find_collection_by_name(
                    args.collection, exact_match=True
                )
                if not matches:
                    return {"error": f"Collection not found: {args.collection}"}
                collections = matches
            else:
                collections = await data_service.get_collections()

            keep_prefix = args.keep_prefix
            items_updated: list[dict] = []
            total_scanned = 0
            total_tags_removed = 0
            limit = args.limit

            for col in collections:
                if limit and len(items_updated) >= limit:
                    break
                col_key = col.get("key", "")
                col_name = col.get("data", {}).get("name", col.get("name", "Unknown"))
                offset = 0
                while limit is None or len(items_updated) < limit:
                    remaining = limit - len(items_updated) if limit else args.batch_size
                    batch_size = min(args.batch_size, remaining)
                    items = await data_service.get_collection_items(
                        col_key, limit=batch_size, start=offset
                    )
                    if not items:
                        break

                    for item in items:
                        total_scanned += 1
                        full_item = await api_client.get_item(item.key)
                        item_data = full_item.get("data", {})
                        existing_tags = item_data.get("tags", [])
                        kept_tags = [
                            t
                            for t in existing_tags
                            if isinstance(t, dict)
                            and t.get("tag", "").startswith(keep_prefix)
                        ]
                        removed_tags = [
                            t
                            for t in existing_tags
                            if isinstance(t, dict)
                            and not t.get("tag", "").startswith(keep_prefix)
                        ]
                        if removed_tags:
                            removed_count = len(removed_tags)
                            total_tags_removed += removed_count
                            items_updated.append(
                                {
                                    "item_key": item.key,
                                    "title": item.title or "(no title)",
                                    "collection": col_name,
                                    "kept": len(kept_tags),
                                    "removed": removed_count,
                                }
                            )
                            if not args.dry_run:
                                full_item["data"]["tags"] = kept_tags
                                await api_client.update_item(full_item)

                        if limit and len(items_updated) >= limit:
                            break

                    if len(items) < batch_size:
                        break
                    offset += batch_size

            return {
                "keep_prefix": keep_prefix,
                "total_items_scanned": total_scanned,
                "items_updated": len(items_updated),
                "total_tags_removed": total_tags_removed,
                "details": items_updated,
                "dry_run": args.dry_run,
            }

        result = asyncio.run(_run())
        emit(args, result)
        return 1 if result.get("error") else 0

    print(f"Unknown workflow subcommand: {sub}", file=sys.stderr)
    return 1


__all__ = ["register", "run"]
