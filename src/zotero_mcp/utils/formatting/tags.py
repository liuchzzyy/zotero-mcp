"""Utilities for normalizing Zotero tag payloads."""

from __future__ import annotations

from typing import Any


def extract_tag_name(raw_tag: Any) -> str:
    """Extract a normalized tag name from Zotero tag payload values."""
    if isinstance(raw_tag, dict):
        return str(raw_tag.get("tag", "")).strip()
    if isinstance(raw_tag, str):
        return raw_tag.strip()
    return ""


def normalize_tag_names(raw_tags: Any) -> list[str]:
    """Normalize mixed tag payloads to an ordered list of non-empty tag names."""
    if not isinstance(raw_tags, list):
        return []

    normalized: list[str] = []
    for raw_tag in raw_tags:
        tag_name = extract_tag_name(raw_tag)
        if tag_name:
            normalized.append(tag_name)
    return normalized


def normalize_input_tags(tags: list[str] | None) -> list[str]:
    """Normalize user input tags by stripping, dropping empties, and deduplicating."""
    if not tags:
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_tag in tags:
        tag_name = str(raw_tag).strip()
        if not tag_name or tag_name in seen:
            continue
        seen.add(tag_name)
        normalized.append(tag_name)
    return normalized


def to_tag_objects(tag_names: list[str]) -> list[dict[str, str]]:
    """Convert normalized tag names to Zotero tag object payload format."""
    return [{"tag": tag_name} for tag_name in tag_names]

