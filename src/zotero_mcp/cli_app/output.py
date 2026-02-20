"""Output formatters for CLI commands."""

from __future__ import annotations

import argparse
import json
from typing import Any


def emit(args: argparse.Namespace, payload: Any) -> None:
    output = getattr(args, "output", "text")
    if output == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        return

    _emit_text(payload)


def _emit_text(payload: Any) -> None:
    if payload is None:
        return
    if isinstance(payload, str):
        print(payload)
        return
    if isinstance(payload, list):
        for item in payload:
            _emit_text(item)
        return
    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                print(f"{key}:")
                print(json.dumps(value, indent=2, ensure_ascii=False, default=str))
            else:
                print(f"{key}: {value}")
        return

    print(payload)
