# CLAUDE.md

Guidance for working in this repository.

## Project Overview

Zotero MCP connects AI assistants to Zotero research libraries via the Model Context Protocol. Provides semantic search (ChromaDB), PDF analysis via LLMs, annotation extraction, and batch workflows.

**Tech Stack**: MCP SDK, Python 3.12+, uv

## Key Commands

```bash
# Development
uv sync --all-groups
uv run zotero-mcp serve
uv run zotero-mcp setup

# Semantic Search
uv run zotero-mcp update-db              # Metadata-only (fast)
uv run zotero-mcp update-db --fulltext   # With full-text
uv run zotero-mcp db-status

# Research Workflow
uv run zotero-mcp scan                   # Scan for unprocessed papers
uv run zotero-mcp update-metadata         # Enhance metadata
uv run zotero-mcp deduplicate            # Find/remove duplicates

# Testing
uv run pytest
uv run pytest --cov=src

# Code Quality
uv run ruff check
uv run ruff format
uv run ty check
```

## Architecture

Layered architecture with domain separation:

```
src/zotero_mcp
├── server.py        # MCP stdio server entrypoint
├── cli.py           # CLI entrypoint
├── settings.py      # Pydantic Settings (env config)
├── handlers/        # MCP tool/prompt handlers
│   ├── annotations.py
│   ├── batch.py
│   ├── collections.py
│   ├── database.py
│   ├── items.py
│   ├── search.py
│   └── workflow.py
├── services/        # Business logic organized by domain
│   ├── zotero/
│   │   ├── item_service.py       # CRUD operations
│   │   ├── search_service.py    # Search logic
│   │   ├── metadata_service.py  # DOI lookup
│   │   ├── metadata_update_service.py
│   │   ├── semantic_search.py   # Vector search
│   │   └── duplicate_service.py  # Deduplication
│   ├── workflow.py      # Batch analysis with checkpoint
│   ├── data_access.py  # Facade for Local DB / Zotero API
│   └── checkpoint.py   # Checkpoint management
├── clients/         # External service clients
│   ├── zotero/        # Zotero API + local DB
│   ├── database/       # ChromaDB vector database
│   ├── metadata/       # Crossref, OpenAlex APIs
│   └── llm/           # LLM providers
├── models/          # Pydantic models organized by domain
│   ├── common/        # Shared base models
│   ├── zotero/        # Item/collection models
│   ├── workflow/       # Batch operation models
│   └── search/        # Search query models
└── utils/           # Utility functions
    ├── config/
    ├── data/
    ├── formatting/
    ├── async_helpers/
    └── system/
```

## Key Notes

- All I/O is async; use `async/await`
- `DataAccessService` auto-selects Local DB (fast reads) vs Zotero API (writes/fallback)
- `WorkflowService` uses `CheckpointService` for resume-capable batch operations
- Feature flags: `ZOTERO_ENABLE_ADVANCED_QUERIES`, `ZOTERO_ENABLE_GIT_OPERATIONS`
- HTML title cleaning in `metadata_update_service.py` for better API matching
- Use absolute imports: `from zotero_mcp.services import ...`
- Type hints required on all functions

## Batch Operation Parameters

| Command | `scan_limit` | `treated_limit` | Skip Tag | Counts |
|---------|----------------|------------------|------------|--------|
| `scan` | Items per batch | Items needing analysis | "AI分析" | Candidates without tag |
| `update-metadata` | Items per batch | Items needing update | "AI元数据" | Items without tag |
| `deduplicate` | Items per batch | **Duplicates found** | None | Duplicate entries |

**Scanning Logic**:
```
for each collection:
    while processed_count < treated_limit:
        fetch scan_limit items (with pagination offset)
        for each item:
            if item should be skipped (has tag, etc.):
                skip  # Does NOT count towards treated_limit
            else:
                process item
                processed_count += 1

        if fetched items < scan_limit:
            break  # Collection exhausted

        if processed_count >= treated_limit:
            break  # Stop all scanning
```

## Code Style

- **Linter/Formatter**: Ruff (line-length: 88, target: py312)
- **Type Checker**: ty
- **Naming**: `snake_case` (variables/functions), `PascalCase` (classes)
- **Imports**: Absolute imports only

## Adding a New Tool

1. Define Pydantic models in `models/`
2. Implement business logic in `services/`
3. Define tool schema in `handlers/tools.py`

## Multi-Modal PDF Analysis

| Provider | Vision Support | Use Case |
|-----------|------------------|------------|
| `claude-cli` | ✅ Yes | Best for papers with figures/charts |
| `deepseek` | ❌ No | Text-only, fastest/cheapest |

**Auto-Selection** (`llm_provider="auto"`):
1. PDF has images/tables → select `claude-cli`
2. PDF is text-only → select `deepseek`

## Troubleshooting

**Zotero local API**: Requires Zotero 7+ running with "Allow other applications to communicate" enabled

**Semantic search empty**: Run `zotero-mcp update-db`

**API timeout**: Default is 45s; may need adjustment for slow networks

**pyzotero HTTP 429**: Silently swallows errors, returns int status codes. Fixed at API client layer with `_check_api_result()`.
