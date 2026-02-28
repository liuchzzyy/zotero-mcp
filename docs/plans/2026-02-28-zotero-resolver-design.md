# Design: `utils/zotero_resolver.py` — Reusable ID Resolution Utilities

**Date:** 2026-02-28
**Status:** Approved

---

## Problem

ID resolution (collection key, item key, PDF attachment key, note key) is repeated across scripts and handlers with 3-layer call chains every time. No shared cache at the script level means redundant API calls on every invocation.

---

## Solution

Create `src/zotero_mcp/utils/zotero_resolver.py` — a set of standalone async functions that wrap the existing service layer with module-level TTL caching and a clean, one-call API.

---

## Public API

```python
# Collections
async def find_collection_id(name: str, exact: bool = False) -> str | None
async def find_collection_by_path(path: str) -> str | None   # "Parent/Child" format

# Items
async def find_item_key(
    doi: str | None = None,
    title: str | None = None,
    url: str | None = None,
) -> str | None

# Attachments
async def find_pdf_key(item_key: str) -> str | None

# Notes
async def find_note_key(item_key: str, tag: str | None = None) -> str | None
async def find_note_keys(item_key: str) -> list[str]

# Cache management
def clear_resolver_cache() -> None
```

---

## Architecture

```
scripts / tools.py
       │
       ▼
utils/zotero_resolver.py    ← NEW (module-level cache, TTL=300s)
       │
       ▼
services/data_access.py     ← unchanged (Facade)
       │
       ▼
clients/zotero/api_client.py ← unchanged
```

---

## Caching Strategy

- Module-level `_cache: dict` holds the full collections list and its fetch timestamp
- TTL = 300 seconds (matches ItemService internal cache)
- All functions that need collections share `_get_collections_cached()` helper
- `clear_resolver_cache()` resets the cache for testing or forced refresh
- Item/PDF/note results are NOT cached (keys are per-item, low repetition)

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Not found | Return `None` |
| Multiple matches | Return highest `match_score` first |
| API error | Re-raise original exception |
| Invalid path segments | Return `None` at failed segment |

---

## `find_collection_by_path` Logic

Splits `"Parent/Child"` by `/` and resolves hierarchically:
1. Find top-level collection matching `parts[0]`
2. Among its children, find one matching `parts[1]`, etc.
3. Uses `parentCollection` field from Zotero API response

---

## `find_item_key` Strategy

Priority: DOI → URL → title. Uses first non-None argument provided:
1. Normalize DOI/URL via existing `_normalize_doi()` / `_normalize_url()`
2. Call `data_access.search_items()` with appropriate qmode
3. Return key of first result

---

## Files Changed

| File | Action |
|---|---|
| `src/zotero_mcp/utils/zotero_resolver.py` | **Create new** |
| Existing scripts (optional) | Migrate call sites to use resolver functions |

No changes to `data_access.py`, `item_service.py`, `api_client.py`, or `tools.py`.

---

## Usage Example

```python
from zotero_mcp.utils.zotero_resolver import (
    find_collection_id,
    find_collection_by_path,
    find_item_key,
    find_pdf_key,
    find_note_key,
)

# Find a top-level collection
inbox_key = await find_collection_id("00_INBOX")

# Find a nested collection
aa_key = await find_collection_by_path("00_INBOXS/00_AA")

# Find an item by DOI
item_key = await find_item_key(doi="10.1021/acsnano.0c01234")

# Get its PDF attachment
pdf_key = await find_pdf_key(item_key)

# Get its AI analysis note
note_key = await find_note_key(item_key, tag="AI分析")
```
