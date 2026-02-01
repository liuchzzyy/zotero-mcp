# Service Architecture Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the service layer into three distinct modules (rss, gmail, zotero) with clear separation of concerns, eliminating code duplication while maintaining the three-stage workflow (fetch → analyze → scan).

**Architecture:** Move from a flat service structure to a modular three-tier architecture:
- **RSS Service** (`services/rss/`) - Handles RSS feed fetching, parsing, and workflow orchestration
- **Gmail Service** (`services/gmail/`) - Handles email fetching, HTML parsing, and workflow orchestration
- **Zotero Service** (`services/zotero/`) - Core Zotero operations (CRUD, search, metadata, AI analysis)
- **Shared utilities** - Common functionality (AI filtering, item creation, retry logic) in `services/common/`

**Tech Stack:** Python 3.10+, FastMCP, Pydantic, asyncio, uv

**Important:** No backward compatibility - all old code will be deleted and replaced with new structure.

---

## Current Problems Identified

1. **Code duplication**: RSS and Gmail services both contain Zotero import logic (`create_zotero_item`)
2. **Mixed responsibilities**: RSS service has both RSS parsing AND Zotero creation logic
3. **Inconsistent naming**: Some functions use `clean_title`, others `_clean_title`
4. **Tight coupling**: Services directly instantiate other services instead of using dependency injection
5. **Common patterns not abstracted**: Retry logic, creator parsing, duplicate checking duplicated across services

## Refactoring Strategy

### Phase 1: Extract Common Utilities (services/common/)
Extract shared functionality used by both RSS and Gmail services:

**New module:** `services/common/zotero_item_creator.py`
- `ZoteroItemCreator.create_item()` - Centralized item creation logic
- `parse_creator_string()` - Extracted from RSS service
- `check_duplicates()` - Unified duplicate checking (URL + title)
- `build_item_data()` - Construct Zotero item dict

**New module:** `services/common/retry.py`
- `async_retry_with_backoff()` - Generic retry decorator
- Used by: RSS, Gmail, Metadata services

**New module:** `services/common/ai_filter.py`
- Move `RSSFilter` from `services/rss/rss_filter.py` to `services/common/ai_filter.py`
- Rename to `PaperFilter` (works for both RSS and Gmail items)

### Phase 2: Refactor RSS Service (services/rss/)
Delete old `rss_service.py`, replace with focused modules:

**`services/rss/rss_fetcher.py`** (NEW)
- `RSSFetcher.fetch_feed()` - Fetch and parse single RSS feed
- `RSSFetcher.fetch_feeds_from_opml()` - Batch fetch from OPML
- `RSSFetcher.parse_opml()` - Parse OPML file
- `clean_title()` - Title cleaning utility (if needed)

**`services/rss/rss_workflow.py`** (NEW)
- `RSSWorkflow.process_rss_workflow()` - Orchestrate fetch → filter → import pipeline
- Uses common `ZoteroItemCreator` for import
- Uses common `PaperFilter` for AI filtering

**DELETE:** `services/rss/rss_service.py` (after migration)

### Phase 3: Refactor Gmail Service (services/gmail/)
Delete old `gmail_service.py`, replace with focused modules:

**`services/gmail/gmail_fetcher.py`** (NEW)
- `GmailFetcher.fetch_and_parse_emails()` - Fetch emails from Gmail API
- `GmailFetcher.parse_html_table()` - Extract items from HTML
- Helper methods for different HTML parsing strategies

**`services/gmail/gmail_workflow.py`** (NEW)
- `GmailWorkflow.process_gmail_workflow()` - Orchestrate fetch → filter → import → delete pipeline
- Uses common `ZoteroItemCreator` for import
- Uses common `PaperFilter` for AI filtering

**DELETE:** `services/gmail/gmail_service.py` (after migration)

### Phase 4: Create Zotero Service (services/zotero/)
Move and rename existing modules:

**Move:** `services/item.py` → `services/zotero/item_manager.py`
- Keep `ItemService` class name

**Move:** `services/metadata.py` → `services/zotero/metadata_enrichment.py`
- Rename `MetadataService` → `MetadataEnrichmentService`

**Move:** `services/workflow.py` → `services/zotero/ai_analysis.py`
- Rename `WorkflowService` → `AIAnalysisService`

**Move:** `services/search.py` → `services/zotero/search.py`
- Keep `SearchService` class name

**DELETE old files after move**

### Phase 5: Update All Imports
Update all references across the codebase to use new module paths and class names.

---

## Implementation Tasks

### Task 1: Create Common Utilities Infrastructure

**Files:**
- Create: `src/zotero_mcp/services/common/__init__.py`
- Create: `src/zotero_mcp/services/common/retry.py`
- Create: `tests/services/test_common_retry.py`

**Step 1: Write the retry utility test**

Create: `tests/services/test_common_retry.py`

```python
"""Test retry utility."""

import pytest
from zotero_mcp.services.common.retry import async_retry_with_backoff


@pytest.mark.asyncio
async def test_retry_success_on_second_attempt():
    """Test that retry succeeds after one failure."""
    attempt_count = 0

    async def flaky_function():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 2:
            raise ValueError("Temporary failure")
        return "success"

    result = await async_retry_with_backoff(
        flaky_function,
        max_retries=3,
        base_delay=0.01,
    )
    assert result == "success"
    assert attempt_count == 2


@pytest.mark.asyncio
async def test_retry_fails_after_max_attempts():
    """Test that retry gives up after max attempts."""
    async def always_fail_function():
        raise ValueError("Permanent failure")

    with pytest.raises(ValueError, match="Permanent failure"):
        await async_retry_with_backoff(
            always_fail_function,
            max_retries=2,
            base_delay=0.01,
        )
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/services/test_common_retry.py -v`
Expected: FAIL with "Module 'zotero_mcp.services.common.retry' not found"

**Step 3: Implement retry utility**

Create: `src/zotero_mcp/services/common/retry.py`

```python
"""Generic retry utility with exponential backoff."""

import asyncio
import logging
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


async def async_retry_with_backoff(
    func: Callable[[], T],
    *,
    max_retries: int = 3,
    base_delay: float = 2.0,
    description: str = "Operation",
) -> T:
    """
    Execute an async function with retry and exponential backoff.

    Args:
        func: Async function to execute
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (will be doubled each retry)
        description: Description for logging

    Returns:
        Result from func

    Raises:
        Last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            error_msg = str(e).lower()

            # Check if error is retryable
            is_retryable = any(
                keyword in error_msg
                for keyword in ["timed out", "timeout", "503", "429", "connection"]
            )

            if not is_retryable or attempt == max_retries - 1:
                raise

            delay = base_delay * (2**attempt)
            logger.warning(
                f"  ↻ {description} failed (attempt {attempt + 1}/{max_retries}): "
                f"{e}. Retrying in {delay:.0f}s..."
            )
            await asyncio.sleep(delay)

    # Should never reach here, but satisfies type checker
    if last_exception:
        raise last_exception
    raise RuntimeError(f"{description} failed after {max_retries} retries")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/services/test_common_retry.py -v`
