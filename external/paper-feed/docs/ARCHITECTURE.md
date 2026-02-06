# Architecture Overview

This document describes the architecture of the paper-feed framework, including module structure, core components, design patterns, and extension points.

## Table of Contents

- [High-Level Architecture](#high-level-architecture)
- [Module Structure](#module-structure)
- [Core Components](#core-components)
- [Design Patterns](#design-patterns)
- [Data Flow](#data-flow)
- [Extension Points](#extension-points)
- [Future Enhancements](#future-enhancements)

## High-Level Architecture

paper-feed follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                     User Code                           │
│  (scripts, applications using paper-feed)               │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                   Public API Layer                      │
│  (imports from paper_feed.__init__)                     │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Sources    │   │   Filters    │   │   Adapters   │
│  (RSS, etc)  │   │  (Pipeline)  │   │  (JSON, etc) │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                ┌───────────────────────┐
                │     Core Models       │
                │  (PaperItem, etc)     │
                └───────────────────────┘
```

## Module Structure

```
src/paper_feed/
├── __init__.py              # Public API exports
│
├── core/                    # Core models and base classes
│   ├── __init__.py
│   ├── base.py              # Abstract base classes
│   └── models.py            # Pydantic data models
│
├── sources/                 # Data sources
│   ├── __init__.py
│   ├── rss.py               # RSS feed source
│   └── rss_parser.py        # RSS parsing logic
│
├── filters/                 # Filtering pipeline
│   ├── __init__.py
│   ├── pipeline.py          # Filter pipeline orchestrator
│   └── keyword.py           # Keyword-based filter stage
│
└── adapters/                # Export adapters
    ├── __init__.py
    ├── json.py              # JSON export adapter
    └── zotero.py            # Zotero export adapter (planned)
```

## Core Components

### 1. Core Models (`core/models.py`)

#### PaperItem

Universal paper representation independent of any specific system.

```python
class PaperItem(BaseModel):
    title: str
    authors: List[str]
    abstract: str
    published_date: Optional[date]
    doi: Optional[str]
    url: Optional[str]
    pdf_url: Optional[str]
    source: str                  # e.g., "arXiv", "Nature"
    source_id: Optional[str]
    source_type: str             # "rss" or "email"
    categories: List[str]
    tags: List[str]
    metadata: Dict[str, Any]     # Source-specific data
```

**Design Decisions:**
- **Pydantic BaseModel**: Automatic validation, serialization, and type safety
- **Optional fields**: Flexibility for different source capabilities
- **metadata field**: Extensible for source-specific data without schema changes

#### FilterCriteria

Defines filtering rules for paper selection.

```python
class FilterCriteria(BaseModel):
    keywords: List[str]          # AND logic
    categories: List[str]        # OR logic
    exclude_keywords: List[str]
    min_date: Optional[date]
    authors: List[str]           # OR logic
    has_pdf: bool
```

**Design Decisions:**
- **List fields**: Support multiple values with clear logic (AND/OR)
- **Optional fields**: Filters only apply if specified
- **Explicit boolean flags**: Clear intent (e.g., `has_pdf`)

#### FilterResult

Contains filtering results and statistics.

```python
class FilterResult(BaseModel):
    papers: List[PaperItem]
    total_count: int
    passed_count: int
    rejected_count: int
    filter_stats: Dict[str, Any]
```

### 2. Base Classes (`core/base.py`)

#### PaperSource (Abstract)

Base class for all paper sources.

```python
class PaperSource(ABC):
    """Abstract base for paper sources."""

    @abstractmethod
    async def fetch_papers(
        self,
        limit: Optional[int] = None,
        since: Optional[date] = None
    ) -> List[PaperItem]:
        """Fetch papers from the source."""
        pass
```

**Implementations:**
- `RSSSource` - Fetch from RSS feeds
- `GmailSource` (planned) - Fetch from Gmail alerts

#### ExportAdapter (Abstract)

Base class for export adapters.

```python
class ExportAdapter(ABC):
    """Abstract base for export adapters."""

    @abstractmethod
    async def export(
        self,
        papers: List[PaperItem],
        **kwargs
    ) -> Dict[str, Any]:
        """Export papers to destination."""
        pass
```

**Implementations:**
- `JSONAdapter` - Export to JSON files
- `ZoteroAdapter` (planned) - Export to Zotero library

### 3. Sources (`sources/`)

#### RSSSource

Fetches papers from RSS feeds (arXiv, bioRxiv, Nature, etc.).

**Key Features:**
- Auto-detects source name from URL
- Configurable timeout and user-agent
- Async HTTP requests with httpx
- Threaded feedparser for blocking I/O
- Comprehensive error handling

**Architecture:**
```
RSSSource
    ├── fetch_papers()      # Public API
    │   ├── HTTP GET        # Async with httpx
    │   ├── feedparser      # Threaded parsing
    │   └── parse entry     # Via RSSParser
    │
    └── RSSParser           # Separated parsing logic
        └── parse()         # Entry → PaperItem
```

**Design Decisions:**
- **Separated Parser**: `RSSParser` handles source-specific parsing logic
- **Auto-detection**: Source name detected from URL pattern matching
- **Graceful Degradation**: Invalid entries logged but don't stop processing
- **Threaded feedparser**: Run blocking feedparser in thread pool to avoid blocking event loop

#### RSSParser

Converts RSS feed entries to `PaperItem` objects.

**Key Features:**
- Handles different RSS formats (Atom, RSS 2.0)
- Extracts authors from various field names
- Parses dates from multiple formats
- Handles missing fields gracefully

### 4. Filters (`filters/`)

#### FilterPipeline

Orchestrates multiple filter stages in sequence.

**Architecture:**
```
FilterPipeline
    ├── filter()                    # Main entry point
    │   ├── KeywordFilterStage      # Stage 1: Keyword-based
    │   ├── AIFilterStage (planned) # Stage 2: AI semantic
    │   └── ...                     # Future stages
    │
    └── FilterResult                # Aggregated results
```

**Design Decisions:**
- **Pipeline Pattern**: Sequential processing through stages
- **Stage Independence**: Each stage is self-contained
- **Statistics Collection**: Each stage contributes to `filter_stats`
- **Skip Logic**: Stages only run if applicable (criteria check)

#### KeywordFilterStage

Implements keyword, category, author, and date filtering.

**Filter Logic:**
```python
# Keywords (AND logic)
if criteria.keywords:
    if not all(kw.lower() in paper_text for kw in criteria.keywords):
        return False

# Categories (OR logic)
if criteria.categories:
    if not any(cat in paper.categories for cat in criteria.categories):
        return False

# Exclude keywords (NOT logic)
if criteria.exclude_keywords:
    if any(ex_kw.lower() in paper_text for ex_kw in criteria.exclude_keywords):
        return False

# Min date
if criteria.min_date and paper.published_date:
    if paper.published_date < criteria.min_date:
        return False

# Has PDF
if criteria.has_pdf and not paper.pdf_url:
    return False
```

**Design Decisions:**
- **Case-insensitive matching**: More user-friendly
- **Flexible logic**: Clear AND/OR/NOT semantics
- **Early exit**: Fail fast on first mismatch
- **Text search**: Searches across title, abstract, and tags

### 5. Adapters (`adapters/`)

#### JSONAdapter

Exports papers to JSON format.

**Key Features:**
- Converts `PaperItem` to JSON-serializable dict
- Handles date serialization (ISO format)
- Optional metadata inclusion
- Automatic directory creation
- UTF-8 encoding with pretty formatting

**Design Decisions:**
- **Custom encoder**: Handles `date` objects without requiring `default=str`
- **Metadata flag**: Users can exclude source-specific metadata
- **Atomic write**: Writes complete file at once (no partial writes)

#### ZoteroAdapter (Planned)

Will export papers to Zotero library via API.

**Planned Features:**
- Convert `PaperItem` to Zotero `journalArticle` format
- Batch import with error handling
- Collection targeting
- Progress tracking

## Design Patterns

### 1. Abstract Factory Pattern

**Base classes define interface, implementations provide behavior:**

```python
# Base class defines contract
class PaperSource(ABC):
    @abstractmethod
    async def fetch_papers(...) -> List[PaperItem]:
        pass

# Implementations provide specific behavior
class RSSSource(PaperSource):
    async def fetch_papers(...) -> List[PaperItem]:
        # RSS-specific implementation

class GmailSource(PaperSource):
    async def fetch_papers(...) -> List[PaperItem]:
        # Gmail-specific implementation
```

**Benefits:**
- Easy to add new sources without changing client code
- Consistent interface across different sources
- Testable with mocks

### 2. Pipeline Pattern

**FilterPipeline chains multiple filter stages:**

```python
class FilterPipeline:
    def __init__(self):
        self.stages = [
            KeywordFilterStage(),
            # AIFilterStage(),  # Future
            # DedupeStage(),    # Future
        ]

    async def filter(self, papers, criteria):
        for stage in self.stages:
            papers = await stage.filter(papers, criteria)
        return papers
```

**Benefits:**
- Modular: Each stage is independent
- Extensible: Add new stages without modifying existing ones
- Composable: Stages can be reordered or skipped

### 3. Strategy Pattern

**Different export strategies (adapters):**

```python
# Client code doesn't need to know which adapter
async def export_papers(papers, adapter):
    return await adapter.export(papers)

# Can use any adapter
await export_papers(papers, JSONAdapter())
await export_papers(papers, ZoteroAdapter())
await export_papers(papers, BibTeXAdapter())  # Future
```

**Benefits:**
- Interchangeable algorithms
- Runtime selection of export strategy
- Easy to add new export formats

### 4. Builder Pattern

**FilterCriteria provides fluent interface:**

```python
criteria = (
    FilterCriteria()
    .with_keywords(["machine learning"])
    .with_categories(["CS"])
    .with_min_date(date(2023, 1, 1))
)
```

**Benefits:**
- Readable code
- Optional parameters handled gracefully
- Easy to extend with new criteria

### 5. Optional Dependency Pattern

**Adapters with optional dependencies:**

```python
# In __init__.py
try:
    from paper_feed.adapters import ZoteroAdapter
    _zotero_available = True
except ImportError:
    ZoteroAdapter = None
    _zotero_available = False
```

**Benefits:**
- Core functionality works without optional deps
- Clear error messages if optional features used
- Flexible installation options

## Data Flow

### Complete Workflow

```
User Code
    │
    ├─→ RSSSource.fetch_papers()
    │       │
    │       ├─→ HTTP GET (async)
    │       ├─→ feedparser.parse() (threaded)
    │       └─→ RSSParser.parse() × N
    │               │
    │               └─→ PaperItem × N
    │
    ├─→ FilterPipeline.filter()
    │       │
    │       ├─→ KeywordFilterStage.filter()
    │       │       │
    │       │       ├─→ Check keywords (AND)
    │       │       ├─→ Check categories (OR)
    │       │       ├─→ Check exclude (NOT)
    │       │       ├─→ Check min_date
    │       │       └─→ Check has_pdf
    │       │
    │       └─→ FilterResult
    │               │
    │               └─→ PaperItem × M (M ≤ N)
    │
    └─→ JSONAdapter.export()
            │
            ├─→ PaperItem → Dict
            ├─→ Serialize dates
            ├─→ Write to file
            └─→ ExportResult
```

### Example: Fetch → Filter → Export

```python
# 1. Fetch papers
source = RSSSource("https://arxiv.org/rss/cs.AI")
papers = await source.fetch_papers(limit=50)
# Returns: List[PaperItem] (50 items)

# 2. Filter papers
criteria = FilterCriteria(keywords=["deep learning"])
result = await FilterPipeline().filter(papers, criteria)
# Returns: FilterResult with subset of papers

# 3. Export papers
await JSONAdapter().export(result.papers, "output.json")
# Returns: Dict with export statistics
```

## Extension Points

### Adding a New Source

**Example: Add PubMed source**

```python
# 1. Create source class
class PubMedSource(PaperSource):
    async def fetch_papers(self, limit=None, since=None):
        # Fetch from PubMed API
        papers = []
        # ... fetch logic
        return papers

# 2. Register in __init__.py
from paper_feed.sources import PubMedSource

# 3. Use it
source = PubMedSource(query="machine learning")
papers = await source.fetch_papers()
```

### Adding a New Filter Stage

**Example: Add language detection stage**

```python
# 1. Create stage class
class LanguageFilterStage:
    async def filter(self, papers, criteria):
        # Filter by language
        filtered = [p for p in papers if self.is_english(p)]
        return filtered, []

    def is_english(self, paper):
        # Language detection logic
        pass

# 2. Add to pipeline
class FilterPipeline:
    def __init__(self):
        self.keyword_stage = KeywordFilterStage()
        self.language_stage = LanguageFilterStage()  # New

    async def filter(self, papers, criteria):
        # Apply stages in sequence
        papers, _ = await self.keyword_stage.filter(papers, criteria)
        papers, _ = await self.language_stage.filter(papers, criteria)
        return FilterResult(...)
```

### Adding a New Export Adapter

**Example: Add BibTeX adapter**

```python
# 1. Create adapter class
class BibTeXAdapter(ExportAdapter):
    async def export(self, papers, filepath, **kwargs):
        # Convert to BibTeX format
        bibtex_entries = []
        for paper in papers:
            entry = self.to_bibtex(paper)
            bibtex_entries.append(entry)

        # Write to file
        with open(filepath, 'w') as f:
            f.write('\n\n'.join(bibtex_entries))

        return {"count": len(papers), "filepath": filepath}

    def to_bibtex(self, paper):
        # Convert PaperItem to BibTeX
        return f"@article{{{paper.doi}, ...}}"

# 2. Register in __init__.py
from paper_feed.adapters import BibTeXAdapter

# 3. Use it
await BibTeXAdapter().export(papers, "output.bib")
```

## Architecture Principles

### 1. Separation of Concerns

Each module has a single responsibility:
- `sources/` - Data fetching only
- `filters/` - Filtering logic only
- `adapters/` - Export logic only
- `core/` - Shared models and base classes

### 2. Dependency Inversion

High-level modules don't depend on low-level details:
- `FilterPipeline` depends on abstract `FilterStage` interface
- User code depends on abstract `PaperSource` interface
- Adapters implement `ExportAdapter` interface

### 3. Open/Closed Principle

Open for extension, closed for modification:
- Add new sources by implementing `PaperSource`
- Add new filters by implementing `FilterStage`
- Add new adapters by implementing `ExportAdapter`

### 4. Async-First

All I/O operations are async:
- Network requests (HTTP)
- File I/O (export)
- Future: Database operations

### 5. Type Safety

Pydantic models provide:
- Runtime validation
- Type hints for IDE support
- Automatic serialization
- Clear data contracts

## Future Enhancements

### Phase 2: Zotero Integration

- Complete `ZoteroAdapter` implementation
- Batch import with progress tracking
- Collection targeting
- Conflict resolution

### Phase 3: Gmail Source

- `GmailSource` implementation
- Parse Google Scholar alerts
- Parse journal TOC emails
- OAuth2 authentication

### Phase 4: AI Filtering

- `AIFilterStage` using OpenAI API
- Semantic similarity filtering
- Abstract-based relevance scoring
- Configurable threshold

### Phase 5: Additional Adapters

- `BibTeXAdapter` - BibTeX export
- `CSVAdapter` - Spreadsheet export
- `MarkdownAdapter` - Markdown documents
- `NotionAdapter` - Notion database
- `ObsidianAdapter` - Obsidian vault

### Phase 6: Advanced Features

- Deduplication across sources
- Full-text search
- Citation graph building
- Automatic categorization
- Recommendation engine

## Performance Considerations

### Async Concurrency

```python
# Fetch from multiple sources concurrently
async def fetch_concurrent():
    sources = [RSSSource(url1), RSSSource(url2), RSSSource(url3)]

    # Concurrent fetch
    results = await asyncio.gather(
        *[s.fetch_papers(limit=50) for s in sources]
    )

    return [paper for result in results for paper in result]
```

### Memory Efficiency

- Process papers in batches (pagination)
- Don't load entire feed into memory
- Stream export to large files

### Error Handling

- Network timeouts: Configurable per source
- Invalid entries: Log and skip
- Partial failures: Continue processing

## Testing Strategy

### Unit Tests

- Test each component in isolation
- Mock external dependencies (HTTP, file I/O)
- Cover edge cases (empty lists, missing fields)

### Integration Tests

- Test full workflows (fetch → filter → export)
- Use real RSS feeds (with test URLs)
- Verify output files are valid

### Example Test Structure

```python
# tests/unit/test_rss_source.py
class TestRSSSource:
    async def test_fetch_papers(self):
        source = RSSSource("https://arxiv.org/rss/cs.AI")
        papers = await source.fetch_papers(limit=10)

        assert len(papers) <= 10
        assert all(isinstance(p, PaperItem) for p in papers)

    async def test_auto_detect_source_name(self):
        source = RSSSource("https://arxiv.org/rss/cs.AI")
        assert source.source_name == "arXiv"
```

## Conclusion

The paper-feed architecture emphasizes:

1. **Modularity** - Clear separation between sources, filters, and adapters
2. **Extensibility** - Easy to add new sources, filters, and adapters
3. **Type Safety** - Pydantic models ensure data integrity
4. **Async-First** - Non-blocking I/O for better performance
5. **User-Friendly** - Simple API for common use cases

This design allows paper-feed to grow from a simple RSS fetcher to a comprehensive paper collection framework while maintaining code quality and usability.
