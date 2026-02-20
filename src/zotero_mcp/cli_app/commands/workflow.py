"""Workflow command group."""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any

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


async def _run_scan(args: argparse.Namespace) -> dict[str, Any]:
    from zotero_mcp.services.scanner import GlobalScanner

    scanner = GlobalScanner()
    return await scanner.scan_and_process(
        scan_limit=args.scan_limit,
        treated_limit=args.treated_limit,
        target_collection=args.target_collection,
        dry_run=args.dry_run,
        llm_provider=args.llm_provider,
        source_collection=args.source_collection,
        include_multimodal=args.multimodal,
    )


async def _run_metadata_update(args: argparse.Namespace) -> dict[str, Any]:
    from zotero_mcp.services.data_access import DataAccessService
    from zotero_mcp.services.zotero.metadata_update_service import MetadataUpdateService

    data_service = DataAccessService()
    update_service = MetadataUpdateService(
        data_service.item_service,
        data_service.metadata_service,
    )
    if args.item_key:
        return await update_service.update_item_metadata(
            args.item_key,
            dry_run=args.dry_run,
        )
    return await update_service.update_all_items(
        collection_key=args.collection,
        scan_limit=args.scan_limit,
        treated_limit=args.treated_limit,
        dry_run=args.dry_run,
    )


async def _run_deduplicate(args: argparse.Namespace) -> dict[str, Any]:
    from zotero_mcp.services.data_access import DataAccessService
    from zotero_mcp.services.zotero.duplicate_service import DuplicateDetectionService

    data_service = DataAccessService()
    service = DuplicateDetectionService(data_service.item_service)
    return await service.find_and_remove_duplicates(
        collection_key=args.collection,
        scan_limit=args.scan_limit,
        treated_limit=args.treated_limit,
        dry_run=args.dry_run,
    )


async def _run_clean_empty(args: argparse.Namespace) -> dict[str, Any]:
    from zotero_mcp.services.zotero.maintenance_service import LibraryMaintenanceService

    service = LibraryMaintenanceService()
    return await service.clean_empty_items(
        collection_name=args.collection,
        scan_limit=args.scan_limit,
        treated_limit=args.treated_limit,
        dry_run=args.dry_run,
    )


async def _run_clean_tags(args: argparse.Namespace) -> dict[str, Any]:
    from zotero_mcp.services.zotero.maintenance_service import LibraryMaintenanceService

    service = LibraryMaintenanceService()
    return await service.clean_tags(
        collection_name=args.collection,
        batch_size=args.batch_size,
        limit=args.limit,
        keep_prefix=args.keep_prefix,
        dry_run=args.dry_run,
    )


def _exit_code(result: dict[str, Any]) -> int:
    if result.get("error"):
        return 1
    success = result.get("success")
    if success is False:
        return 1
    return 0


def run(args: argparse.Namespace) -> int:
    load_config()

    handlers = {
        "scan": _run_scan,
        "metadata-update": _run_metadata_update,
        "deduplicate": _run_deduplicate,
        "clean-empty": _run_clean_empty,
        "clean-tags": _run_clean_tags,
    }

    handler = handlers.get(args.subcommand)
    if handler is None:
        print(f"Unknown workflow subcommand: {args.subcommand}", file=sys.stderr)
        return 1

    result = asyncio.run(handler(args))
    emit(args, result)
    return _exit_code(result)


__all__ = ["register", "run"]
