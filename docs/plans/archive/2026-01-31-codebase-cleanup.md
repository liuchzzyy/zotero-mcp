# Codebase Cleanup & Simplification Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Clean up the zotero-mcp repository by removing dead code, consolidating redundant files, updating outdated documentation, and improving project organization.

**Architecture:** The existing layered architecture (Entry → Tools → Services → Clients → Models → Utils) is sound and will be preserved. This plan focuses on removing cruft, not restructuring. Changes are safe, incremental, and independently committable.

**Tech Stack:** Python 3.10+, uv, ruff, pytest

---

## Task 1: Remove Dead `metrics.py` Module

**Files:**
- Delete: `src/zotero_mcp/utils/metrics.py`
- Modify: `src/zotero_mcp/tools/search.py:25,351` (remove import and decorator)
- Modify: `src/zotero_mcp/utils/__init__.py` (remove metrics export if present)

**Step 1: Check if metrics is exported from utils/__init__.py**

Run: `ruff check src/zotero_mcp/utils/metrics.py` — confirm no external consumers.

**Step 2: Remove `@monitored_tool` decorator and import from `tools/search.py`**

In `src/zotero_mcp/tools/search.py`:
- Remove line 25: `from zotero_mcp.utils.metrics import monitored_tool`
- Remove line 351: `@monitored_tool` decorator from `zotero_semantic_search()`

**Step 3: Delete `src/zotero_mcp/utils/metrics.py`**

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
Only one decorator was applied and the report function was dead code."
```

---

## Task 2: Remove Dead `format_response` Function

**Files:**
- Modify: `src/zotero_mcp/formatters/base.py:42-68` (remove `format_response` function)
- Modify: `src/zotero_mcp/formatters/__init__.py:7,17` (remove export)

**Step 1: Remove `format_response` from `formatters/__init__.py`**

In `src/zotero_mcp/formatters/__init__.py`:
- Line 7: Change `from .base import BaseFormatter, format_response` → `from .base import BaseFormatter`
- Remove `"format_response"` from `__all__` list

**Step 2: Remove `format_response` function from `formatters/base.py`**

Delete lines 42-68 (the entire `format_response` function) and the unused `import json` and `ResponseFormat` import if they become unused.

**Step 3: Run tests**

Run: `uv run pytest -x -q`
Expected: All tests pass.

**Step 4: Run linter**

Run: `uv run ruff check src/zotero_mcp/formatters/`
Expected: No errors.

**Step 5: Commit**

```bash
git add -u
git commit -m "refactor: remove unused format_response function

This function was defined and exported but never called anywhere."
```

---

## Task 3: Remove Superseded `auto_analyze.py` Script

**Files:**
- Delete: `src/scripts/auto_analyze.py`

**Step 1: Verify `analyze_new_items.py` covers all functionality**

`auto_analyze.py` hardcodes a single collection and has no DRY_RUN, no env var overrides, no collection movement. `analyze_new_items.py` covers all these scenarios plus more. Confirmed superseded.

**Step 2: Check if any workflow references `auto_analyze.py`**

Run: Search all `.yml` files in `.github/workflows/` for `auto_analyze`.

**Step 3: Delete `src/scripts/auto_analyze.py`**

**Step 4: Commit**

```bash
git add -u
git commit -m "chore: remove superseded auto_analyze.py script

Functionality fully covered by analyze_new_items.py with env var
support, DRY_RUN mode, and collection movement."
```

---

## Task 4: Merge AGENTS.md into CLAUDE.md and Delete

**Files:**
- Delete: `AGENTS.md`
- Modify: `CLAUDE.md` (ensure all unique AGENTS.md content is present)

**Step 1: Identify unique content in AGENTS.md not in CLAUDE.md**

After thorough comparison, the unique content in AGENTS.md that is NOT in CLAUDE.md:
1. "CORE DIRECTIVE" about committing locally after each modification (lines 3-5)
2. "Workflow Mandatory Requirement" about git add/commit after each task (lines 7-13)
3. "Do NOT push to remote unless explicitly instructed" (line 5)
4. Task#1 Workflow CLI examples (lines 87-115) — `zotero-mcp ingest rss`, `zotero-mcp scan` commands
5. Configuration section about `RSS_PROMPT`, `ZOTERO_INBOX_COLLECTION`, `ZOTERO_PROCESSED_COLLECTION` env vars (lines 116-122)
6. Error Handling guideline (lines 123-127)
7. Common Patterns: Pydantic dot notation, DataAccessService preference (lines 134-148)
8. Local vs Web API guidance (lines 145-148)

Everything else (Quick Start, Architecture, Code Style, Naming, Async, Testing, Agent Instructions) is already covered in CLAUDE.md.

**Step 2: Add unique AGENTS.md content to CLAUDE.md**

Add a new section `## Agent Workflow Rules` at the end of CLAUDE.md (before `## Additional Documentation`) containing:
- Commit locally after each modification (do NOT push unless instructed)
- Task#1 workflow CLI examples
- New env vars (RSS_PROMPT, ZOTERO_INBOX_COLLECTION, ZOTERO_PROCESSED_COLLECTION)
- Error handling guidelines
- Pydantic dot notation pattern
- Local vs Web API guidance

**Step 3: Delete `AGENTS.md`**

**Step 4: Update any references to AGENTS.md**

