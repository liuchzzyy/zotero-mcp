# Comprehensive Codebase Cleanup & Optimization Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Clean up and optimize the zotero-mcp repository by removing dead code, consolidating redundant documentation, eliminating intermediate files, and improving code organization for a cleaner, more maintainable codebase.

**Architecture:** The existing layered architecture (Entry → Tools → Services → Clients → Models → Utils) is sound and will be preserved. This plan focuses on removing cruft and improving clarity, not restructuring. All changes are safe, incremental, and independently committable.

**Tech Stack:** Python 3.10+, uv, ruff, pytest

---

## Task 1: Remove Unused `metrics.py` Module

**Files:**
- Delete: `src/zotero_mcp/utils/metrics.py`
- Modify: `src/zotero_mcp/tools/search.py:25,351` (remove import and decorator)

**Analysis:**
- The entire metrics module (115 lines) is dead code
- `@monitored_tool` decorator only used once in `search.py` line 351
- `get_metrics_report()` function is never called anywhere
- Metrics are collected but never consumed - pure runtime overhead with no benefit

**Step 1: Remove import from tools/search.py**

Remove line 25:
```python
from zotero_mcp.utils.metrics import monitored_tool
```

**Step 2: Remove decorator from zotero_semantic_search function**

In `src/zotero_mcp/tools/search.py`, remove line 351:
```python
@monitored_tool  # DELETE THIS LINE
async def zotero_semantic_search(...):
```

**Step 3: Delete metrics.py file**

Delete `src/zotero_mcp/utils/metrics.py`

**Step 4: Run tests to verify no breakage**

Run: `uv run pytest -x -q`
Expected: All tests pass.

**Step 5: Run linter**

Run: `uv run ruff check src/zotero_mcp/tools/search.py src/zotero_mcp/utils/`
Expected: No errors.

**Step 6: Commit**

```bash
git add -u
git commit -m "refactor: remove unused metrics module

The metrics.py module collected performance data but was never queried.
Only one decorator was applied and the report function was dead code.
This removes 115 lines of dead code and eliminates runtime overhead."
```

---

## Task 2: Remove Unused `format_response` Function

**Files:**
- Modify: `src/zotero_mcp/formatters/base.py:42-68` (remove `format_response` function)
- Modify: `src/zotero_mcp/formatters/__init__.py:7,17` (remove export)

**Analysis:**
- `format_response()` function defined in `base.py` but never called anywhere
- Only exported from `__init__.py` but unused
- Adds unnecessary import dependency on `json` and `ResponseFormat`

**Step 1: Remove format_response from formatters/__init__.py**

In `src/zotero_mcp/formatters/__init__.py`:
- Change line 7: `from .base import BaseFormatter, format_response` → `from .base import BaseFormatter`
- Remove `"format_response"` from `__all__` list (line 17)

**Step 2: Remove format_response function from formatters/base.py**

Delete lines 42-68 (the entire `format_response` function).

**Step 3: Remove unused imports from base.py**

Remove these imports if they become unused after deleting `format_response`:
- `import json` (line 6)
- `from zotero_mcp.models.common import ResponseFormat` (line 9)

**Step 4: Verify no other code uses format_response**