Expected: PASS

**Step 5: Create common __init__.py**

Create: `src/zotero_mcp/services/common/__init__.py`

```python
"""Common utilities shared across services."""

from .retry import async_retry_with_backoff

__all__ = ["async_retry_with_backoff"]
```

**Step 6: Commit**

```bash
git add tests/services/test_common_retry.py src/zotero_mcp/services/common/
git commit -m "feat(services): add common retry utility"
```

---

### Task 2: Create ZoteroItemCreator Common Utility

**Files:**
- Create: `src/zotero_mcp/services/common/zotero_item_creator.py`
- Create: `tests/services/test_zotero_item_creator.py`
- Modify: `src/zotero_mcp/services/common/__init__.py`
- Reference: `src/zotero_mcp/services/rss/rss_service.py:299-401`

**Step 1: Write test for ZoteroItemCreator**

Create: `tests/services/test_zotero_item_creator.py`

```python
"""Test ZoteroItemCreator."""

import pytest
from zotero_mcp.models.rss import RSSItem
from zotero_mcp.services.common.zotero_item_creator import (
    ZoteroItemCreator,
    parse_creator_string,
)


@pytest.mark.asyncio
async def test_create_zotero_item_with_minimal_data(mock_data_service, mock_metadata_service):
    """Test creating item with minimal required fields."""
    creator = ZoteroItemCreator(mock_data_service, mock_metadata_service)

    item = RSSItem(
        title="Test Paper",
        link="https://example.com/paper",
        source_url="https://feed.com",
        source_title="Test Feed",
    )

    # Mock the services
    mock_data_service.search_items.return_value = []
    mock_data_service.create_items.return_value = {"successful": {"KEY": {}}}
    mock_metadata_service.lookup_doi.return_value = None

    result = await creator.create_item(item, collection_key="ABC123")

    assert result is not None
    assert isinstance(result, str)


def test_parse_creator_string_single_author():
    """Test parsing single author."""
    creators = parse_creator_string("John Doe")
    assert len(creators) == 1
    assert creators[0]["name"] == "John Doe"
    assert creators[0]["creatorType"] == "author"


def test_parse_creator_string_multiple_authors():
    """Test parsing multiple authors separated by commas."""
    creators = parse_creator_string("John Doe, Jane Smith, Bob Johnson")
    assert len(creators) == 3
    assert creators[0]["name"] == "John Doe"
    assert creators[1]["name"] == "Jane Smith"
    assert creators[2]["name"] == "Bob Johnson"


def test_parse_creator_string_truncation():
    """Test that long author lists are truncated."""
    many_authors = ", ".join([f"Author {i}" for i in range(15)])
    creators = parse_creator_string(many_authors)
    assert len(creators) == 10
    assert "et al." in creators[-1]["name"]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/services/test_zotero_item_creator.py -v`
Expected: FAIL with "Module not found"

**Step 3: Implement ZoteroItemCreator**

Create: `src/zotero_mcp/services/common/zotero_item_creator.py`

```python
"""Common Zotero item creation logic for RSS and Gmail workflows."""

import logging
from datetime import datetime

from zotero_mcp.models.rss import RSSItem
from zotero_mcp.services.common.retry import async_retry_with_backoff
from zotero_mcp.utils.helpers import DOI_PATTERN, clean_title

logger = logging.getLogger(__name__)

# Zotero limits
MAX_CREATOR_NAME_LENGTH = 210
MAX_CREATORS = 10


class ZoteroItemCreator:
    """
    Centralized service for creating Zotero items from external sources.

    Used by both RSS and Gmail workflows to avoid code duplication.
    """

    def __init__(self, data_service, metadata_service):
        """
        Initialize item creator.

        Args:
            data_service: DataAccessService instance
            metadata_service: MetadataService instance for DOI lookup
        """
        self.data_service = data_service
        self.metadata_service = metadata_service

    async def create_item(
        self,
        item: RSSItem,
        collection_key: str,
    ) -> str | None:
        """
        Create a Zotero item from an RSS/email item.

        Args:
            item: RSSItem with paper metadata
            collection_key: Target collection key

        Returns:
            Zotero item key if created, None if duplicate or failed
        """
        cleaned_title = clean_title(item.title)

        # Check for duplicates
        duplicate_key = await self._check_duplicates(item, cleaned_title)
        if duplicate_key:
            logger.info(f"  ⊘ Duplicate: {cleaned_title[:50]}")
            return None

        # Lookup DOI if not available
        doi = item.doi
        if not doi:
            logger.info(f"  ? Looking up DOI for: {cleaned_title[:50]}")
            doi = await self.metadata_service.lookup_doi(cleaned_title, item.author)
            if doi:
                logger.info(f"  + Found DOI: {doi}")

        # Build item data
        item_data = self._build_item_data(item, cleaned_title, doi, collection_key)

        # Create item with retry
        try:
            result = await async_retry_with_backoff(
                lambda: self.data_service.create_items([item_data]),
                description=f"Create item '{cleaned_title[:30]}'",
            )

            if self._is_successful_result(result):
                item_key = self._extract_item_key(result)
                logger.info(f"  ✓ Created: {cleaned_title[:50]} (key: {item_key})")
                return item_key
            else:
                logger.warning(f"  ✗ Failed to create: {cleaned_title[:50]}")
                return None

        except Exception as e:
            logger.error(f"  ✗ Error creating item '{cleaned_title[:50]}': {e}")
            return None

    async def _check_duplicates(
        self, item: RSSItem, cleaned_title: str
    ) -> str | None:
        """Check if item already exists by URL or title."""
        # Check by URL
        existing_by_url = await async_retry_with_backoff(
            lambda: self.data_service.search_items(
                query=item.link, limit=1, qmode="everything"
            ),
            description=f"Search URL '{cleaned_title[:30]}'",
        )
        if existing_by_url and len(existing_by_url) > 0:
            return "url"

        # Check by title
        existing_by_title = await async_retry_with_backoff(
            lambda: self.data_service.search_items(
                query=cleaned_title, qmode="titleCreatorYear", limit=1
            ),
            description=f"Search title '{cleaned_title[:30]}'",
        )
        if existing_by_title and len(existing_by_title) > 0:
            found_title = existing_by_title[0].title
            if found_title.lower() == cleaned_title.lower():
                return "title"

        return None

    def _build_item_data(
        self, item: RSSItem, cleaned_title: str, doi: str | None, collection_key: str
    ) -> dict:
        """Build Zotero item data dict."""
        item_data = {
            "itemType": "journalArticle",
            "title": cleaned_title,
            "url": item.link,
            "publicationTitle": item.source_title,
            "date": item.pub_date.strftime("%Y-%m-%d") if item.pub_date else "",
            "accessDate": datetime.now().strftime("%Y-%m-%d"),
            "collections": [collection_key],
            "DOI": doi or "",
            "tags": [],
        }

        if item.author:
            item_data["creators"] = parse_creator_string(item.author)

        return item_data

    def _is_successful_result(self, result: dict | int) -> bool:
        """Check if creation result indicates success."""
        if isinstance(result, int):
            return False
        if not isinstance(result, dict):
            return False

        return len(result.get("successful", {})) > 0 or len(result.get("success", {})) > 0

    def _extract_item_key(self, result: dict) -> str | None:
        """Extract item key from creation result."""
        if "successful" in result and result["successful"]:
            return list(result["successful"].keys())[0]
        if "success" in result and result["success"]:
            return list(result["success"].keys())[0]
        return None


def parse_creator_string(author_string: str) -> list[dict[str, str]]:
    """
    Parse author string and split into individual creators.

    Handles comma-separated author lists and truncates if necessary
    to avoid Zotero HTTP 413 errors.

    Args:
        author_string: Raw author string from feed/email

    Returns:
        List of creator dicts with 'creatorType' and 'name' keys
    """
    if not author_string:
        return []

    creators = []

    # Try to split by common separators
    parts = []
    for sep in [", ", "; ", "\n", ","]:
        if sep in author_string:
            parts = [p.strip() for p in author_string.split(sep) if p.strip()]
            break

    if not parts:
        parts = [author_string.strip()]

    # Limit number of creators
    if len(parts) > MAX_CREATORS:
        logger.warning(
            f"  ! Author list too long ({len(parts)} authors), "
            f"truncating to {MAX_CREATORS} + et al."
        )
        parts = parts[:MAX_CREATORS]

    # Create creator dicts
    for author in parts:
        author = author.strip()
        if len(author) > MAX_CREATOR_NAME_LENGTH:
            author = author[: MAX_CREATOR_NAME_LENGTH - 4] + "..."
            logger.warning(f"  ! Author name too long, truncated to: {author}")

        if author:
            creators.append({"creatorType": "author", "name": author})

    # Add "et al." if truncated
    if len(creators) == MAX_CREATORS:
        original_count = len(
            [p.strip() for p in author_string.split(",") if p.strip()]
            if "," in author_string or ";" in author_string
            else [author_string.strip()]
        )
        if original_count > MAX_CREATORS:
            creators[-1]["name"] = creators[-1]["name"] + " et al."

    return creators
```