Search the codebase for references to `AGENTS.md` and update them to point to `CLAUDE.md`:
- `CLAUDE.md` itself references `AGENTS.md` in the Additional Documentation section — remove that line
- `README.md` — check for references

**Step 5: Commit**

```bash
git add -u
git commit -m "docs: merge AGENTS.md into CLAUDE.md

AGENTS.md was a subset of CLAUDE.md with some unique directives.
All unique content merged into CLAUDE.md to eliminate redundancy
and potential conflicts."
```

---

## Task 5: Update CONTRIBUTING.md with Current Tooling

**Files:**
- Modify: `CONTRIBUTING.md`

**Step 1: Replace all Black/isort references with Ruff**

Changes needed:
- Line 86: Remove "或 pip" — keep only uv
- Lines 108-112: Replace `uv pip install -e ".[dev]"` and `pip install` with `uv sync --all-groups`
- Lines 115-118: Remove pre-commit section (no pre-commit config exists)
- Line 122-123: Update test commands to use `uv run pytest`
- Lines 138-139: Replace `Black` and `isort` with `Ruff`
- Lines 145-153: Replace `black src/` and `isort src/` with:
  ```bash
  uv run ruff format src/
  uv run ruff check --fix src/
  ```
- Lines 283-288: Replace `pytest`, `black --check`, `isort --check` with:
  ```bash
  uv run pytest
  uv run ruff check src/
  uv run ruff format --check src/
  ```

**Step 2: Run a quick review of the updated file**

Skim through for any other outdated references.

**Step 3: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "docs: update CONTRIBUTING.md tooling references

Replace Black/isort with Ruff, pip with uv sync, remove
non-existent pre-commit references."
```

---

## Task 6: Consolidate GitHub Actions Documentation

**Files:**
- Delete: `docs/GITHUB-ACTIONS-SETUP.md`
- Modify: `docs/GITHUB_ACTIONS_GUIDE.md` (add setup content)

**Step 1: Read both files fully to identify what to merge**

`GITHUB-ACTIONS-SETUP.md` has:
- Setup instructions for GitHub Secrets (valuable)
- Step-by-step secret configuration (valuable)
- References to old collection names and schedules (outdated)

`GITHUB_ACTIONS_GUIDE.md` already covers:
- All workflow descriptions
- Triggers, inputs, job descriptions
- Troubleshooting

**Step 2: Add a "Quick Setup" section to `GITHUB_ACTIONS_GUIDE.md`**

Add at the top (after Overview) a concise setup section with:
- GitHub Secrets configuration table (from SETUP.md)
- Link to `.env.example` for all variables
- Remove outdated collection/schedule references

**Step 3: Delete `docs/GITHUB-ACTIONS-SETUP.md`**

**Step 4: Update any references**

Check `CLAUDE.md`, `README.md` for links to `GITHUB-ACTIONS-SETUP.md` and update to `GITHUB_ACTIONS_GUIDE.md`.

**Step 5: Commit**

```bash
git add -u
git commit -m "docs: consolidate GitHub Actions docs into single guide

Merged setup instructions from GITHUB-ACTIONS-SETUP.md into
GITHUB_ACTIONS_GUIDE.md. Removed outdated collection references."
```

---

## Task 7: Clean Up CLAUDE.md References

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update Additional Documentation section**

Remove references to deleted files:
- Remove `AGENTS.md` line
- Update `GITHUB-ACTIONS-SETUP.md` → `GITHUB_ACTIONS_GUIDE.md`
- Remove `TaskFile.txt` if referenced (it doesn't exist)

**Step 2: Update `uv sync --group dev` to `uv sync --all-groups`**

CLAUDE.md line in Key Commands section already has both. Ensure consistency.

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md references after cleanup

Remove references to deleted AGENTS.md and GITHUB-ACTIONS-SETUP.md."
```

---

## Task 8: Final Verification

**Step 1: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass.

**Step 2: Run linter on entire codebase**

Run: `uv run ruff check`
Expected: No errors.

**Step 3: Run formatter check**

Run: `uv run ruff format --check`
Expected: No formatting issues.

**Step 4: Verify git status is clean**

Run: `git status`
Expected: Working tree clean.

**Step 5: Review all commits**

Run: `git log --oneline -10`
Expected: Clean commit history with descriptive messages.

---

## Summary

| Task | Action | Files Affected | Impact |
|------|--------|---------------|--------|
| 1 | Remove dead metrics module | 2 modified, 1 deleted | Removes 115 lines of dead code |
| 2 | Remove dead format_response | 2 modified | Removes ~30 lines of dead code |
| 3 | Remove superseded script | 1 deleted | Removes 231 lines of redundant script |
| 4 | Merge AGENTS.md into CLAUDE.md | 1 deleted, 1 modified | Eliminates redundant doc |
| 5 | Update CONTRIBUTING.md tooling | 1 modified | Fixes outdated tool references |
| 6 | Consolidate GitHub Actions docs | 1 deleted, 1 modified | Eliminates redundant doc |
| 7 | Clean up CLAUDE.md references | 1 modified | Fixes broken references |
| 8 | Final verification | None | Confirms everything works |

**Total cleanup:** ~376 lines of dead code removed, 3 files deleted, 2 redundant docs consolidated, outdated references fixed.
