"""CLI parser and dispatch registry."""

from __future__ import annotations

import argparse

from zotero_mcp.cli_app.commands import resources, semantic, system, workflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Zotero Model Context Protocol server")
    subparsers = parser.add_subparsers(dest="command")

    system.register(subparsers)
    workflow.register(subparsers)
    semantic.register(subparsers)
    resources.register_items(subparsers)
    resources.register_notes(subparsers)
    resources.register_annotations(subparsers)
    resources.register_pdfs(subparsers)
    resources.register_collections(subparsers)

    return parser


def dispatch(args: argparse.Namespace) -> int:
    command = args.command
    if command == "system":
        return system.run(args)
    if command == "workflow":
        return workflow.run(args)
    if command == "semantic":
        return semantic.run(args)
    if command == "items":
        return resources.run_items(args)
    if command == "notes":
        return resources.run_notes(args)
    if command == "annotations":
        return resources.run_annotations(args)
    if command == "pdfs":
        return resources.run_pdfs(args)
    if command == "collections":
        return resources.run_collections(args)

    raise ValueError(f"Unknown command: {command}")
