# GitHub Actions Guide

This document explains how to use and configure GitHub Actions for automated testing and scheduled tasks.

## Workflows

### 1. CI/CD Pipeline (`ci.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

**Jobs:**
- **Lint and Type Check** - Runs Ruff linter, formatter check, and type checker
- **Unit Tests** - Runs pytest with coverage reporting
- **Security Audit** - Checks for outdated dependencies
- **Build Test** - Verifies the package can be built

**Status:** ✅ Active and working (all jobs passing)

### 2. RSS Ingestion (`rss-ingestion.yml`)

**Triggers:**
- **Scheduled:** Daily at 00:00 Beijing Time (16:00 UTC)
- **Manual:** Via `workflow_dispatch` in GitHub Actions tab

**Purpose:** Automatically fetches RSS feeds, filters papers using AI, and imports them to Zotero.

**Manual Testing:**
```bash
gh workflow run rss-ingestion.yml
```

### 3. Gmail Ingestion (`gmail-ingestion.yml`)

**Triggers:**
- **Scheduled:** Daily at 00:00 Beijing Time (16:00 UTC)
- **Manual:** Via `workflow_dispatch`

**Purpose:** Processes Gmail emails, extracts paper information, and imports to Zotero.

**Manual Testing:**
```bash
gh workflow run gmail-ingestion.yml
```

### 4. Global Analysis (`global-analysis.yml`)

**Triggers:**
- **Scheduled:** Daily at 01:00 Beijing Time (17:00 UTC)
- **Manual:** Via `workflow_dispatch`

**Purpose:** Scans Zotero library for items with PDFs and notes, performs batch AI analysis.

**Manual Testing:**
```bash
gh workflow run global-analysis.yml
```

## Required Secrets

Configure these in GitHub repository settings (`Settings` → `Secrets and variables` → `Actions`):

| Secret Name | Description | Example |
|--------------|-------------|---------|
| `ZOTERO_LIBRARY_ID` | Zotero library ID | `123456` |
| `ZOTERO_API_KEY` | Zotero API key | `zotero_api_key_from_zotero_org` |
| `RSS_PROMPT` | AI filtering prompt | Path to prompt file or inline prompt |
| `DEEPSEEK_API_KEY` | DeepSeek API key for keyword extraction | `sk-...` |
| `GMAIL_CREDS` | Gmail OAuth credentials (JSON) | `{"client_id": "...", "client_secret": "..."}` |
| `CLAUDE_API_KEY` | Claude API key (optional) | `sk-ant-...` |

## Testing Workflows Manually

### Using GitHub CLI

1. **List all workflows:**
   ```bash
   gh workflow list
   ```

2. **Trigger a workflow:**
   ```bash
   # RSS ingestion with default parameters
   gh workflow run rss-ingestion.yml

   # Gmail ingestion with custom collection
   gh workflow run gmail-ingestion.yml -f collection_name="My Papers"

   # Global analysis with custom scan limit
   gh workflow run global-analysis.yml -f scan_limit=100
   ```

3. **View workflow run status:**
   ```bash
   gh run list --limit 5
   gh run view <run-id>
   ```

### Using GitHub Web UI

1. Go to repository on GitHub
2. Click "Actions" tab
3. Select workflow from left sidebar
4. Click "Run workflow" button
5. Configure inputs if needed
6. Click "Run workflow" green button

## Troubleshooting

### Workflow Failures

**Check logs:**
```bash
gh run view <run-id>
```

**Common Issues:**

1. **Missing secrets** - Ensure all required secrets are configured in GitHub repository settings
2. **API key expiration** - Update expired API keys in secrets
3. **Zotero library not accessible** - Ensure Zotero is running with local API enabled
4. **Rate limiting** - DeepSeek/OpenAI API rate limits may affect AI filtering

### Monitoring Scheduled Workflows

**View recent runs:**
```bash
gh run list --workflow="Global Analysis" --limit 10
```

**Check scheduled workflow status:**
```bash
gh workflow view global-analysis.yml
```

## Updating Workflows

After code refactoring, all workflows have been updated to use:

- **actions/checkout@v4** - Latest stable checkout action
- **actions/setup-python@v5** - Latest Python setup action
- **astral-sh/setup-uv@v4** - Fast Python package manager setup
- **codecov/codecov-action@v4** - Code coverage reporting
- **actions/upload-artifact@v4** - Artifact upload for logs

All workflows use **Python 3.10** (minimum required version).

## Best Practices

1. **Test workflows manually** before relying on schedules
2. **Monitor workflow logs** for failures or issues
3. **Keep API keys secure** - never commit them to repository
4. **Use dry-run mode** for testing ingestion workflows
5. **Review workflow summaries** in GitHub Actions tab

## Recent Changes

After the architecture refactoring (2025-02-01):

- ✅ Updated all workflows to use Python 3.10
- ✅ Verified CI/CD pipeline with refactored code structure
- ✅ All workflows compatible with new domain-driven architecture
- ✅ Test suite passing (64/64) in CI environment

## Schedules Summary

| Workflow | Schedule (Beijing) | Purpose |
|----------|-------------------|---------|
| RSS Ingestion | Daily 00:00 | Auto-import papers from RSS feeds |
| Gmail Ingestion | Daily 00:00 | Auto-import papers from Gmail |
| Global Analysis | Daily 01:00 | Batch AI analysis of PDFs with notes |
| CI/CD | On push/PR | Code quality checks and testing |
