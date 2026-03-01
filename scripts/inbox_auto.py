"""
00_INBOXS_AA 全自动流程
========================
1. 直接下载 meta.json 里的 SI/MS URL（Elsevier CDN、RSC、Nature 等）
2. 上传所有已下载文件到 Zotero，移动有 MS 的条目到 00_AA
3. 科研通 Playwright 自动化：为剩余缺 MS 的条目下载 + 上传 + 移动

运行:
    uv run python scripts/inbox_auto.py
"""
import json
from pathlib import Path
import re
import time

import httpx
from playwright.sync_api import sync_playwright
import pyzotero.zotero as zotero
import requests
import win32com.client

# ── 配置 ──────────────────────────────────────────────────────────────────────
LIBRARY_ID = "5452188"
API_KEY    = "***ZOTERO_API_KEY***"
INBOX_KEY  = "2PSBFJEI"
AA_KEY     = "LTANQXA9"

DOWNLOAD_DIR   = Path("F:/ICMAB-Data/UAB-Thesis/zotero-mcp/.si-downloads/inbox")
META_FILE      = DOWNLOAD_DIR / "download_meta.json"
KYAN_FILE      = DOWNLOAD_DIR / "keyan_queue.txt"
PLAYWRIGHT_DIR = Path("F:/ICMAB-Data/UAB-Thesis/zotero-mcp/.playwright-mcp")
PLAYWRIGHT_DIR.mkdir(parents=True, exist_ok=True)

SI_KEYWORDS = [
    "supporting", "supplementary", "supplem", "suppl", "esi",
    "_si_", "_si.", "-si.", "si_001", "si_002", "si_00",
    "supp_info", "additional", "_s1.", "_s2.", "supplement",
]

ABLESCI_EMAIL    = "liuchzzyy@gmail.com"
ABLESCI_PASSWORD = "***ABLESCI_PASSWORD***"

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

