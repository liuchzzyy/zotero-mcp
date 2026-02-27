"""
00_INBOXS_AA Phase 1: 扫描 + 生成下载队列
============================================
输出：
  .si-downloads/inbox/surge_list.txt    — Surge 导入的纯 URL 列表（一行一个）
  .si-downloads/inbox/download_meta.json — URL → {key, type, fname} 映射
  .si-downloads/inbox/keyan_queue.txt   — 无法自动获取 MS 的条目（供科研通）
"""
import re
import json
import time
import urllib.parse
import requests
import pyzotero.zotero as zotero
import httpx
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────────────────────────────
LIBRARY_ID = "5452188"
API_KEY    = "***ZOTERO_API_KEY***"
INBOX_KEY  = "2PSBFJEI"   # 00_INBOXS_AA
OA_EMAIL   = "liuchzzyy@gmail.com"

OUT_DIR = Path("F:/ICMAB-Data/UAB-Thesis/zotero-mcp/.si-downloads/inbox")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SURGE_FILE = OUT_DIR / "surge_list.txt"
META_FILE  = OUT_DIR / "download_meta.json"
KYAN_FILE  = OUT_DIR / "keyan_queue.txt"

SI_KEYWORDS = [
    "supporting", "supplementary", "supplem", "suppl", "esi",
    "_si_", "_si.", "-si.", "si_001", "si_002", "si_00",
    "supp_info", "additional", "_s1.", "_s2.", "supplement",
]
ALLOWED_EXT = {".pdf", ".docx", ".doc"}

# ── 初始化 ────────────────────────────────────────────────────────────────────
zot = zotero.Zotero(LIBRARY_ID, "user", API_KEY)
zot.client = httpx.Client(timeout=120, headers=zot.default_headers())
sess = requests.Session()


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def clean_title(t):
    return re.sub(r"<[^>]+>", "", t or "")[:60]


def classify_pdf(att):
    fname = att["data"].get("filename", "").lower()
    title = att["data"].get("title", "").lower()
    for kw in SI_KEYWORDS:
        if kw in fname or kw in title:
            return "SI"
    return "MS"


def get_publisher(doi):
    d = (doi or "").lower().strip()
    if d.startswith("10.1021/"): return "ACS"
    if d.startswith("10.1039/"): return "RSC"
    if d.startswith("10.1016/"): return "Elsevier"
    if d.startswith("10.1002/"): return "Wiley"
    if d.startswith("10.1038/"): return "Nature"
    if d.startswith("10.1126/"): return "Science"
    if d.startswith("10.1149/"): return "ECS"
    if d.startswith("10.1103/"): return "APS"
    if d.startswith("10.1063/"): return "AIP"
    return "Other"


# ── SI URL 查找 ────────────────────────────────────────────────────────────────

def find_si_acs(doi):
    enc = urllib.parse.quote(doi, safe="")
    url = (f"https://widgets.figshare.com/public/files"
           f"?institution=acs&limit=21&offset=0&collectionResourceDOI={enc}")
    try:
        r = sess.get(url, timeout=20)
        if r.status_code == 200:
            files = r.json().get("files", [])
            seen, out = set(), []
            for f in files:
                if f["name"] not in seen and Path(f["name"]).suffix.lower() in ALLOWED_EXT:
                    seen.add(f["name"])
                    out.append((f["downloadUrl"], f["name"]))
            return out
    except Exception as e:
        print(f"    figshare error: {e}")
    return []


def find_si_elsevier(doi):
    try:
        r = sess.get(f"https://doi.org/{doi}", timeout=25, allow_redirects=True)
        pii = None
        for pattern in (r"/pii/(S[\dX]{16,20})", r"pii[/=](S[\dX]{16,20})"):
            m = re.search(pattern, r.url + " " + r.text[:3000], re.I)
            if m:
                pii = m.group(1)
                break
        if not pii:
            return []
        return [
            (f"https://ars.els-cdn.com/content/image/1-s2.0-{pii}-mmc1.pdf",  "mmc1.pdf"),
            (f"https://ars.els-cdn.com/content/image/1-s2.0-{pii}-mmc1.docx", "mmc1.docx"),
        ]
    except Exception as e:
        print(f"    Elsevier error: {e}")
    return []


def find_si_rsc(doi):
    paper_id = doi.split("10.1039/")[-1].lower() if "10.1039/" in doi.lower() else ""
    if not paper_id:
        return []
    try:
        r = sess.get(f"https://doi.org/{doi}", timeout=25, allow_redirects=True)
        links = re.findall(
            r'href="(https://www\.rsc\.org/suppdata/[^"]+\.(pdf|docx))"', r.text, re.I
        )
        if links:
            return [(url, url.split("/")[-1]) for url, _ in links]
        # 构造 suppdata URL: paper_id 格式 c8ee01234a
        m = re.match(r"([a-z])(\d)([a-z]+)\d+[a-z]?", paper_id)
        if m:
            year_code = m.group(1) + m.group(2)
            journal   = m.group(3)
            return [
                (f"https://www.rsc.org/suppdata/{journal}/{year_code}/{paper_id}/{paper_id}1.pdf",
                 f"{paper_id}_si1.pdf"),
                (f"https://www.rsc.org/suppdata/{journal}/{year_code}/{paper_id}/{paper_id}2.pdf",
                 f"{paper_id}_si2.pdf"),
            ]
    except Exception as e:
        print(f"    RSC error: {e}")
    return []