**Step 4: Update common __init__.py**

Modify: `src/zotero_mcp/services/common/__init__.py`

```python
"""Common utilities shared across services."""

from .retry import async_retry_with_backoff
from .zotero_item_creator import ZoteroItemCreator, parse_creator_string

__all__ = [
    "async_retry_with_backoff",
    "ZoteroItemCreator",
    "parse_creator_string",
]
```

**Step 5: Run tests**

Run: `uv run pytest tests/services/test_zotero_item_creator.py -v`
Expected: PASS (you may need to create mocks for data_service and metadata_service)

**Step 6: Commit**

```bash
git add tests/services/test_zotero_item_creator.py src/zotero_mcp/services/common/
git commit -m "feat(services): add ZoteroItemCreator for unified item creation"
```

---

### Task 3: Move and Rename RSSFilter to PaperFilter

**Files:**
- Move: `src/zotero_mcp/services/rss/rss_filter.py` → `src/zotero_mcp/services/common/ai_filter.py`
- Rename: `RSSFilter` → `PaperFilter`
- Modify: `src/zotero_mcp/services/common/__init__.py`
- Find and update all imports across codebase

**Step 1: Move file to common**

Run:
```bash
mv src/zotero_mcp/services/rss/rss_filter.py src/zotero_mcp/services/common/ai_filter.py
```

**Step 2: Rename class in ai_filter.py**

Modify: `src/zotero_mcp/services/common/ai_filter.py`

```python
# Change class name
class PaperFilter:  # was RSSFilter
    """Filter papers (RSS or Gmail) based on research interests."""
    # ... rest of code stays the same
```

**Step 3: Update common __init__.py**

Modify: `src/zotero_mcp/services/common/__init__.py`

```python
"""Common utilities shared across services."""

from .ai_filter import PaperFilter
from .retry import async_retry_with_backoff
from .zotero_item_creator import ZoteroItemCreator, parse_creator_string

__all__ = [
    "PaperFilter",
    "async_retry_with_backoff",
    "ZoteroItemCreator",
    "parse_creator_string",
]
```

**Step 4: Find and update all imports**

Run:
```bash
grep -r "from.*rss_filter import" src/ --include="*.py"
grep -r "import RSSFilter" src/ --include="*.py"
```

Update each found import:

**In `src/zotero_mcp/services/rss/rss_service.py`:**
```python
# Change:
from zotero_mcp.services.rss.rss_filter import RSSFilter
# To:
from zotero_mcp.services.common import PaperFilter

# Update usage:
# rss_filter = RSSFilter(prompt_file=prompt_path)
# To:
# paper_filter = PaperFilter(prompt_file=prompt_path)
```

**In `src/zotero_mcp/services/gmail/gmail_service.py`:**
```python
# Change:
from zotero_mcp.services.rss.rss_filter import RSSFilter
# To:
from zotero_mcp.services.common import PaperFilter

# Update type hints and usage:
# rss_filter: RSSFilter | None = None
# To:
# paper_filter: PaperFilter | None = None
```

**Step 5: Update RSS __init__.py**

Modify: `src/zotero_mcp/services/rss/__init__.py`

```python
from .rss_service import RSSService

__all__ = ["RSSService"]
```

**Step 6: Run tests**

Run: `uv run pytest tests/ -v -k "filter"`
Expected: All existing filter tests pass

**Step 7: Commit**

```bash
git add src/zotero_mcp/services/common/ src/zotero_mcp/services/rss/ src/zotero_mcp/services/gmail/
git commit -m "refactor(services): move RSSFilter to common as PaperFilter"
```

---

### Task 4: Refactor RSS Service - Split fetcher and workflow

**Files:**
- Create: `src/zotero_mcp/services/rss/rss_fetcher.py`
- Create: `src/zotero_mcp/services/rss/rss_workflow.py`
- Modify: `src/zotero_mcp/services/rss/__init__.py`
- DELETE: `src/zotero_mcp/services/rss/rss_service.py`
- Test: Update existing RSS tests

**Step 1: Create RSSFetcher class**

