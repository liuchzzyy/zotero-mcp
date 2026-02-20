"""Resource command groups: items, notes, annotations, pdfs, collections."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from zotero_mcp.cli_app.common import add_output_arg
from zotero_mcp.cli_app.output import emit
from zotero_mcp.utils.config import load_config
from zotero_mcp.utils.formatting.helpers import normalize_item_key


def _add_paging(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--offset", type=int, default=0)


def register_items(subparsers: argparse._SubParsersAction) -> None:
    items = subparsers.add_parser("items", help="Item operations")
    items_sub = items.add_subparsers(dest="subcommand", required=True)

    get_cmd = items_sub.add_parser("get", help="Get one item by key")
    get_cmd.add_argument("--item-key", required=True)
    add_output_arg(get_cmd)

    list_cmd = items_sub.add_parser("list", help="List items")
    _add_paging(list_cmd)
    list_cmd.add_argument("--item-type")
    add_output_arg(list_cmd)

    children = items_sub.add_parser("children", help="List child items")
    children.add_argument("--item-key", required=True)
    children.add_argument("--item-type", choices=["attachment", "note", "annotation"])
    add_output_arg(children)

    fulltext = items_sub.add_parser("fulltext", help="Get fulltext")
    fulltext.add_argument("--item-key", required=True)
    add_output_arg(fulltext)

    bundle = items_sub.add_parser("bundle", help="Get item bundle")
    bundle.add_argument("--item-key", required=True)
    bundle.add_argument("--include-fulltext", action="store_true")
    bundle.add_argument(
        "--include-annotations", action=argparse.BooleanOptionalAction, default=True
    )
    bundle.add_argument(
        "--include-notes", action=argparse.BooleanOptionalAction, default=True
    )
    add_output_arg(bundle)

    delete = items_sub.add_parser("delete", help="Delete item")
    delete.add_argument("--item-key", required=True)
    add_output_arg(delete)

    update = items_sub.add_parser("update", help="Update item from JSON file")
    update.add_argument(
        "--input-file",
        required=True,
        help="Path to JSON file containing full item object",
    )
    add_output_arg(update)

    create = items_sub.add_parser("create", help="Create items from JSON file")
    create.add_argument(
        "--input-file",
        required=True,
        help="Path to JSON file containing one item or list of items",
    )
    add_output_arg(create)

    tags = items_sub.add_parser("add-tags", help="Add tags to item")
    tags.add_argument("--item-key", required=True)
    tags.add_argument("--tags", nargs="+", required=True)
    add_output_arg(tags)

    add_col = items_sub.add_parser("add-to-collection", help="Add item to collection")
    add_col.add_argument("--item-key", required=True)
    add_col.add_argument("--collection-key", required=True)
    add_output_arg(add_col)

    remove_col = items_sub.add_parser(
        "remove-from-collection", help="Remove item from collection"
    )
    remove_col.add_argument("--item-key", required=True)
    remove_col.add_argument("--collection-key", required=True)
    add_output_arg(remove_col)


def run_items(args: argparse.Namespace) -> int:
    load_config()
    from zotero_mcp.services.data_access import DataAccessService

    async def _run() -> dict:
        svc = DataAccessService()
        sub = args.subcommand

        if sub == "get":
            return await svc.get_item(normalize_item_key(args.item_key))
        if sub == "list":
            results = await svc.get_all_items(
                limit=args.limit, start=args.offset, item_type=args.item_type
            )
            return {"count": len(results), "items": [i.model_dump() for i in results]}
        if sub == "children":
            children = await svc.get_item_children(
                normalize_item_key(args.item_key), item_type=args.item_type
            )
            return {"count": len(children), "children": children}
        if sub == "fulltext":
            text = await svc.get_fulltext(normalize_item_key(args.item_key))
            return {"item_key": args.item_key, "fulltext": text}
        if sub == "bundle":
            bundle = await svc.get_item_bundle(
                normalize_item_key(args.item_key),
                include_fulltext=args.include_fulltext,
                include_annotations=args.include_annotations,
                include_notes=args.include_notes,
            )
            return bundle
        if sub == "delete":
            return await svc.delete_item(normalize_item_key(args.item_key))
        if sub == "update":
            with open(args.input_file, encoding="utf-8") as f:
                payload = json.load(f)
            return await svc.update_item(payload)
        if sub == "create":
            with open(args.input_file, encoding="utf-8") as f:
                payload = json.load(f)
            items = payload if isinstance(payload, list) else [payload]
            return await svc.create_items(items)
        if sub == "add-tags":
            return await svc.add_tags_to_item(
                normalize_item_key(args.item_key), args.tags
            )
        if sub == "add-to-collection":
            return await svc.add_item_to_collection(
                args.collection_key, normalize_item_key(args.item_key)
            )
        if sub == "remove-from-collection":
            return await svc.remove_item_from_collection(
                args.collection_key, normalize_item_key(args.item_key)
            )

        raise ValueError(f"Unknown items subcommand: {sub}")

    result = asyncio.run(_run())
    emit(args, result)
    return 0


def register_notes(subparsers: argparse._SubParsersAction) -> None:
    notes = subparsers.add_parser("notes", help="Note operations")
    notes_sub = notes.add_subparsers(dest="subcommand", required=True)

    list_cmd = notes_sub.add_parser("list", help="List notes under item")
    list_cmd.add_argument("--item-key", required=True)
    _add_paging(list_cmd)
    add_output_arg(list_cmd)

    create = notes_sub.add_parser("create", help="Create a note")
    create.add_argument("--item-key", required=True)
    create.add_argument("--content", help="Note content")
    create.add_argument("--content-file", help="Path to note content file")
    create.add_argument("--tags", nargs="*", default=[])
    add_output_arg(create)

    search = notes_sub.add_parser("search", help="Search note text")
    search.add_argument("--query", required=True)
    _add_paging(search)
    add_output_arg(search)


def run_notes(args: argparse.Namespace) -> int:
    load_config()
    from zotero_mcp.services.data_access import DataAccessService

    if args.subcommand == "create" and bool(args.content) == bool(args.content_file):
        raise ValueError("Provide exactly one of --content or --content-file")

    async def _run() -> dict:
        svc = DataAccessService()

        if args.subcommand == "list":
            notes = await svc.get_notes(normalize_item_key(args.item_key))
            total = len(notes)
            sliced = notes[args.offset : args.offset + args.limit]
            return {"total": total, "count": len(sliced), "notes": sliced}

        if args.subcommand == "create":
            content = args.content
            if args.content_file:
                content = Path(args.content_file).read_text(encoding="utf-8")
            return await svc.create_note(
                parent_key=normalize_item_key(args.item_key),
                content=content or "",
                tags=args.tags,
            )

        if args.subcommand == "search":
            candidates = await svc.search_items(
                args.query, limit=max(args.limit * 2, 50), offset=0
            )
            hits: list[dict] = []
            query_lower = args.query.lower()
            for item in candidates:
                notes = await svc.get_notes(item.key)
                for note in notes:
                    data = note.get("data", {})
                    raw = str(data.get("note", ""))
                    if query_lower in raw.lower():
                        hits.append(
                            {
                                "item_key": item.key,
                                "item_title": item.title,
                                "note_key": data.get("key", ""),
                                "note": raw,
                            }
                        )
            total = len(hits)
            sliced = hits[args.offset : args.offset + args.limit]
            return {
                "query": args.query,
                "total": total,
                "count": len(sliced),
                "results": sliced,
            }

        raise ValueError(f"Unknown notes subcommand: {args.subcommand}")

    result = asyncio.run(_run())
    emit(args, result)
    return 0


def register_annotations(subparsers: argparse._SubParsersAction) -> None:
    annotations = subparsers.add_parser("annotations", help="Annotation operations")
    ann_sub = annotations.add_subparsers(dest="subcommand", required=True)

    list_cmd = ann_sub.add_parser("list", help="List annotations for item")
    list_cmd.add_argument("--item-key", required=True)
    list_cmd.add_argument("--annotation-type", default="all")
    _add_paging(list_cmd)
    add_output_arg(list_cmd)


def run_annotations(args: argparse.Namespace) -> int:
    load_config()
    from zotero_mcp.services.data_access import DataAccessService

    async def _run() -> dict:
        svc = DataAccessService()
        annotations = await svc.get_annotations(normalize_item_key(args.item_key))
        if args.annotation_type != "all":
            annotations = [
                a
                for a in annotations
                if a.get("data", {}).get("annotationType", "").lower()
                == args.annotation_type.lower()
            ]
        total = len(annotations)
        sliced = annotations[args.offset : args.offset + args.limit]
        return {
            "item_key": args.item_key,
            "total": total,
            "count": len(sliced),
            "annotations": sliced,
        }

    result = asyncio.run(_run())
    emit(args, result)
    return 0


def register_pdfs(subparsers: argparse._SubParsersAction) -> None:
    pdfs = subparsers.add_parser("pdfs", help="PDF attachment operations")
    pdf_sub = pdfs.add_subparsers(dest="subcommand", required=True)

    upload = pdf_sub.add_parser("upload", help="Upload PDF attachment")
    upload.add_argument("--item-key", required=True)
    upload.add_argument("--file", required=True, help="Local file path")
    upload.add_argument("--title")
    add_output_arg(upload)


def run_pdfs(args: argparse.Namespace) -> int:
    load_config()
    from zotero_mcp.services.data_access import DataAccessService

    async def _run() -> dict:
        svc = DataAccessService()
        return await svc.item_service.upload_attachment(
            parent_key=normalize_item_key(args.item_key),
            file_path=args.file,
            title=args.title,
        )

    result = asyncio.run(_run())
    emit(args, result)
    return 0


def register_collections(subparsers: argparse._SubParsersAction) -> None:
    collections = subparsers.add_parser("collections", help="Collection operations")
    col_sub = collections.add_subparsers(dest="subcommand", required=True)

    list_cmd = col_sub.add_parser("list", help="List collections")
    add_output_arg(list_cmd)

    find = col_sub.add_parser("find", help="Find collection by name")
    find.add_argument("--name", required=True)
    find.add_argument("--exact", action="store_true")
    add_output_arg(find)

    create = col_sub.add_parser("create", help="Create collection")
    create.add_argument("--name", required=True)
    create.add_argument("--parent-key")
    add_output_arg(create)

    rename = col_sub.add_parser("rename", help="Rename collection")
    rename.add_argument("--collection-key", required=True)
    rename.add_argument("--name", required=True)
    add_output_arg(rename)

    move = col_sub.add_parser("move", help="Move collection")
    move.add_argument("--collection-key", required=True)
    move.add_argument("--parent-key", default="")
    add_output_arg(move)

    delete = col_sub.add_parser("delete", help="Delete collection")
    delete.add_argument("--collection-key", required=True)
    add_output_arg(delete)

    items = col_sub.add_parser("items", help="List items in collection")
    items.add_argument("--collection-key", required=True)
    _add_paging(items)
    add_output_arg(items)


def run_collections(args: argparse.Namespace) -> int:
    load_config()
    from zotero_mcp.services.data_access import DataAccessService

    async def _run() -> dict:
        svc = DataAccessService()
        sub = args.subcommand

        if sub == "list":
            collections = await svc.get_collections()
            return {"count": len(collections), "collections": collections}
        if sub == "find":
            matches = await svc.find_collection_by_name(
                args.name, exact_match=args.exact
            )
            return {"count": len(matches), "collections": matches}
        if sub == "create":
            return await svc.create_collection(args.name, parent_key=args.parent_key)
        if sub == "rename":
            await svc.update_collection(args.collection_key, name=args.name)
            return {
                "updated": True,
                "collection_key": args.collection_key,
                "name": args.name,
            }
        if sub == "move":
            await svc.update_collection(args.collection_key, parent_key=args.parent_key)
            return {
                "updated": True,
                "collection_key": args.collection_key,
                "parent_key": args.parent_key,
            }
        if sub == "delete":
            await svc.delete_collection(args.collection_key)
            return {"deleted": True, "collection_key": args.collection_key}
        if sub == "items":
            results = await svc.get_collection_items(
                args.collection_key, limit=args.limit, start=args.offset
            )
            return {"count": len(results), "items": [i.model_dump() for i in results]}

        raise ValueError(f"Unknown collections subcommand: {sub}")

    result = asyncio.run(_run())
    emit(args, result)
    return 0


__all__ = [
    "register_items",
    "run_items",
    "register_notes",
    "run_notes",
    "register_annotations",
    "run_annotations",
    "register_pdfs",
    "run_pdfs",
    "register_collections",
    "run_collections",
]
