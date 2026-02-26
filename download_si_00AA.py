"""
Download Supporting Information (SI) for 00_AA collection items from ACS via figshare public API.
Only downloads PDF and DOCX files. DOCX is converted to PDF via win32com before upload.
"""
import os
import time
import requests
import urllib.parse
import pyzotero.zotero as zotero
import httpx
from pathlib import Path

# Config
ZOTERO_LIB = '5452188'
ZOTERO_KEY = '***ZOTERO_API_KEY***'
COLLECTION_KEY = 'LTANQXA9'
SI_DIR = Path(__file__).parent / '.si-downloads' / '00_AA'
SI_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXT = {'.pdf', '.docx', '.doc'}

zot = zotero.Zotero(ZOTERO_LIB, 'user', ZOTERO_KEY)
zot.client = httpx.Client(timeout=600, headers=zot.default_headers())


def get_figshare_si(doi):
    """Query figshare public API for SI files."""
    encoded = urllib.parse.quote(doi, safe='')
    url = (f'https://widgets.figshare.com/public/files'
           f'?institution=acs&limit=21&offset=0&collectionResourceDOI={encoded}')
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            return r.json().get('files', [])
    except Exception as e:
        print(f'    figshare API error: {e}')
    return []


def download_file(url, dest_path):
    """Download file to dest_path. Returns (ok, size_mb)."""
    try:
        r = requests.get(url, timeout=120, stream=True)
        if r.status_code != 200:
            return False, 0
        with open(dest_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
        size_mb = os.path.getsize(dest_path) / 1024 / 1024
        # Reject HTML responses (Cloudflare block)
        with open(dest_path, 'rb') as f:
            header = f.read(8)
        if header[:5].lower() in (b'<html', b'<!doc'):
            os.remove(dest_path)
            return False, 0
        return True, size_mb
    except Exception:
        return False, 0


def docx_to_pdf(docx_path):
    """Convert a DOCX file to PDF using win32com. Returns PDF path or None."""
    import win32com.client
    pdf_path = docx_path.with_suffix('.pdf')
    word = None
    try:
        word = win32com.client.Dispatch('Word.Application')
        word.Visible = False
        doc = word.Documents.Open(str(docx_path.resolve()))
        doc.SaveAs(str(pdf_path.resolve()), FileFormat=17)  # 17 = wdFormatPDF
        doc.Close()
        print(f'    Converted to PDF: {pdf_path.name}')
        return pdf_path
    except Exception as e:
        print(f'    DOCX->PDF conversion failed: {e}')
        return None
    finally:
        if word:
            try:
                word.Quit()
            except:
                pass


def has_si_attachment(item_key):
    """Check if item already has a SI-like attachment."""
    try:
        children = zot.children(item_key)
        si_keywords = ['supporting', 'suppl', '_si_', '_si.', 'si_001', 'si_002', 'supp_']
        for c in children:
            if c['data'].get('itemType') == 'attachment':
                title = c['data'].get('title', '').lower()
                fname = c['data'].get('filename', '').lower()
                if any(kw in title or kw in fname for kw in si_keywords):
                    return True
        return False
    except:
        return False


def upload_files_to_zotero(filepaths, item_key):
    """Upload list of files to a Zotero item. Returns success count."""
    success = 0
    for fpath in filepaths:
        try:
            result = zot.attachment_simple([str(fpath)], parentid=item_key)
            if result.get('success'):
                print(f'    ✓ Uploaded: {fpath.name}')
                success += 1
            elif result.get('unchanged'):
                print(f'    ✓ Already in Zotero (unchanged): {fpath.name}')
                success += 1
            else:
                print(f'    ✗ Upload failed: {fpath.name} | {result}')
        except Exception as e:
            print(f'    ✗ Upload error ({fpath.name}): {str(e)[:120]}')
    return success


def process_item(item, idx, total):
    """Process one Zotero item: find SI -> download PDF/DOCX -> convert if needed -> upload."""
    d = item['data']
    key = item['key']
    doi = d.get('DOI', '')
    title = (d.get('title', '')
             .replace('<sub>', '').replace('</sub>', '')
             .replace('<i>', '').replace('</i>', '')
             .replace('<sup>', '').replace('</sup>', ''))[:55]

    print(f'\n[{idx:02d}/{total}] [{key}] {title}')
    print(f'  DOI: {doi}')

    if not doi:
        print('  SKIP: no DOI')
        return 'skip_no_doi'

    if has_si_attachment(key):
        print('  SKIP: already has SI')
        return 'skip_has_si'

    # Query figshare
    all_files = get_figshare_si(doi)
    if not all_files:
        print('  No SI on figshare')
        return 'no_si'

    # Filter: only PDF and DOCX; deduplicate by file name
    seen_names = set()
    filtered = []
    for f in all_files:
        if Path(f['name']).suffix.lower() in ALLOWED_EXT and f['name'] not in seen_names:
            seen_names.add(f['name'])
            filtered.append(f)
    files = filtered
    skipped = [f['name'] for f in all_files if f not in files]
    if skipped:
        print(f'  Skipping non-PDF/DOCX: {skipped}')
    if not files:
        print(f'  No PDF/DOCX SI found (only {[f["name"] for f in all_files]})')
        return 'no_si_pdf'

    print(f'  Files to get: {[f["name"] for f in files]}')

    # Download
    to_upload = []
    for fi in files:
        fname = fi['name']
        suffix = Path(fname).suffix.lower()
        dest = SI_DIR / f'{key}_{fname}'

        # Skip if already done
        if dest.exists() and dest.stat().st_size > 500:
            print(f'  Already downloaded: {fname}')
        else:
            size_mb = fi.get('size', 0) / 1024 / 1024
            print(f'  Downloading {fname} ({size_mb:.1f} MB)...', end='', flush=True)
            ok, actual = download_file(fi['downloadUrl'], dest)
            if not ok:
                print(' ✗ FAILED')
                continue
            print(f' ✓ {actual:.1f} MB')

        # Convert DOCX -> PDF
        if suffix in ('.docx', '.doc'):
            pdf_dest = dest.with_suffix('.pdf')
            if pdf_dest.exists() and pdf_dest.stat().st_size > 500:
                print(f'  Already converted: {pdf_dest.name}')
                to_upload.append(pdf_dest)
            else:
                converted = docx_to_pdf(dest)
                if converted:
                    to_upload.append(converted)
                else:
                    print(f'  Falling back to DOCX upload')
                    to_upload.append(dest)
        else:
            to_upload.append(dest)

    if not to_upload:
        return 'download_failed'

    # Upload to Zotero
    print(f'  Uploading {len(to_upload)} file(s)...')
    n = upload_files_to_zotero(to_upload, key)
    return 'success' if n > 0 else 'upload_failed'


def main():
    print('=== ACS SI Downloader (figshare) for 00_AA ===')
    print(f'Output: {SI_DIR}')

    items = zot.collection_items(COLLECTION_KEY, itemType='-attachment')
    total = len(items)
    print(f'Total items: {total}')

    stats = {}
    for idx, item in enumerate(items, 1):
        status = process_item(item, idx, total)
        stats[status] = stats.get(status, 0) + 1
        time.sleep(0.3)

    print('\n=== SUMMARY ===')
    for k, v in sorted(stats.items()):
        print(f'  {k:20s}: {v}')


if __name__ == '__main__':
    main()
