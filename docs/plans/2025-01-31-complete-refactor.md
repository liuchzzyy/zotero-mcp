# Complete Architecture Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Comprehensive refactoring of the entire codebase into modular, well-organized structure with clear separation of concerns across all modules.

**Architecture Overview:**
- **services/** - Business logic layer (already planned)
- **clients/** - External API clients organized by domain
- **models/** - Pydantic models organized by domain
- **utils/** - Utility functions organized by purpose
- **formatters/** - Output formatting (keep as-is or minor reorg)
- **tools/** - MCP tool wrappers (keep as-is)

**Tech Stack:** Python 3.10+, FastMCP, Pydantic, asyncio, uv

**Important:** No backward compatibility - all old code will be deleted and replaced with new structure.

---

## Part 1: Services Layer Refactor (8 Tasks)

*See original plan for services refactoring tasks.*

---

## Part 2: Clients Layer Refactor (3 Tasks)

### Current Structure
```
clients/
├── better_bibtex.py    # Better BibTeX plugin
├── chroma.py            # ChromaDB vector database
├── cli_llm.py           # Claude CLI LLM client
├── crossref.py          # Crossref API
├── gmail.py             # Gmail API
├── llm.py               # Generic LLM client
├── local_db.py          # Zotero local SQLite DB
├── openalex.py          # OpenAlex API
└── zotero_client.py     # Zotero Web API
```

### Proposed Structure
```
clients/
├── __init__.py
├── zotero/
│   ├── __init__.py
│   ├── api_client.py         # Zotero Web API (from zotero_client.py)
│   ├── local_db.py           # Local SQLite DB (from local_db.py)
│   └── better_bibtex.py      # Better BibTeX integration
├── database/
│   ├── __init__.py
│   └── chroma.py             # ChromaDB client (from chroma.py)
├── metadata/
│   ├── __init__.py
│   ├── crossref.py           # Crossref API (from crossref.py)
│   └── openalex.py           # OpenAlex API (from openalex.py)
├── llm/
│   ├── __init__.py
│   ├── base.py               # Base LLM client (from llm.py)
│   └── cli.py                # Claude CLI client (from cli_llm.py)
└── gmail/
    ├── __init__.py
    └── client.py             # Gmail API (from gmail.py)
```

### Task 9: Reorganize Clients into Domain-Specific Modules

**Files:**
- Create: `src/zotero_mcp/clients/zotero/`
- Create: `src/zotero_mcp/clients/database/`
- Create: `src/zotero_mcp/clients/metadata/`
- Create: `src/zotero_mcp/clients/llm/`
- Create: `src/zotero_mcp/clients/gmail/`
- Move existing files into new structure
- Update all imports across codebase

**Step 1: Create directory structure**

Run:
```bash
cd src/zotero_mcp/clients
mkdir -p zotero database metadata llm gmail
```

**Step 2: Move Zotero-related clients**

Run:
```bash
mv zotero_client.py zotero/api_client.py
mv local_db.py zotero/
mv better_bibtex.py zotero/
```

**Step 3: Create zotero/__init__.py**

Create: `src/zotero_mcp/clients/zotero/__init__.py`

```python
"""Zotero clients - API, local DB, and Better BibTeX integration."""

from .api_client import ZoteroAPIClient, get_zotero_client
from .better_bibtex import BetterBibTeXClient, get_better_bibtex_client
from .local_db import LocalDatabaseClient, get_local_database_client

__all__ = [
    "ZoteroAPIClient",
    "get_zotero_client",
    "BetterBibTeXClient",
    "get_better_bibtex_client",
    "LocalDatabaseClient",
    "get_local_database_client",
]
```

**Step 4: Move database client**

Run:
```bash
mv chroma.py database/chroma.py
```

Create: `src/zotero_mcp/clients/database/__init__.py`

```python
"""Database clients - vector databases and caches."""

from .chroma import ChromaDBClient, get_chroma_client

__all__ = [
    "ChromaDBClient",
    "get_chroma_client",
]
```

**Step 5: Move metadata clients**

Run:
```bash
mv crossref.py metadata/crossref.py
mv openalex.py metadata/openalex.py
```

Create: `src/zotero_mcp/clients/metadata/__init__.py`

```python
"""Metadata clients - academic paper metadata APIs."""

from .crossref import CrossrefClient, CrossrefWork
from .openalex import OpenAlexClient, OpenAlexWork

__all__ = [
    "CrossrefClient",
    "CrossrefWork",
    "OpenAlexClient",
    "OpenAlexWork",
]
```

**Step 6: Move LLM clients**

Run:
```bash
mv llm.py llm/base.py
mv cli_llm.py llm/cli.py
```

Create: `src/zotero_mcp/clients/llm/__init__.py`

```python
"""LLM clients - various LLM providers."""

from .base import get_llm_client
from .cli import CLILLMClient

__all__ = [
    "get_llm_client",
    "CLILLMClient",
]
```

**Step 7: Move Gmail client**

Run:
```bash
mv gmail.py gmail/client.py
```

Create: `src/zotero_mcp/clients/gmail/__init__.py`

```python
"""Gmail client - Gmail API integration."""

from .client import GmailClient

__all__ = [
    "GmailClient",
]
```

**Step 8: Update main clients __init__.py**

Modify: `src/zotero_mcp/clients/__init__.py`

```python
"""External service clients organized by domain."""

from .database import ChromaDBClient, get_chroma_client
from .gmail import GmailClient
from .llm import CLILLMClient, get_llm_client
from .metadata import CrossrefClient, OpenAlexClient
from .zotero import (
    BetterBibTeXClient,
    LocalDatabaseClient,
    ZoteroAPIClient,
    get_better_bibtex_client,
    get_local_database_client,
    get_zotero_client,
)

__all__ = [
    # Zotero
    "ZoteroAPIClient",
    "get_zotero_client",
    "LocalDatabaseClient",
    "get_local_database_client",
    "BetterBibTeXClient",
    "get_better_bibtex_client",
    # Database
    "ChromaDBClient",
    "get_chroma_client",
    # Metadata
    "CrossrefClient",
    "OpenAlexClient",
    # LLM
    "get_llm_client",
    "CLILLMClient",
    # Gmail
    "GmailClient",
]
```

**Step 9: Find and update all imports**

Run:
```bash
grep -r "from zotero_mcp.clients" src/ --include="*.py" | grep -v "__pycache__"
```

Update each import. Example changes:
```python
# Old:
from zotero_mcp.clients.zotero_client import ZoteroAPIClient
# New:
from zotero_mcp.clients.zotero import ZoteroAPIClient

# Old:
from zotero_mcp.clients.chroma import ChromaDBClient
# New:
from zotero_mcp.clients.database import ChromaDBClient

# Old:
from zotero_mcp.clients.llm import get_llm_client
# New:
from zotero_mcp.clients.llm import get_llm_client
```

**Step 10: Run tests**

Run:
```bash
uv run pytest tests/ -v 2>&1 | head -50
```

**Step 11: Fix import errors iteratively**

Fix each import error until all tests pass.

**Step 12: Commit**

```bash
git add src/zotero_mcp/clients/
git commit -m "refactor(clients): reorganize into domain-specific modules"
```

---

## Part 3: Models Layer Refactor (2 Tasks)

### Current Structure
```
models/
├── annotations.py    # Annotation models
├── batch.py          # Batch operation models
├── collections.py    # Collection models
├── common.py         # Common response models
├── database.py       # Semantic search models
├── gmail.py          # Gmail models
├── items.py          # Item models
├── note_structure.py # Note structure models
├── rss.py            # RSS models
├── search.py         # Search models
└── workflow.py       # Workflow models
```

### Proposed Structure
```
models/
├── __init__.py
├── common/           # Shared base models
│   ├── __init__.py
│   └── responses.py  # ResponseFormat, standard response fields
├── zotero/           # Zotero-specific models
│   ├── __init__.py
│   ├── items.py      # Item, Creator, Note models
│   ├── collections.py
│   └── annotations.py
├── workflow/         # Batch operation models
│   ├── __init__.py
│   ├── batch.py
│   └── analysis.py
├── search/           # Search-related models
│   ├── __init__.py
│   └── queries.py
├── ingestion/        # RSS/Gmail ingestion models
│   ├── __init__.py
│   ├── rss.py
│   └── gmail.py
└── database/         # Semantic search models
    ├── __init__.py
    └── semantic.py
```

### Task 10: Reorganize Models into Domain-Specific Modules

**Files:**
- Create domain directories
- Move files into new structure
- Update all imports

**Step 1: Create directory structure**

Run:
```bash
cd src/zotero_mcp/models
mkdir -p common zotero workflow search ingestion database
```

**Step 2: Move common models**

Run:
```bash
mv common.py common/responses.py
```

Create: `src/zotero_mcp/models/common/__init__.py`

```python
"""Common base models used across the application."""

from .responses import ResponseFormat, SearchResultItem

__all__ = [
    "ResponseFormat",
    "SearchResultItem",
]
```

**Step 3: Move Zotero models**

Run:
```bash
mv items.py zotero/
mv collections.py zotero/
mv annotations.py zotero/
mv note_structure.py zotero/
```

Create: `src/zotero_mcp/models/zotero/__init__.py`

```python
"""Zotero-specific models."""

from .annotations import Annotation, AnnotationPayload
from .collections import Collection
from .items import Item, Creator, Note
from .note_structure import NoteStructure

__all__ = [
    "Annotation",
    "AnnotationPayload",
    "Collection",
    "Item",
    "Creator",
    "Note",
    "NoteStructure",
]
```

**Step 4: Move workflow models**

Run:
```bash
mv batch.py workflow/batch.py
mv workflow.py workflow/analysis.py
```

Create: `src/zotero_mcp/models/workflow/__init__.py`

```python
"""Batch workflow and analysis models."""

from .analysis import AnalysisItem, ItemAnalysisResult, PrepareAnalysisResponse
from .batch import BatchAnalyzeResponse

__all__ = [
    "AnalysisItem",
    "ItemAnalysisResult",
    "PrepareAnalysisResponse",
    "BatchAnalyzeResponse",
]
```

**Step 5: Move search models**

Run:
```bash
mv search.py search/queries.py
```

Create: `src/zotero_mcp/models/search/__init__.py`

```python
"""Search-related models."""

from .queries import AdvancedSearchInput, SearchInput

__all__ = [
    "AdvancedSearchInput",
    "SearchInput",
]
```

**Step 6: Move ingestion models**

Run:
```bash
mv rss.py ingestion/rss.py
mv gmail.py ingestion/gmail.py
```

Create: `src/zotero_mcp/models/ingestion/__init__.py`

```python
"""RSS and Gmail ingestion models."""

from .gmail import EmailItem, EmailMessage, GmailProcessResult
from .rss import RSSFeed, RSSItem, RSSProcessResult

__all__ = [
    "EmailItem",
    "EmailMessage",
    "GmailProcessResult",
    "RSSFeed",
    "RSSItem",
    "RSSProcessResult",
]
```

**Step 7: Move database models**

Run:
```bash
mv database.py database/semantic.py
```

Create: `src/zotero_mcp/models/database/__init__.py`

```python
"""Semantic search database models."""

from .semantic import DatabaseStatusResponse

__all__ = [
    "DatabaseStatusResponse",
]
```

**Step 8: Update main models __init__.py**

Modify: `src/zotero_mcp/models/__init__.py`

```python
"""Pydantic models organized by domain."""

from .common import ResponseFormat, SearchResultItem
from .database import DatabaseStatusResponse
from .ingestion import EmailItem, EmailMessage, GmailProcessResult, RSSFeed, RSSItem, RSSProcessResult
from .search import AdvancedSearchInput, SearchInput
from .workflow import AnalysisItem, BatchAnalyzeResponse, ItemAnalysisResult, PrepareAnalysisResponse
from .zotero import Annotation, AnnotationPayload, Collection, Item, Note

__all__ = [
    # Common
    "ResponseFormat",
    "SearchResultItem",
    # Zotero
    "Annotation",
    "AnnotationPayload",
    "Collection",
    "Item",
    "Note",
    # Workflow
    "AnalysisItem",
    "BatchAnalyzeResponse",
    "ItemAnalysisResult",
    "PrepareAnalysisResponse",
    # Search
    "SearchInput",
    "AdvancedSearchInput",
    # Ingestion
    "RSSFeed",
    "RSSItem",
    "RSSProcessResult",
    "EmailItem",
    "EmailMessage",
    "GmailProcessResult",
    # Database
    "DatabaseStatusResponse",
]
```

**Step 9: Find and update all imports**

Run:
```bash
grep -r "from zotero_mcp.models" src/ --include="*.py" | grep -v "__pycache__"
```

Update each import. Example changes:
```python
# Old:
from zotero_mcp.models.items import Item
# New:
from zotero_mcp.models.zotero import Item

# Old:
from zotero_mcp.models.rss import RSSItem
# New:
from zotero_mcp.models.ingestion import RSSItem

# Old:
from zotero_mcp.models.workflow import PrepareAnalysisResponse
# New:
from zotero_mcp.models.workflow import PrepareAnalysisResponse
```

**Step 10: Run tests**

Run:
```bash
uv run pytest tests/ -v 2>&1 | head -50
```

**Step 11: Fix import errors iteratively**

**Step 12: Commit**

```bash
git add src/zotero_mcp/models/
git commit -m "refactor(models): reorganize into domain-specific modules"
```

---

## Part 4: Utils Layer Refactor (2 Tasks)

### Current Structure
```
utils/
├── batch_loader.py      # Batch loading logic
├── beautify.py          # Note beautification
├── cache.py             # Caching utilities
├── config.py            # Configuration management
├── errors.py            # Error definitions
├── helpers.py           # Helper functions
├── logging_config.py    # Logging setup
├── markdown_html.py     # Markdown conversion
├── setup.py             # Setup utilities
├── templates.py         # Template management
├── updater.py           # Update utilities
└── zotero_mapper.py     # Zotero data mapping
```

### Proposed Structure
```
utils/
├── __init__.py
├── config/              # Configuration and environment
│   ├── __init__.py
│   ├── config.py        # Config management
│   └── logging.py       # Logging setup
├── data/                # Data processing and mapping
│   ├── __init__.py
│   ├── mapper.py        # Zotero data mapping
│   └── templates.py     # Template management
├── formatting/          # Text/formatting utilities
│   ├── __init__.py
│   ├── beautify.py      # Note beautification
│   ├── markdown.py      # Markdown conversion
│   └── helpers.py       # Common helper functions
├── async_helpers/       # Async/batch operations
│   ├── __init__.py
│   ├── batch_loader.py  # Batch loading
│   └── cache.py         # Caching utilities
└── system/              # System-level utilities
    ├── __init__.py
    ├── errors.py        # Error definitions
    ├── setup.py         # Setup utilities
    └── updater.py       # Update utilities
```

### Task 11: Reorganize Utils into Purpose-Specific Modules

**Files:**
- Create purpose directories
- Move files into new structure
- Update all imports

**Step 1: Create directory structure**

Run:
```bash
cd src/zotero_mcp/utils
mkdir -p config data formatting async_helpers system
```

**Step 2: Move config utilities**

Run:
```bash
mv config.py config/
mv logging_config.py config/logging.py
```

Create: `src/zotero_mcp/utils/config/__init__.py`

```python
"""Configuration and logging setup."""

from .config import get_config
from .logging import get_logger, log_task_end, log_task_start

__all__ = [
    "get_config",
    "get_logger",
    "log_task_end",
    "log_task_start",
]
```

**Step 3: Move data utilities**

Run:
```bash
mv zotero_mapper.py data/mapper.py
mv templates.py data/
```

Create: `src/zotero_mcp/utils/data/__init__.py`

```python
"""Data processing and mapping utilities."""

from .mapper import map_zotero_item
from .templates import DEFAULT_ANALYSIS_TEMPLATE_JSON, get_analysis_questions

__all__ = [
    "map_zotero_item",
    "DEFAULT_ANALYSIS_TEMPLATE_JSON",
    "get_analysis_questions",
]
```

**Step 4: Move formatting utilities**

Run:
```bash
mv beautify.py formatting/beautify.py
mv markdown_html.py formatting/markdown.py
mv helpers.py formatting/helpers.py
```

Create: `src/zotero_mcp/utils/formatting/__init__.py`

```python
"""Text and formatting utilities."""

from .beautify import beautify_ai_note
from .helpers import DOI_PATTERN, clean_title, format_creators
from .markdown import markdown_to_html

__all__ = [
    "beautify_ai_note",
    "DOI_PATTERN",
    "clean_title",
    "format_creators",
    "markdown_to_html",
]
```

**Step 5: Move async utilities**

Run:
```bash
mv batch_loader.py async_helpers/
mv cache.py async_helpers/
```

Create: `src/zotero_mcp/utils/async_helpers/__init__.py`

```python
"""Async operations and caching utilities."""

from .batch_loader import BatchLoader
from .cache import cached

__all__ = [
    "BatchLoader",
    "cached",
]
```

**Step 6: Move system utilities**

Run:
```bash
mv errors.py system/
mv setup.py system/
mv updater.py system/
```

Create: `src/zotero_mcp/utils/system/__init__.py`

```python
"""System-level utilities."""

from .errors import ZoteroMCPError, handle_errors
from .setup import check_dependencies
from .updater import check_for_updates

__all__ = [
    "ZoteroMCPError",
    "handle_errors",
    "check_dependencies",
    "check_for_updates",
]
```

**Step 7: Update main utils __init__.py**

Modify: `src/zotero_mcp/utils/__init__.py`

```python
"""Utility functions organized by purpose."""

# Re-export commonly used utilities for backward compatibility
from .config import get_logger, log_task_end, log_task_start
from .formatting import DOI_PATTERN, clean_title, format_creators
from .data import DEFAULT_ANALYSIS_TEMPLATE_JSON, get_analysis_questions

__all__ = [
    # Config
    "get_logger",
    "log_task_end",
    "log_task_start",
    # Formatting
    "DOI_PATTERN",
    "clean_title",
    "format_creators",
    # Data
    "DEFAULT_ANALYSIS_TEMPLATE_JSON",
    "get_analysis_questions",
]
```

**Step 8: Find and update all imports**

Run:
```bash
grep -r "from zotero_mcp.utils" src/ --include="*.py" | grep -v "__pycache__"
```

Update each import. Example changes:
```python
# Old:
from zotero_mcp.utils.helpers import clean_title
# New:
from zotero_mcp.utils.formatting import clean_title

# Old:
from zotero_mcp.utils.templates import get_analysis_questions
# New:
from zotero_mcp.utils.data import get_analysis_questions

# Old:
from zotero_mcp.utils.logging_config import get_logger
# New:
from zotero_mcp.utils.config import get_logger
```

**Step 9: Run tests**

Run:
```bash
uv run pytest tests/ -v 2>&1 | head -50
```

**Step 10: Fix import errors iteratively**

**Step 11: Commit**

```bash
git add src/zotero_mcp/utils/
git commit -m "refactor(utils): reorganize into purpose-specific modules"
```

---

## Part 5: Formatters and Tools Review (1 Task)

### Task 12: Review and Minor Cleanup of Formatters/Tools

**Step 1: Review formatters structure**

Run:
```bash
ls -la src/zotero_mcp/formatters/
```

If well-organized, keep as-is. If not, consider minor reorganization.

**Step 2: Review tools structure**

Run:
```bash
ls -la src/zotero_mcp/tools/
```

Tools should be thin wrappers around services. If any business logic exists in tools, extract to services.

**Step 3: Update documentation if changes made**

**Step 4: Commit**

```bash
git add src/zotero_mcp/formatters/ src/zotero_mcp/tools/
git commit -m "refactor: minor cleanup of formatters and tools"
```

---

## Part 6: Final Integration and Testing (3 Tasks)

### Task 13: Global Import Update and Verification

**Step 1: Run comprehensive grep for old imports**

Run:
```bash
cd src/zotero_mcp
grep -r "from zotero_mcp" . --include="*.py" | grep -v "__pycache__" | grep -v ".pyc" > /tmp/old_imports.txt
cat /tmp/old_imports.txt
```

**Step 2: Update all remaining old imports**

Update each import that references old paths.

**Step 3: Run full test suite**

Run:
```bash
uv run pytest tests/ -v
```

**Step 4: Fix all test failures**

Iterate until all tests pass.

**Step 5: Commit**

```bash
git add src/zotero_mcp/
git commit -m "refactor: update all imports to new structure"
```

### Task 14: Update CLAUDE.md with Complete Architecture

**Step 1: Rewrite architecture section**

Modify: `CLAUDE.md`

```markdown
## Architecture

Layered architecture with strict separation of concerns:

### Entry Layer
- `server.py` - FastMCP server initialization
- `cli.py` - Command-line interface

### Tools Layer (`tools/`)
Thin MCP tool wrappers (`@mcp.tool`) that delegate to Services

### Services Layer (`services/`)
Business logic organized by domain:
- `rss/` - RSS feed fetching and workflow orchestration
  - `RSSFetcher` - Fetch and parse RSS feeds
  - `RSSWorkflow` - Orchestrate fetch → filter → import pipeline
- `gmail/` - Gmail fetching and workflow orchestration
  - `GmailFetcher` - Fetch emails and parse HTML
  - `GmailWorkflow` - Orchestrate fetch → filter → import → delete pipeline
- `zotero/` - Core Zotero operations
  - `ItemService` - CRUD operations, collections, tags
  - `MetadataEnrichmentService` - DOI lookup via Crossref/OpenAlex
  - `AIAnalysisService` - Batch PDF analysis with checkpointing
  - `SearchService` - Search and semantic search
- `common/` - Shared utilities
  - `PaperFilter` - AI-powered keyword filtering
  - `ZoteroItemCreator` - Unified item creation logic
  - `async_retry_with_backoff` - Retry with exponential backoff

### Clients Layer (`clients/`)
External service clients organized by domain:
- `zotero/` - Zotero API, local DB, Better BibTeX
- `database/` - ChromaDB vector database
- `metadata/` - Crossref, OpenAlex APIs
- `llm/` - LLM providers (DeepSeek, OpenAI, Gemini, Claude CLI)
- `gmail/` - Gmail API

### Models Layer (`models/`)
Pydantic models organized by domain:
- `common/` - Shared base models
- `zotero/` - Item, collection, annotation models
- `workflow/` - Batch operation models
- `search/` - Search query models
- `ingestion/` - RSS/Gmail ingestion models
- `database/` - Semantic search models

### Utils Layer (`utils/`)
Utility functions organized by purpose:
- `config/` - Configuration and logging
- `data/` - Data mapping and templates
- `formatting/` - Text formatting and helpers
- `async_helpers/` - Async operations and caching
- `system/` - System utilities and errors

### Formatters Layer (`formatters/`)
Output formatters (Markdown, JSON, BibTeX)

### Key Patterns

1. **Layered Architecture**: Entry → Tools → Services → Clients
2. **Domain Organization**: Each layer organized by domain/purpose
3. **Common Utilities**: Shared functionality in dedicated modules
4. **Service Layer First**: Always use services, never call clients directly
5. **Async Everywhere**: All I/O must be async (`async/await`)
6. **Type Safety**: Use Pydantic models for all complex data structures
7. **Config Priority**: Environment vars > `~/.config/zotero-mcp/config.json` > defaults
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with complete refactored architecture"
```

### Task 15: Final Code Quality and Documentation

**Step 1: Run linter and formatter**

Run:
```bash
uv run ruff check src/ --fix
uv run ruff format src/
```

**Step 2: Run type checker**

Run:
```bash
uv run ty check src/
```

**Step 3: Run full test suite with coverage**

Run:
```bash
uv run pytest --cov=src/zotero_mcp
```

**Step 4: Fix any remaining issues**

Iterate until all quality checks pass.

**Step 5: Final commit**

```bash
git add src/
git commit -m "style: final formatting and type hints after complete refactor"
```

**Step 6: Create refactoring summary**

Create: `docs/REFACTORING_SUMMARY.md`

```markdown
# Refactoring Summary

## Overview
Comprehensive refactoring of the codebase into modular, domain-organized structure.

## Changes Made

### Services Layer
- Reorganized into `rss/`, `gmail/`, `zotero/`, `common/` modules
- Extracted common utilities: `PaperFilter`, `ZoteroItemCreator`, `async_retry_with_backoff`
- Split monolithic services into focused Fetcher and Workflow classes

### Clients Layer
- Reorganized into domain-specific modules: `zotero/`, `database/`, `metadata/`, `llm/`, `gmail/`
- Improved discoverability and reduced cognitive load

### Models Layer
- Reorganized into domain-specific modules: `common/`, `zotero/`, `workflow/`, `search/`, `ingestion/`, `database/`
- Better separation of concerns

### Utils Layer
- Reorganized into purpose-specific modules: `config/`, `data/`, `formatting/`, `async_helpers/`, `system/`
- Clear module boundaries

## Benefits
- **Clearer structure**: Easier to navigate and understand
- **Better separation**: Each module has a single, well-defined purpose
- **Reduced duplication**: Common utilities extracted and shared
- **Easier testing**: Smaller, focused modules are easier to test
- **Better maintainability**: Changes are localized to specific domains

## Migration Notes
All imports updated to new structure. No backward compatibility maintained.
```

**Step 7: Commit documentation**

```bash
git add docs/
git commit -m "docs: add refactoring summary"
```

---

## Final Architecture Summary

**Complete refactored structure:**
```
src/zotero_mcp/
├── cli.py                          # CLI entry point
├── server.py                       # MCP server entry point
├── clients/                        # External API clients
│   ├── zotero/                     # Zotero clients
│   │   ├── api_client.py           # Web API
│   │   ├── local_db.py             # Local SQLite DB
│   │   └── better_bibtex.py        # Better BibTeX
│   ├── database/                   # Database clients
│   │   └── chroma.py               # ChromaDB
│   ├── metadata/                   # Metadata APIs
│   │   ├── crossref.py             # Crossref
│   │   └── openalex.py             # OpenAlex
│   ├── llm/                        # LLM providers
│   │   ├── base.py                 # Generic LLM client
│   │   └── cli.py                  # Claude CLI
│   └── gmail/                      # Gmail
│       └── client.py               # Gmail API
├── models/                         # Pydantic models
│   ├── common/                     # Base models
│   ├── zotero/                     # Zotero models
│   ├── workflow/                   # Batch operations
│   ├── search/                     # Search models
│   ├── ingestion/                  # RSS/Gmail models
│   └── database/                   # Semantic search models
├── services/                       # Business logic
│   ├── rss/                        # RSS workflows
│   │   ├── rss_fetcher.py
│   │   └── rss_workflow.py
│   ├── gmail/                      # Gmail workflows
│   │   ├── gmail_fetcher.py
│   │   └── gmail_workflow.py
│   ├── zotero/                     # Zotero operations
│   │   ├── item_manager.py
│   │   ├── metadata_enrichment.py
│   │   ├── ai_analysis.py
│   │   └── search.py
│   ├── common/                     # Shared utilities
│   │   ├── ai_filter.py
│   │   ├── retry.py
│   │   └── zotero_item_creator.py
│   └── data_access.py              # Facade
├── utils/                          # Utilities
│   ├── config/                     # Config & logging
│   ├── data/                       # Data & templates
│   ├── formatting/                 # Text formatting
│   ├── async_helpers/              # Async & caching
│   └── system/                     # System utilities
├── formatters/                     # Output formatters
├── tools/                          # MCP tool wrappers
└── __init__.py
```

**Total: 15 tasks across 6 parts**
- Part 1: Services (8 tasks)
- Part 2: Clients (1 task)
- Part 3: Models (1 task)
- Part 4: Utils (1 task)
- Part 5: Formatters/Tools (1 task)
- Part 6: Integration (3 tasks)

**Estimated time:** 6-8 hours for complete implementation
