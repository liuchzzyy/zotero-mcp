from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path
import textwrap

import fitz


def build_rows() -> list[tuple[str, str, str, str]]:
    return [
        ("Adding Items", "Save to Zotero", "Ctrl+Shift+S", "Save an item via Zotero Connector."),
        (
            "Adding Items",
            "Create a New Item by Hand",
            "Ctrl+Shift+N",
            "Create a new item manually.",
        ),
        (
            "Adding Items",
            "Create a New Note",
            "Ctrl+Shift+O",
            "Create a standalone note.",
        ),
        ("Adding Items", "Import", "Ctrl+Shift+I", "Import items/files."),
        (
            "Adding Items",
            "Import from Clipboard",
            "Ctrl+Shift+Alt+I",
            "Import metadata from clipboard text.",
        ),
        (
            "Editing Items (Info Tab)",
            "Add Another Author/Creator while editing creator",
            "Shift+Enter",
            "When editing creator fields in Info tab.",
        ),
        (
            "Editing Items (Info Tab)",
            "Save Abstract or Extra field",
            "Shift+Enter",
            "Commit multiline field edits.",
        ),
        (
            "Removing or Deleting",
            "Move to Trash (from My Library)",
            "Del",
            "Moves selected item(s) to trash.",
        ),
        (
            "Removing or Deleting",
            "Move to Trash (from a Collection)",
            "Shift+Del",
            "Collection context differs from library context.",
        ),
        (
            "Removing or Deleting",
            "Move to Trash without confirmation (from My Library)",
            "Shift+Del",
            "Skips confirmation dialog in My Library context.",
        ),
        (
            "Removing or Deleting",
            "Move to Trash without confirmation (from a Collection)",
            "Not available",
            "No default shortcut listed.",
        ),
        (
            "Removing or Deleting",
            "Remove top-level item from Collection",
            "Del",
            "Removes from collection only, does not trash item.",
        ),
        (
            "Removing or Deleting",
            "Delete Collection (keep items)",
            "Del",
            "Removes collection container only.",
        ),
        (
            "Removing or Deleting",
            "Delete Collection and move items to Trash",
            "Shift+Del",
            "Removes collection and trashes items.",
        ),
        (
            "Creating Citations / Quick Copy",
            "Copy selected item citations to clipboard",
            "Ctrl+Shift+A",
            "Uses current citation style.",
        ),
        (
            "Creating Citations / Quick Copy",
            "Quick Copy selected items to clipboard",
            "Ctrl+Shift+C",
            "Uses Quick Copy output format.",
        ),
        (
            "Navigating Panes",
            "Focus Libraries pane",
            "Ctrl+Shift+L",
            "Jump focus to left pane.",
        ),
        (
            "Navigating Panes",
            "Move through panes and fields",
            "Tab / Shift+Tab",
            "Forward/backward focus.",
        ),
        (
            "Navigating Panes",
            "Move through Info/Notes/Tags/Related tabs",
            "Right/Left; Ctrl+Tab; Ctrl+Shift+Tab; Ctrl+PgUp/PgDn",
            "Multiple equivalent defaults.",
        ),
        ("Navigating Panes", "Quick Search", "Ctrl+Shift+K", "Focus quick search box."),
        ("Navigating Panes", "Quick Search", "Ctrl+F", "Alternative quick search shortcut."),
        (
            "Moving Between Tabs",
            "Next/Previous tab",
            "Ctrl+PageDown / Ctrl+PageUp",
            "Switch among Zotero tabs.",
        ),
        (
            "Moving Between Tabs",
            "Next/Previous tab",
            "Ctrl+Tab / Ctrl+Shift+Tab",
            "Alternative tab navigation.",
        ),
        (
            "Moving Between Tabs",
            "Jump directly to tab 1..9",
            "Ctrl+1 ... Ctrl+9",
            "Open specific tab index.",
        ),
        ("Searching", "Quick Search", "Ctrl+Shift+K", "Focus quick search."),
        ("Searching", "Quick Search", "Ctrl+F", "Alternative quick search."),
        (
            "Searching",
            "Find/highlight collections item belongs to",
            "Hold Ctrl",
            "When selecting an item, highlights owning collections.",
        ),
        (
            "Tags",
            "Toggle Tag Selector",
            "Ctrl+Shift+T",
            "Show/hide tag selector pane.",
        ),
        (
            "Tags",
            "Assign colored tag to item",
            "1, 2, 3, 4, 5, 6",
            "Numeric keys for colored tags.",
        ),
        (
            "Feeds",
            "Mark all feed items as read/unread",
            "Ctrl+Shift+R",
            "In feed context.",
        ),
        (
            "Feeds",
            "Mark feed as read/unread",
            "Ctrl+Shift+`",
            "Backtick key.",
        ),
        (
            "Other",
            "Expand/Collapse collections or items list",
            "+ / -",
            "Tree/list expansion controls.",
        ),
        (
            "Other",
            "Highlight all collections item is in",
            "Hold Ctrl",
            "Collection highlighting behavior.",
        ),
        (
            "Other",
            "Count items (result in right pane)",
            "Ctrl+A",
            "Select all to show count.",
        ),
        ("Other", "Edit collection name", "F2", "Rename selected collection."),
        (
            "PDF Reader (Official list is incomplete)",
            "Switch annotation tools",
            "Alt+1 / Alt+2 / Alt+3 / Alt+4",
            "Reader shortcut group.",
        ),
        (
            "PDF Reader (Official list is incomplete)",
            "Back in PDF links/history",
            "Alt+Left",
            "Navigate backward.",
        ),
        (
            "PDF Reader (Official list is incomplete)",
            "Forward in PDF links/history",
            "Alt+Right",
            "Navigate forward.",
        ),
        ("Notes", "Bold", "Ctrl+B", "Text formatting."),
        ("Notes", "Italic", "Ctrl+I", "Text formatting."),
        ("Notes", "Underline", "Ctrl+U", "Text formatting."),
        ("Notes", "Select all", "Ctrl+A", "Editing shortcut."),
        ("Notes", "Undo", "Ctrl+Z", "Editing shortcut."),
        ("Notes", "Redo", "Ctrl+Y or Ctrl+Shift+Z", "Editing shortcut."),
        ("Notes", "Cut", "Ctrl+X", "Editing shortcut."),
        ("Notes", "Copy", "Ctrl+C", "Editing shortcut."),
        ("Notes", "Paste", "Ctrl+V", "Editing shortcut."),
        ("Notes", "Paste without formatting", "Ctrl+Shift+V", "Plain text paste."),
        (
            "Notes",
            "Format as Heading levels",
            "Shift+Alt+1..6",
            "Heading 1 to Heading 6.",
        ),
        ("Notes", "Format as Paragraph", "Shift+Alt+7", "Paragraph block."),
        ("Notes", "Format as Div", "Shift+Alt+8", "Div block."),
        ("Notes", "Format as Address", "Shift+Alt+9", "Address block."),
        ("Notes", "Find and replace", "Ctrl+F", "Search/replace in note."),
        ("Notes", "Insert link", "Ctrl+K", "Add hyperlink."),
        ("Notes", "Focus toolbar", "Alt+F10", "Keyboard focus to editor toolbar."),
    ]