Create: `src/zotero_mcp/services/rss/rss_fetcher.py`

```python
"""RSS feed fetching and parsing."""

import asyncio
from datetime import datetime
import logging
import time
from typing import Any
from xml.etree import ElementTree as ET

import feedparser

from zotero_mcp.models.rss import RSSFeed, RSSItem

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
MAX_RETRIES = 5


class RSSFetcher:
    """Handles RSS feed fetching and parsing."""

    async def fetch_feed(self, url: str) -> RSSFeed | None:
        """Fetch and parse a single RSS feed asynchronously."""
        for attempt in range(1, MAX_RETRIES + 1):
            feed = await asyncio.to_thread(self._fetch_sync, url)

            if feed:
                return feed

            if attempt < MAX_RETRIES:
                wait_time = attempt
                logger.warning(
                    f"Attempt {attempt}/{MAX_RETRIES} failed for {url}. "
                    f"Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Failed to fetch {url} after {MAX_RETRIES} attempts")

        return None

    def _get_entry_value(self, entry: Any, key: str, default: Any = None) -> Any:
        """Helper to safely get value from entry which might be dict or object"""
        if isinstance(entry, dict):
            return entry.get(key, default)
        return getattr(entry, key, default)

    def _extract_doi(self, entry: Any) -> str | None:
        """Extract DOI from entry metadata or link."""
        from zotero_mcp.utils.helpers import DOI_PATTERN

        # 1. Try common feedparser fields for DOI
        for key in ["prism_doi", "dc_identifier"]:
            val = self._get_entry_value(entry, key)
            if val and isinstance(val, str):
                if val.lower().startswith("doi:"):
                    val = val[4:].strip()
                if DOI_PATTERN.match(val):
                    return val

        # 2. Try to find DOI in link or guid
        for key in ["link", "id"]:
            val = self._get_entry_value(entry, key)
            if val and isinstance(val, str):
                match = DOI_PATTERN.search(val)
                if match:
                    return match.group(0)

        return None

    def _fetch_sync(self, url: str) -> RSSFeed | None:
        """Synchronously fetch and parse RSS feed."""
        try:
            feed: Any = feedparser.parse(url, agent=USER_AGENT)

            if hasattr(feed, "bozo") and feed.bozo:
                logger.warning(
                    f"Potential issue parsing feed {url}: {getattr(feed, 'bozo_exception', 'Unknown error')}"
                )

            items = []
            entries = getattr(feed, "entries", [])

            for entry in entries:
                pub_date = None
                published_parsed = self._get_entry_value(entry, "published_parsed")

                if published_parsed and isinstance(published_parsed, time.struct_time):
                    pub_date = datetime.fromtimestamp(time.mktime(published_parsed))
                else:
                    updated_parsed = self._get_entry_value(entry, "updated_parsed")
                    if updated_parsed and isinstance(updated_parsed, time.struct_time):
                        pub_date = datetime.fromtimestamp(time.mktime(updated_parsed))

                # Extract simple content
                summary = self._get_entry_value(entry, "summary")
                description = self._get_entry_value(entry, "description")
                content_val = summary if summary else (description if description else "")

                # Extract link, id, author
                title_val = self._get_entry_value(entry, "title", "No Title")
                link_val = self._get_entry_value(entry, "link", "")
                author_val = self._get_entry_value(entry, "author")
                guid_val = self._get_entry_value(entry, "id", link_val)
                doi_val = self._extract_doi(entry)

                # Get feed title safely
                feed_title = "Unknown Feed"
                feed_obj = getattr(feed, "feed", None)
                if feed_obj:
                    feed_title = self._get_entry_value(feed_obj, "title", feed_title)

                items.append(
                    RSSItem(
                        title=str(title_val),
                        link=str(link_val),
                        description=str(content_val) if content_val else None,
                        pub_date=pub_date,
                        author=str(author_val) if author_val else None,
                        guid=str(guid_val),
                        source_url=url,
                        source_title=str(feed_title),
                        doi=doi_val,
                    )
                )

            # Get feed metadata safely
            feed_title = "Unknown Feed"
            feed_link = url
            feed_desc = None

            feed_obj = getattr(feed, "feed", None)
            if feed_obj:
                feed_title = str(self._get_entry_value(feed_obj, "title", feed_title))
                feed_link = str(self._get_entry_value(feed_obj, "link", url))
                desc_val = self._get_entry_value(feed_obj, "description")
                if desc_val:
                    feed_desc = str(desc_val)

            return RSSFeed(
                title=feed_title,
                link=feed_link,
                description=feed_desc,
                items=items,
                last_updated=datetime.now(),
            )
        except Exception as e:
            logger.error(f"Error fetching RSS feed {url}: {e}")
            return None

    async def parse_opml(self, content: str) -> list[str]:
        """Parse OPML content to extract feed URLs."""
        try:
            urls = []
            root = ET.fromstring(content)
            for outline in root.findall(".//outline[@xmlUrl]"):
                url = outline.get("xmlUrl")
                if url:
                    urls.append(url)
            return urls
        except Exception as e:
            logger.error(f"Error parsing OPML: {e}")
            return []

    async def fetch_feeds_from_opml(self, opml_path: str) -> list[RSSFeed]:
        """Read OPML file and fetch all feeds."""
        try:
            with open(opml_path, encoding="utf-8") as f:
                content = f.read()

            urls = await self.parse_opml(content)
            tasks = [self.fetch_feed(url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            feeds = []
            for res in results:
                if isinstance(res, RSSFeed):
                    feeds.append(res)
                elif isinstance(res, Exception):
                    logger.error(f"Task failed: {res}")

            return feeds
        except Exception as e:
            logger.error(f"Error processing OPML file {opml_path}: {e}")
            return []
```

**Step 2: Create RSS workflow using common utilities**

Create: `src/zotero_mcp/services/rss/rss_workflow.py`

