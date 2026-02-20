from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from zotero_mcp.services.resource_service import ResourceService


@pytest.mark.asyncio
async def test_create_items_wraps_single_payload():
    data_service = MagicMock()
    data_service.create_items = AsyncMock(return_value={"successful": {"0": {}}})
    service = ResourceService(data_service=data_service)

    payload = {"data": {"title": "Example"}}
    await service.create_items(payload)

    data_service.create_items.assert_awaited_once_with([payload])


@pytest.mark.asyncio
async def test_search_notes_filters_and_paginates():
    data_service = MagicMock()
    data_service.search_items = AsyncMock(
        return_value=[
            SimpleNamespace(key="I1", title="Item One"),
            SimpleNamespace(key="I2", title="Item Two"),
        ]
    )
    data_service.get_notes = AsyncMock(
        side_effect=[
            [
                {"data": {"key": "N1", "note": "matched note A"}},
                {"data": {"key": "N2", "note": "irrelevant"}},
            ],
            [{"data": {"key": "N3", "note": "Matched note B"}}],
        ]
    )
    service = ResourceService(data_service=data_service)

    result = await service.search_notes(query="matched", limit=1, offset=1)

    data_service.search_items.assert_awaited_once_with("matched", limit=50, offset=0)
    assert result["total"] == 2
    assert result["count"] == 1
    assert result["results"][0]["note_key"] == "N3"


@pytest.mark.asyncio
async def test_list_annotations_filters_by_type():
    data_service = MagicMock()
    data_service.get_annotations = AsyncMock(
        return_value=[
            {"data": {"annotationType": "highlight"}},
            {"data": {"annotationType": "note"}},
        ]
    )
    service = ResourceService(data_service=data_service)

    result = await service.list_annotations(
        item_key="ITEM1",
        annotation_type="HIGHLIGHT",
        limit=10,
        offset=0,
    )

    assert result["total"] == 1
    assert result["count"] == 1
    assert result["annotations"][0]["data"]["annotationType"] == "highlight"


@pytest.mark.asyncio
async def test_rename_collection_calls_update_and_returns_summary():
    data_service = MagicMock()
    data_service.update_collection = AsyncMock(return_value=None)
    service = ResourceService(data_service=data_service)

    result = await service.rename_collection(collection_key="C1", name="Renamed")

    data_service.update_collection.assert_awaited_once_with("C1", name="Renamed")
    assert result == {"updated": True, "collection_key": "C1", "name": "Renamed"}
