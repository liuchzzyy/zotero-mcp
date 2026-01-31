#!/usr/bin/env python3
"""Inspect <br> tags in the note."""

import asyncio
import re
from zotero_mcp.services.data_access import get_data_service


async def main():
    ds = get_data_service()

    # Get the note from 7I72IMC4
    notes = await ds.get_notes("7I72IMC4")

    if not notes:
        print("❌ No notes found")
        return

    note_key = notes[0].get("key")
    note_data = await ds.get_item(note_key)
    note_content = note_data.get("data", {}).get("note", "")

    print("=" * 80)
    print("查找 <br> 标签位置")
    print("=" * 80)
    print()

    # Find all <br> tags and their context
    br_matches = []
    for match in re.finditer(r".{0,100}<br\s*/?>.{0,100}", note_content, re.DOTALL):
        br_matches.append(match.group())

    print(f"总共找到 {len(br_matches)} 个 <br> 标签\n")

    for i, context in enumerate(br_matches, 1):
        # Clean up for display
        display = context.replace("\n", "\\n")
        print(f"{i}. ...{display}...")
        print()

    print("=" * 80)
    print("分析 <br> 标签的来源")
    print("=" * 80)
    print()

    # Check if <br> are between paragraphs
    para_br_pattern = r"</p>\s*<br\s*/?>\s*<p"
    para_br = re.findall(para_br_pattern, note_content)
    print(f"段落之间的 <br>: {len(para_br)} 个")

    # Check if <br> are after headings
    heading_br_pattern = r"</h[1-6]>\s*<br\s*/?>"
    heading_br = re.findall(heading_br_pattern, note_content)
    print(f"标题后的 <br>: {len(heading_br)} 个")

    # Check if <br> are before headings
    br_heading_pattern = r"<br\s*/?>\s*<h[1-6]>"
    br_heading = re.findall(br_heading_pattern, note_content)
    print(f"标题前的 <br>: {len(br_heading)} 个")

    print()
    print("=" * 80)
    print("检查 Markdown 源文本（可能是 LLM 输出的问题）")
    print("=" * 80)
    print()

    # The issue is likely in the markdown source returned by LLM
    # Check for double newlines in markdown which create paragraph breaks
    # Extract a section to see the pattern

    # Look for the pattern around headings
    heading_contexts = re.findall(
        r".{0,200}<h3[^>]*>.*?</h3>.{0,200}", note_content, re.DOTALL
    )
    print(f"找到 {len(heading_contexts)} 个 H3 标题上下文")
    print()
    print("前 2 个 H3 标题上下文:")
    for i, ctx in enumerate(heading_contexts[:2], 1):
        print(f"{i}. {ctx[:300]}...")
        print()


if __name__ == "__main__":
    asyncio.run(main())