def find_si_from_page(doi, pub):
    """通用：抓论文页面找 SI 链接（Wiley/Nature 等）。"""
    try:
        r = sess.get(f"https://doi.org/{doi}", timeout=30, allow_redirects=True)
        text = r.text
        base = r.url

        candidates = []
        for link in re.findall(r'href="([^"]+\.(?:pdf|docx))"', text, re.I):
            ll = link.lower()
            if any(kw in ll for kw in ["support", "suppl", "esi", "si_", "_si"]):
                full = link if link.startswith("http") else urllib.parse.urljoin(base, link)
                fname = re.sub(r'[<>:"/\\|?*]', "_", full.split("/")[-1].split("?")[0]) or "si.pdf"
                candidates.append((full, fname))

        # Wiley suppinfo 特殊链接
        for link in re.findall(
            r'href="(https://onlinelibrary\.wiley\.com[^"]*suppinfo[^"]*)"', text
        ):
            candidates.append((link, "suppinfo.pdf"))

        return candidates[:3]
    except Exception as e:
        print(f"    Page scrape error ({pub}): {e}")
    return []


# ── MS URL 查找 (Unpaywall) ───────────────────────────────────────────────────

def find_ms_oa(doi):
    try:
        r = sess.get(
            f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}",
            params={"email": OA_EMAIL}, timeout=15,
        )
        if r.status_code == 200:
            loc = r.json().get("best_oa_location") or {}
            return loc.get("url_for_pdf")
    except Exception as e:
        print(f"    Unpaywall error: {e}")
    return None


# ── 主流程 ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  00_INBOXS_AA — 扫描并生成 Surge 下载队列")
    print("=" * 65)

    items = zot.everything(zot.collection_items(INBOX_KEY, itemType="-attachment"))
    total = len(items)
    print(f"共 {total} 个条目\n{'─'*65}")

    # download_meta: {url: {key, type, fname}}
    download_meta = {}
    keyan = []

    for idx, item in enumerate(items, 1):
        key   = item["key"]
        data  = item["data"]
        doi   = data.get("DOI", "").strip()
        title = clean_title(data.get("title", "(无标题)"))
        pub   = get_publisher(doi)

        print(f"\n[{idx:3d}/{total}] {key}  [{pub}]  {title}")

        # ── Phase 1: 扫描现有 PDF ──────────────────────────────────────────
        children = zot.children(key)
        pdfs = [c for c in children
                if c["data"].get("itemType") == "attachment"
                and c["data"].get("contentType") == "application/pdf"]

        has_ms = has_si = False
        for p in pdfs:
            cls = classify_pdf(p)
            fn  = p["data"].get("filename") or p["data"].get("title", "")
            print(f"  已有 [{cls}]: {fn[:60]}")
            if cls == "MS": has_ms = True
            if cls == "SI": has_si = True

        if len(pdfs) == 1 and not has_ms and not has_si:
            has_ms = True

        print(f"  状态: MS={'✓' if has_ms else '✗'}  SI={'✓' if has_si else '✗'}")

        # ── Phase 2: 找 SI ──────────────────────────────────────────────────
        if not has_si and doi:
            si_urls = []
            if pub == "ACS":       si_urls = find_si_acs(doi)
            elif pub == "Elsevier":si_urls = find_si_elsevier(doi)
            elif pub == "RSC":     si_urls = find_si_rsc(doi)
            else:                  si_urls = find_si_from_page(doi, pub)

            for url, fname in si_urls:
                safe = re.sub(r'[<>:"/\\|?*]', "_", fname)
                target = f"{key}_SI_{safe}"
                download_meta[url] = {"key": key, "type": "SI", "fname": target}
                print(f"  SI URL: {url[:80]}")
                print(f"    → 保存为: {target}")

            if not si_urls:
                print("  → 未找到 SI URL")

        # ── Phase 3: 找 MS ──────────────────────────────────────────────────
        if not has_ms:
            if doi:
                print("  → 查找 OA MS (Unpaywall)...")
                oa_url = find_ms_oa(doi)
                if oa_url:
                    target = f"{key}_MS_ms.pdf"
                    download_meta[oa_url] = {"key": key, "type": "MS", "fname": target}
                    print(f"  MS OA URL: {oa_url[:80]}")
                    print(f"    → 保存为: {target}")
                else:
                    print("  → 无 OA 版本，加入科研通队列")
                    keyan.append({"key": key, "doi": doi, "title": title})
            else:
                print("  → 无 DOI，加入科研通队列")
                keyan.append({"key": key, "doi": "", "title": title})

        time.sleep(0.15)

    # ── 写输出文件 ─────────────────────────────────────────────────────────────
    with open(SURGE_FILE, "w", encoding="utf-8") as f:
        for url in download_meta:
            f.write(url + "\n")
    print(f"\n✅ Surge 下载列表已保存: {SURGE_FILE}  ({len(download_meta)} 个 URL)")

    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(download_meta, f, ensure_ascii=False, indent=2)
    print(f"✅ 元数据映射已保存: {META_FILE}")

    if keyan:
        with open(KYAN_FILE, "w", encoding="utf-8") as f:
            f.write("# 科研通队列 — 在 ablesci.com 提交 DOI 下载 MS\n")
            f.write("# KEY\tDOI\tTITLE\n\n")
            for item in keyan:
                f.write(f"{item['key']}\t{item['doi']}\t{item['title']}\n")
        print(f"✅ 科研通队列已保存: {KYAN_FILE}  ({len(keyan)} 条)")

    print(f"\n{'='*65}")
    print("下一步:")
    print(f"  1. 打开 Surge，导入 {SURGE_FILE}")
    print(f"  2. 设置下载目录为: {OUT_DIR}")
    print(f"  3. 下载完成后运行: uv run python scripts/inbox_upload_move.py")
    if keyan:
        print(f"  4. 查看 {KYAN_FILE}，在 ablesci.com 请求缺失的正文")


if __name__ == "__main__":
    main()
