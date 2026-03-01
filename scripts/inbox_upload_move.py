"""
00_INBOXS_AA Phase 2: 上传已下载文件 + 移动完整条目
====================================================
前提：
  - inbox_scan_queue.py 已生成 download_meta.json
  - Surge 已将所有文件下载到 .si-downloads/inbox/
  - 科研通下载的 MS PDF 也已放入同一目录，文件名为 {KEY}_MS_*.pdf

流程：
  1. 读取 download_meta.json
  2. 扫描下载目录，匹配文件到条目
  3. DOCX → PDF 转换
  4. 上传到 Zotero (双重超时补丁)
  5. 科研通 MS 文件也上传
  6. 重新扫描附件，MS ✓ 的条目移动到 00_AA
"""
import json
from pathlib import Path
import re

import httpx
import pyzotero.zotero as zotero
import win32com.client

# ── 配置 ──────────────────────────────────────────────────────────────────────
LIBRARY_ID = "5452188"
API_KEY    = "***ZOTERO_API_KEY***"
INBOX_KEY  = "2PSBFJEI"
AA_KEY     = "LTANQXA9"

DOWNLOAD_DIR = Path("F:/ICMAB-Data/UAB-Thesis/zotero-mcp/.si-downloads/inbox")
META_FILE    = DOWNLOAD_DIR / "download_meta.json"

SI_KEYWORDS = [
    "supporting", "supplementary", "supplem", "suppl", "esi",
    "_si_", "_si.", "-si.", "si_001", "si_002", "si_00",
    "supp_info", "additional", "_s1.", "_s2.", "supplement",
]

# ── 双重超时补丁 ──────────────────────────────────────────────────────────────
_orig_post = httpx.post
def _patched_post(*a, **kw):
    kw["timeout"] = httpx.Timeout(600.0, connect=60.0)
    return _orig_post(*a, **kw)
httpx.post = _patched_post

zot = zotero.Zotero(LIBRARY_ID, "user", API_KEY)
zot.client = httpx.Client(
    timeout=httpx.Timeout(600.0, connect=60.0),
    headers=dict(zot.client.headers),
)


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def docx_to_pdf(docx_path: Path) -> Path | None:
    pdf_path = docx_path.with_suffix(".pdf")
    word = None
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(str(docx_path.resolve()))
        doc.SaveAs(str(pdf_path.resolve()), FileFormat=17)
        doc.Close()
        print(f"    DOCX→PDF: {pdf_path.name}")
        return pdf_path
    except Exception as e:
        print(f"    DOCX→PDF failed: {e}")
        return None
    finally:
        if word:
            try: word.Quit()
            except: pass


def upload_to_zotero(filepath: Path, item_key: str) -> bool:
    try:
        result = zot.attachment_simple([str(filepath)], parentid=item_key)
        ok = bool(result.get("success") or result.get("unchanged"))
        if ok:
            print(f"    ✓ 上传成功: {filepath.name}")
        else:
            print(f"    ✗ 上传失败: {filepath.name}  {result}")
        return ok
    except Exception as e:
        print(f"    ✗ 上传错误: {e}")
        return False


def classify_pdf(att):
    fname = att["data"].get("filename", "").lower()
    title = att["data"].get("title", "").lower()
    for kw in SI_KEYWORDS:
        if kw in fname or kw in title:
            return "SI"
    return "MS"


def move_to_aa(key: str):
    try:
        fresh = zot.item(key)
        cols = fresh["data"].get("collections", [])
        new_cols = list(set(cols + [AA_KEY]) - {INBOX_KEY})
        zot.update_item({"key": key, "version": fresh["version"], "collections": new_cols})
        print("  → ✅ 移动到 00_AA")
        return True
    except Exception as e:
        print(f"  → ❌ 移动失败: {e}")
        return False


