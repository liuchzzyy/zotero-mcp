"""
download_wiley_dd_si.py
=======================
Try to fetch SI for the 10 Wiley items blocked during download_dd_si.py.
Reads DOIs from dd_blocked.txt (wiley lines), looks them up in Zotero,
scrapes Wiley article pages for SI links, downloads and uploads.

If Cloudflare blocks: saves URL to dd_wiley_blocked.txt for manual VPN download.

Usage:
    cd zotero-mcp
    uv run python scripts/download_wiley_dd_si.py
"""
import os
import re
import time
import requests
import pyzotero.zotero as zotero
import httpx
from pathlib import Path
from dotenv import load_dotenv

PROJECT = Path(__file__).parent.parent
load_dotenv(PROJECT / '.env')

LIBRARY_ID   = os.environ['ZOTERO_LIBRARY_ID']
API_KEY      = os.environ['ZOTERO_API_KEY']
SI_DIR       = Path(os.environ.get('SHORTTERMS_SI_DIR',
                    str(PROJECT / '.si-downloads/shortterms')))
BLOCKED_IN   = PROJECT / '.si-downloads/dd_blocked.txt'
BLOCKED_OUT  = PROJECT / '.si-downloads/dd_wiley_blocked.txt'
SI_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXT   = {'.pdf', '.docx', '.doc'}
OLE_MAGIC     = b'\xd0\xcf\x11\xe0'
HEADERS       = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
}

# ── Zotero client ─────────────────────────────────────────────────────────────
_orig_post = httpx.post
def _post_timeout(*a, **kw):
    kw['timeout'] = httpx.Timeout(600.0, connect=60.0)
    return _orig_post(*a, **kw)
httpx.post = _post_timeout

zot = zotero.Zotero(LIBRARY_ID, 'user', API_KEY)
zot.client = httpx.Client(
    timeout=httpx.Timeout(600.0, connect=60.0),
    headers=dict(zot.client.headers),
)

# ── Helpers ────────────────────────────────────────────────────────────────────
_DD_ITEMS: list[dict] | None = None

def _load_dd_items() -> list[dict]:
    global _DD_ITEMS
    if _DD_ITEMS is None:
        print('Loading 00_INBOXS_DD items...')
        col_key = next(c['key'] for c in zot.collections()
                       if c['data']['name'] == '00_INBOXS_DD')
        raw = zot.everything(zot.collection_items(col_key, itemType='-attachment'))
        _DD_ITEMS = [i for i in raw if i['data'].get('itemType') != 'note']
        print(f'  {len(_DD_ITEMS)} items loaded\n')
    return _DD_ITEMS


def find_item_by_doi(doi: str) -> dict | None:
    for item in _load_dd_items():
        if item['data'].get('DOI', '').lower() == doi.lower():
            return item
    return None


def find_wiley_si(doi: str) -> list[tuple[str, str]]:
    """Scrape Wiley article page for SI download links."""
    url = f'https://onlinelibrary.wiley.com/doi/{doi}'
    try:
        r = requests.get(url, timeout=25, allow_redirects=True, headers=HEADERS)
        if r.status_code != 200:
            return []
        content_low = r.content[:3000].lower()
        if b'challenge' in content_low or b'cf-ray' in str(r.headers).lower().encode():
            return []

        results = []
        # Pattern 1: /action/downloadSupplement
        hits = re.findall(r'href="(/action/downloadSupplement\?[^"]+)"', r.text, re.I)
        for path in hits:
            si_url = f'https://onlinelibrary.wiley.com{path}'
            fname_m = re.search(r'file=([^&"]+)', path)
            fname = fname_m.group(1) if fname_m else path.split('=')[-1]
            if Path(fname).suffix.lower() in ALLOWED_EXT:
                results.append((si_url, fname))

        # Pattern 2: direct suppdata links
        if not results:
            direct = re.findall(
                r'href="(https://[^"]*onlinelibrary\.wiley\.com[^"]+\.(pdf|docx))"',
                r.text, re.I)
            for si_url, _ in direct:
                if 'suppdat' in si_url.lower() or 'supplement' in si_url.lower():
                    results.append((si_url, si_url.split('/')[-1].split('?')[0]))

        return results
    except Exception as e:
        print(f'    scrape error: {e}')
        return []


