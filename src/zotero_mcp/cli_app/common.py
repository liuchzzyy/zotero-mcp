"""Shared argparse helpers for CLI commands."""

from __future__ import annotations

import argparse


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return parsed


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
        type=_positive_int,
        default=default,
        help=f"Number of items to fetch per batch from API (default: {default})",
    )


def add_treated_limit_arg(
    parser: argparse.ArgumentParser,
    default: int | None = None,
    help_text: str | None = None,
) -> None:
    if default is not None:
        parser.add_argument(
            "--treated-limit",
            type=_positive_int,
            default=default,
            help=help_text or "Maximum total number of items to process",
        )
        return
    parser.add_argument(
        "--treated-limit",
        type=_positive_int,
        help=help_text or "Maximum total number of items to process",
    )


def add_all_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all matching items (ignores --treated-limit)",
    )