```python
"""RSS workflow orchestration."""

import asyncio
from datetime import datetime, timedelta
import logging

from zotero_mcp.models.rss import RSSItem, RSSProcessResult
from zotero_mcp.services.common import PaperFilter, ZoteroItemCreator
from zotero_mcp.services.data_access import get_data_service
from zotero_mcp.services.metadata import MetadataService
from zotero_mcp.services.rss.rss_fetcher import RSSFetcher

logger = logging.getLogger(__name__)


class RSSWorkflow:
    """Orchestrates RSS fetch → filter → import pipeline."""

    def __init__(self):
        self.fetcher = RSSFetcher()
        self.data_service = get_data_service()
        self.metadata_service = MetadataService()
        self.item_creator = ZoteroItemCreator(
            self.data_service, self.metadata_service
        )

    async def process_rss_workflow(
        self,
        opml_path: str,
        prompt_path: str | None = None,
        collection_name: str = "00_INBOXS",
        days_back: int = 15,
        max_items: int | None = None,
        dry_run: bool = False,
        llm_provider: str = "deepseek",
    ) -> RSSProcessResult:
        """
        Full RSS fetching and importing workflow.

        1. Fetch feeds from OPML
        2. Filter by date
        3. Apply AI keyword filtering
        4. Import to Zotero collection
        """
        result = RSSProcessResult()

        # Find collection
        matches = await self.data_service.find_collection_by_name(collection_name)
        if not matches:
            raise ValueError(f"Collection '{collection_name}' not found")
        collection_key = matches[0].get("data", {}).get("key")

        # Fetch feeds
        feeds = await self.fetcher.fetch_feeds_from_opml(opml_path)
        result.feeds_fetched = len(feeds)

        # Collect and filter by date
        cutoff = datetime.now() - timedelta(days=days_back) if days_back else None
        all_items = self._collect_items(feeds, cutoff)
        result.items_found = len(all_items)
        result.items_after_date_filter = len(all_items)

        if not all_items:
            logger.info("No recent items found")
            return result

        # AI filter
        paper_filter = PaperFilter(prompt_file=prompt_path)

        if llm_provider == "claude-cli":
            logger.info("Using Claude CLI for RSS filtering")
            relevant, _, _ = await paper_filter.filter_with_cli(all_items)
        else:
            relevant, _, _ = await paper_filter.filter_with_keywords(all_items)

        result.items_filtered = len(relevant)

        # Sort and limit
        relevant.sort(key=lambda x: x.pub_date or datetime.min, reverse=True)
        if max_items:
            relevant = relevant[:max_items]

        # Import
        for item in relevant:
            if dry_run:
                logger.info(f"[DRY RUN] Would import: {item.title}")
                continue

            item_key = await self.item_creator.create_item(item, collection_key)
            if item_key:
                result.items_imported += 1
            else:
                result.items_duplicate += 1

            await asyncio.sleep(0.5)

        return result

    def _collect_items(
        self, feeds: list[RSSFeed], cutoff: datetime | None
    ) -> list[RSSItem]:
        """Collect items from feeds, filtering by date."""
        all_items = []
        for feed in feeds:
            all_items.extend(
                [
                    i
                    for i in feed.items
                    if not i.pub_date or (cutoff is None or i.pub_date >= cutoff)
                ]
            )
        return all_items
```

**Step 3: Update RSS __init__.py**

Modify: `src/zotero_mcp/services/rss/__init__.py`

```python
"""RSS service package."""

from .rss_fetcher import RSSFetcher
from .rss_workflow import RSSWorkflow

__all__ = ["RSSFetcher", "RSSWorkflow"]
```

**Step 4: Delete old rss_service.py**

Run:
```bash
rm src/zotero_mcp/services/rss/rss_service.py
```

**Step 5: Find and update all imports**

Run:
```bash
grep -r "from.*rss.*import.*RSSService" src/ --include="*.py"
grep -r "from zotero_mcp.services.rss.rss_service" src/ --include="*.py"
```

Update imports to use new classes:
```python
# Change:
from zotero_mcp.services.rss.rss_service import RSSService
# To:
from zotero_mcp.services.rss import RSSFetcher, RSSWorkflow
```

**Step 6: Run RSS tests**

Run: `uv run pytest tests/ -v -k "rss" 2>&1 | head -50`
Expected: Some test failures (need to update tests to use new classes)

**Step 7: Update failing tests**

For each failing test, update to use `RSSFetcher` or `RSSWorkflow` instead of `RSSService`.

**Step 8: Commit**

```bash
git add src/zotero_mcp/services/rss/ tests/
git commit -m "refactor(services): split RSS service into fetcher and workflow"
```

---

### Task 5: Refactor Gmail Service - Split fetcher and workflow

**Files:**
- Create: `src/zotero_mcp/services/gmail/gmail_fetcher.py`
- Create: `src/zotero_mcp/services/gmail/gmail_workflow.py`
- Modify: `src/zotero_mcp/services/gmail/__init__.py`
- DELETE: `src/zotero_mcp/services/gmail/gmail_service.py`

**Step 1: Create GmailFetcher class**

Create: `src/zotero_mcp/services/gmail/gmail_fetcher.py`

