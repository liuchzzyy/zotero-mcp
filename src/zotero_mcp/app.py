"""FastMCP app factory for tool registration."""

from __future__ import annotations

from fastmcp import FastMCP

from zotero_mcp.settings import settings
from zotero_mcp.tools import register_all_tools

_fastmcp_app: FastMCP | None = None


def get_fastmcp_app() -> FastMCP:
    """Return a singleton FastMCP app with all tools registered."""
    global _fastmcp_app
    if _fastmcp_app is None:
        _fastmcp_app = FastMCP(name=settings.server_name)
        register_all_tools(_fastmcp_app)
    return _fastmcp_app


mcp = get_fastmcp_app()

