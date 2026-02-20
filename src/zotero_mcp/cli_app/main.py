"""Main entry point for the refactored CLI."""

from __future__ import annotations

import sys

from zotero_mcp.cli_app.registry import build_parser, dispatch
from zotero_mcp.utils.config.logging import initialize_logging


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        raise SystemExit(2)

    initialize_logging()

    try:
        code = dispatch(args)
        raise SystemExit(code)
    except KeyboardInterrupt as exc:
        raise SystemExit(130) from exc
    except SystemExit:
        raise
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
