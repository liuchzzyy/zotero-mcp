"""
Utility functions and helpers for Zotero MCP.
"""

from .config import get_logger, log_task_end, log_task_start
from .data import (
    RESEARCH_ANALYSIS_TEMPLATE_JSON,
    get_analysis_questions,
)
from .formatting import (
    DOI_PATTERN,
    beautify_ai_note,
    clean_html,
    clean_title,
    format_creators,
    is_local_mode,
    markdown_to_html,
)
from .system import (
    AuthenticationError,
    ConfigurationError,
    ConnectionError,
    DatabaseError,
    NotFoundError,
    ValidationError,
    ZoteroMCPError,
)

__all__ = [
    # System
    "ZoteroMCPError",
    "ConnectionError",
    "AuthenticationError",
    "NotFoundError",
    "ValidationError",
    "DatabaseError",
    "ConfigurationError",
    # Config
    "get_logger",
    "log_task_start",
    "log_task_end",
    # Data
    "get_analysis_questions",
    "RESEARCH_ANALYSIS_TEMPLATE_JSON",
    # Formatting
    "beautify_ai_note",
    "markdown_to_html",
    "format_creators",
    "clean_title",
    "clean_html",
    "is_local_mode",
    "DOI_PATTERN",
]