# ── 主流程 ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  00_INBOXS_AA Phase 2: 上传 + 移动")
    print("=" * 65)

    if not META_FILE.exists():
        print(f"❌ 找不到 {META_FILE}，请先运行 inbox_scan_queue.py")
        return

    meta = json.loads(META_FILE.read_text(encoding="utf-8"))
    print(f"元数据: {len(meta)} 个 URL\n")

    # ── Step 1: 处理 Surge 下载的文件（按 meta 匹配）─────────────────────────
    # meta 格式: {url: {key, type, fname}}
    # Surge 下载后文件名 = URL 最后一段；我们用 fname 中的 KEY_TYPE_ 前缀匹配
    all_files = {f.name: f for f in DOWNLOAD_DIR.iterdir() if f.is_file()}
    print(f"下载目录共 {len(all_files)} 个文件\n{'─'*65}")

    # 收集每个 item_key 需要上传的文件列表
    uploads: dict[str, list[Path]] = {}   # key → [filepath, ...]

    for url, info in meta.items():
        key   = info["key"]
        fname = info["fname"]   # e.g. "ITEMKEY_SI_mmc1.pdf"

        # 优先精确匹配 fname
        target_path = DOWNLOAD_DIR / fname
        if not target_path.exists():
            # Surge 可能用 URL 原始文件名保存，尝试匹配
            url_fname = url.split("/")[-1].split("?")[0]
            if url_fname in all_files:
                src = all_files[url_fname]
                src.rename(target_path)  # 重命名为标准名
            else:
                print(f"  [{key}] 未找到: {fname}（Surge 未下载或文件名不符）")
                continue

        uploads.setdefault(key, []).append(target_path)

    # ── Step 2: 处理科研通手动放入的文件（名称含 KEY_MS_）───────────────────
    for f in DOWNLOAD_DIR.iterdir():
        if not f.is_file():
            continue
        # 匹配 {KEY}_MS_{任意}.pdf 但不在 meta 中
        m = re.match(r"([A-Z0-9]{8})_MS_", f.name)
        if m:
            key = m.group(1)
            # 检查是否已在 uploads 中
            already = any(str(p) == str(f) for p in uploads.get(key, []))
            if not already:
                uploads.setdefault(key, []).append(f)
                print(f"  [{key}] 科研通 MS: {f.name}")

    print(f"\n共 {len(uploads)} 个条目有待上传文件\n{'─'*65}")

    # ── Step 3: 对每个条目：上传文件 → 检查完整性 → 移动 ───────────────────
    stats = dict(uploaded=0, moved=0, skipped=0)

    for key, files in uploads.items():
        print(f"\n[{key}]")
        upload_ok = False

        for fpath in files:
            # DOCX → PDF
            if fpath.suffix.lower() in (".docx", ".doc"):
                pdf_p = fpath.with_suffix(".pdf")
                if pdf_p.exists() and pdf_p.stat().st_size > 500:
                    fpath = pdf_p
                else:
                    converted = docx_to_pdf(fpath)
                    if converted:
                        fpath = converted

            ok = upload_to_zotero(fpath, key)
            if ok:
                upload_ok = True
                stats["uploaded"] += 1

        if not upload_ok:
            print("  → 所有文件上传失败，跳过移动")
            stats["skipped"] += 1
            continue

        # 重新检查该条目是否有 MS
        children = zot.children(key)
        pdfs = [c for c in children
                if c["data"].get("itemType") == "attachment"
                and c["data"].get("contentType") == "application/pdf"]

        has_ms = any(classify_pdf(p) == "MS" for p in pdfs)
        # 单 PDF 默认为 MS
        if len(pdfs) == 1 and not has_ms:
            has_ms = True

        if has_ms:
            if move_to_aa(key):
                stats["moved"] += 1
        else:
            print("  → 仍无 MS，不移动")

    # ── 汇总 ─────────────────────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print("完成！")
    print(f"  ✅ 文件上传     : {stats['uploaded']} 个")
    print(f"  ✅ 移动到 00_AA : {stats['moved']} 个条目")
    print(f"  ➖ 上传失败跳过 : {stats['skipped']} 个条目")


if __name__ == "__main__":
    main()
