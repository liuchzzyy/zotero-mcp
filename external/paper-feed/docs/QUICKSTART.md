# Quick Start Guide

This tutorial will guide you through a complete paper collection workflow: fetching from RSS feeds, filtering by keywords, and exporting to JSON.

## What You'll Learn

By the end of this tutorial, you'll be able to:
- Fetch papers from arXiv and other RSS feeds
- Filter papers by keywords, categories, authors, and dates
- Export filtered papers to JSON format
- Combine multiple sources and filters

## Prerequisites

- paper-feed installed (see [Installation Guide](INSTALLATION.md))
- Basic Python knowledge
- Internet connection for fetching RSS feeds

## Tutorial 1: Your First Paper Collection

Let's start with a simple example: fetching recent AI papers from arXiv.

### Step 1: Basic RSS Fetch

Create a file `basic_fetch.py`:

```python
import asyncio
from paper_feed import RSSSource

async def main():
    # Create RSS source for arXiv CS.AI
    source = RSSSource("https://arxiv.org/rss/cs.AI")

    # Fetch 10 most recent papers
    papers = await source.fetch_papers(limit=10)

    # Display results
    print(f"Fetched {len(papers)} papers from {source.source_name}")
    print()

    for i, paper in enumerate(papers, 1):
        print(f"{i}. {paper.title}")
        print(f"   Authors: {', '.join(paper.authors[:3])}")
        if paper.authors > 3:
            print(f"   ... and {len(paper.authors) - 3} more")
        print(f"   Date: {paper.published_date}")
        print()

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
python basic_fetch.py
```

**Expected output:**
```
Fetched 10 papers from arXiv
1. Deep Learning for Computer Vision
   Authors: Zhang San, Li Si, Wang Wu
   Date: 2024-01-15
...
```

### Step 2: Add Keyword Filtering

Now let's filter for papers about "machine learning":

```python
import asyncio
from paper_feed import RSSSource, FilterPipeline, FilterCriteria

async def main():
    # Fetch papers
    source = RSSSource("https://arxiv.org/rss/cs.AI")
    papers = await source.fetch_papers(limit=50)

    print(f"Fetched {len(papers)} papers")

    # Define filter criteria
    criteria = FilterCriteria(
        keywords=["machine learning"],  # Must contain "machine learning"
    )

    # Apply filter
    result = await FilterPipeline().filter(papers, criteria)

    print(f"Filtered to {result.passed_count} papers")
    print()

    # Display filtered papers
    for i, paper in enumerate(result.papers[:5], 1):
        print(f"{i}. {paper.title}")
        print(f"   Abstract: {paper.abstract[:100]}...")
        print()

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 3: Export to JSON

Finally, let's export the filtered papers:

```python
import asyncio
from paper_feed import RSSSource, FilterPipeline, JSONAdapter, FilterCriteria

async def main():
    # Fetch and filter
    source = RSSSource("https://arxiv.org/rss/cs.AI")
    papers = await source.fetch_papers(limit=50)

    criteria = FilterCriteria(keywords=["machine learning"])
    result = await FilterPipeline().filter(papers, criteria)

    # Export to JSON
    await JSONAdapter().export(
        result.papers,
        "ml_papers.json",
        include_metadata=True
    )

    print(f"Exported {len(result.papers)} papers to ml_papers.json")

if __name__ == "__main__":
    asyncio.run(main())
```

Check the output file:
```bash
cat ml_papers.json
```

## Tutorial 2: Advanced Filtering

Let's explore more sophisticated filtering options.

### Multiple Keywords (AND Logic)

Papers must contain ALL specified keywords:

```python
criteria = FilterCriteria(
    keywords=["neural networks", "transformers"],
)
```

### Category Filtering

Filter by subject categories (OR logic):

```python
criteria = FilterCriteria(
    categories=["Computer Science", "Artificial Intelligence"],
)
```

### Exclude Keywords

Filter OUT papers containing certain words:

```python
criteria = FilterCriteria(
    keywords=["machine learning"],
    exclude_keywords=["review", "survey", "tutorial"],
)
```

### Date Filtering

Only recent papers:

```python
from datetime import date

