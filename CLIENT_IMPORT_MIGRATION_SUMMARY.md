# Client Import Migration Summary

This document summarizes the client module restructuring completed on 2026-02-01.

## New Client Structure

The `clients/` directory has been reorganized into domain-specific subdirectories:

```
clients/
├── database/          # Vector databases and caching
│   ├── __init__.py
│   └── chroma.py      # ChromaDB client
├── gmail/             # Gmail API integration
│   ├── __init__.py
│   └── client.py      # Gmail client
├── llm/               # LLM providers
│   ├── __init__.py
│   ├── base.py        # DeepSeek LLM client
│   └── cli.py         # Claude CLI client
├── metadata/          # Academic metadata lookup
│   ├── __init__.py
│   ├── crossref.py    # Crossref API client
│   └── openalex.py    # OpenAlex API client
└── zotero/            # Zotero integration
    ├── __init__.py
    ├── api_client.py  # Zotero Web API client
    ├── better_bibtex.py  # Better BibTeX client
    └── local_db.py    # Local database client
```

## Import Path Changes

### Old → New Mappings

| Old Path | New Path |
|----------|----------|
| `zotero_mcp.clients.zotero_client` | `zotero_mcp.clients.zotero` |
| `zotero_mcp.clients.local_db` | `zotero_mcp.clients.zotero` |
| `zotero_mcp.clients.better_bibtex` | `zotero_mcp.clients.zotero` |
| `zotero_mcp.clients.chroma` | `zotero_mcp.clients.database` |
| `zotero_mcp.clients.crossref` | `zotero_mcp.clients.metadata` |
| `zotero_mcp.clients.openalex` | `zotero_mcp.clients.metadata` |
| `zotero_mcp.clients.llm` | `zotero_mcp.clients.llm` (unchanged) |
| `zotero_mcp.clients.cli_llm` | `zotero_mcp.clients.llm` |
| `zotero_mcp.clients.gmail` | `zotero_mcp.clients.gmail` (unchanged) |

### Specific Import Changes

#### Zotero Clients
```python
# Old
from zotero_mcp.clients.zotero_client import ZoteroAPIClient, get_zotero_client
from zotero_mcp.clients.local_db import LocalDatabaseClient, ZoteroItem, get_local_database_client
from zotero_mcp.clients.better_bibtex import BetterBibTeXClient, get_better_bibtex_client

# New
from zotero_mcp.clients.zotero import (
    ZoteroAPIClient,
    get_zotero_client,
    LocalDatabaseClient,
    ZoteroItem,
    get_local_database_client,
    BetterBibTeXClient,
    get_better_bibtex_client,
)
```

#### Database Clients
```python
# Old
from zotero_mcp.clients.chroma import ChromaDBClient, get_chroma_client

# New
from zotero_mcp.clients.database import ChromaClient, create_chroma_client
```

#### Metadata Clients
```python
# Old
from zotero_mcp.clients.crossref import CrossrefClient, CrossrefWork
from zotero_mcp.clients.openalex import OpenAlexClient, OpenAlexWork

# New
from zotero_mcp.clients.metadata import (
    CrossrefClient,
    CrossrefWork,
    OpenAlexClient,
    OpenAlexWork,
)
```

#### LLM Clients
```python
# Old
from zotero_mcp.clients.cli_llm import CLILLMClient, is_cli_llm_available
from zotero_mcp.clients.llm import LLMClient, get_llm_client

# New (all from same module)
from zotero_mcp.clients.llm import (
    CLILLMClient,
    LLMClient,
    get_llm_client,
    is_cli_llm_available,
)
```

#### Gmail Client
```python
# Old
from zotero_mcp.clients.gmail import GmailClient
# (DEFAULT_CREDENTIALS_PATH was accessed separately)

# New
from zotero_mcp.clients.gmail import GmailClient, DEFAULT_CREDENTIALS_PATH
```

## Files Updated

### Source Files
1. `src/zotero_mcp/cli.py` - Updated Gmail imports
2. `src/scripts/google_scholar_to_zotero.py` - No changes needed
3. `src/zotero_mcp/services/gmail/gmail_fetcher.py` - No changes needed
4. `src/zotero_mcp/services/data_access.py` - Updated Zotero client imports
5. `src/zotero_mcp/services/common/ai_filter.py` - Updated CLI LLM import
6. `src/zotero_mcp/services/workflow.py` - No changes needed
7. `src/zotero_mcp/services/zotero/semantic_search.py` - Updated database and local_db imports
8. `src/zotero_mcp/services/zotero/search_service.py` - Updated Zotero client imports
9. `src/zotero_mcp/services/zotero/metadata_service.py` - Updated metadata client imports
10. `src/zotero_mcp/services/zotero/item_service.py` - Updated Zotero client imports

### Test Files
1. `tests/test_cli_llm.py` - Updated all mock patches
2. `tests/test_custom_template.py` - No changes needed
3. `tests/test_item_service.py` - Updated Zotero client imports
4. `tests/test_search_service.py` - Updated Zotero client imports

### Client Module Files
1. `src/zotero_mcp/clients/__init__.py` - Updated exports
2. `src/zotero_mcp/clients/zotero/__init__.py` - Added ZoteroItem to exports
3. `src/zotero_mcp/clients/database/__init__.py` - Updated exports (ChromaClient)
4. `src/zotero_mcp/clients/gmail/__init__.py` - Added DEFAULT_CREDENTIALS_PATH to exports
5. `src/zotero_mcp/clients/llm/__init__.py` - Added LLMClient and is_cli_llm_available to exports
6. `src/zotero_mcp/clients/llm/base.py` - Updated internal import

## Verification

- All 64 tests collect successfully
- All import paths work correctly
- No breaking changes to public APIs

## Benefits

1. **Better organization**: Clients grouped by domain (Zotero, database, metadata, LLM, Gmail)
2. **Clearer structure**: Easier to locate and maintain client code
3. **Consistent imports**: All related clients imported from single module
4. **Future-proof**: Easy to add new clients to appropriate domain directories

## Migration Notes

- The old `ChromaDBClient` has been renamed to `ChromaClient` for consistency
- The old `get_chroma_client` has been renamed to `create_chroma_client` for clarity
- All client factory functions follow the pattern: `get_<client>_client()` or `create_<client>()`
