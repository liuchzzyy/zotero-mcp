"""
把 00_INBOXS_AA 中 publisher 字段为 "Elsevier" 或 "Elsevier BV" 的条目移动到 00_AA。
先列出所有候选条目，确认后再执行移动。
"""
import sys
from pyzotero import zotero

LIBRARY_ID = "5452188"
API_KEY    = "***ZOTERO_API_KEY***"

ELSEVIER_VALUES = {"elsevier", "elsevier bv"}


def is_elsevier(item: dict) -> bool:
    pub = item["data"].get("publisher", "").strip().lower()
    return pub in ELSEVIER_VALUES


def move_item(zot, item: dict, inbox_key: str, aa_key: str) -> bool:
    current_cols = item["data"].get("collections", [])
    new_cols = list(set(current_cols + [aa_key]) - {inbox_key})
    try:
        zot.update_item({
            "key":        item["key"],
            "version":    item["version"],
            "collections": new_cols,
        })
        return True
    except Exception as e:
        print(f"  ❌ 移动失败: {e}")
        return False


def main():
    zot = zotero.Zotero(LIBRARY_ID, "user", API_KEY)

    # 1. 获取 collections
    print("正在获取 collections...")
    col_map = {c["data"]["name"]: c["key"]
               for c in zot.everything(zot.collections())}
    inbox_key = col_map.get("00_INBOXS_AA")
    aa_key    = col_map.get("00_AA")
    if not inbox_key or not aa_key:
        sys.exit(f"❌ 找不到 collection。现有: {sorted(col_map.keys())}")
    print(f"✅ 00_INBOXS_AA={inbox_key}  00_AA={aa_key}\n")

    # 2. 获取全部非附件条目
    print("正在获取 00_INBOXS_AA 条目...")
    items = zot.everything(zot.collection_items(inbox_key, itemType="-attachment"))
    print(f"共 {len(items)} 个条目，正在筛选 Elsevier...\n")

    candidates = []
    for item in items:
        if is_elsevier(item):
            candidates.append(item)

    if not candidates:
        print("未找到 publisher 为 Elsevier / Elsevier BV 的条目。")
        return

    # 3. 打印候选列表
    print(f"找到 {len(candidates)} 条 Elsevier 条目：")
    print(f"{'─'*80}")
    print(f"  {'#':>3}  {'KEY':<10}  {'publisher':<15}  标题")
    print(f"{'─'*80}")
    for i, item in enumerate(candidates, 1):
        key   = item["key"]
        pub   = item["data"].get("publisher", "")
        title = item["data"].get("title", "(无标题)")[:55]
        print(f"  {i:>3}  {key:<10}  {pub:<15}  {title}")
    print(f"{'─'*80}")

    # 4. 执行移动
    print()
    ok_count = 0
    for i, item in enumerate(candidates, 1):
        title = item["data"].get("title", "")[:50]
        ok = move_item(zot, item, inbox_key, aa_key)
        status = "✅" if ok else "❌"
        print(f"  [{i:>3}/{len(candidates)}] {status} {item['key']}  {title}")
        if ok:
            ok_count += 1

    print(f"\n完成！成功移动 {ok_count}/{len(candidates)} 条到 00_AA。")


if __name__ == "__main__":
    main()
