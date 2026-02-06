# Search Services

This document describes the search services provided by `zotero-core`.

## Overview

`zotero-core` provides three search services:

1. **SearchService** - Keyword-based search using Zotero API
2. **SemanticSearchService** - Vector-based semantic search using ChromaDB (optional)
3. **HybridSearchService** - Combines keyword and semantic search with RRF fusion

## Installation

### Basic Installation (keyword search only)

```bash
pip install zotero-core
```

### With Semantic Search

```bash
pip install zotero-core[semantic]
# or
pip install zotero-core chromadb
```

## SearchService

Keyword-based search using Zotero's native search API.

### Features

- **Title/Creator/Year search**: Search in title, author, and publication year
- **Full-text search**: Search across all item fields
- **Tag filtering**: Filter results by tags
- **Item type filtering**: Include/exclude specific item types
- **Pagination**: Control result size and offset

### Example

```python
from zotero_core.clients import ZoteroClient
from zotero_core.models import SearchItemsInput, SearchMode
from zotero_core.services import SearchService

# Initialize
client = ZoteroClient(library_id="...", api_key="...")
search_service = SearchService(client=client)

# Create search query
input_data = SearchItemsInput(
    query="machine learning",
    mode=SearchMode.TITLE_CREATOR_YEAR,
    item_type="-attachment",  # Exclude attachments
    tags=["research"],
    limit=10,
)

# Execute search
results = await search_service.search_items(input_data)

# Process results
for item in results.items:
    print(f"{item.title} - {item.authors}")
```

### Search Modes

- `titleCreatorYear`: Searches title, authors, and year fields (default)
- `everything`: Searches all fields including notes and full-text

## SemanticSearchService

Vector-based semantic search using ChromaDB embeddings.

### Features

- **Natural language queries**: Search using concepts and meaning
- **Semantic similarity**: Find related papers beyond exact keyword matches
- **Persistent storage**: Optional disk-based vector database
- **Metadata filtering**: Filter by item type, collections, etc.

### Requirements

ChromaDB must be installed:

```bash
pip install chromadb
```

### Example

```python
from zotero_core.services import SemanticSearchService, CHROMADB_AVAILABLE

if CHROMADB_AVAILABLE:
    # Initialize semantic search
    semantic_service = SemanticSearchService(
        collection_name="zotero_items",
        persist_directory="./chroma_db",  # Optional, None for in-memory
    )

    # Add items to vector database
    await semantic_service.add_items(items_data)

    # Search by semantic similarity
    results = await semantic_service.search(
        query="deep learning for computer vision",
        top_k=10,
        filters={"item_type": "journalArticle"},
    )

    for result in results:
        print(f"{result['key']}: {result['score']:.3f}")
```

## HybridSearchService

Combines keyword and semantic search using **Reciprocal Rank Fusion (RRF)**.

### RRF Algorithm

RRF fusion combines ranked results from multiple sources:

```
score(item) = Σ 1 / (k + rank)
```

Where:
- `k` is a constant (default: 60)
- Higher scores indicate better matches
- Items appearing in both lists get boosted

### Features

- **Three search modes**: keyword-only, semantic-only, or hybrid
- **Automatic fallback**: Gracefully degrades if semantic search unavailable
- **Combined scoring**: Provides individual and fused relevance scores
- **Configurable RRF constant**: Adjust rank smoothing parameter

### Example

```python
from zotero_core.services import (
    HybridSearchService,
    SearchService,
    SemanticSearchService,
)

# Initialize services
search_service = SearchService(client=client)
semantic_service = SemanticSearchService() if CHROMADB_AVAILABLE else None

# Create hybrid service
hybrid_service = HybridSearchService(
    keyword_search=search_service,
    semantic_search=semantic_service,
    rrf_k=60,  # RRF constant (higher = more smoothing)
)

# Perform hybrid search
results = await hybrid_service.search(
    query="neural networks for natural language processing",
    mode="hybrid",  # "keyword", "semantic", or "hybrid"
    top_k=10,
)

# Process results with combined scores
for item in results.items:
    print(f"{item.rank}. {item.title}")
    if item.keyword_score:
        print(f"  Keyword: {item.keyword_score:.4f}")
    if item.semantic_score:
        print(f"  Semantic: {item.semantic_score:.4f}")
    print(f"  Combined: {item.relevance_score:.4f}")
```

### Search Modes

1. **`keyword`**: Traditional keyword search only
2. **`semantic`**: Semantic similarity search only (requires ChromaDB)
3. **`hybrid`**: RRF fusion of both (default)

### Fallback Behavior

If semantic search is unavailable (ChromaDB not installed or initialization fails):

- `mode="keyword"`: Works normally
- `mode="semantic"`: Raises `HybridSearchServiceError`
- `mode="hybrid"`: Falls back to keyword-only search

## Result Models

### SearchResultItem

```python
class SearchResultItem:
    key: str
    title: str
    item_type: str
    authors: str | None
    date: str | None
    year: int | None
    abstract: str | None
    tags: list[str]
    doi: str | None
    url: str | None

    # Scoring
    relevance_score: float | None  # Combined score
    keyword_score: float | None    # Keyword search score
    semantic_score: float | None   # Semantic similarity score
    rank: int | None               # Position in results

    # Context
    matched_text: str | None
    snippet: str | None

    # Metadata
    date_added: str | None
    collections: list[str]
```

### SearchResults

```python
class SearchResults:
    query: str           # Search query that was executed
    total: int           # Total matching items
    count: int           # Items in this response
    items: list[SearchResultItem]
    has_more: bool       # Whether more results available
```

## Performance Considerations

### Keyword Search

- **Speed**: Fast, uses Zotero API indexing
- **Accuracy**: Exact matching, depends on query quality
- **Best for**: Known titles, author names, specific keywords

### Semantic Search

- **Speed**: Slower, requires vector similarity computation
- **Accuracy**: Conceptual matching, finds related papers
- **Best for**: Exploratory research, finding related work

### Hybrid Search

- **Speed**: Medium, performs both searches
- **Accuracy**: Best of both, RRF balances precision and recall
- **Best for**: General research queries, comprehensive results

### Tips

1. Use `mode="keyword"` for quick, exact matches
2. Use `mode="semantic"` for discovering related papers
3. Use `mode="hybrid"` for comprehensive research queries
4. Adjust `rrf_k` parameter:
   - Lower (30-50): More weight on top-ranked items
   - Higher (80-100): More smoothing, broader results

## See Also

- [Example Code](../examples/search_example.py)
- [API Reference](../api/services.rst)
- [Models Documentation](models.md)
