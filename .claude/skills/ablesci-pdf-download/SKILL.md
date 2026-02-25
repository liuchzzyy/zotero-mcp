---
name: ablesci-pdf-download
description: Use when downloading full-text PDFs for Zotero items via ablesci.com (科研通). Trigger on "ablesci", "科研通", "文献互助", "download PDFs for inbox items", or batch PDF acquisition for literature items without attachments.
---

# Ablesci PDF Download via Playwright

Download full-text PDFs from https://www.ablesci.com using Playwright MCP browser automation, then upload to Zotero.

## Prerequisites

- Playwright MCP browser available
- Zotero API credentials in `.env` (ZOTERO_LIBRARY_ID, ZOTERO_API_KEY)
- `pyzotero` installed

## Login

Playwright browser does NOT share cookies with the user's browser. Auto-login before starting:

- **URL**: `https://www.ablesci.com/site/login` (note: `/login` returns 404)
- **Account**: `liuchzzyy@gmail.com`
- **Password**: `***ABLESCI_PASSWORD***`

### Login Steps
1. Navigate to `https://www.ablesci.com/site/login` (note: `/login` returns 404)
2. If already on homepage, click "登录" link in header
3. Find email input and type: `liuchzzyy@gmail.com`
4. Find password input and type: `***ABLESCI_PASSWORD***`
5. Click "登 录" button (may need JavaScript due to overlay issues)
6. Wait 2s, verify login success (redirect to homepage, look for user avatar)

## Points System

- Each request costs **10 points**
- Batch mode requires **500+ points** (not available if below)
- **IMPORTANT**: When points < 500, you cannot submit new requests if you have any "待确认" (pending confirmation) items. Must accept/reject all pending items first.
- Check balance: visible on sidebar "当前拥有 X 积分"
- Daily sign-in gives 10 points (button: "今日打卡签到")
- Always calculate max requests before starting: `points / 10`

## CRITICAL: Use Snapshot/Click, NOT run_code

`browser_run_code` with generic CSS selectors **FAILS** on ablesci.com (SPA with dynamic rendering). Always use the `browser_snapshot` + `browser_click` approach with `ref=` attributes.

**Exception:** Use `browser_run_code` ONLY for the download step (see Step 3 below), where Playwright download interception is required.

## Workflow: Single Item Complete Loop (RECOMMENDED)

**Important**: Process items ONE BY ONE. Do NOT batch submit all DOIs first.
For each item: submit → wait → accept → download → upload → next item.

**Before starting the loop: Login ONCE**
1. Navigate to `https://www.ablesci.com/site/login`
2. Type email: `liuchzzyy@gmail.com`, password: `***ABLESCI_PASSWORD***`
3. Click "登 录" button, wait 2s, verify login

### Single Item Loop (Repeat for each DOI)

**Step 1: Submit DOI**
1. **Navigate** to `/assist/create`
2. **Snapshot** to get refs
3. **Type** DOI in quick-input textbox: `textbox "请输入DOI、PMID 或 标题"`
4. **Click** "智能提取文献信息" button
5. **Wait** for auto-fill popup (usually instant)
6. **Snapshot** to see popup with extracted info
7. **Click** "信息正确，直接发布" button in popup (exact text: `信息正确，直接发布`)
   - If no popup appears, click `button "立即发布"` on the main form instead
8. **Snapshot** — success message appears, click "查看求助详情"

**Step 2: Wait for File Upload**
- Community members upload files (usually within **seconds to minutes**)
- Navigate to `/my/assist-my?status=uploaded` to check status
- Wait until you see the item with "待确认" status and a PDF link
- If still "求助中", wait 30–60 seconds and refresh

**Step 3: Accept**

1. **Navigate** to `/my/assist-my?status=uploaded`
2. **Click** "全选" checkbox area (ref contains `全选` text)
3. **Click** "批量采纳所选项" button
4. **Click** "确定" in confirmation popup
5. **Wait** for "批量采纳处理完毕" message (shows success count)

**Step 4: Download — MUST use browser_run_code with download interception**

⚠️ **CRITICAL**: Do NOT use `browser_navigate` to the `/assist/download?id=XXX` page.
The page auto-triggers a browser download via 高速通道 which **freezes Playwright and kills the MCP connection**.

⚠️ **CRITICAL**: Do NOT use Python `requests` with the token URL — the download token requires full browser session state and returns HTML when accessed outside the browser.

**Correct approach**: Use `browser_run_code` with Playwright's `waitForEvent('download')` + `saveAs()`. The browser handles the download natively (including cookies/session), we just intercept it and save to our path. Timeout is 15 minutes to handle slow servers or large files:

