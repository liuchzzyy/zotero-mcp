"""Metadata clients - academic paper metadata APIs."""

from .crossref import CrossrefClient, CrossrefWork
from .openalex import OpenAlexClient, OpenAlexWork

__all__ = [
    "CrossrefClient",
    "CrossrefWork",
    "OpenAlexClient",
    "OpenAlexWork",
]