criteria = FilterCriteria(
    keywords=["deep learning"],
    min_date=date(2023, 1, 1),  # Only papers from 2023 onwards
)
```

### Author Filtering

Papers by specific authors:

```python
criteria = FilterCriteria(
    authors=["Hinton", "LeCun", "Bengio"],
)
```

### Combined Filter

Put it all together:

```python
from datetime import date

criteria = FilterCriteria(
    keywords=["neural networks"],
    exclude_keywords=["review"],
    categories=["Computer Science"],
    min_date=date(2023, 1, 1),
    has_pdf=True,  # Only papers with PDF links
)

result = await FilterPipeline().filter(papers, criteria)
print(f"Found {result.passed_count} papers")
```

## Tutorial 3: Multiple Sources

Fetch from multiple RSS feeds and combine results:

```python
import asyncio
from paper_feed import RSSSource, FilterPipeline, FilterCriteria

async def fetch_from_sources():
    # Define multiple sources
    sources = [
        RSSSource("https://arxiv.org/rss/cs.AI"),
        RSSSource("https://arxiv.org/rss/cs.LG"),
        RSSSource("https://www.biorxiv.org/content/early/recent"),
    ]

    # Fetch from all sources
    all_papers = []
    for source in sources:
        papers = await source.fetch_papers(limit=20)
        all_papers.extend(papers)
        print(f"Fetched {len(papers)} from {source.source_name}")

    print(f"Total papers: {len(all_papers)}")

    # Filter combined results
    criteria = FilterCriteria(keywords=["learning"])
    result = await FilterPipeline().filter(all_papers, criteria)

    print(f"Filtered to {result.passed_count} papers")
    return result

if __name__ == "__main__":
    result = asyncio.run(fetch_from_sources())
```

## Tutorial 4: Real-World Examples

### Example 1: Collect arXiv AI Papers Daily

```python
import asyncio
from datetime import date, timedelta
from paper_feed import RSSSource, FilterPipeline, JSONAdapter, FilterCriteria

async def collect_daily_ai_papers():
    # Fetch recent papers (last 7 days)
    week_ago = date.today() - timedelta(days=7)

    source = RSSSource("https://arxiv.org/rss/cs.AI")
    papers = await source.fetch_papers(since=week_ago)

    print(f"Found {len(papers)} papers from the last week")

    # Filter for AI topics
    criteria = FilterCriteria(
        keywords=["artificial intelligence", "machine learning"],
        exclude_keywords=["review"],
    )

    result = await FilterPipeline().filter(papers, criteria)

    # Export with timestamp
    filename = f"ai_papers_{date.today().isoformat()}.json"
    await JSONAdapter().export(result.papers, filename)

    print(f"Exported {result.passed_count} papers to {filename}")

if __name__ == "__main__":
    asyncio.run(collect_daily_ai_papers())
```

### Example 2: Monitor bioRxiv for COVID-19 Research

```python
import asyncio
from paper_feed import RSSSource, FilterPipeline, FilterCriteria

async def monitor_covid_research():
    # Fetch from bioRxiv
    source = RSSSource("https://www.biorxiv.org/content/early/recent")
    papers = await source.fetch_papers(limit=100)

    # Filter for COVID-related papers
    criteria = FilterCriteria(
        keywords=["COVID-19", "SARS-CoV-2", "coronavirus"],
        categories=["Virology", "Epidemiology"],
    )

    result = await FilterPipeline().filter(papers, criteria)

    print(f"Found {result.passed_count} COVID-19 papers")

    # Display titles
    for paper in result.papers:
        print(f"- {paper.title}")
        print(f"  {paper.url}")
        print()

