"""Complete workflow example: Fetch → Filter → Export.

This example demonstrates a full paper collection workflow:
1. Fetch papers from multiple RSS sources
2. Filter by keywords, categories, and date
3. Export to JSON format

Run this file directly:
    python complete_workflow.py
"""

import asyncio
import logging
from datetime import date, timedelta
from pathlib import Path

from paper_feed import RSSSource, FilterPipeline, JSONAdapter, FilterCriteria

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def fetch_papers_from_sources() -> list:
    """Step 1: Fetch papers from multiple RSS sources.

    Returns:
        List of PaperItem objects from all sources
    """
    logger.info("Step 1: Fetching papers from RSS sources")

    # Define RSS sources to fetch from
    # You can add more sources from arXiv, bioRxiv, Nature, etc.
    sources = [
        # arXiv Computer Science - Artificial Intelligence
        RSSSource("https://arxiv.org/rss/cs.AI"),

        # arXiv Computer Science - Machine Learning
        RSSSource("https://arxiv.org/rss/cs.LG"),

        # arXiv Computer Science - Computer Vision
        RSSSource("https://arxiv.org/rss/cs.CV"),
    ]

    all_papers = []

    # Fetch papers from each source
    for source in sources:
        logger.info(f"Fetching from {source.source_name}...")

        # Fetch last 100 papers from this source
        # In production, you might want to use 'since' parameter instead
        papers = await source.fetch_papers(limit=100)

        logger.info(f"  Fetched {len(papers)} papers from {source.source_name}")

        # Add to collection
        all_papers.extend(papers)

    logger.info(f"Total papers fetched: {len(all_papers)}")

    return all_papers


async def filter_papers(papers: list) -> list:
    """Step 2: Filter papers based on criteria.

    Args:
        papers: List of PaperItem objects to filter

    Returns:
        List of filtered PaperItem objects
    """
    logger.info("Step 2: Filtering papers")

    # Define filter criteria
    # You can customize these criteria based on your needs
    criteria = FilterCriteria(
        # Papers must contain these keywords (AND logic)
        keywords=[
            "machine learning",
            "deep learning",
        ],

        # Exclude papers with these keywords
        exclude_keywords=[
            "review",
            "survey",
            "tutorial",
        ],

        # Only papers from these categories (OR logic)
        categories=[
            "Computer Science",
            "Artificial Intelligence",
        ],

        # Only papers published after this date
        min_date=date.today() - timedelta(days=30),  # Last 30 days

        # Only papers with PDF links available
        has_pdf=True,
    )

    logger.info(f"Filter criteria:")
    logger.info(f"  Keywords: {criteria.keywords}")
    logger.info(f"  Exclude: {criteria.exclude_keywords}")
    logger.info(f"  Categories: {criteria.categories}")
    logger.info(f"  Min date: {criteria.min_date}")
    logger.info(f"  Has PDF: {criteria.has_pdf}")

    # Create filter pipeline
    pipeline = FilterPipeline()

    # Apply filter
    result = await pipeline.filter(papers, criteria)

    # Log results
    logger.info(f"Filter results:")
    logger.info(f"  Total papers: {result.total_count}")
    logger.info(f"  Passed filter: {result.passed_count}")
    logger.info(f"  Rejected: {result.rejected_count}")

    # Show filter statistics
    if result.filter_stats:
        logger.info(f"Filter statistics: {result.filter_stats}")

    return result.papers


async def export_papers(papers: list, output_dir: str = "output") -> dict:
    """Step 3: Export filtered papers to JSON.

    Args:
        papers: List of PaperItem objects to export
        output_dir: Directory to save output file

    Returns:
        Export result dictionary
    """
    logger.info("Step 3: Exporting papers to JSON")

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Generate output filename with timestamp
    timestamp = date.today().isoformat()
    filepath = f"{output_dir}/papers_{timestamp}.json"

    # Export to JSON
    adapter = JSONAdapter()

    # Export with metadata (includes source-specific fields)
    # Set include_metadata=False for cleaner output
    result = await adapter.export(
        papers=papers,
        filepath=filepath,
        include_metadata=True
    )

    logger.info(f"Export results:")
    logger.info(f"  Papers exported: {result['count']}")
    logger.info(f"  Filepath: {result['filepath']}")
    logger.info(f"  Success: {result['success']}")

    return result


def display_sample_papers(papers: list, count: int = 5) -> None:
    """Display a sample of papers.

    Args:
        papers: List of PaperItem objects
        count: Number of papers to display
    """
    logger.info(f"Sample of {min(count, len(papers))} papers:")

    for i, paper in enumerate(papers[:count], 1):
        print(f"\n{i}. {paper.title}")
        print(f"   Authors: {', '.join(paper.authors[:3])}")
        if len(paper.authors) > 3:
            print(f"           ... and {len(paper.authors) - 3} more authors")
        print(f"   Source: {paper.source}")
        print(f"   Date: {paper.published_date}")
        if paper.doi:
            print(f"   DOI: {paper.doi}")
        if paper.url:
            print(f"   URL: {paper.url}")
        if paper.abstract:
            # Show first 150 characters of abstract
            abstract_preview = paper.abstract[:150]
            if len(paper.abstract) > 150:
                abstract_preview += "..."
            print(f"   Abstract: {abstract_preview}")


async def main():
    """Main workflow: Fetch → Filter → Export."""
    logger.info("=" * 60)
    logger.info("Starting paper collection workflow")
    logger.info("=" * 60)

    # Step 1: Fetch papers from RSS sources
    papers = await fetch_papers_from_sources()

    if not papers:
        logger.warning("No papers fetched. Exiting.")
        return

    # Step 2: Filter papers
    filtered_papers = await filter_papers(papers)

    if not filtered_papers:
        logger.warning("No papers passed the filter. Try relaxing the criteria.")
        return

    # Step 3: Export to JSON
    result = await export_papers(filtered_papers)

    # Display sample of exported papers
    display_sample_papers(filtered_papers, count=3)

    logger.info("=" * 60)
    logger.info("Workflow completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    """Run the complete workflow."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Workflow interrupted by user")
    except Exception as e:
        logger.error(f"Workflow failed with error: {e}", exc_info=True)
        raise
