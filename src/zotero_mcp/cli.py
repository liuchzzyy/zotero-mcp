"""Command-line interface for Zotero MCP server."""

from zotero_mcp.cli_app.commands.system import obfuscate_config_for_display
from zotero_mcp.cli_app.main import main

__all__ = ["main", "obfuscate_config_for_display"]


if __name__ == "__main__":
    main()