def build_text_lines(rows: list[tuple[str, str, str, str]]) -> list[str]:
    today = date.today().isoformat()
    source = "https://www.zotero.org/support/kb/keyboard_shortcuts"
    lines: list[str] = [
        "Zotero Default Keyboard Shortcuts (Windows)",
        f"Generated: {today}",
        f"Source: {source}",
        "Note: Official page states PDF Reader and Notes lists may be incomplete.",
        "",
    ]

    grouped: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for section, action, shortcut, notes in rows:
        grouped[section].append((action, shortcut, notes))

    col_widths = (41, 24, 31)
    border = f"+-{'-' * col_widths[0]}-+-{'-' * col_widths[1]}-+-{'-' * col_widths[2]}-+"

    for section, items in grouped.items():
        lines.append(section)
        lines.append(border)
        lines.extend(format_row(("Action", "Shortcut", "Notes"), col_widths))
        lines.append(border)
        for item in items:
            lines.extend(format_row(item, col_widths))
            lines.append(border)
        lines.append("")

    lines.append("Additional official references:")
    lines.append("- https://www.zotero.org/support/preferences/advanced")
    lines.append("- https://www.zotero.org/support/word_processor_plugin_shortcuts")
    return lines


def format_row(cells: tuple[str, str, str], widths: tuple[int, int, int]) -> list[str]:
    wrapped_cols: list[list[str]] = []
    for cell, width in zip(cells, widths, strict=True):
        wrapped = textwrap.wrap(
            cell,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        wrapped_cols.append(wrapped or [""])

    height = max(len(col) for col in wrapped_cols)
    lines: list[str] = []
    for i in range(height):
        c0 = wrapped_cols[0][i] if i < len(wrapped_cols[0]) else ""
        c1 = wrapped_cols[1][i] if i < len(wrapped_cols[1]) else ""
        c2 = wrapped_cols[2][i] if i < len(wrapped_cols[2]) else ""
        lines.append(f"| {c0:<{widths[0]}} | {c1:<{widths[1]}} | {c2:<{widths[2]}} |")
    return lines


def write_text_file(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_pdf(path: Path, lines: list[str]) -> None:
    doc = fitz.open()
    page_width, page_height = 595, 842  # A4 portrait
    margin = 36
    font_size = 8.5
    line_height = 11
    max_chars = 102

    page = doc.new_page(width=page_width, height=page_height)
    y = margin
    for raw in lines:
        wrapped = (
            textwrap.wrap(
                raw,
                width=max_chars,
                break_long_words=False,
                break_on_hyphens=False,
            )
            if raw
            else [""]
        )
        for line in wrapped:
            if y > page_height - margin:
                page = doc.new_page(width=page_width, height=page_height)
                y = margin
            page.insert_text((margin, y), line, fontname="cour", fontsize=font_size)
            y += line_height

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()


def main() -> None:
    rows = build_rows()
    lines = build_text_lines(rows)

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    txt_path = output_dir / "Zotero_Windows_Default_Shortcuts.txt"
    pdf_path = output_dir / "Zotero_Windows_Default_Shortcuts.pdf"

    write_text_file(txt_path, lines)
    write_pdf(pdf_path, lines)

    print(txt_path)
    print(pdf_path)


if __name__ == "__main__":
    main()
