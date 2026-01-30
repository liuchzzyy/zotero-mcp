#!/usr/bin/env python3
"""
Dependency Audit Script for Zotero MCP.

This script checks for:
1. Outdated dependencies
2. Known security vulnerabilities
3. Unused dependencies
4. Dependency conflicts

Usage:
    python scripts/audit_dependencies.py
"""

from pathlib import Path
import subprocess
import sys


def run_command(cmd: list[str], description: str) -> tuple[bool, str]:
    """
    Run a command and return success status and output.

    Args:
        cmd: Command to run
        description: Description of what the command does

    Returns:
        Tuple of (success, output)
    """
    print(f"\n{'=' * 60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'=' * 60}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(f"⚠️  Command failed with exit code {result.returncode}")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False, result.stdout or result.stderr

        print(result.stdout)
        return True, result.stdout

    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False, str(e)


def check_outdated() -> None:
    """Check for outdated dependencies using uv."""
    print("\n" + "=" * 60)
    print("CHECKING FOR OUTDATED DEPENDENCIES")
    print("=" * 60)

    # Try uv first
    success, output = run_command(
        ["uv", "pip", "list", "--outdated"],
        "Check for outdated packages (uv)",
    )

    if not success:
        # Fallback to pip
        run_command(
            ["pip", "list", "--outdated"],
            "Check for outdated packages (pip)",
        )


def check_security_vulnerabilities() -> None:
    """Check for known security vulnerabilities."""
    print("\n" + "=" * 60)
    print("CHECKING FOR SECURITY VULNERABILITIES")
    print("=" * 60)

    # Check if pip-audit is installed
    try:
        subprocess.run(
            ["pip-audit", "--version"],
            capture_output=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("⚠️  pip-audit not found. Installing...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pip-audit"],
            check=True,
        )

    run_command(
        ["pip-audit"],
        "Audit dependencies for vulnerabilities",
    )


def check_dependency_conflicts() -> None:
    """Check for dependency conflicts."""
    print("\n" + "=" * 60)
    print("CHECKING FOR DEPENDENCY CONFLICTS")
    print("=" * 60)

    run_command(
        ["uv", "pip", "check"],
        "Check for dependency conflicts",
    )


def analyze_unused_dependencies() -> None:
    """
    Analyze potentially unused dependencies.

    This is a simple heuristic check and should be verified manually.
    """
    print("\n" + "=" * 60)
    print("ANALYZING POTENTIALLY UNUSED DEPENDENCIES")
    print("=" * 60)

    # Core dependencies from pyproject.toml
    core_deps = [
        "fastmcp",
        "mcp",
        "pyzotero",
        "openai",
        "google-generativeai",
        "beautifulsoup4",
        "feedparser",
        "pydantic",
        "chromadb",
        "google-api-python-client",
        "google-auth-oauthlib",
        "httpx",
        "requests",
        "python-dotenv",
        "pyyaml",
        "markitdown",
    ]

    print("\nScanning source code for import statements...")

    src_dir = Path(__file__).parent.parent / "src"
    imported_packages = set()

    for py_file in src_dir.rglob("*.py"):
        try:
            with open(py_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("import ") or line.startswith("from "):
                        # Extract package name
                        parts = line.split()
                        if len(parts) >= 2:
                            package = parts[1].split(".")[0]
                            imported_packages.add(package)
        except Exception:
            pass

    print("\nCore dependencies and their usage:")
    print("-" * 60)

    unused = []
    for dep in core_deps:
        # Normalize package names (some use different import names)
        import_name = dep.replace("-", "_").lower()

        if import_name in imported_packages:
            print(f"✅ {dep:30} - USED")
        else:
            print(f"⚠️  {dep:30} - POSSIBLY UNUSED")
            unused.append(dep)

    if unused:
        print("\n⚠️  The following dependencies may be unused:")
        for dep in unused:
            print(f"  - {dep}")
        print("\nPlease verify manually before removing them.")


def generate_report() -> None:
    """Generate a summary report."""
    print("\n" + "=" * 60)
    print("DEPENDENCY AUDIT SUMMARY")
    print("=" * 60)

    print("\n✅ Completed checks:")
    print("  1. Outdated dependencies")
    print("  2. Security vulnerabilities")
    print("  3. Dependency conflicts")
    print("  4. Unused dependencies (heuristic)")

    print("\n📋 Recommendations:")
    print("  1. Review outdated dependencies and update if needed")
    print("  2. Address any security vulnerabilities immediately")
    print("  3. Resolve dependency conflicts")
    print("  4. Verify and remove unused dependencies")

    print("\n🔧 Useful commands:")
    print("  uv pip list                          # List installed packages")
    print("  uv pip list --outdated               # Check for updates")
    print("  uv pip update --upgrade              # Update all packages")
    print("  pip-audit                            # Check for vulnerabilities")
    print("  uv pip check                         # Check for conflicts")


def main() -> int:
    """
    Main entry point for the dependency audit script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("=" * 60)
    print("ZOTERO MCP DEPENDENCY AUDIT")
    print("=" * 60)

    try:
        # Run all checks
        check_outdated()
        check_security_vulnerabilities()
        check_dependency_conflicts()
        analyze_unused_dependencies()

        # Generate summary
        generate_report()

        print("\n✅ Dependency audit completed!")
        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Audit interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Error during audit: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
