# Installation Guide

This guide covers installing paper-feed for local development and usage. PyPI publishing is not yet available - use local editable installation.

## Prerequisites

### Required

- **Python**: 3.10 or higher
- **pip**: Python package installer (included with Python)

### Check Python Version

```bash
python --version
# or
python3 --version
```

You should see Python 3.10.x or higher.

### Check pip

```bash
pip --version
# or
pip3 --version
```

## Installation Steps

### Step 1: Navigate to paper-feed Directory

```bash
cd external/paper-feed
```

### Step 2: Install in Editable Mode

**Basic installation (core dependencies only):**

```bash
pip install -e .
```

This installs paper-feed in "editable" mode, meaning changes to the source code are immediately reflected without reinstalling.

### Step 3: Verify Installation

```bash
python -c "import paper_feed; print(paper_feed.__version__)"
```

You should see: `1.0.0`

## Optional Dependencies

### Gmail Support

For fetching papers from Gmail alerts (Google Scholar, journal TOCs):

```bash
pip install -e ".[gmail]"
```

**Extra dependencies:**
- `ezgmail` - Gmail API client

### LLM-Based Filtering

For AI-powered semantic filtering (planned feature):

```bash
pip install -e ".[llm]"
```

**Extra dependencies:**
- `openai` - OpenAI API client

### Development Tools

For running tests and linting:

```bash
pip install -e ".[dev]"
```

**Extra dependencies:**
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `ruff` - Linter and formatter

### Install Everything

Install all optional dependencies at once:

```bash
pip install -e ".[all]"
```

**Note:** This excludes Zotero support, which is planned for Phase 2.

## Verification

### Test Basic Import

```python
from paper_feed import (
    PaperItem,
    FilterCriteria,
    FilterResult,
    RSSSource,
    FilterPipeline,
    JSONAdapter,
)
print("✅ All imports successful")
```

### Test RSS Fetch

Create a test script `test_install.py`:

```python
import asyncio
from paper_feed import RSSSource

async def main():
    source = RSSSource("https://arxiv.org/rss/cs.AI")
    papers = await source.fetch_papers(limit=5)
    print(f"✅ Successfully fetched {len(papers)} papers")
    for paper in papers[:2]:
        print(f"  - {paper.title}")

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
python test_install.py
```

Expected output:
```
✅ Successfully fetched 5 papers
  - [Paper title 1]
  - [Paper title 2]
```

### Test Filter Pipeline

```python
import asyncio
from paper_feed import RSSSource, FilterPipeline, FilterCriteria

async def main():
    source = RSSSource("https://arxiv.org/rss/cs.AI")
    papers = await source.fetch_papers(limit=50)

    criteria = FilterCriteria(keywords=["learning"])
    result = await FilterPipeline().filter(papers, criteria)

    print(f"✅ Filtered {result.total_count} papers to {result.passed_count}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Test JSON Export

```python
import asyncio
from paper_feed import RSSSource, FilterPipeline, JSONAdapter, FilterCriteria

async def main():
    source = RSSSource("https://arxiv.org/rss/cs.AI")
    papers = await source.fetch_papers(limit=10)

    await JSONAdapter().export(papers, "test_output.json")
    print("✅ Successfully exported to test_output.json")

if __name__ == "__main__":
    asyncio.run(main())
```

Check that `test_output.json` was created with valid JSON.

## Troubleshooting

### Issue: ModuleNotFoundError

**Error:**
```
ModuleNotFoundError: No module named 'paper_feed'
```

**Solution:**
- Make sure you're in the correct directory: `cd external/paper-feed`
- Reinstall with: `pip install -e .`
- Check Python path: `python -c "import sys; print(sys.path)"`

### Issue: Permission Denied

**Error:**
```
PermissionError: [Errno 13] Permission denied
```

**Solution:**
- Use user-specific installation: `pip install --user -e .`
- Or use a virtual environment (recommended)

### Issue: Python Version Too Old

**Error:**
```
ERROR: Package 'paper-feed' requires a different Python: 3.9.x not in '>=3.10'
```

**Solution:**
- Install Python 3.10 or higher from [python.org](https://www.python.org/downloads/)
- Use pyenv or conda to manage Python versions

### Issue: pip Not Found

**Error:**
```
bash: pip: command not found
```

**Solution:**
- On Ubuntu/Debian: `sudo apt-get install python3-pip`
- On macOS: `brew install python`
- On Windows: Reinstall Python with "pip" checked

### Issue: SSL Certificate Errors

**Error:**
```
SSLError: [SSL: CERTIFICATE_VERIFY_FAILED]
```

**Solution:**
- Update certificates: `pip install --upgrade certifi`
- Or install from trusted sources: `pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -e .`

## Virtual Environment Setup (Recommended)

Using a virtual environment keeps paper-feed dependencies isolated from your system Python.

### Create Virtual Environment

```bash
# Navigate to paper-feed directory
cd external/paper-feed

# Create virtual environment
python -m venv .venv
```

### Activate Virtual Environment

**On Linux/macOS:**
```bash
source .venv/bin/activate
```

**On Windows (Command Prompt):**
```bash
.venv\Scripts\activate
```

**On Windows (PowerShell):**
```bash
.venv\Scripts\Activate.ps1
```

### Install in Virtual Environment

```bash
pip install -e .
```

### Deactivate Virtual Environment

```bash
deactivate
```

## Development Setup

For contributors or those wanting to run tests:

```bash
# Install with development tools
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=src/paper_feed

# Lint code
ruff check

# Auto-fix lint issues
ruff check --fix

# Format code
ruff format
```

## Uninstallation

To remove paper-feed:

```bash
pip uninstall paper-feed
```

If using a virtual environment, you can also simply delete the environment directory:

```bash
deactivate  # If activated
rm -rf .venv
```

## Next Steps

After installation, check out these resources:

- **[Quick Start Tutorial](QUICKSTART.md)** - Learn how to fetch, filter, and export papers
- **[Architecture Overview](ARCHITECTURE.md)** - Understand the module structure
- **[Adapter Documentation](ADAPTERS.md)** - Learn about export adapters
- **[Examples](../examples/)** - Run complete, working examples

## Getting Help

If you encounter issues not covered here:

1. Check the main project documentation
2. Review example code in `examples/`
3. Open an issue on the project repository