```python
"""Gmail fetching and HTML parsing."""

from bs4 import BeautifulSoup, Tag
import logging

from zotero_mcp.clients.gmail import GmailClient
from zotero_mcp.models.gmail import EmailItem, EmailMessage
from zotero_mcp.utils.helpers import DOI_PATTERN, clean_title

logger = logging.getLogger(__name__)


class GmailFetcher:
    """Handles Gmail fetching and HTML parsing."""

    def __init__(self, gmail_client: GmailClient | None = None):
        self._gmail_client = gmail_client

    @property
    def gmail_client(self) -> GmailClient:
        """Lazy-initialize Gmail client."""
        if self._gmail_client is None:
            from zotero_mcp.clients.gmail import GmailClient
            self._gmail_client = GmailClient()
        return self._gmail_client

    async def fetch_and_parse_emails(
        self,
        sender: str | None = None,
        subject: str | None = None,
        query: str | None = None,
        max_emails: int = 50,
    ) -> list[EmailMessage]:
        """Fetch emails and parse their content."""
        from datetime import datetime

        messages = await self.gmail_client.search_messages(
            sender=sender,
            subject=subject,
            query=query,
            max_results=max_emails,
        )

        if not messages:
            logger.info("No matching emails found")
            return []

        parsed_emails: list[EmailMessage] = []
        for msg_info in messages:
            msg_id = msg_info["id"]
            thread_id = msg_info.get("threadId", "")

            try:
                headers = await self.gmail_client.get_message_headers(msg_id)
                subject_val = headers.get("Subject", "")
                sender_val = headers.get("From", "")
                date_str = headers.get("Date", "")

                date_val = None
                if date_str:
                    try:
                        for fmt in [
                            "%a, %d %b %Y %H:%M:%S %z",
                            "%d %b %Y %H:%M:%S %z",
                            "%a, %d %b %Y %H:%M:%S",
                        ]:
                            try:
                                date_val = datetime.strptime(date_str[:31], fmt)
                                break
                            except ValueError:
                                continue
                    except Exception:
                        pass

                html_body, text_body = await self.gmail_client.get_message_body(msg_id)
                items = self.parse_html_table(html_body, msg_id, subject_val)

                parsed_emails.append(
                    EmailMessage(
                        id=msg_id,
                        thread_id=thread_id,
                        subject=subject_val,
                        sender=sender_val,
                        date=date_val,
                        html_body=html_body,
                        text_body=text_body,
                        items=items,
                    )
                )

            except Exception as e:
                logger.error(f"Failed to parse email {msg_id}: {e}")
                continue

        logger.info(f"Parsed {len(parsed_emails)} emails")
        return parsed_emails

    def parse_html_table(
        self,
        html_content: str,
        email_id: str = "",
        email_subject: str = "",
    ) -> list[EmailItem]:
        """Parse HTML content to extract items from tables."""
        if not html_content:
            return []

        items: list[EmailItem] = []
        soup = BeautifulSoup(html_content, "lxml")

        # Strategy 1: Look for table rows with links
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            for row in rows:
                item = self._extract_item_from_row(row, email_id, email_subject)
                if item:
                    items.append(item)

        # Strategy 2: If no tables, look for article-like divs/sections
        if not items:
            items = self._extract_items_from_divs(soup, email_id, email_subject)

        # Strategy 3: Extract from plain links with surrounding text
        if not items:
            items = self._extract_items_from_links(soup, email_id, email_subject)

        # Deduplicate by title
        seen_titles: set[str] = set()
        unique_items: list[EmailItem] = []
        for item in items:
            title_lower = item.title.lower().strip()
            if title_lower and title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_items.append(item)

        logger.info(f"Extracted {len(unique_items)} items from email {email_id[:8]}...")
        return unique_items

    def _extract_item_from_row(
        self,
        row: Tag,
        email_id: str,
        email_subject: str,
    ) -> EmailItem | None:
        """Extract an item from a table row."""
        title = ""
        link = ""

        links = row.find_all("a", href=True)
        for a in links:
            href_value = a.get("href", "")
            href = href_value if isinstance(href_value, str) else ""
            text = a.get_text(strip=True)

            if len(text) < 10 or text.lower() in ("read more", "view", "click here"):
                continue

            if not title or len(text) > len(title):
                title = text
                link = href

        if not title:
            cells = row.find_all(["td", "th"])
            for cell in cells:
                text = cell.get_text(strip=True)
                if len(text) > 20 and len(text) < 500:
                    title = text
                    break

        if not title or len(title) < 10:
            return None

        doi = None
        row_text = row.get_text()
        doi_match = DOI_PATTERN.search(link) or DOI_PATTERN.search(row_text)
        if doi_match:
            doi = doi_match.group(0)

        authors = None
        journal = None
        cells = row.find_all(["td", "th"])
        for cell in cells:
            text = cell.get_text(strip=True)
            if text == title:
                continue
            if "," in text and len(text) < 200:
                if not authors:
                    authors = text
            elif len(text) < 100 and not journal:
                journal = text

        return EmailItem(
            title=clean_title(title),
            link=link,
            authors=authors,
            journal=journal,
            doi=doi,
            source_email_id=email_id,
            source_subject=email_subject,
        )

    def _extract_items_from_divs(
        self,
        soup: BeautifulSoup,
        email_id: str,
        email_subject: str,
    ) -> list[EmailItem]:
        """Extract items from div-based layouts."""
        items: list[EmailItem] = []

        for container in soup.find_all(["div", "article", "section"]):
            link_elem = container.find("a", href=True)
            if not link_elem:
                continue

            title = link_elem.get_text(strip=True)
            link_value = link_elem.get("href", "")
            link = link_value if isinstance(link_value, str) else ""

            if len(title) < 15:
                heading = container.find(["h1", "h2", "h3", "h4"])
                if heading:
                    title = heading.get_text(strip=True)

            if len(title) < 15 or len(title) > 500:
                continue

            doi = None
            container_text = container.get_text()
            doi_match = DOI_PATTERN.search(link) or DOI_PATTERN.search(container_text)
            if doi_match:
                doi = doi_match.group(0)

            items.append(
                EmailItem(
                    title=clean_title(title),
                    link=link,
                    doi=doi,
                    source_email_id=email_id,
                    source_subject=email_subject,
                )
            )

        return items

    def _extract_items_from_links(
        self,
        soup: BeautifulSoup,
        email_id: str,
        email_subject: str,
    ) -> list[EmailItem]:
        """Extract items from standalone links."""
        items: list[EmailItem] = []

        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            href_value = a.get("href", "")
            href = href_value if isinstance(href_value, str) else ""

            if len(text) < 20 or len(text) > 500:
                continue
            if text.lower() in ("unsubscribe", "view in browser", "read more"):
                continue

            is_article_link = any(
                domain in href.lower()
                for domain in [
                    "doi.org",
                    "nature.com",
                    "science.org",
                    "wiley.com",
                    "springer.com",
                    "acs.org",
                    "rsc.org",
                    "elsevier.com",
                    "cell.com",
                    "pnas.org",
                    "sciencedirect.com",
                ]
            )

            doi = None
            doi_match = DOI_PATTERN.search(href)
            if doi_match:
                doi = doi_match.group(0)
                is_article_link = True

            if is_article_link:
                items.append(
                    EmailItem(
                        title=clean_title(text),
                        link=href,
                        doi=doi,
                        source_email_id=email_id,
                        source_subject=email_subject,
                    )
                )

        return items
```

**Step 2: Create Gmail workflow using common utilities**

Create: `src/zotero_mcp/services/gmail/gmail_workflow.py`