if __name__ == "__main__":
    asyncio.run(monitor_covid_research())
```

### Example 3: Track Specific Authors

```python
import asyncio
from paper_feed import RSSSource, FilterPipeline, JSONAdapter, FilterCriteria

async def track_authors():
    # List of authors to track
    authors_of_interest = [
        "Geoffrey Hinton",
        "Yann LeCun",
        "Yoshua Bengio",
    ]

    # Fetch from multiple arXiv categories
    all_papers = []
    for category in ["cs.AI", "cs.LG", "cs.CV"]:
        source = RSSSource(f"https://arxiv.org/rss/{category}")
        papers = await source.fetch_papers(limit=50)
        all_papers.extend(papers)

    # Filter by author
    criteria = FilterCriteria(authors=authors_of_interest)
    result = await FilterPipeline().filter(all_papers, criteria)

    print(f"Found {result.passed_count} papers by tracked authors")

    # Export
    await JSONAdapter().export(result.papers, "tracked_authors.json")

if __name__ == "__main__":
    asyncio.run(track_authors())
```

## Tutorial 5: Understanding Filter Results

The `FilterResult` object provides detailed statistics:

```python
result = await FilterPipeline().filter(papers, criteria)

# Basic stats
print(f"Total papers: {result.total_count}")
print(f"Passed filter: {result.passed_count}")
print(f"Rejected: {result.rejected_count}")

# Detailed stats
print(f"Filter stats: {result.filter_stats}")

# Example output:
# {
#   "keyword_filter": {
#     "input_count": 50,
#     "output_count": 15,
#     "messages": ["Applied keyword filter", "Applied category filter"]
#   }
# }
```

## Common Use Cases

### Use Case 1: Literature Review

Collect recent papers on a specific topic:

```python
async def literature_review(topic):
    source = RSSSource("https://arxiv.org/rss/cs.AI")
    papers = await source.fetch_papers(limit=200)

    criteria = FilterCriteria(
        keywords=[topic],
        min_date=date(2023, 1, 1),
        exclude_keywords=["survey", "review"],
    )

    result = await FilterPipeline().filter(papers, criteria)
    await JSONAdapter().export(result.papers, f"{topic}_literature.json")

    return result

asyncio.run(literature_review("reinforcement learning"))
```

### Use Case 2: Daily Digest

Get a daily summary of new papers:

```python
async def daily_digest():
    sources = [
        ("https://arxiv.org/rss/cs.AI", "arXiv AI"),
        ("https://arxiv.org/rss.cs.LG", "arXiv LG"),
    ]

    all_papers = []
    for url, name in sources:
        source = RSSSource(url, source_name=name)
        papers = await source.fetch_papers(limit=10)
        all_papers.extend(papers)

    await JSONAdapter().export(all_papers, "daily_digest.json")

asyncio.run(daily_digest())
```

### Use Case 3: Preprint Collection

Collect preprints from multiple sources:

```python
async def collect_preprints():
    preprint_servers = [
        "https://arxiv.org/rss/cs.AI",
        "https://www.biorxiv.org/content/early/recent",
        "https://www.medrxiv.org/content/early/recent",
    ]

    all_papers = []
    for url in preprint_servers:
        source = RSSSource(url)
        papers = await source.fetch_papers(limit=25)
        all_papers.extend(papers)

    # Filter for recent preprints
    from datetime import timedelta
    week_ago = date.today() - timedelta(days=7)

    criteria = FilterCriteria(min_date=week_ago)
    result = await FilterPipeline().filter(all_papers, criteria)

    await JSONAdapter().export(result.papers, "preprints_weekly.json")

asyncio.run(collect_preprints())
```

## Best Practices

### 1. Use Limits for Initial Testing

```python
# Start with small limits
papers = await source.fetch_papers(limit=10)

# Increase once confirmed working
papers = await source.fetch_papers(limit=100)
```

### 2. Handle Empty Results

```python
result = await FilterPipeline().filter(papers, criteria)

