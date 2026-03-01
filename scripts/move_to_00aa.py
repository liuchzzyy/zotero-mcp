"""
把 00_INBOXS_AA 中符合以下任一条件的含 PDF 附件条目移动到 00_AA：
  1. 含有两个或以上 PDF 附件
  2. 出版社为 Wiley、RSC、ACS 或 Elsevier（含一个 PDF）
  3. 综述文章（review article）——先元数据启发式，不确定时调用 DeepSeek
  4. 发表时间早于 2000 年

合并自：move_dual_pdf_to_aa.py, move_publisher_to_aa.py,
         move_elsevier_to_aa.py, move_to_aa.py
"""
import re
import sys

from openai import OpenAI
from pyzotero import zotero

# ── 配置 ──────────────────────────────────────────────────────────────────────
LIBRARY_ID = "5452188"
API_KEY = "***ZOTERO_API_KEY***"
DEEPSEEK_API_KEY = "***DEEPSEEK_API_KEY***"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
YEAR_THRESHOLD = 2000

# ── 综述识别关键词 ─────────────────────────────────────────────────────────────
REVIEW_TITLE_KEYWORDS = [
    "review", "overview", "progress", "advances in", "recent advance",
    "perspective", "survey", "roadmap", "state of the art",
]
REVIEW_ABSTRACT_PHRASES = [
    "we review", "this review", "herein we review", "in this review",
    "comprehensive review", "we summarize", "this article reviews",
    "this paper reviews", "we overview", "we present a review",
    "is reviewed", "are reviewed",
]

# ── 出版社识别规则（匹配 publicationTitle / publisher / extra，不区分大小写）──
PUBLISHER_PATTERNS = {
    "Wiley": [
        r"wiley",
        r"angewandte chemie",
        r"advanced materials",
        r"advanced energy materials",
        r"advanced functional materials",
        r"advanced science",
        r"\bsmall\b",
        r"chemsuschem",
        r"chemelectrochem",
        r"chemcatchem",
        r"chemistry[- ]+a european journal",
        r"batteries.*supercaps",
        r"electroanalysis",
        r"european journal of inorganic chemistry",
        r"european journal of organic chemistry",
        r"macromolecular",
    ],
    "RSC": [
        r"royal society of chemistry",
        r"\brsc\b",
        r"journal of materials chemistry",
        r"energy.*environmental science",
        r"physical chemistry chemical physics",
        r"\bnanoscale\b",
        r"green chemistry",
        r"chemical communications",
        r"\bchem\.?\s*comm",
        r"dalton transactions",
        r"rsc advances",
        r"chemical science",
        r"new journal of chemistry",
        r"crystengcomm",
        r"faraday discuss",
        r"materials chemistry frontiers",
        r"journal of the chemical society",
    ],
    "ACS": [
        r"american chemical society",
        r"\bacs\s+\w",
        r"journal of the american chemical society",
        r"\bjacs\b",
        r"nano letters",
        r"chemistry of materials",
        r"journal of physical chemistry",
        r"\blangmuir\b",
        r"inorganic chemistry",
        r"analytical chemistry",
        r"environmental science.*technology",
        r"accounts of chemical research",
        r"crystal growth.*design",
        r"macromolecules",
        r"organometallics",
        r"biochemistry",
        r"the journal of organic chemistry",
        r"industrial.*engineering chemistry",
    ],
    "Elsevier": [
        r"\belsevier\b",
        r"electrochimica acta",
        r"journal of power sources",
        r"journal of electroanalytical chemistry",
        r"chemical engineering journal",
        r"applied surface science",
        r"materials today",
        r"nano energy",
        r"energy storage materials",
        r"journal of alloys and compounds",
        r"ceramics international",
        r"solid state ionics",
        r"carbon",
        r"journal of colloid and interface science",
        r"chemical physics letters",
        r"electrochemistry communications",
        r"international journal of hydrogen energy",
        r"applied energy",
        r"journal of energy storage",
        r"journal of membrane science",
        r"materials letters",
        r"scripta materialia",
        r"acta materialia",
        r"journal of solid state chemistry",
        r"coordination chemistry reviews",
        r"progress in natural science",
        r"chinese chemical letters",
        r"journal of hazardous materials",
        r"chemosphere",
    ],
}

# 编译正则
COMPILED = {
    pub: [re.compile(p, re.IGNORECASE) for p in patterns]
    for pub, patterns in PUBLISHER_PATTERNS.items()
}


# ── 工具函数 ──────────────────────────────────────────────────────────────────
def extract_year(item: dict) -> int | None:
    date_str = item["data"].get("date", "")
    m = re.search(r"\b(1[5-9]\d\d|20\d\d)\b", date_str)
    return int(m.group(1)) if m else None


def detect_publisher(item: dict) -> tuple[str | None, str | None]:
    """返回 (出版社名, 匹配字段)，匹配不到返回 (None, None)。"""
    fields = [
        item["data"].get("publicationTitle", ""),
        item["data"].get("publisher", ""),
        item["data"].get("extra", ""),
    ]
    text = " | ".join(fields)
    for pub, regexes in COMPILED.items():
        for rx in regexes:
            if rx.search(text):
                matched = (item["data"].get("publicationTitle")
                           or item["data"].get("publisher", ""))
                return pub, matched[:50]
    return None, None


