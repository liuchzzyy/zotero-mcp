import json
from unittest.mock import MagicMock

import pytest

from zotero_mcp.handlers.tools import ToolHandler
from zotero_mcp.models.enums import ToolName
from zotero_mcp.services.resource_service import ResourceService


def test_upload_pdf_tool_is_exposed():
    names = {tool.name for tool in ToolHandler.get_tools()}
    assert ToolName.UPLOAD_PDF in names


@pytest.mark.asyncio
async def test_upload_pdf_tool_returns_json_payload(monkeypatch, tmp_path):
    expected_file = str(tmp_path / "paper.pdf")
    captured: dict[str, str | None] = {}

    async def fake_upload_pdf(self, item_key: str, file_path: str, title: str | None):
        captured["item_key"] = item_key
        captured["file_path"] = file_path
        captured["title"] = title
        return {
            "success": True,
            "item_key": item_key,
            "file_path": file_path,
            "title": title,
            "attachment_keys": ["ATTACH001"],
            "result": {"successful": {"0": "ATTACH001"}},
        }

    monkeypatch.setattr(ResourceService, "upload_pdf", fake_upload_pdf)
    monkeypatch.setattr(
        "zotero_mcp.handlers.tools.get_data_service",
        lambda: MagicMock(),
    )

    handler = ToolHandler()
    contents = await handler.handle_tool(
        ToolName.UPLOAD_PDF,
        {
            "item_key": "abcd1234",
            "file_path": expected_file,
            "title": "My PDF",
            "response_format": "json",
        },
    )

    payload = json.loads(contents[0].text)
    assert captured["item_key"] == "ABCD1234"
    assert captured["file_path"] == expected_file
    assert captured["title"] == "My PDF"
    assert payload["success"] is True
    assert payload["item_key"] == "ABCD1234"
    assert payload["attachment_keys"] == ["ATTACH001"]