if result.passed_count == 0:
    print("No papers matched. Try relaxing criteria.")
else:
    await JSONAdapter().export(result.papers, "output.json")
```

### 3. Check Filter Statistics

```python
result = await FilterPipeline().filter(papers, criteria)

if result.rejected_count > result.passed_count * 2:
    print("Warning: Most papers were rejected. Consider relaxing criteria.")
```

### 4. Use Date Filters for Large Feeds

```python
from datetime import timedelta

# Only fetch recent papers
recent = date.today() - timedelta(days=30)
papers = await source.fetch_papers(since=recent)
```

### 5. Combine Filters Gradually

```python
# Start broad
criteria = FilterCriteria(keywords=["learning"])
result = await FilterPipeline().filter(papers, criteria)

# Then refine
criteria = FilterCriteria(
    keywords=["machine learning", "deep learning"],
    exclude_keywords=["review"],
    min_date=date(2023, 1, 1),
)
result = await FilterPipeline().filter(papers, criteria)
```

## Tips and Tricks

### Tip 1: Auto-Detect Source Names

`RSSSource` automatically detects source names from URLs:

```python
# These are equivalent
source1 = RSSSource("https://arxiv.org/rss/cs.AI")
# source1.source_name == "arXiv"

source2 = RSSSource("https://www.biorxiv.org/content/early/recent")
# source2.source_name == "bioRxiv"

# Or specify manually
source3 = RSSSource("https://example.com/feed", source_name="Custom Feed")
```

### Tip 2: Export Without Metadata

For cleaner JSON output:

```python
# Includes all fields (default)
await JSONAdapter().export(papers, "full.json", include_metadata=True)

# Excludes metadata field
await JSONAdapter().export(papers, "clean.json", include_metadata=False)
```

### Tip 3: Inspect Paper Items

```python
papers = await source.fetch_papers(limit=1)

if papers:
    paper = papers[0]
    print(f"Title: {paper.title}")
    print(f"Authors: {paper.authors}")
    print(f"Abstract: {paper.abstract}")
    print(f"DOI: {paper.doi}")
    print(f"URL: {paper.url}")
    print(f"PDF: {paper.pdf_url}")
    print(f"Date: {paper.published_date}")
    print(f"Categories: {paper.categories}")
    print(f"Tags: {paper.tags}")
    print(f"Source: {paper.source}")
    print(f"Metadata: {paper.metadata}")
```

### Tip 4: Filter by Multiple Categories

```python
# Papers in ANY of these categories (OR logic)
criteria = FilterCriteria(
    categories=["Computer Science", "Physics", "Mathematics"],
)
```

## Next Steps

Now that you've mastered the basics:

- **[Architecture Overview](ARCHITECTURE.md)** - Understand how paper-feed works internally
- **[Adapter Documentation](ADAPTERS.md)** - Learn about export adapters
- **[Examples](../examples/)** - Explore complete, runnable examples
- **[API Reference](#)** - Full API documentation (coming soon)

## Troubleshooting

### Issue: No Papers Fetched

**Problem:** `fetch_papers()` returns empty list.

**Solutions:**
- Check RSS URL is valid: Try opening in browser
- Check internet connection
- Try increasing `timeout` parameter: `RSSSource(url, timeout=60)`
- Check for errors in logs

### Issue: All Papers Filtered Out

**Problem:** Filter returns 0 papers.

**Solutions:**
- Relax filter criteria (fewer keywords, no exclusions)
- Check if keywords are too specific
- Try without `exclude_keywords`
- Inspect paper content to see what keywords match

### Issue: Import Errors

**Problem:** `ModuleNotFoundError: No module named 'paper_feed'`

**Solutions:**
- Ensure paper-feed is installed: `pip install -e .`
- Check you're in the correct environment
- See [Installation Guide](INSTALLATION.md) for details

Happy paper collecting!
