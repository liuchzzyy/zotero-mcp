# Dependency Management Guide

This document explains the dependency management strategy for Zotero MCP.

## Overview

Zotero MCP uses [uv](https://github.com/astral-sh/uv) for fast and reliable Python package management. Dependencies are organized into three categories:

1. **Core Dependencies** - Required for runtime functionality
2. **Development Dependencies** - Only needed for development and testing
3. **Optional Dependencies** - Not required but provide additional functionality

## Dependency Categories

### Core Dependencies

These are installed automatically when you install the package:

```bash
pip install zotero-mcp
# or
uv pip install zotero-mcp
```

Core dependencies are defined in `pyproject.toml` under `dependencies`.

#### Current Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| fastmcp | >=2.14.0 | FastMCP framework for building MCP servers |
| mcp | >=1.2.0 | Model Context Protocol SDK |
| pyzotero | >=1.5.0 | Zotero API client library |
| openai | >=1.0.0 | OpenAI API client (for GPT models) |
| google-generativeai | >=0.3.0 | Google Gemini API client |
| beautifulsoup4 | >=4.14.3 | HTML/XML parsing |
| feedparser | >=6.0.12 | RSS/Atom feed parsing |
| pydantic | >=2.0.0 | Data validation and settings |
| chromadb | >=0.4.0 | Vector database for semantic search |
| google-api-python-client | >=2.100.0 | Google API client for Gmail |
| google-auth-oauthlib | >=1.2.0 | OAuth flow for Gmail |
| httpx | >=0.24.0 | Async HTTP client (Crossref, OpenAlex) |
| requests | >=2.28.0 | Sync HTTP client (fallback) |
| python-dotenv | >=1.0.0 | Load environment variables from .env |
| pyyaml | >=6.0.3 | Parse YAML configuration files |
| markitdown | >=0.0.1 | PDF to Markdown conversion |

### Development Dependencies

These are only needed for development and testing:

```bash
uv sync --group dev
# or
uv sync --all  # Install all dev groups
```

Development dependencies are defined in `pyproject.toml` under `[dependency-groups.dev]`.

#### Current Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=7.0.0 | Testing framework |
| pytest-asyncio | >=0.21.0 | Async support for pytest |
| pytest-cov | >=4.0.0 | Code coverage plugin |
| ruff | >=0.14.13 | Fast Python linter and formatter |
| ty | >=0.0.12 | Fast type checker |
| basedpyright | >=1.37.2 | Pyright type checker (alternative) |
| pip-audit | >=2.0.0 | Audit dependencies for vulnerabilities |

## Installation

### For Users

Install the package with core dependencies:

```bash
pip install zotero-mcp
```

### For Developers

Clone the repository and install with development dependencies:

```bash
git clone https://github.com/54yyyu/zotero-mcp.git
cd zotero-mcp
uv sync --all
```

## Updating Dependencies

### Check for Updates

See which packages are outdated:

```bash
uv pip list --outdated
```

### Update All Dependencies

Update all packages to their latest compatible versions:

```bash
uv pip update --upgrade
uv sync
```

### Update Specific Package

Update a specific package:

```bash
uv pip install --upgrade <package-name>
uv sync
```

## Security Auditing

### Check for Vulnerabilities

Use `pip-audit` to check for known security vulnerabilities:

```bash
pip-audit
```

### Dependency Audit Script

Run the comprehensive audit script:

```bash
python scripts/audit_dependencies.py
```

This script checks for:
- Outdated dependencies
- Security vulnerabilities
- Dependency conflicts
- Unused dependencies

## Adding New Dependencies

### Adding a Core Dependency

1. Add the package to `dependencies` in `pyproject.toml`
2. Document why it's needed
3. Run `uv sync` to install it
4. Update this document

Example:

```toml
dependencies = [
    # ... existing dependencies ...
    "new-package>=1.0.0",  # Brief description
]
```

### Adding a Development Dependency

1. Add the package to `dependency-groups.dev` in `pyproject.toml`
2. Run `uv sync --group dev`

Example:

```toml
[dependency-groups]
dev = [
    # ... existing dev dependencies ...
    "new-dev-package>=1.0.0",  # Brief description
]
```

## Removing Dependencies

### Before Removing

1. Verify the dependency is not used in the codebase
2. Check if it's required by other dependencies
3. Test thoroughly after removal

### Removing Process

1. Remove the package from `pyproject.toml`
2. Run `uv sync`
3. Run tests to ensure nothing breaks
4. Update this document

## Dependency Pinning

We use **minimum version constraints** (e.g., `>=1.0.0`) rather than **exact version pinning** (e.g., `==1.0.0`) for most dependencies.

### Rationale

- **Flexibility**: Allows bug fixes and minor updates
- **Compatibility**: Reduces conflicts with other packages
- **Maintenance**: Less frequent dependency updates needed

### When to Pin Exact Versions

Pin exact versions only when:
- A specific version is required for compatibility
- A newer version has breaking changes
- Testing is limited to a specific version

Example:

```toml
dependencies = [
    "problematic-package==1.2.3",  # Pinned due to breaking changes in 1.2.4
]
```

## Best Practices

### 1. Keep Dependencies Minimal

Only add dependencies that are absolutely necessary. Each additional dependency:
- Increases attack surface for security vulnerabilities
- Adds maintenance burden
- May conflict with other packages

### 2. Regular Updates

Update dependencies regularly to:
- Get security patches
- Benefit from bug fixes
- Access new features

Recommended schedule:
- **Security updates**: Immediately
- **Core dependencies**: Monthly
- **Development dependencies**: Quarterly

### 3. Test Before Updating

Always test thoroughly after updating dependencies:

```bash
# Update dependencies
uv pip update --upgrade
uv sync

# Run tests
uv run pytest

# Run linting
uv run ruff check

# Run type checking
uv run ty check
```

### 4. Monitor Security Advisories

Subscribe to security advisories for your dependencies:
- [GitHub Security Advisories](https://github.com/advisories)
- [PyPI Security](https://pypi.org/security/)

## Troubleshooting

### Dependency Conflicts

If you encounter dependency conflicts:

```bash
# Check for conflicts
uv pip check

# Resolve by updating all packages
uv pip update --upgrade
uv sync
```

### Circular Dependencies

If you encounter circular dependencies:

1. Check if any dependency is unnecessary
2. Consider splitting functionality into separate packages
3. Report upstream if it's a third-party issue

### Version Incompatibility

If a new version breaks compatibility:

1. Pin to the last working version
2. Report the issue upstream
3. Monitor for fixes in newer versions

## Tools and Commands

### Useful uv Commands

```bash
# List installed packages
uv pip list

# Check for updates
uv pip list --outdated

# Update all packages
uv pip update --upgrade

# Check for conflicts
uv pip check

# Show package details
uv pip show <package-name>
```

### Useful pip Commands

```bash
# List installed packages
pip list

# Check for updates
pip list --outdated

# Update specific package
pip install --upgrade <package-name>

# Check for vulnerabilities
pip-audit
```

## Additional Resources

- [uv Documentation](https://github.com/astral-sh/uv)
- [Python Packaging Guide](https://packaging.python.org/)
- [PyPI](https://pypi.org/)
- [GitHub Security Advisories](https://github.com/advisories)
- [Dependabot](https://dependabot.com/)