```python
"""Gmail workflow orchestration."""

import asyncio
import logging

from zotero_mcp.models.gmail import GmailProcessResult
from zotero_mcp.models.rss import RSSItem
from zotero_mcp.services.common import PaperFilter, ZoteroItemCreator
from zotero_mcp.services.data_access import get_data_service
from zotero_mcp.services.metadata import MetadataService
from zotero_mcp.services.gmail.gmail_fetcher import GmailFetcher

logger = logging.getLogger(__name__)


class GmailWorkflow:
    """Orchestrates Gmail fetch → filter → import → delete pipeline."""

    def __init__(self):
        self.fetcher = GmailFetcher()
        self.data_service = get_data_service()
        self.metadata_service = MetadataService()
        self.item_creator = ZoteroItemCreator(
            self.data_service, self.metadata_service
        )
        self.paper_filter = PaperFilter()

    async def process_gmail_workflow(
        self,
        sender: str | None = None,
        subject: str | None = None,
        query: str | None = None,
        collection_name: str = "00_INBOXS",
        max_emails: int = 50,
        delete_after: bool = True,
        trash_only: bool = True,
        dry_run: bool = False,
        llm_provider: str = "deepseek",
    ) -> GmailProcessResult:
        """
        Full Gmail processing workflow.

        1. Fetch emails from Gmail
        2. Extract items from HTML
        3. Mark emails as read
        4. Apply AI filtering
        5. Import to Zotero
        6. Trash/delete processed emails
        """
        result = GmailProcessResult()

        # Fetch and parse emails
        emails = await self.fetcher.fetch_and_parse_emails(
            sender=sender,
            subject=subject,
            query=query,
            max_emails=max_emails,
        )
        result.emails_found = len(emails)

        if not emails:
            logger.info("No emails to process")
            return result

        # Extract items and mark as read
        all_items, all_email_ids = await self._extract_items_and_mark_read(
            emails, result
        )

        if not all_items:
            logger.info("No items extracted from emails")
            await self._trash_emails(all_email_ids, delete_after, trash_only, result)
            return result

        # Convert to RSSItem for filtering
        rss_items = [self._email_to_rss_item(item) for item in all_items]

        # AI filter
        if llm_provider == "claude-cli":
            relevant, _, _ = await self.paper_filter.filter_with_cli(rss_items)
        else:
            relevant, _, _ = await self.paper_filter.filter_with_keywords(rss_items)

        result.items_filtered = len(relevant)

        if not relevant:
            logger.info("No items passed AI filter")
            await self._trash_emails(all_email_ids, delete_after, trash_only, result)
            return result

        # Import to Zotero
        if not dry_run:
            await self._import_items(relevant, collection_name, result)

        # Trash emails
        await self._trash_emails(all_email_ids, delete_after, trash_only, result)

        logger.info(
            f"Gmail workflow complete: "
            f"{result.emails_processed} emails, "
            f"{result.items_imported} imported, "
            f"{result.emails_deleted} trashed"
        )

        return result

    async def _extract_items_and_mark_read(
        self, emails: list[EmailMessage], result: GmailProcessResult
    ) -> tuple[list[EmailItem], list[str]]:
        """Extract items from emails and mark as read."""
        all_items = []
        all_email_ids = []

        for email in emails:
            all_email_ids.append(email.id)
            if email.items:
                all_items.extend(email.items)
                result.emails_processed += 1

        result.items_extracted = len(all_items)

        # Mark as read
        for email_id in all_email_ids:
            try:
                await self.fetcher.gmail_client.mark_as_read(email_id)
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Failed to mark email {email_id} as read: {e}")

        return all_items, all_email_ids

    def _email_to_rss_item(self, email_item: EmailItem) -> RSSItem:
        """Convert EmailItem to RSSItem for filtering compatibility."""
        return RSSItem(
            title=email_item.title,
            link=email_item.link,
            description=email_item.abstract,
            pub_date=email_item.pub_date,
            author=email_item.authors,
            guid=email_item.link or email_item.title,
            source_url=f"gmail:{email_item.source_email_id}",
            source_title=email_item.source_subject,
            doi=email_item.doi,
        )

    async def _import_items(
        self, items: list[RSSItem], collection_name: str, result: GmailProcessResult
    ):
        """Import filtered items to Zotero."""
        matches = await self.data_service.find_collection_by_name(collection_name)
        if not matches:
            error_msg = f"Collection '{collection_name}' not found"
            logger.error(error_msg)
            result.errors.append(error_msg)
            return

        collection_key = matches[0].get("data", {}).get("key")

        for item in items:
            try:
                item_key = await self.item_creator.create_item(item, collection_key)
                if item_key:
                    result.items_imported += 1
                else:
                    result.items_duplicate += 1

                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Failed to import item '{item.title[:50]}': {e}")
                result.errors.append(f"Import failed: {item.title[:50]}")

    async def _trash_emails(
        self,
        email_ids: list[str],
        delete_after: bool,
        trash_only: bool,
        result: GmailProcessResult,
    ):
        """Trash or delete emails."""
        if not delete_after or not email_ids:
            return

        for email_id in email_ids:
            try:
                if trash_only:
                    success = await self.fetcher.gmail_client.trash_message(email_id)
                else:
                    success = await self.fetcher.gmail_client.delete_message(email_id)

                if success:
                    result.emails_deleted += 1

                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Failed to delete email {email_id}: {e}")
                result.errors.append(f"Delete failed: {email_id}")
```

**Step 3: Update Gmail __init__.py**

Modify: `src/zotero_mcp/services/gmail/__init__.py`

```python
"""Gmail service package."""

from .gmail_fetcher import GmailFetcher
from .gmail_workflow import GmailWorkflow

__all__ = ["GmailFetcher", "GmailWorkflow"]
```

**Step 4: Delete old gmail_service.py**

Run:
```bash
rm src/zotero_mcp/services/gmail/gmail_service.py
```

**Step 5: Find and update all imports**

Run:
```bash
grep -r "from.*gmail.*import.*GmailService" src/ --include="*.py"
grep -r "from zotero_mcp.services.gmail.gmail_service" src/ --include="*.py"
```

Update imports:
```python
# Change:
from zotero_mcp.services.gmail.gmail_service import GmailService
# To:
from zotero_mcp.services.gmail import GmailFetcher, GmailWorkflow
```

**Step 6: Run Gmail tests**

Run: `uv run pytest tests/ -v -k "gmail"`
Expected: Some test failures (need to update tests)

**Step 7: Update failing tests**

Update tests to use `GmailFetcher` or `GmailWorkflow`.

**Step 8: Commit**

```bash
git add src/zotero_mcp/services/gmail/ tests/
git commit -m "refactor(services): split Gmail service into fetcher and workflow"
```

---

### Task 6: Create Zotero Service Module Structure

**Files:**
- Create: `src/zotero_mcp/services/zotero/__init__.py`
- Move: `src/zotero_mcp/services/item.py` → `src/zotero_mcp/services/zotero/item_manager.py`
- Move: `src/zotero_mcp/services/metadata.py` → `src/zotero_mcp/services/zotero/metadata_enrichment.py`
- Move: `src/zotero_mcp/services/workflow.py` → `src/zotero_mcp/services/zotero/ai_analysis.py`
- Move: `src/zotero_mcp/services/search.py` → `src/zotero_mcp/services/zotero/search.py`
- Modify: `src/zotero_mcp/services/__init__.py`

**Step 1: Create zotero service directory**

Run:
```bash
mkdir -p src/zotero_mcp/services/zotero
```

**Step 2: Move and rename item.py**

Run:
```bash
mv src/zotero_mcp/services/item.py src/zotero_mcp/services/zotero/item_manager.py
```

No class name change needed - keep `ItemService`.

**Step 3: Move and rename metadata.py**

Run:
```bash
mv src/zotero_mcp/services/metadata.py src/zotero_mcp/services/zotero/metadata_enrichment.py
```

Update class name in the file:
```python
# Change:
class MetadataService:
# To:
class MetadataEnrichmentService:
```

**Step 4: Move and rename workflow.py**

Run:
```bash
mv src/zotero_mcp/services/workflow.py src/zotero_mcp/services/zotero/ai_analysis.py
```

Update class name in the file:
```python
# Change:
class WorkflowService:
# To:
class AIAnalysisService:
```

**Step 5: Move search.py**

