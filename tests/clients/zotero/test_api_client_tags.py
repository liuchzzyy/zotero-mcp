"""Tests for ZoteroAPIClient tag operations."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from zotero_mcp.clients.zotero.api_client import ZoteroAPIClient


@pytest.mark.asyncio
async def test_add_tags_normalizes_and_avoids_duplicate_append():
    client = ZoteroAPIClient(library_id="1", local=True)
    client._client = MagicMock()
    client._client.update_item.return_value = {"ok": True}

    client.get_item = AsyncMock(
        return_value={
            "key": "ITEM1",
            "data": {
                "tags": [{"tag": "AI分析"}, "保留"],
            },
        }
    )

    await client.add_tags("ITEM1", [" 保留 ", "新增", "", "新增"])

    client.get_item.assert_awaited_once_with("ITEM1")
    client.client.update_item.assert_called_once()
    updated = client.client.update_item.call_args.args[0]
    assert updated["data"]["tags"] == [
        {"tag": "AI分析"},
        {"tag": "保留"},
        {"tag": "新增"},
    ]