def is_review_by_metadata(item: dict) -> tuple[bool, str | None]:
    """元数据启发式判断是否为综述，不确定则返回 (False, None)。"""
    title = item["data"].get("title", "").lower()
    extra = item["data"].get("extra", "").lower()
    abstract = item["data"].get("abstractNote", "").lower()

    if re.search(r"\btype\s*:\s*review\b", extra):
        return True, "extra: Type=Review"

    for kw in REVIEW_TITLE_KEYWORDS:
        if kw in title:
            return True, f"标题含 '{kw}'"

    snippet = abstract[:400]
    for phrase in REVIEW_ABSTRACT_PHRASES:
        if phrase in snippet:
            return True, f"摘要含 '{phrase}'"

    journal = item["data"].get("publicationTitle", "").lower()
    if "review" in journal or "reviews" in journal:
        return True, f"期刊名含 review ({journal[:40]})"

    return False, None


def is_review_by_deepseek(item: dict, client: OpenAI) -> bool:
    """调用 DeepSeek 判断是否为综述（仅在元数据无法确定时使用）。"""
    title = item["data"].get("title", "（无标题）")
    abstract = item["data"].get("abstractNote", "")
    journal = item["data"].get("publicationTitle", "")
    year = extract_year(item)

    prompt = (
        "判断下面这篇文章是否是综述文章（review article）。\n"
        "综述的特征：系统回顾某领域研究进展，总结多篇文献，通常无原创实验数据。\n\n"
        f"标题：{title}\n"
        f"期刊：{journal}\n"
        f"年份：{year}\n"
        f"摘要：{abstract[:600] if abstract else '（无摘要）'}\n\n"
        "只回答 YES 或 NO，不要解释。"
    )
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5,
            temperature=0,
        )
        answer = resp.choices[0].message.content.strip().upper()
        return "YES" in answer
    except Exception as e:
        print(f"    ⚠️  DeepSeek 调用失败: {e}")
        return False


def move_item(zot, item: dict, inbox_key: str, aa_key: str) -> bool:
    current_cols = item["data"].get("collections", [])
    new_cols = list(set(current_cols + [aa_key]) - {inbox_key})
    try:
        zot.update_item({
            "key": item["key"],
            "version": item["version"],
            "collections": new_cols,
        })
        return True
    except Exception as e:
        print(f"    ❌ 移动失败: {e}")
        return False


# ── 主流程 ────────────────────────────────────────────────────────────────────
def main():
    zot = zotero.Zotero(LIBRARY_ID, "user", API_KEY)
    deepseek = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

    # 1. 获取 collections
    print("正在获取 collections...")
    col_map = {c["data"]["name"]: c["key"]
               for c in zot.everything(zot.collections())}
    inbox_key = col_map.get("00_INBOXS_AA")
    aa_key = col_map.get("00_AA")
    if not inbox_key or not aa_key:
        sys.exit(f"❌ 找不到所需 collection。现有: {sorted(col_map.keys())}")
    print(f"✅ 00_INBOXS_AA={inbox_key}, 00_AA={aa_key}\n")

    # 2. 获取所有非附件/非笔记条目
    print("正在获取条目...")
    raw = zot.everything(zot.collection_items(inbox_key, itemType="-attachment"))
    items = [i for i in raw if i["data"].get("itemType") != "note"]
    total = len(items)
    print(f"共 {total} 个条目\n{'─'*65}")

    results = {"moved": [], "skipped_no_pdf": [], "skipped_no_match": []}
    deepseek_calls = 0

    for i, item in enumerate(items, 1):
        key = item["key"]
        title = item["data"].get("title", "(无标题)")[:55]
        prefix = f"[{i:3d}/{total}]"

        # 获取 PDF 附件
        children = zot.children(key)
        pdfs = [c for c in children
                if c["data"].get("itemType") == "attachment"
                and c["data"].get("contentType") == "application/pdf"]
        pdf_count = len(pdfs)

        if pdf_count == 0:
            print(f"{prefix} ⏭️  无PDF，跳过: {title}")
            results["skipped_no_pdf"].append(key)
            continue

        reason = None

        # 条件 1：两个或以上 PDF
        if pdf_count >= 2:
            reason = f"{pdf_count} 个PDF"

        # 条件 4：发表时间早于 2000
        if reason is None:
            year = extract_year(item)
            if year is not None and year < YEAR_THRESHOLD:
                reason = f"发表于 {year} 年"

        # 条件 2：出版社匹配（Wiley / RSC / ACS / Elsevier）
        if reason is None:
            pub, journal = detect_publisher(item)
            if pub:
                reason = f"{pub} ({journal})"

        # 条件 3：综述文章（元数据 → DeepSeek）
        if reason is None:
            is_rev, meta_reason = is_review_by_metadata(item)
            if is_rev:
                reason = f"综述（{meta_reason}）"
            else:
                print(f"{prefix} 🤖 DeepSeek 判断中: {title}")
                deepseek_calls += 1
                if is_review_by_deepseek(item, deepseek):
                    reason = "综述（DeepSeek）"

        if reason:
            print(f"{prefix} ✅ 【{reason}】: {title}")
            ok = move_item(zot, item, inbox_key, aa_key)
            if ok:
                results["moved"].append((key, title, reason))
        else:
            print(f"{prefix} ➖ 不符合条件: {title}")
            results["skipped_no_match"].append(key)

    # 汇总
    print(f"\n{'═'*65}")
    print(f"完成！DeepSeek 共调用 {deepseek_calls} 次")
    print(f"  ✅ 已移动到 00_AA : {len(results['moved'])} 条")
    print(f"  ⏭️  无PDF跳过     : {len(results['skipped_no_pdf'])} 条")
    print(f"  ➖ 不符合条件    : {len(results['skipped_no_match'])} 条")

    if results["moved"]:
        print("\n移动明细：")
        for key, title, reason in results["moved"]:
            print(f"  {key}  [{reason}]  {title}")


if __name__ == "__main__":
    main()
