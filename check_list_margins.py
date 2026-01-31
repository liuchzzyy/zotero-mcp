#!/usr/bin/env python3
"""Check list and paragraph margins."""

import asyncio
import re
from zotero_mcp.services.data_access import get_data_service


async def main():
    ds = get_data_service()

    # Get the note
    notes = await ds.get_notes("7I72IMC4")

    if not notes:
        print("❌ No notes found")
        return

    note_key = notes[0].get("key")
    note_data = await ds.get_item(note_key)
    note_content = note_data.get("data", {}).get("note", "")

    print("=" * 80)
    print("问题分析：列表 vs 段落的 margin")
    print("=" * 80)
    print()

    # Show example HTML structure
    print("HTML 结构示例:")
    print("-" * 80)
    examples = re.findall(
        r"</[uo]l>.{0,150}<(?:p|ul|ol|h[1-6])", note_content, re.DOTALL
    )

    for i, ex in enumerate(examples[:3], 1):
        clean = ex.replace("\n", " ")
        print(f"{i}. {clean}")
        print()

    print("-" * 80)
    print()

    # Check margins
    ul_margins = re.findall(r'<ul[^>]*margin:\s*([0-9.]+)em', note_content)
    ol_margins = re.findall(r'<ol[^>]*margin:\s*([0-9.]+)em', note_content)
    p_margins = re.findall(
        r'<p[^>]*margin:\s*([0-9.]+)em', note_content, re.DOTALL
    )

    print("当前的 margin 设置:")
    print(f"  <ul> margin: {set(ul_margins)}")
    print(f"  <ol> margin: {set(ol_margins)}")
    print(f"  <p> margin: {set(p_margins)}")
    print()

    print("=" * 80)
    print("问题根源")
    print("=" * 80)
    print()

    ul_margin = set(ul_margins).pop() if ul_margins else "0.5"
    p_margin = set(p_margins).pop() if p_margins else "0.2"

    print(f"列表的上下间距: {ul_margin}em")
    print(f"段落的上下间距: {p_margin}em")
    print()

    print("因此产生的实际间距:")
    print(f"  列表 ↔ 列表: {float(ul_margin) + float(ul_margin)}em")
    print(f"  列表 ↔ 段落: {float(ul_margin) + float(p_margin)}em")
    print(f"  段落 ↔ 段落: {float(p_margin) + float(p_margin)}em")
    print()

    print("=" * 80)
    print("解决方案")
    print("=" * 80)
    print()

    print("需要将列表的 margin 从 0.5em 改为 0.2em")
    print("这样列表之间、列表与段落之间的间距就会与段落之间一致")
    print()
    print("修改位置: src/zotero_mcp/utils/templates.py")
    print("修改项: orange-heart theme 的 list_margin")
    print("修改值: '0.8em' → '0.2em'")


if __name__ == "__main__":
    asyncio.run(main())
