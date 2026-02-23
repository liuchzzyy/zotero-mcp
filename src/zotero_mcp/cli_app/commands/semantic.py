"""Semantic database command group."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from zotero_mcp.cli_app.common import (
    add_output_arg,
    add_scan_limit_arg,
    add_treated_limit_arg,
)
from zotero_mcp.cli_app.output import emit
from zotero_mcp.utils.config import load_config


def _save_zotero_db_path_to_config(config_path: Path, db_path: str) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)

    full_config: dict = {}
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                full_config = json.load(f)
        except Exception:
            full_config = {}

    full_config.setdefault("semantic_search", {})
    full_config["semantic_search"]["zotero_db_path"] = db_path

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(full_config, f, indent=2)


def _add_local_mode_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--local",
        dest="local",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Use local Zotero DB/API mode for semantic commands "
            "(default: enabled; use --no-local for Web API mode)"
        ),
    )


def register(subparsers: argparse._SubParsersAction) -> None:
    semantic = subparsers.add_parser("semantic", help="Semantic database commands")
    semantic_sub = semantic.add_subparsers(dest="subcommand", required=True)

    db_update = semantic_sub.add_parser(
        "db-update", help="Update semantic search database"
    )
    db_update.add_argument(
        "--force-rebuild", action="store_true", help="Force complete rebuild"
    )
    add_scan_limit_arg(db_update, default=500)
    add_treated_limit_arg(
        db_update,
        default=100,
        help_text="Maximum total number of items to process (default: 100)",
    )
    db_update.add_argument(
        "--no-fulltext",
        action="store_true",
        help="Disable fulltext extraction (default: enabled)",
    )
    db_update.add_argument("--config-path", help="Path to semantic search config")
    db_update.add_argument("--db-path", help="Path to Zotero database file")
    _add_local_mode_arg(db_update)
    add_output_arg(db_update)

    db_status = semantic_sub.add_parser("db-status", help="Show database status")
    db_status.add_argument("--config-path", help="Path to semantic search config")
    _add_local_mode_arg(db_status)
    add_output_arg(db_status)

    inspect = semantic_sub.add_parser("db-inspect", help="Inspect indexed documents")
    inspect.add_argument(
        "--limit", type=int, default=20, help="How many records to show"
    )
    inspect.add_argument("--filter", dest="filter_text", help="Filter by title/creator")
    inspect.add_argument(
        "--filter-field",
        choices=["doi", "title", "author"],
        default="title",
        help="Field to filter by (default: title)",
    )
    inspect.add_argument(
        "--show-documents", action="store_true", help="Show document text"
    )
    inspect.add_argument("--stats", action="store_true", help="Show aggregate stats")
    inspect.add_argument("--config-path", help="Path to semantic search config")
    _add_local_mode_arg(inspect)
    add_output_arg(inspect)


def run(args: argparse.Namespace) -> int:
    load_config()
    os.environ["ZOTERO_LOCAL"] = "true" if getattr(args, "local", True) else "false"
    from zotero_mcp.services.zotero.semantic_search import create_semantic_search

    if args.subcommand == "db-update":
        config_path = args.config_path
        db_path = getattr(args, "db_path", None)
        if db_path:
            cfg_path = (
                Path(config_path)
                if config_path
                else Path.home() / ".config" / "zotero-mcp" / "config.json"
            )
            _save_zotero_db_path_to_config(cfg_path, db_path)

        search = create_semantic_search(config_path, db_path=db_path)
        stats = search.update_database(
            force_full_rebuild=args.force_rebuild,
            scan_limit=args.scan_limit,
            treated_limit=args.treated_limit,
            extract_fulltext=not args.no_fulltext,
        )
        emit(args, {"operation": "db-update", "stats": stats})
        return 0

    if args.subcommand == "db-status":
        search = create_semantic_search(args.config_path)
        status = search.get_database_status()
        emit(args, status)
        return 0

    if args.subcommand == "db-inspect":
        search = create_semantic_search(args.config_path)
        col = search.chroma_client.collection
        if args.stats:
            emit(args, {"count": col.count()})
            return 0

        include = ["metadatas", "documents"] if args.show_documents else ["metadatas"]
        records: list[dict] = []

        if args.filter_text:
            field_map = {"doi": "doi", "title": "title", "author": "creators"}
            target_field = field_map[args.filter_field]
            needle = args.filter_text.lower()
            fetch_limit = max(args.limit * 10, 500)
            results = col.get(limit=fetch_limit, include=include)
            metadatas = results.get("metadatas") or []
            documents = results.get("documents") or []
            for i, meta in enumerate(metadatas):
                val = meta.get(target_field, "")
                if needle not in str(val).lower():
                    continue
                row = {"title": meta.get("title", "Untitled"), "metadata": meta}
                if args.show_documents and documents:
                    row["document_preview"] = documents[i][:100]
                records.append(row)
                if len(records) >= args.limit:
                    break
        else:
            results = col.get(limit=args.limit, include=include)
            metadatas = results.get("metadatas") or []
            documents = results.get("documents") or []
            for i, meta in enumerate(metadatas):
                row = {"title": meta.get("title", "Untitled"), "metadata": meta}
                if args.show_documents and documents:
                    row["document_preview"] = documents[i][:100]
                records.append(row)

        emit(args, {"count": len(records), "records": records})
        return 0

    raise ValueError(f"Unknown semantic subcommand: {args.subcommand}")


__all__ = ["register", "run"]
