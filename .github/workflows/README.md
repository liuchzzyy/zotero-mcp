# GitHub Actions Workflows

## Overview

Four GitHub Actions workflows for CI/CD and automated research paper management:

1. **CI/CD** (`ci.yml`) - Linting, type checking, tests, security audit, build verification
2. **RSS Ingestion** (`rss-ingestion.yml`) - Daily RSS feed fetch with AI filtering
3. **Gmail Ingestion** (`gmail-ingestion.yml`) - Daily Gmail processing for research papers
4. **Global Analysis** (`global-analysis.yml`) - Daily library-wide scan and AI analysis

## Schedule

| Workflow | Schedule (Beijing Time) | UTC |
|----------|------------------------|-----|
| Gmail Ingestion | 00:00 daily | 16:00 UTC |
| RSS Ingestion | 02:00 daily | 18:00 UTC |
| Global Analysis | 03:00 daily | 19:00 UTC |
| CI/CD | On push/PR to main/develop | - |

## Configuration

Workflows use the following repository secrets:

- `ZOTERO_API_KEY`, `ZOTERO_LIBRARY_ID` - Zotero API access
- `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY` - AI providers
- `RSS_PROMPT` - Research interests for AI filtering
- `GMAIL_TOKEN_JSON` - Gmail OAuth token
- `GMAIL_SENDER_FILTER` - Gmail sender filter

## Features

- All workflows support **manual trigger** via `workflow_dispatch`
- All workflows support **dry-run mode** for testing
- **Concurrency control** prevents duplicate runs
- **Log archiving** with 3-day retention
- **GitHub Step Summary** for quick run overview
- Uses `astral-sh/setup-uv` for fast dependency installation with caching

## Dependencies

- Python 3.11
- uv package manager
- zotero-mcp package with all dependencies
