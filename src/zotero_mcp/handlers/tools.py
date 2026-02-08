"""MCP tool handlers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastmcp import FastMCP
from mcp.types import CallToolResult, ContentBlock, TextContent, Tool

from zotero_mcp.utils.system.errors import handle_error


class ToolHandler:
    """Handler for MCP tool calls."""

    def __init__(self, app: FastMCP):
        self.app = app

    async def get_tools(self) -> list[Tool]:
        """Get all tool definitions."""
        tools = await self.app.get_tools()
        return [tool.to_mcp_tool() for tool in tools.values()]

    async def handle_tool(self, name: str, arguments: dict[str, Any]) -> Sequence[ContentBlock]:
        """Handle tool call."""
        try:
            tool = await self.app.get_tool(name)
            result = await tool.run(arguments)
            mcp_result = result.to_mcp_result()
            if isinstance(mcp_result, CallToolResult):
                return mcp_result.content
            if isinstance(mcp_result, tuple):
                return mcp_result[0]
            return mcp_result
        except Exception as exc:
            message = handle_error(exc, operation=name)
            return [TextContent(type="text", text=message)]
