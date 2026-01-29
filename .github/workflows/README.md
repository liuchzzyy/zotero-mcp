# GitHub Actions Workflows for Zotero MCP Task#1

## Overview
Two GitHub Actions workflows for automated research paper management:

1. **RSS Ingestion**: Daily fetch from RSS feeds with AI filtering
2. **Gmail Ingestion**: Process Gmail emails with research papers
3. **Global Analysis**: Scan library for unprocessed papers and analyze them

## Files
- `.github/workflows/rss-ingestion.yml` - Daily RSS fetch workflow
- `.github/workflows/gmail-ingestion.yml` - Gmail processing workflow
- `.github/workflows/global-analysis.yml` - Library-wide scan and analysis

## Configuration
Workflows use the following environment variables from repository secrets:
- `ZOTERO_API_KEY`, `ZOTERO_LIBRARY_ID` - Zotero API access
- `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY` - AI providers
- `RSS_PROMPT` - Research interests for AI filtering
- `ZOTERO_INBOX_COLLECTION`, `ZOTERO_PROCESSED_COLLECTION` - Collection names

## Usage
- Workflows run automatically on schedule (daily for RSS, weekly for analysis)
- Can be triggered manually via GitHub Actions "Run workflow" button
- All workflows support dry-run mode for testing

## Dependencies
- Requires zotero-mcp Docker image with all services
- Uses Python environment with required packages