"""
把 00_INBOXS_AA 中含有两个 PDF 附件的条目移动到 00_AA
"""
import os
from pyzotero import zotero

LIBRARY_ID = "5452188"
API_KEY = "***ZOTERO_API_KEY***"

zot = zotero.Zotero(LIBRARY_ID, "user", API_KEY)

# 1. 找到目标 collection
print("正在获取所有 collections...")
all_collections = zot.everything(zot.collections())
col_map = {c["data"]["name"]: c["key"] for c in all_collections}

inbox_key = col_map.get("00_INBOXS_AA")
aa_key = col_map.get("00_AA")

if not inbox_key:
    print("❌ 找不到 collection: 00_INBOXS_AA")
    print("现有 collections:", sorted(col_map.keys()))
    exit(1)
if not aa_key:
    print("❌ 找不到 collection: 00_AA")
    print("现有 collections:", sorted(col_map.keys()))
    exit(1)

print(f"✅ 00_INBOXS_AA key: {inbox_key}")
print(f"✅ 00_AA key: {aa_key}")

# 2. 获取 00_INBOXS_AA 中所有条目
print("\n正在获取 00_INBOXS_AA 中的条目...")
items = zot.everything(zot.collection_items(inbox_key, itemType="-attachment"))
print(f"共 {len(items)} 个条目（非附件）")

# 3. 找出含 2 个 PDF 附件的条目
to_move = []
for item in items:
    item_key = item["key"]
    children = zot.children(item_key)
    pdf_children = [
        c for c in children
        if c["data"].get("itemType") == "attachment"
        and c["data"].get("contentType", "") == "application/pdf"
    ]
    count = len(pdf_children)
    title = item["data"].get("title", "(无标题)")[:60]
    if count == 2:
        to_move.append(item)
        print(f"  [2 PDF] {item_key}: {title}")
    elif count > 0:
        print(f"  [{count} PDF] {item_key}: {title}")

print(f"\n共找到 {len(to_move)} 个含 2 个 PDF 附件的条目，准备移动到 00_AA...")

if not to_move:
    print("没有需要移动的条目，退出。")
    exit(0)

# 4. 移动：添加到 00_AA，从 00_INBOXS_AA 移除
moved = 0
for item in to_move:
    item_key = item["key"]
    title = item["data"].get("title", "(无标题)")[:60]

    # 获取当前 collections
    current_cols = item["data"].get("collections", [])

    # 构建新的 collections 列表
    new_cols = list(set(current_cols + [aa_key]) - {inbox_key})

    # 更新
    patch_data = {
        "key": item_key,
        "version": item["version"],
        "collections": new_cols,
    }
    try:
        zot.update_item(patch_data)
        print(f"  ✅ 已移动: {item_key} — {title}")
        moved += 1
    except Exception as e:
        print(f"  ❌ 移动失败 {item_key}: {e}")

print(f"\n完成！共移动 {moved}/{len(to_move)} 个条目到 00_AA。")