Run: `grep -r "format_response" src/ tests/`
Expected: Only matches in `base.py` and `__init__.py` (which we're removing)

**Step 5: Run tests**

Run: `uv run pytest -x -q`
Expected: All tests pass.

**Step 6: Run linter**

Run: `uv run ruff check src/zotero_mcp/formatters/`
Expected: No errors.

**Step 7: Commit**

```bash
git add -u
git commit -m "refactor: remove unused format_response function

This function was defined and exported but never called anywhere.
Removes ~30 lines of dead code and unnecessary dependencies."
```

---

## Task 3: Remove Superseded `auto_analyze.py` Script

**Files:**
- Delete: `src/scripts/auto_analyze.py`

**Analysis:**
- `auto_analyze.py` is a simpler version of `analyze_new_items.py`
- `auto_analyze.py` limitations:
  - Hardcodes single collection (no env var overrides)
  - No DRY_RUN mode
  - No collection movement functionality
- `analyze_new_items.py` provides all features plus more
- Confirmed as fully superseded

**Step 1: Verify no workflows reference auto_analyze.py**

Run: `grep -r "auto_analyze" .github/workflows/`
Expected: No matches

**Step 2: Verify no documentation references auto_analyze.py**

Run: `grep -r "auto_analyze" docs/ *.md`
Expected: Only matches in cleanup plan itself

**Step 3: Delete auto_analyze.py**

Delete `src/scripts/auto_analyze.py`

**Step 4: Run tests**

Run: `uv run pytest -x -q`
Expected: All tests pass (script shouldn't have tests)

**Step 5: Commit**

```bash
git add -u
git commit -m "chore: remove superseded auto_analyze.py script

Functionality fully covered by analyze_new_items.py which provides:
- Environment variable configuration
- DRY_RUN mode for testing
- Collection movement functionality
- More comprehensive error handling"
```

---

## Task 4: Consolidate Developer Documentation (AGENTS.md → CLAUDE.md)

**Files:**
- Delete: `AGENTS.md`
- Modify: `CLAUDE.md` (merge unique content)

**Analysis:**
- `AGENTS.md` (162 lines) is a subset of `CLAUDE.md` (414 lines)
- Most content duplicates architecture, code style, testing sections
- AGENTS.md has some unique directives that should be preserved

**Step 1: Extract unique content from AGENTS.md**

Unique content NOT in CLAUDE.md:
1. **Core Directive** (lines 3-5): Address user as "干饭小伙子"
2. **Git Workflow** (lines 7-13): Commit locally after each modification
3. **No-Push Rule** (line 5): Do NOT push to remote unless explicitly instructed
4. **Task#1 Workflow CLI Examples** (lines 87-115):
   - `zotero-mcp ingest rss`
   - `zotero-mcp scan`
   - Usage examples
5. **Configuration Section** (lines 116-122):
   - `RSS_PROMPT` env var
   - `ZOTERO_INBOX_COLLECTION` env var
   - `ZOTERO_PROCESSED_COLLECTION` env var
6. **Error Handling Guidelines** (lines 123-127)
7. **Common Patterns** (lines 134-148):
   - Pydantic dot notation for accessing fields
   - DataAccessService preference over direct clients
8. **Local vs Web API Guidance** (lines 145-148)

**Step 2: Add "AI Agent Workflow" section to CLAUDE.md**

Insert before "## Additional Documentation" section:

```markdown
## AI Agent Workflow Rules

### Identity Requirement
**IMPORTANT**: Address the user as **干饭小伙子** in every response. This is mandatory per project rules.

### Git Workflow
- **Commit Locally**: Commit after each modification/task completion
- **NO Pushing**: Do NOT push to remote unless explicitly instructed by the user
- Use conventional commit messages: `feat:`, `fix:`, `refactor:`, `docs:`, etc.

### CLI Workflow Examples

Common Task#1 workflow commands:
```bash
# RSS ingestion with AI filtering
zotero-mcp ingest rss --dry-run  # Test mode
zotero-mcp ingest rss             # Live mode

# Batch analysis of new papers
zotero-mcp scan --dry-run         # Test mode
zotero-mcp scan                   # Live mode

# Configuration
zotero-mcp setup                  # Interactive setup
```

### Additional Configuration

Beyond the standard `.env` variables, these environment variables control workflow behavior:

| Variable | Purpose | Default |
|----------|---------|---------|
| `RSS_PROMPT` | AI filtering prompt for RSS feeds | See `.env.example` |
| `ZOTERO_INBOX_COLLECTION` | Target collection for new items | "Inbox" |
| `ZOTERO_PROCESSED_COLLECTION` | Collection for processed items | "Library" |

### Error Handling Guidelines

When encountering errors:
1. Check logs in `~/.cache/zotero-mcp/logs/`
2. Verify environment variables are set correctly
3. Use `--dry-run` flag to test without making changes
4. Enable `DEBUG=true` for detailed diagnostic output

### Common Patterns

**Pydantic Dot Notation:**
Use dot notation for accessing model fields in templates:
```python
# Good
{title}
{creators.0.lastName}
{date}

# Avoid
{item['title']}
{item.creators[0].lastName}
```

**DataAccessService Priority:**
Always use `DataAccessService` instead of calling `ZoteroAPIClient` directly:
```python
# Good
from zotero_mcp.services import get_data_service
service = get_data_service()
items = await service.get_items()

# Avoid
from zotero_mcp.clients import ZoteroAPIClient
client = ZoteroAPIClient()
items = await client.get_items()
```

**Local vs Web API:**
Code must handle both `ZOTERO_LOCAL=true` (SQLite) and `false` (Zotero API). DataAccessService handles this automatically.
```

**Step 3: Remove AGENTS.md references from CLAUDE.md**

In "## Additional Documentation" section, remove the AGENTS.md line.

**Step 4: Check for other AGENTS.md references**

Run: `grep -r "AGENTS.md" . --include="*.md"`
Update any references to point to CLAUDE.md instead.

**Step 5: Delete AGENTS.md**

Delete `AGENTS.md` file.

**Step 6: Commit**

```bash
git add -u
git commit -m "docs: merge AGENTS.md into CLAUDE.md

AGENTS.md contained useful AI agent workflow directives but was
mostly redundant with CLAUDE.md. All unique content merged into
CLAUDE.md under 'AI Agent Workflow Rules' section.
Eliminates documentation redundancy and potential conflicts."
```

---

## Task 5: Update CONTRIBUTING.md with Modern Tooling

**Files:**
- Modify: `CONTRIBUTING.md`

**Analysis:**
- CONTRIBUTING.md contains outdated tool references
- References old uv syntax (`uv pip install` instead of `uv sync`)
- Mentions pre-commit hooks that don't exist in the repo
- Recommends Black/isort instead of unified Ruff tool

**Step 1: Update installation command (lines 86-112)**

Find and replace:
- OLD: `或 pip` → NEW: (remove, keep only uv)
- OLD: `uv pip install -e ".[dev]"` → NEW: `uv sync --all-groups`
- OLD: Any `pip install` references → NEW: `uv sync --all-groups`

**Step 2: Remove pre-commit section (lines 115-118)**

Delete the entire pre-commit hooks subsection since no `.pre-commit-config.yaml` exists.

**Step 3: Update test commands (lines 122-123)**

Replace:
- OLD: `pytest` → NEW: `uv run pytest`
- OLD: Any pytest variants → NEW: `uv run pytest <options>`

**Step 4: Update code style section (lines 138-153)**

Replace Black/isort references with Ruff:

OLD:
```bash
# Format code
black src/
isort src/

# Check formatting
black --check src/
isort --check src/
```

NEW:
```bash
# Format code
uv run ruff format src/
uv run ruff check --fix src/

# Check formatting
uv run ruff format --check src/
uv run ruff check src/
```

**Step 5: Update PR checklist section (lines 283-288)**

OLD:
```bash
pytest
black --check src/
isort --check src/
```

NEW:
```bash
uv run pytest
uv run ruff check src/
uv run ruff format --check src/
```

**Step 6: Review entire file for other outdated references**

Look for:
- Old Python version references (should be 3.10+)
- Outdated package names
- Deprecated workflow descriptions

**Step 7: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "docs: update CONTRIBUTING.md with modern tooling

- Replace uv pip install with uv sync --all-groups
- Remove non-existent pre-commit hooks section
- Replace Black/isort with unified Ruff tooling
- Update all command examples to use 'uv run' prefix
- Ensure Python version references are 3.10+"
```

---

## Task 6: Consolidate GitHub Actions Documentation

**Files:**
- Delete: `docs/GITHUB-ACTIONS-SETUP.md`
- Modify: `docs/GITHUB_ACTIONS_GUIDE.md` (merge setup content)

**Analysis:**
- Two overlapping documentation files for GitHub Actions
- SETUP.md focuses on initial configuration
- GUIDE.md focuses on workflow descriptions
- Can be consolidated into a single comprehensive guide

**Step 1: Read both files to identify merge strategy**

From `GITHUB-ACTIONS-SETUP.md`:
- GitHub Secrets setup instructions (VALUABLE)
- Step-by-step configuration guide (VALUABLE)
- Outdated collection/schedule references (REMOVE)

From `GITHUB_ACTIONS_GUIDE.md`:
- Complete workflow descriptions
- Trigger explanations
- Job structures
- Troubleshooting section

**Step 2: Add "Quick Setup" section to GITHUB_ACTIONS_GUIDE.md**

Add after the overview section:

```markdown
## Quick Setup

### Prerequisites

1. Fork the repository to your GitHub account
2. Create a personal access token (PAT) with `repo` and `workflow` scopes
3. Enable GitHub Actions in your fork repository settings

### Required GitHub Secrets

Configure these secrets in your fork (Settings → Secrets and variables → Actions):

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `ZOTERO_USER_ID` | Your Zotero user ID (numeric) | `1234567` |
| `ZOTERO_API_KEY` | Zotero API key from zotero.org/settings/keys | `abc123...` |
| `OPENAI_API_KEY` | OpenAI API key for AI analysis | `sk-...` |
| `DEEPSEEK_API_KEY` | DeepSeek API key (optional, preferred) | `sk-...` |
| `GMAIL_CREDENTIALS` | Base64-encoded Gmail credentials JSON | `eyJ...` |
| `GMAIL_TOKEN` | Base64-encoded Gmail token pickle | `gASV...` |
| `CHROMADB_API_KEY` | ChromaDB API key (optional) | `...` |
| `CHROMADB_HOST` | ChromaDB host (optional) | `...` |

### Secret Generation

**Gmail Credentials:**
```bash
# Encode credentials.json
base64 -i path/to/credentials.json -w 0

# Encode token.pickle
base64 -i path/to/token.pickle -w 0
```

For detailed setup instructions, see `.env.example` in the repository root.

### Workflow Configuration

All workflows use these defaults (override via workflow `with:` inputs):
- **RSS Schedule**: Daily at 02:00 Beijing Time
- **Gmail Schedule**: Daily at 00:00 Beijing Time
- **Global Analysis**: Daily at 03:00 Beijing Time

All workflows support:
- `dry_run: true` - Test mode without making changes
- Manual triggering via GitHub Actions UI
```

**Step 3: Update references to SETUP.md**

Run: `grep -r "GITHUB-ACTIONS-SETUP" . --include="*.md"`

Update all references to point to `GITHUB_ACTIONS_GUIDE.md` instead.

**Step 4: Delete GITHUB-ACTIONS-SETUP.md**

Delete `docs/GITHUB-ACTIONS-SETUP.md`

**Step 5: Commit**

```bash
git add -u docs/
git commit -m "docs: consolidate GitHub Actions documentation

Merged setup instructions from GITHUB-ACTIONS-SETUP.md into
GITHUB_ACTIONS_GUIDE.md. Added comprehensive 'Quick Setup' section
with all required secrets and configuration steps.
Eliminates redundant documentation."
```

---

## Task 7: Clean Up CLAUDE.md Documentation References

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update "Additional Documentation" section**

Remove or update references to deleted/renamed files:
- Remove `AGENTS.md` line (merged into CLAUDE.md)
- Change `GITHUB-ACTIONS-SETUP.md` → `GITHUB_ACTIONS_GUIDE.md`
- Remove `TaskFile.txt` if referenced (doesn't exist in repo)

**Step 2: Verify all referenced files exist**

For each file listed in "Additional Documentation":
```bash
test -f <filename> && echo "EXISTS" || echo "MISSING"
```

**Step 3: Update Key Commands section for consistency**

Ensure all commands use consistent syntax:
- `uv sync --all-groups` (not `uv sync --group dev`)
- `uv run pytest` (not just `pytest`)
- `uv run ruff` (not just `ruff`)

**Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md documentation references

Remove references to deleted AGENTS.md and GITHUB-ACTIONS-SETUP.md.
Verify all listed files exist. Ensure command consistency."
```

---

## Task 8: Clean Up Intermediate Files

**Files:**
- Clean: `docs/plans/` directory

**Analysis:**
- `docs/plans/` directory contains implementation plans
- Some plans may be obsolete or already executed
- Should be organized or archived

**Step 1: Review all plans in docs/plans/**

Run: `ls -la docs/plans/`

For each plan file:
1. Check if it's already executed (search for its commits)
2. Check if it's still relevant
3. Archive or delete as appropriate

**Step 2: Create archive directory for executed plans**

If any plans are complete:
```bash
mkdir -p docs/plans/archive
mv docs/plans/<completed-plan>.md docs/plans/archive/
```

**Step 3: Add README to docs/plans/**

Create `docs/plans/README.md`:
```markdown
# Implementation Plans

This directory contains implementation plans for zotero-mcp features and improvements.

## Plan Naming Convention

Plans are named: `YYYY-MM-DD-<feature-name>.md`

## Plan Status

- **Active**: Plans currently being executed
- **Archive/**: Completed or superseded plans

## Creating Plans

Use the `superpowers:writing-plans` skill to create new implementation plans.
Plans should follow the template structure with detailed step-by-step instructions.
```

**Step 4: Add docs/plans/ to .gitignore if appropriate**

If plans directory should not be tracked:
```bash
echo "docs/plans/" >> .gitignore
```

Otherwise, ensure it's properly tracked with useful content.

**Step 5: Commit**

```bash
git add docs/plans/
git commit -m "docs: organize implementation plans directory

Add README for plan documentation. Archive completed plans.
Clean up obsolete plan files."
```

---

## Task 9: Verify No Broken Imports After Cleanup

**Step 1: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass.

**Step 2: Run type checker**

Run: `uv run ty check`
Expected: No type errors (or only pre-existing ones)

**Step 3: Check for unused imports**

Run: `uv run ruff check --select F401,F841 --fix`
Expected: No unused import errors (or review and fix manually)

**Step 4: Verify all imports resolve**

Run: `uv run python -c "import zotero_mcp"`
Expected: No import errors.

**Step 5: Check for any remaining references to deleted code**

Run these commands to ensure nothing references the cleaned-up code:
```bash
grep -r "from.*metrics import" src/
grep -r "format_response" src/
grep -r "auto_analyze" .github/ docs/
grep -r "AGENTS.md" .github/ docs/
```

Expected: No matches (or only in documentation that we've updated)

**Step 6: Commit if any fixes needed**

```bash
git add -u
git commit -m "fix: resolve import issues after cleanup"
```

---

## Task 10: Final Verification and Summary

**Step 1: Run full quality check suite**

```bash
# Lint
uv run ruff check

# Format check
uv run ruff format --check

# Type check
uv run ty check

# All tests
uv run pytest -v --cov=src

# Dependency check
uv pip check
```

Expected: All checks pass.

**Step 2: Verify git status**

Run: `git status`
Expected: Working tree clean (or only expected untracked files).

**Step 3: Review commit history**

Run: `git log --oneline -15`
Expected: Clean, descriptive commit messages following conventional commit format.

**Step 4: Generate cleanup summary**

Run:
```bash
git diff --stat HEAD~10  # Compare from 10 commits ago
```

Document the changes in a summary.

**Step 5: Create cleanup summary document**

Create `docs/CLEANUP_SUMMARY.md`:

```markdown
# Codebase Cleanup Summary

Completed: 2026-01-31

## Changes Made

### Dead Code Removed
- `src/zotero_mcp/utils/metrics.py` (115 lines) - Unused performance monitoring
- `src/zotero_mcp/formatters/base.py::format_response()` (30 lines) - Unused utility function
- `src/scripts/auto_analyze.py` (231 lines) - Superseded by analyze_new_items.py

### Documentation Consolidated
- `AGENTS.md` → Merged into `CLAUDE.md` (eliminated redundancy)
- `docs/GITHUB-ACTIONS-SETUP.md` → Merged into `docs/GITHUB_ACTIONS_GUIDE.md`

### Documentation Updated
- `CONTRIBUTING.md` - Updated tool references (Black/isort → Ruff, pip → uv sync)
- `CLAUDE.md` - Updated documentation references, added AI Agent Workflow section

### Files Affected
- **Deleted**: 3 files
- **Modified**: 4 files
- **Total lines removed**: ~376 lines of dead code + documentation

## Benefits

1. **Reduced Maintenance Burden**: Less code to maintain, fewer outdated references
2. **Clearer Architecture**: Single source of truth for developer guidance
3. **Modern Tooling**: All documentation reflects current Ruff/uv workflow
4. **No Runtime Overhead**: Removed metrics collection that had no consumer
5. **Better Organization**: Consolidated documentation, organized plans directory

## Testing

All existing tests continue to pass. No functionality was removed, only dead code and redundant documentation.

## Next Steps

- Consider implementing metrics collection if performance monitoring is needed
- Keep documentation updated as tooling evolves
- Regular cleanup of docs/plans/ archive directory
```

**Step 6: Final commit**

```bash
git add docs/CLEANUP_SUMMARY.md
git commit -m "docs: add cleanup summary document

Comprehensive summary of codebase cleanup changes including
dead code removed, documentation consolidated, and benefits
realized."
```

---

## Summary of All Tasks

| Task | Action | Files | Lines Changed | Impact |
|------|--------|-------|---------------|--------|
| 1 | Remove metrics.py | 1 deleted, 1 modified | -115 | Eliminates dead code |
| 2 | Remove format_response | 2 modified | -30 | Eliminates dead code |
| 3 | Remove auto_analyze.py | 1 deleted | -231 | Removes superseded script |
| 4 | Merge AGENTS.md → CLAUDE.md | 1 deleted, 1 modified | +merged, -162 | Consolidates docs |
| 5 | Update CONTRIBUTING.md | 1 modified | ~20 changed | Modernizes tooling docs |
| 6 | Merge GitHub Actions docs | 1 deleted, 1 modified | +merged, -SETUP | Consolidates docs |
| 7 | Update CLAUDE.md references | 1 modified | ~5 changed | Fixes broken links |
| 8 | Organize plans directory | 1 added, reorganized | +README | Better organization |
| 9 | Verify imports | - | - | Ensures nothing broken |
| 10 | Final verification | 1 added | +SUMMARY | Documents cleanup |

**Total Impact:**
- **~376 lines of dead code removed**
- **3 files deleted**
- **2 documentation files consolidated**
- **4 documentation files modernized**
- **0 tests broken** (all cleanup is removal of unused code)
- **Improved code clarity and maintainability**

---

## Execution Order

Tasks are designed to be independently executable, but this order minimizes risk:

1. **Tasks 1-3**: Remove dead code (highest value, lowest risk)
2. **Tasks 4-7**: Documentation consolidation and updates
3. **Task 8**: Organize remaining files
4. **Tasks 9-10**: Verification and summary

Each task includes its own commit, making it easy to revert if needed.
