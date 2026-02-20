"""Service layer for CLI resource operations."""

from __future__ import annotations

from typing import Any

from zotero_mcp.services.data_access import DataAccessService


class ResourceService:
    """Business operations for item/note/annotation/pdf/collection commands."""

    def __init__(self, data_service: DataAccessService | None = None):
        self.data_service = data_service or DataAccessService()

    # -------------------- Item operations --------------------

    async def get_item(self, item_key: str) -> dict[str, Any]:
        return await self.data_service.get_item(item_key)

    async def list_items(
        self,
        limit: int,
        offset: int,
        item_type: str | None = None,
    ) -> dict[str, Any]:
        results = await self.data_service.get_all_items(
            limit=limit,
            start=offset,
            item_type=item_type,
        )
        return {"count": len(results), "items": [item.model_dump() for item in results]}

    async def list_item_children(
        self,
        item_key: str,
        item_type: str | None = None,
    ) -> dict[str, Any]:
        children = await self.data_service.get_item_children(
            item_key, item_type=item_type
        )
        return {"count": len(children), "children": children}

    async def get_item_fulltext(self, item_key: str) -> dict[str, Any]:
        fulltext = await self.data_service.get_fulltext(item_key)
        return {"item_key": item_key, "fulltext": fulltext}

    async def get_item_bundle(
        self,
        item_key: str,
        include_fulltext: bool,
        include_annotations: bool,
        include_notes: bool,
    ) -> dict[str, Any]:
        return await self.data_service.get_item_bundle(
            item_key=item_key,
            include_fulltext=include_fulltext,
            include_annotations=include_annotations,
            include_notes=include_notes,
        )

    async def delete_item(self, item_key: str) -> dict[str, Any]:
        return await self.data_service.delete_item(item_key)

    async def update_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.data_service.update_item(payload)

    async def create_items(
        self, payload: dict[str, Any] | list[dict[str, Any]]
    ) -> dict[str, Any]:
        items = payload if isinstance(payload, list) else [payload]
        return await self.data_service.create_items(items)

    async def add_tags_to_item(self, item_key: str, tags: list[str]) -> dict[str, Any]:
        return await self.data_service.add_tags_to_item(item_key, tags)

    async def add_item_to_collection(
        self, collection_key: str, item_key: str
    ) -> dict[str, Any]:
        return await self.data_service.add_item_to_collection(collection_key, item_key)

    async def remove_item_from_collection(
        self, collection_key: str, item_key: str
    ) -> dict[str, Any]:
        return await self.data_service.remove_item_from_collection(
            collection_key, item_key
        )

    # -------------------- Note operations --------------------

    async def list_notes(
        self, item_key: str, limit: int, offset: int
    ) -> dict[str, Any]:
        notes = await self.data_service.get_notes(item_key)
        total = len(notes)
        sliced = notes[offset : offset + limit]
        return {"total": total, "count": len(sliced), "notes": sliced}

    async def create_note(
        self, item_key: str, content: str, tags: list[str] | None = None
    ) -> dict[str, Any]:
        return await self.data_service.create_note(
            parent_key=item_key,
            content=content,
            tags=tags or [],
        )

    async def search_notes(self, query: str, limit: int, offset: int) -> dict[str, Any]:
        candidates = await self.data_service.search_items(
            query,
            limit=max(limit * 2, 50),
            offset=0,
        )
        hits: list[dict[str, Any]] = []
        query_lower = query.lower()

        for item in candidates:
            notes = await self.data_service.get_notes(item.key)
            for note in notes:
                data = note.get("data", {})
                raw_note = str(data.get("note", ""))
                if query_lower in raw_note.lower():
                    hits.append(
                        {
                            "item_key": item.key,
                            "item_title": item.title,
                            "note_key": data.get("key", ""),
                            "note": raw_note,
                        }
                    )

        total = len(hits)
        sliced = hits[offset : offset + limit]
        return {
            "query": query,
            "total": total,
            "count": len(sliced),
            "results": sliced,
        }

    # -------------------- Annotation operations --------------------

    async def list_annotations(
        self,
        item_key: str,
        annotation_type: str,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        annotations = await self.data_service.get_annotations(item_key)
        if annotation_type != "all":
            annotations = [
                annotation
                for annotation in annotations
                if annotation.get("data", {}).get("annotationType", "").lower()
                == annotation_type.lower()
            ]
        total = len(annotations)
        sliced = annotations[offset : offset + limit]
        return {
            "item_key": item_key,
            "total": total,
            "count": len(sliced),
            "annotations": sliced,
        }

    # -------------------- PDF operations --------------------

    async def upload_attachment(
        self,
        item_key: str,
        file_path: str,
        title: str | None = None,
    ) -> dict[str, Any]:
        return await self.data_service.item_service.upload_attachment(
            parent_key=item_key,
            file_path=file_path,
            title=title,
        )

    # -------------------- Collection operations --------------------

    async def list_collections(self) -> dict[str, Any]:
        collections = await self.data_service.get_collections()
        return {"count": len(collections), "collections": collections}

    async def find_collections(self, name: str, exact: bool = False) -> dict[str, Any]:
        matches = await self.data_service.find_collection_by_name(
            name, exact_match=exact
        )
        return {"count": len(matches), "collections": matches}

    async def create_collection(
        self,
        name: str,
        parent_key: str | None = None,
    ) -> dict[str, Any]:
        return await self.data_service.create_collection(name, parent_key=parent_key)

    async def rename_collection(self, collection_key: str, name: str) -> dict[str, Any]:
        await self.data_service.update_collection(collection_key, name=name)
        return {"updated": True, "collection_key": collection_key, "name": name}

    async def move_collection(
        self,
        collection_key: str,
        parent_key: str | None,
    ) -> dict[str, Any]:
        await self.data_service.update_collection(collection_key, parent_key=parent_key)
        return {
            "updated": True,
            "collection_key": collection_key,
            "parent_key": parent_key,
        }

    async def delete_collection(self, collection_key: str) -> dict[str, Any]:
        await self.data_service.delete_collection(collection_key)
        return {"deleted": True, "collection_key": collection_key}

    async def list_collection_items(
        self,
        collection_key: str,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        results = await self.data_service.get_collection_items(
            collection_key,
            limit=limit,
            start=offset,
        )
        return {"count": len(results), "items": [item.model_dump() for item in results]}
