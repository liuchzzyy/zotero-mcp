"""Shared argparse helpers for CLI commands."""

from __future__ import annotations

import argparse


def add_output_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )


def add_scan_limit_arg(parser: argparse.ArgumentParser, default: int) -> None:
    parser.add_argument(
        "--scan-limit",
        type=int,
        default=default,
        help=f"Number of items to fetch per batch from API (default: {default})",
    )


def add_treated_limit_arg(
    parser: argparse.ArgumentParser,
    default: int | None = None,
    help_text: str | None = None,
) -> None:
    kwargs: dict[str, object] = {
        "type": int,
        "help": help_text or "Maximum total number of items to process",
    }
    if default is not None:
        kwargs["default"] = default
    parser.add_argument("--treated-limit", **kwargs)
