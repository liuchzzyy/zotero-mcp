"""
Zotero MCP.

A Model Context Protocol server for Zotero research libraries.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("zotero-mcp")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["__version__"]