def download(url: str, dest: Path) -> tuple[bool, float]:
    try:
        r = requests.get(url, timeout=120, stream=True, headers=HEADERS)
        if r.status_code != 200:
            return False, 0.0
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(65536):
                f.write(chunk)
        size_mb = dest.stat().st_size / 1024 / 1024
        with open(dest, 'rb') as f:
            magic = f.read(8)
        if magic[:5].lower() in (b'<html', b'<!doc', b'<?xml'):
            dest.unlink()
            return False, 0.0
        return True, size_mb
    except Exception:
        if dest.exists():
            dest.unlink()
        return False, 0.0


def docx_to_pdf(docx_path: Path) -> Path | None:
    import win32com.client
    pdf_path  = docx_path.with_suffix('.pdf')
    open_path = docx_path
    if docx_path.suffix.lower() == '.docx':
        with open(docx_path, 'rb') as f:
            if f.read(4) == OLE_MAGIC:
                open_path = docx_path.with_suffix('.doc')
                docx_path.rename(open_path)
    word = None
    try:
        word = win32com.client.Dispatch('Word.Application')
        word.Visible = False
        doc = word.Documents.Open(str(open_path.resolve()))
        doc.SaveAs(str(pdf_path.resolve()), FileFormat=17)
        doc.Close()
        return pdf_path
    except Exception as e:
        print(f'    DOCX→PDF failed: {e}')
        return None
    finally:
        if word:
            try: word.Quit()
            except: pass


def upload_files(files: list[Path], item_key: str) -> int:
    n = 0
    for path in files:
        try:
            result = zot.attachment_simple([str(path)], parentid=item_key)
            if result.get('success') or result.get('unchanged'):
                label = 'unchanged' if result.get('unchanged') else 'uploaded'
                print(f'    ✓ {label}: {path.name}')
                n += 1
            else:
                print(f'    ✗ upload failed: {path.name} | {result}')
        except Exception as e:
            print(f'    ✗ upload error: {str(e)[:80]}')
    return n

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    # Read Wiley DOIs from blocked file
    wiley_dois = []
    for line in BLOCKED_IN.read_text(encoding='utf-8').splitlines():
        parts = line.strip().split('\t')
        if len(parts) >= 2 and parts[1].strip() == 'wiley':
            wiley_dois.append(parts[0].strip())

    print(f'Wiley DOIs from dd_blocked.txt: {len(wiley_dois)}\n')

    uploaded = 0
    blocked  = 0

    for idx, doi in enumerate(wiley_dois, 1):
        print(f'\n[{idx:02d}/{len(wiley_dois)}] {doi}')

        # Find item in Zotero
        item = find_item_by_doi(doi)
        if not item:
            print('  ✗ 未在 Zotero 中找到条目')
            blocked += 1
            continue

        key   = item['key']
        title = re.sub(r'<[^>]+>', '', item['data'].get('title', ''))[:60]
        print(f'  [{key}] {title}')

        # Find SI links
        print('  🔍 抓取 Wiley 页面...')
        hits = find_wiley_si(doi)
        if not hits:
            print('  ⚠️  Cloudflare 阻断，记录到 blocked')
            with open(BLOCKED_OUT, 'a') as f:
                f.write(f'{doi}\thttps://onlinelibrary.wiley.com/doi/{doi}\n')
            blocked += 1
            time.sleep(1)
            continue

        print(f'  找到 {len(hits)} 个 SI 链接')
        to_upload: list[Path] = []
        for url, fname in hits:
            ext  = Path(fname).suffix.lower()
            if ext not in ALLOWED_EXT:
                continue
            dest = SI_DIR / f'{key}_{fname}'
            if dest.exists() and dest.stat().st_size > 500:
                print(f'  已缓存: {fname}')
            else:
                ok, sz = download(url, dest)
                if not ok:
                    print(f'  ✗ 下载被阻断: {fname}')
                    with open(BLOCKED_OUT, 'a') as f:
                        f.write(f'{doi}\t{url}\n')
                    blocked += 1
                    continue
                print(f'  ✓ 下载: {fname} ({sz:.1f}MB)')
            if ext in ('.docx', '.doc'):
                to_upload.append(docx_to_pdf(dest) or dest)
            else:
                to_upload.append(dest)

        if to_upload:
            n = upload_files(to_upload, key)
            uploaded += n

        time.sleep(1)

    print(f'\n{"="*60}')
    print(f'完成：uploaded={uploaded}  blocked/failed={blocked}')
    if BLOCKED_OUT.exists():
        n = len(BLOCKED_OUT.read_text().strip().splitlines())
        print(f'手动下载列表 ({n} 条): {BLOCKED_OUT}')


if __name__ == '__main__':
    main()