dl_sess = requests.Session()
dl_sess.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/pdf,application/octet-stream,*/*",
    "Referer": "https://www.sciencedirect.com/",
})


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def classify_pdf(att):
    fname = att["data"].get("filename", "").lower()
    title = att["data"].get("title", "").lower()
    for kw in SI_KEYWORDS:
        if kw in fname or kw in title:
            return "SI"
    return "MS"


def docx_to_pdf(docx_path: Path) -> Path | None:
    pdf_path = docx_path.with_suffix(".pdf")
    if pdf_path.exists() and pdf_path.stat().st_size > 500:
        return pdf_path
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
        print(f"    DOCX→PDF 失败: {e}")
        return None
    finally:
        if word:
            try: word.Quit()
            except: pass


def upload_to_zotero(filepath: Path, item_key: str) -> bool:
    try:
        result = zot.attachment_simple([str(filepath)], parentid=item_key)
        ok = bool(result.get("success") or result.get("unchanged"))
        status = "✓" if ok else "✗"
        print(f"    {status} 上传{'成功' if ok else '失败'}: {filepath.name}")
        if not ok:
            print(f"      {result}")
        return ok
    except Exception as e:
        print(f"    ✗ 上传错误: {e}")
        return False


def move_to_aa(key: str) -> bool:
    try:
        fresh = zot.item(key)
        cols  = fresh["data"].get("collections", [])
        new_cols = list(set(cols + [AA_KEY]) - {INBOX_KEY})
        zot.update_item({"key": key, "version": fresh["version"], "collections": new_cols})
        print("  → ✅ 移动到 00_AA")
        return True
    except Exception as e:
        print(f"  → ❌ 移动失败: {e}")
        return False


def item_has_ms(key: str) -> bool:
    """检查 Zotero 中该条目是否已有 MS（主文）"""
    children = zot.children(key)
    pdfs = [c for c in children
            if c["data"].get("itemType") == "attachment"
            and c["data"].get("contentType") == "application/pdf"]
    has_ms = any(classify_pdf(p) == "MS" for p in pdfs)
    if len(pdfs) == 1 and not has_ms:
        has_ms = True  # 单 PDF 默认为 MS
    return has_ms


def item_in_inbox(key: str) -> bool:
    """确认条目仍在 00_INBOXS_AA"""
    try:
        item = zot.item(key)
        return INBOX_KEY in item["data"].get("collections", [])
    except:
        return False


# ── Phase 1: 直接下载 ─────────────────────────────────────────────────────────

def direct_download_file(url: str, dest: Path, timeout=45) -> str:
    """下载单个文件，返回 'ok' / 'not_found' / 'blocked' / 'timeout' / 'err:{msg}'"""
    if dest.exists() and dest.stat().st_size > 500:
        return "cached"
    try:
        r = dl_sess.get(url, timeout=timeout, stream=True)
        if r.status_code == 404:
            return "not_found"
        if r.status_code != 200:
            return f"http_{r.status_code}"
        with open(dest, "wb") as f:
            for chunk in r.iter_content(65536):
                f.write(chunk)
        with open(dest, "rb") as f:
            hdr = f.read(8)
        if hdr[:5].lower() in (b"<html", b"<!doc"):
            dest.unlink()
            return "blocked"
        if dest.stat().st_size < 500:
            dest.unlink()
            return "too_small"
        return "ok"
    except requests.exceptions.Timeout:
        return "timeout"
    except Exception as e:
        return f"err:{e}"


def phase1_direct_download(meta: dict) -> dict[str, list[Path]]:
    """下载 meta.json 里的所有文件，返回 {key: [Path,...]}"""
    print("\n" + "="*65)
    print("  Phase 1: 直接下载 SI/MS 文件")
    print("="*65)

    uploads: dict[str, list[Path]] = {}
    from collections import Counter
    stats = Counter()

    for url, info in meta.items():
        key   = info["key"]
        fname = info["fname"]
        dest  = DOWNLOAD_DIR / fname

        status = direct_download_file(url, dest)
        stats[status] += 1

        if status in ("ok", "cached"):
            uploads.setdefault(key, []).append(dest)
            flag = "✓" if status == "ok" else "·"
            print(f"  {flag} [{key}] {fname} ({dest.stat().st_size//1024}KB)", flush=True)
        elif status == "timeout":
            # 重试一次，更长超时
            print(f"  ↺ [{key}] 超时，重试 {fname}...", end="", flush=True)
            status2 = direct_download_file(url, dest, timeout=90)
            if status2 in ("ok", "cached"):
                uploads.setdefault(key, []).append(dest)
                print(f" ✓ ({dest.stat().st_size//1024}KB)")
                stats["ok_retry"] += 1
                stats["timeout"] -= 1
            else:
                print(f" ✗ ({status2})")
        elif status != "not_found":
            print(f"  ✗ [{key}] {status}: {url[:60]}", flush=True)

        time.sleep(0.1)

    print("\n  结果:", flush=True)
    for k, v in sorted(stats.items()):
        print(f"    {k:15s}: {v}")
    print(f"  成功条目数: {len(uploads)}")
    return uploads


# ── Phase 2: 上传 + 移动（已下载文件）──────────────────────────────────────────

def phase2_upload_move(all_uploads: dict[str, list[Path]]) -> set[str]:
    """上传文件并移动有 MS 的条目，返回已成功移动的 key 集合"""
    print("\n" + "="*65)
    print(f"  Phase 2: 上传 + 移动（{len(all_uploads)} 个条目）")
    print("="*65)

    moved_keys: set[str] = set()
    stats = dict(uploaded=0, moved=0, skipped=0)

    for key, files in all_uploads.items():
        print(f"\n[{key}]", flush=True)

        if not item_in_inbox(key):
            print("  → 条目不在 INBOXS_AA，跳过")
            continue

        upload_ok = False
        for fpath in files:
            if fpath.suffix.lower() in (".docx", ".doc"):
                converted = docx_to_pdf(fpath)
                if converted:
                    fpath = converted

            ok = upload_to_zotero(fpath, key)
            if ok:
                upload_ok = True
                stats["uploaded"] += 1

        if not upload_ok:
            print("  → 所有文件上传失败，跳过")
            stats["skipped"] += 1
            continue

        if item_has_ms(key):
            if move_to_aa(key):
                stats["moved"] += 1
                moved_keys.add(key)
        else:
            print("  → 仍无 MS（已上传 SI），等待科研通")

    print(f"\n  ✅ 上传: {stats['uploaded']}个  已移动: {stats['moved']}个  跳过: {stats['skipped']}个")
    return moved_keys


# ── Phase 3: 科研通 Playwright 自动化 ────────────────────────────────────────

def ablesci_login(page) -> bool:
    print("  登录科研通...", flush=True)
    page.goto("https://www.ablesci.com/site/login")
    page.wait_for_timeout(2000)
    try:
        page.get_by_placeholder("邮箱").fill(ABLESCI_EMAIL)
        page.get_by_placeholder("密码").fill(ABLESCI_PASSWORD)
    except:
        # 备用: 按顺序填写
        inputs = page.locator("input[type=email], input[type=text]").first
        inputs.fill(ABLESCI_EMAIL)
        page.locator("input[type=password]").fill(ABLESCI_PASSWORD)
    page.get_by_text("登 录").click()
    page.wait_for_timeout(3000)
    print("  ✓ 登录完成", flush=True)
    return True


def ablesci_clear_pending(page):
    """清空已上传待确认列表（防止积压）"""
    page.goto("https://www.ablesci.com/my/assist-my?status=uploaded")
    page.wait_for_timeout(2000)
    content = page.content()
    if "/assist/download?id=" not in content:
        return  # 队列为空
    print("  清空待确认队列...", flush=True)
    try:
        page.get_by_text("全选").click()
        page.wait_for_timeout(500)
        page.get_by_role("button", name="批量采纳所选项").click()
        page.wait_for_timeout(1000)
        page.get_by_text("确定").click()
        page.wait_for_timeout(3000)
        print("  ✓ 队列已清空", flush=True)
    except Exception as e:
        print(f"  ⚠ 清空队列失败: {e}", flush=True)


def ablesci_submit_doi(page, doi: str) -> bool:
    """提交 DOI，返回是否成功"""
    page.goto("https://www.ablesci.com/assist/create")
    page.wait_for_timeout(2000)
    try:
        page.get_by_placeholder("请输入DOI、PMID 或 标题").fill(doi)
        page.get_by_text("智能提取文献信息").click()
        page.wait_for_timeout(4000)
        # 检测 popup
        try:
            btn = page.get_by_text("信息正确，直接发布")
            if btn.is_visible(timeout=3000):
                btn.click()
                page.wait_for_timeout(2000)
                return True
        except:
            pass
        # 备用：直接发布
        page.get_by_role("button", name="立即发布").click()
        page.wait_for_timeout(2000)
        return True
    except Exception as e:
        print(f"    提交失败: {e}", flush=True)
        return False


def ablesci_wait_and_get_id(page, timeout_min=8) -> str | None:
    """等待文件上传完成，返回 download_id"""
    deadline = time.time() + timeout_min * 60
    while time.time() < deadline:
        page.goto("https://www.ablesci.com/my/assist-my?status=uploaded")
        page.wait_for_timeout(3000)
        content = page.content()
        ids = re.findall(r'/assist/download\?id=(\d+)', content)
        if ids:
            return ids[0]
        remaining = int((deadline - time.time()) / 60)
        print(f"    等待上传... ({remaining}min)", flush=True)
        time.sleep(40)
    return None


def ablesci_accept_download(page, download_id: str, save_path: Path) -> bool:
    """采纳 + 下载文件"""
    # 采纳
    page.goto("https://www.ablesci.com/my/assist-my?status=uploaded")
    page.wait_for_timeout(2000)
    try:
        page.get_by_text("全选").click()
        page.wait_for_timeout(500)
        page.get_by_role("button", name="批量采纳所选项").click()
        page.wait_for_timeout(1000)
        page.get_by_text("确定").click()
        page.wait_for_timeout(3000)
        print("    ✓ 已采纳", flush=True)
    except Exception as e:
        print(f"    ⚠ 采纳操作: {e}", flush=True)

    # 下载：先设置监听，再导航
    print(f"    下载 id={download_id}...", flush=True)
    try:
        with page.expect_download(timeout=900000) as dl_info:
            page.goto(
                f"https://www.ablesci.com/assist/download?id={download_id}",
                wait_until="commit",
                timeout=15000,
            )
        dl = dl_info.value
        failure = dl.failure()
        if failure:
            print(f"    ✗ 下载失败: {failure}", flush=True)
            return False
        dl.save_as(str(save_path))
        print(f"    ✓ 下载完成: {save_path.name} ({save_path.stat().st_size//1024}KB)", flush=True)
        return True
    except Exception as e:
        print(f"    ✗ 下载错误: {e}", flush=True)
        return False


def phase3_keyan(keyan_items: list, already_moved: set) -> dict[str, list[Path]]:
    """科研通自动化下载 MS PDF，返回 {key: [Path]}"""
    # 过滤：去掉已移动的、已有 MS 的
    pending = []
    for item in keyan_items:
        key = item["key"]
        if key in already_moved:
            continue
        if not item_in_inbox(key):
            continue
        if item_has_ms(key):
            print(f"  [{key}] Zotero 已有 MS，跳过", flush=True)
            continue
        pending.append(item)

    total = len(pending)
    print("\n" + "="*65)
    print(f"  Phase 3: 科研通自动化（{total} 条目）")
    print("="*65)

    if not pending:
        print("  无需处理")
        return {}

    ms_uploads: dict[str, list[Path]] = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        ctx = browser.new_context(accept_downloads=True)
        page = ctx.new_page()

        ablesci_login(page)
        ablesci_clear_pending(page)

        for idx, item in enumerate(pending, 1):
            key   = item["key"]
            doi   = item["doi"]
            title = item.get("title", "")[:55]

            print(f"\n[{idx:2d}/{total}] [{key}] {title}", flush=True)
            print(f"  DOI: {doi}", flush=True)

            if not doi:
                print("  跳过: 无 DOI", flush=True)
                continue

            # 提交 DOI
            ok = ablesci_submit_doi(page, doi)
            if not ok:
                print("  ✗ 提交失败", flush=True)
                continue

            # 等待上传
            download_id = ablesci_wait_and_get_id(page)
            if not download_id:
                print("  ✗ 超时未上传", flush=True)
                continue

            # 下载
            save_path = PLAYWRIGHT_DIR / f"ms_{key}.pdf"
            if not ablesci_accept_download(page, download_id, save_path):
                continue

            # 移到 inbox dir
            dest = DOWNLOAD_DIR / f"{key}_MS_{save_path.name}"
            save_path.rename(dest)
            ms_uploads.setdefault(key, []).append(dest)
            print(f"  → 保存: {dest.name}", flush=True)

            # 上传到 Zotero + 移动
            print("  上传并移动...", flush=True)
            ok_upload = upload_to_zotero(dest, key)
            if ok_upload:
                if item_has_ms(key):
                    move_to_aa(key)

        browser.close()

    print(f"\n  科研通下载: {len(ms_uploads)} 个条目")
    return ms_uploads


# ── 主流程 ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  00_INBOXS_AA 全自动流程")
    print("=" * 65)

    if not META_FILE.exists():
        print(f"❌ 找不到 {META_FILE}，请先运行 inbox_scan_queue.py")
        return

    meta = json.loads(META_FILE.read_text(encoding="utf-8"))
    print(f"meta.json: {len(meta)} 个 URL")

    # ── Phase 1: 直接下载 SI/MS ──────────────────────────────────────────────
    all_uploads = phase1_direct_download(meta)

    # ── Phase 2: 上传 + 移动已下载文件 ───────────────────────────────────────
    moved_keys: set[str] = set()
    if all_uploads:
        moved_keys = phase2_upload_move(all_uploads)
    else:
        print("\n  Phase 1 无文件下载，跳过 Phase 2")

    # ── Phase 3: 科研通（缺 MS 的条目）───────────────────────────────────────
    keyan_items = []
    if KYAN_FILE.exists():
        for line in KYAN_FILE.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                keyan_items.append({
                    "key":   parts[0].strip(),
                    "doi":   parts[1].strip(),
                    "title": parts[2].strip() if len(parts) > 2 else "",
                })
        print(f"\nkeyan_queue.txt: {len(keyan_items)} 个待 MS 条目")

    if keyan_items:
        phase3_keyan(keyan_items, moved_keys)

    print("\n" + "="*65)
    print("全部完成！")
    print("="*65)


if __name__ == "__main__":
    main()