```javascript
// browser_run_code — WORKING PATTERN (tested 2026-02-24)
// Key: set up listener FIRST, then navigate with .catch() to ignore navigation timeout
async (page) => {
  const downloadId = 'DOWNLOAD_ID';  // e.g. 'zBeoY2' from /assist/download?id=zBeoY2
  const savePath = 'F:/ICMAB-Data/UAB-Thesis/zotero-mcp/.playwright-mcp/item-N.pdf';

  // 1. Set up download listener BEFORE navigating
  const downloadPromise = page.waitForEvent('download', { timeout: 900000 });

  // 2. Navigate but ignore timeout — download pages often don't fire 'load'
  page.goto(`https://www.ablesci.com/assist/download?id=${downloadId}`, {
    waitUntil: 'commit',
    timeout: 10000
  }).catch(() => {});  // intentionally ignore navigation timeout

  // 3. Wait for download to start (browser handles auth automatically)
  const download = await downloadPromise;

  // 4. Save to our path (waits for full download to complete)
  await download.saveAs(savePath);

  const failure = await download.failure();
  return {
    path: savePath,
    filename: download.suggestedFilename(),
    failed: failure  // null = success
  };
}
```

**Why `Promise.all` fails**: Using `Promise.all([waitForEvent, page.goto()])` causes the download to be cancelled when goto resolves. Always use the sequential pattern above instead.

**How to get the download ID**: From the "待确认" list page snapshot, the PDF link shows `/assist/download?id=XXXX`. Extract this ID **before** clicking accept (note it from the snapshot), or from the detail page after accepting.

**Step 5: Upload to Zotero**

Files saved to `.playwright-mcp/` directory. Use pyzotero with patched timeout + collection-scoped DOI search:

```python
import httpx, os
from pyzotero import zotero

API_KEY = '***ZOTERO_API_KEY***'
LIBRARY_ID = '5452188'
COLLECTION_KEY = 'NVL3QTP6'  # target collection key
headers = {"Zotero-API-Key": API_KEY}

target_doi = '10.xxxx/xxxxx'
pdf_path = os.path.abspath('.playwright-mcp/item-N.pdf')

# IMPORTANT: Search within collection, NOT global search
# Global search via ?q=DOI fails to match DOIs reliably
r = httpx.get(
    f"https://api.zotero.org/users/{LIBRARY_ID}/collections/{COLLECTION_KEY}/items",
    params={"limit": 100, "itemType": "-attachment"},
    headers=headers, timeout=30
)
items = [i for i in r.json() if i['data'].get('DOI','').lower() == target_doi.lower()]
item_key = items[0]['data']['key']
print(f"Found: {item_key}")

# DUAL timeout patch — BOTH are required (tested 2026-02-25, handles 20+ MB files):
# 1. httpx.post (module-level): used by pyzotero _upload.py for the actual file upload
# 2. zot.client replacement: used by pyzotero for the auth/registration stage
# WARNING: Patching httpx.Client.post does NOT work — pyzotero calls httpx.post directly.
_orig_post = httpx.post
def _patched_post(*a, **kw):
    kw['timeout'] = httpx.Timeout(600.0, connect=60.0)
    return _orig_post(*a, **kw)
httpx.post = _patched_post

zot = zotero.Zotero(LIBRARY_ID, 'user', API_KEY)
zot.client = httpx.Client(
    timeout=httpx.Timeout(600.0, connect=60.0),
    headers=dict(zot.client.headers),
)