Run:
```bash
mv src/zotero_mcp/services/search.py src/zotero_mcp/services/zotero/search.py
```

No class name change needed - keep `SearchService`.

**Step 6: Create zotero __init__.py**

Create: `src/zotero_mcp/services/zotero/__init__.py`

```python
"""Zotero service package - Core Zotero operations."""

from .ai_analysis import AIAnalysisService
from .item_manager import ItemService
from .metadata_enrichment import MetadataEnrichmentService
from .search import SearchService

__all__ = [
    "AIAnalysisService",
    "ItemService",
    "MetadataEnrichmentService",
    "SearchService",
]
```

**Step 7: Update main services __init__.py**

Modify: `src/zotero_mcp/services/__init__.py`

```python
"""Services for Zotero MCP."""

from .common import PaperFilter, async_retry_with_backoff
from .data_access import DataAccessService, get_data_service
from .gmail import GmailFetcher, GmailWorkflow
from .rss import RSSFetcher, RSSWorkflow
from .zotero import (
    AIAnalysisService,
    ItemService,
    MetadataEnrichmentService,
    SearchService,
)

__all__ = [
    "DataAccessService",
    "get_data_service",
    "PaperFilter",
    "async_retry_with_backoff",
    "RSSFetcher",
    "RSSWorkflow",
    "GmailFetcher",
    "GmailWorkflow",
    "AIAnalysisService",
    "ItemService",
    "MetadataEnrichmentService",
    "SearchService",
]
```

**Step 8: Find and update all imports**

Run:
```bash
grep -r "from zotero_mcp.services.item" src/ --include="*.py"
grep -r "from zotero_mcp.services.metadata" src/ --include="*.py"
grep -r "from zotero_mcp.services.workflow" src/ --include="*.py"
grep -r "from zotero_mcp.services.search" src/ --include="*.py"
```

Update each import:
```python
# Change:
from zotero_mcp.services.item import ItemService
# To:
from zotero_mcp.services.zotero import ItemService

# Change:
from zotero_mcp.services.metadata import MetadataService
# To:
from zotero_mcp.services.zotero import MetadataEnrichmentService as MetadataService

# Or update class name:
# Change:
MetadataService(...)
# To:
MetadataEnrichmentService(...)

# Change:
from zotero_mcp.services.workflow import WorkflowService
# To:
from zotero_mcp.services.zotero import AIAnalysisService

# Change:
from zotero_mcp.services.search import SearchService
# To:
from zotero_mcp.services.zotero import SearchService
```

**Step 9: Run all tests**

Run: `uv run pytest tests/ -v 2>&1 | head -100`
Expected: Some import/test errors, fix them iteratively

**Step 10: Commit**

```bash
git add src/zotero_mcp/services/
git commit -m "refactor(services): organize Zotero services into dedicated module"
```

---

### Task 7: Update Documentation and CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md` (if needed)

**Step 1: Update CLAUDE.md architecture section**

Modify: `CLAUDE.md`

```markdown
## Architecture

Layered architecture with strict separation of concerns:

- **Entry** (`server.py`, `cli.py`) - FastMCP initialization, CLI commands
- **Tools** (`tools/`) - Thin MCP tool wrappers (`@mcp.tool`) that delegate to Services
- **Services** (`services/`) - Business logic layer with modular organization
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
    - `PaperFilter` - AI-powered keyword filtering (DeepSeek/Claude CLI)
    - `ZoteroItemCreator` - Unified item creation logic
    - `async_retry_with_backoff` - Retry with exponential backoff
- **Clients** (`clients/`) - Low-level external service interfaces
- **Models** (`models/`) - Pydantic models for type-safe data exchange
- **Formatters** (`formatters/`) - Output formatters
- **Utils** (`utils/`) - Shared utilities

### Key Patterns

1. **Service Layer First**: Always use `DataAccessService` instead of calling clients directly
2. **Common Utilities**: Shared functionality in `services/common/` to avoid duplication
3. **Workflow Separation**: Fetchers handle I/O, workflows orchestrate pipelines
4. **Async Everywhere**: All I/O must be async (`async/await`)
5. **Type Safety**: Use Pydantic models for all complex data structures
6. **Config Priority**: Environment vars > `~/.config/zotero-mcp/config.json` > defaults

### Data Flow Patterns

- **Tools → Services → Clients**: Tools delegate to Services, which coordinate multiple Clients
- **Backend Selection**: `DataAccessService` auto-selects Local DB (fast reads) vs Zotero API (writes/fallback)
- **Workflow Checkpointing**: `AIAnalysisService` uses checkpoint/resume for batch operations
```

**Step 2: Update Adding a New MCP Tool section**

Modify: `CLAUDE.md` (if needed to reflect new service structure)

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with refactored service architecture"
```

---

### Task 8: Final Code Quality Checks

**Files:**
- All modified files

**Step 1: Run linter and formatter**

Run:
```bash
uv run ruff check src/zotero_mcp/services/ --fix
uv run ruff format src/zotero_mcp/services/
```

**Step 2: Run type checker**

Run:
```bash
uv run ty check src/zotero_mcp/services/
```

**Step 3: Run full test suite**

Run:
```bash
uv run pytest --cov=src/zotero_mcp/services
```

**Step 4: Fix any issues found**

Address any lint, type, or test failures iteratively.

**Step 5: Final commit**

```bash
git add src/zotero_mcp/
git commit -m "style: apply formatting and fix type hints after refactor"
```

---

## Summary

This refactoring achieves:

1. **Clear separation of concerns**: RSS, Gmail, and Zotero functionalities isolated
2. **Eliminated code duplication**: Common utilities in `services/common/`
3. **Better naming**: `PaperFilter` instead of `RSSFilter`, descriptive module names
4. **Easier testing**: Smaller, focused classes with single responsibilities
5. **Maintainability**: Changes to common logic only need to be made once
6. **No backward compatibility**: Old code deleted, clean slate

**Final file structure:**
```
src/zotero_mcp/services/
├── __init__.py
├── data_access.py
├── common/
│   ├── __init__.py
│   ├── ai_filter.py (PaperFilter)
│   ├── retry.py
│   └── zotero_item_creator.py
├── rss/
│   ├── __init__.py
│   ├── rss_fetcher.py (RSSFetcher)
│   └── rss_workflow.py (RSSWorkflow)
├── gmail/
│   ├── __init__.py
│   ├── gmail_fetcher.py (GmailFetcher)
│   └── gmail_workflow.py (GmailWorkflow)
└── zotero/
    ├── __init__.py
    ├── ai_analysis.py (AIAnalysisService)
    ├── item_manager.py (ItemService)
    ├── metadata_enrichment.py (MetadataEnrichmentService)
    └── search.py (SearchService)
```

**Estimated time:** 3-4 hours for full implementation
