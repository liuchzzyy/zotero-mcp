"""System command group."""

from __future__ import annotations

import argparse
import asyncio
import shutil
import sys

from zotero_mcp.cli_app.common import add_output_arg
from zotero_mcp.cli_app.output import emit
from zotero_mcp.server import serve
from zotero_mcp.utils.config import load_config
from zotero_mcp.utils.system.setup import main as setup_main
from zotero_mcp.utils.system.updater import update_zotero_mcp


def obfuscate_sensitive_value(value: str | None, keep_chars: int = 4) -> str | None:
    if not value or not isinstance(value, str):
        return value
    if len(value) <= keep_chars:
        return "*" * len(value)
    return value[:keep_chars] + "*" * (len(value) - keep_chars)


def obfuscate_config_for_display(config: dict) -> dict:
    if not isinstance(config, dict):
        return config

    obfuscated = config.copy()
    exact_sensitive_keys = {
        "ZOTERO_API_KEY",
        "ZOTERO_LIBRARY_ID",
        "API_KEY",
        "LIBRARY_ID",
        "DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
    }
    sensitive_suffixes = ("_API_KEY", "_TOKEN", "_SECRET", "_PASSWORD")

    for key, value in obfuscated.items():
        key_upper = str(key).upper()
        if key_upper in exact_sensitive_keys or key_upper.endswith(sensitive_suffixes):
            obfuscated[key] = obfuscate_sensitive_value(value)

    return obfuscated


def register(subparsers: argparse._SubParsersAction) -> None:
    system = subparsers.add_parser("system", help="System and runtime commands")
    system_sub = system.add_subparsers(dest="subcommand", required=True)

    system_sub.add_parser("serve", help="Run the MCP server over stdio")

    setup = system_sub.add_parser("setup", help="Configure zotero-mcp")
    setup.add_argument(
        "--no-local",
        action="store_true",
        default=False,
        help="Configure for Zotero Web API instead of local API",
    )
    setup.add_argument("--zotero-api-key", help="Zotero API key")
    setup.add_argument("--library-id", help="Zotero library ID")
    setup.add_argument(
        "--library-type",
        choices=["user", "group"],
        default="user",
        help="Zotero library type",
    )
    setup.add_argument(
        "--skip-semantic-search",
        action="store_true",
        help="Skip semantic search configuration",
    )
    setup.add_argument(
        "--semantic-config-only",
        action="store_true",
        default=False,
        help="Only configure semantic search",
    )

    system_sub.add_parser("setup-info", help="Show installation info")
    system_sub.add_parser("version", help="Print version information")

    update = system_sub.add_parser("update", help="Update zotero-mcp")
    update.add_argument(
        "--check-only", action="store_true", help="Only check for updates"
    )
    update.add_argument("--force", action="store_true", help="Force update")
    update.add_argument(
        "--method",
        choices=["pip", "uv", "conda", "pipx"],
        help="Override installation method",
    )
    add_output_arg(update)


def run(args: argparse.Namespace) -> int:
    sub = args.subcommand

    if sub == "serve":
        load_config()
        asyncio.run(serve())
        return 0

    if sub == "setup":
        return int(setup_main(args))

    if sub == "version":
        from zotero_mcp import __version__

        print(f"Zotero MCP v{__version__}")
        return 0

    if sub == "setup-info":
        config = load_config()
        env_vars = config.get("env", {})
        executable_path = shutil.which("zotero-mcp") or (
            sys.executable + " -m zotero_mcp"
        )

        payload = {
            "command_path": executable_path,
            "python_path": sys.executable,
            "environment": obfuscate_config_for_display(env_vars),
        }

        try:
            from zotero_mcp.services.zotero.semantic_search import (
                create_semantic_search,
            )

            search = create_semantic_search()
            status = search.get_database_status()
            payload["semantic_search"] = {
                "status": "Initialized" if status.get("exists") else "Not Initialized",
                "items": status.get("item_count"),
                "model": status.get("embedding_model"),
            }
        except Exception as exc:
            payload["semantic_search_error"] = str(exc)

        emit(args, payload)
        return 0

    if sub == "update":
        result = update_zotero_mcp(
            check_only=args.check_only, force=args.force, method=args.method
        )
        emit(args, result)
        return 0 if result.get("success") else 1

    raise ValueError(f"Unknown system subcommand: {sub}")


__all__ = ["register", "run", "obfuscate_config_for_display"]