zot.attachment_simple([pdf_path], item_key)
print("✓ Uploaded!")
os.remove(pdf_path)  # clean up
```

**Note**: Dual-patch handles files up to 20+ MB reliably (confirmed with 20.16 MB upload).

**Step 6: Clean Up**
- Delete the downloaded PDF from `.playwright-mcp/` after successful Zotero upload
- **IMPORTANT**: Close the browser with `browser_close` when ALL items are done (not between items)

**Step 7: Repeat for Next Item**
- After completing one item (downloaded + uploaded to Zotero), move to the next DOI
- This ensures no "待确认" items pile up (which would block new submissions when points < 500)

## Page Element Reference

### Create Page (`/assist/create`)
| Element | Snapshot Pattern | Purpose |
|---------|-----------------|---------|
| Quick input | `textbox "请输入DOI、PMID 或 标题"` | Enter DOI |
| Extract button | `button " 智能提取文献信息"` | Auto-fill form |
| DOI field | `textbox "选填，强烈建议输入..."` | DOI (auto-filled) |
| Title field | `textbox "请正确填写..."` | Title (auto-filled) |
| Publish button | `button "立即发布"` | Submit (if no popup) |
| Quick publish | `"信息正确，直接发布"` | Publish directly from popup |
| Points display | `"您当前有 X 积分"` | Check balance |

### Detail Page (`/assist/detail?id=XXX`)
| Element | Snapshot Pattern | Purpose |
|---------|-----------------|---------|
| Status | `"待确认"` or `"已完结"` | Request status |
| Download link | `link "FILENAME.pdf"` with `/assist/download?id=XXX` URL | Get download ID |
| Accept button | `button " 采纳文件"` | Accept uploaded file |
| Reject button | `button " 驳回文件"` | Reject wrong file |

### Pending List (`/my/assist-my?status=uploaded`)
| Element | Snapshot Pattern | Purpose |
|---------|-----------------|---------|
| PDF filename link | `link "FILENAME.pdf"` → href `/assist/download?id=XXX` | Extract download ID HERE |
| Select all | click element containing `全选` text | Select all items |
| Batch accept | `button "批量采纳所选项"` | Accept all |

### Download Page (`/assist/download?id=XXX`)
- ⚠️ **DO NOT navigate here with `browser_navigate`** — auto-download freezes browser
- Use `browser_run_code` with `waitForEvent('download')` instead (see Step 4)
- Download ID format: `XXX` from URL `/assist/download?id=XXX`

### My Requests (`/my/assist-my`)
- Lists all submitted requests with status

## Downloaded File Location

Files saved to `.playwright-mcp/` in working directory via `download.saveAs()`.
Naming convention: `item-N-DOI-SUFFIX.pdf` (e.g. `item1-electacta-2022-141129.pdf`)

## Common Issues

| Issue | Solution |
|-------|----------|
| "智能提取" fails | DOI may be invalid or not in database. Try entering title manually |
| No "信息正确，直接发布" popup | Form fields auto-filled but no popup. Click `button "立即发布"` instead |
| File not uploaded | Wait longer. Most files uploaded within 1-5 min. Check back later |
| "积分不够" for batch | Need 500+ points for batch mode. Use single-item loop instead |
| Login expired | Re-run auto-login flow (see Login section above) |
| run_code selectors fail | ALWAYS use snapshot/click approach with ref= attributes (except download step) |
| pyzotero upload timeout | Apply httpx timeout monkey-patch (see Step 5 code) |
| **"待确认" blocks new requests** | **CRITICAL**: Site blocks new requests when you have pending "待确认" items AND points < 500. Must accept/reject ALL pending uploads before submitting new ones. |
| **Browser freezes on download page** | **CRITICAL**: NEVER use `browser_navigate` to `/assist/download`. Use `browser_run_code` with `waitForEvent('download', {timeout: 900000})` + `saveAs()` — lets browser download natively then saves to path |
| **Python requests returns HTML for token URL** | Token URL requires full browser session, not just cookies. Use `browser_run_code` download interception instead (browser handles auth automatically) |
| **Download timeout** | Default 15 min (900000ms) should be enough. If file is very large or server slow, check server load indicator on download page and switch to 线路3 (lower load) |
| **`find_dotenv()` AssertionError in heredoc** | Don't use `load_dotenv()` in stdin heredoc mode. Hardcode credentials or use `load_dotenv('/abs/path/.env')`. |
| **pyzotero SSL error** | Retry — usually transient. If persistent, check network. |
| **Global DOI search returns empty** | Do NOT use `?q=DOI` — it fails to match reliably. Always search within collection using `collections/KEY/items` and filter by DOI in Python |
| **Large files timeout on Zotero upload** | Use the **dual-patch** pattern (patch both `httpx.post` module-level AND replace `zot.client`). Handles 20+ MB. Patching only `httpx.Client.post` does NOT work. |
| **Login page 404** | Use `https://www.ablesci.com/site/login` instead of `/login` |
| **Cannot click elements through overlays** | Use `browser_run_code` with JavaScript to directly trigger click events |

## Data Preparation

To get items needing PDFs from a Zotero collection (use httpx directly to avoid SSL issues):

```python
import httpx

API_KEY = '***ZOTERO_API_KEY***'
LIBRARY_ID = '5452188'
COLLECTION_KEY = 'XXXXXXXX'  # from Zotero URL
headers = {"Zotero-API-Key": API_KEY}

# Get all items in collection
items = []
start = 0
while True:
    r = httpx.get(
        f"https://api.zotero.org/users/{LIBRARY_ID}/collections/{COLLECTION_KEY}/items",
        params={"limit": 100, "start": start, "itemType": "-attachment"},
        headers=headers, timeout=30
    )
    batch = r.json()
    if not batch: break
    items.extend(batch)
    if len(batch) < 100: break
    start += 100

# Check which items lack PDFs
no_pdf = []
for item in items:
    key = item['data']['key']
    r2 = httpx.get(f"https://api.zotero.org/users/{LIBRARY_ID}/items/{key}/children",
                   headers=headers, timeout=30)
    children = r2.json()
    has_pdf = any(c['data'].get('contentType') == 'application/pdf'
                  for c in children if c['data']['itemType'] == 'attachment')
    if not has_pdf:
        print(f"{key} | {item['data'].get('DOI','NO DOI')} | {item['data'].get('title','')[:60]}")
        no_pdf.append({'key': key, 'doi': item['data'].get('DOI',''),
                       'title': item['data'].get('title','')})
```
