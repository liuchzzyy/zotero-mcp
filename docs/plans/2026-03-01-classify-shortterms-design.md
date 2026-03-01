# Design: Classify & Move 01_SHORTTERMS Items

**Date:** 2026-03-01
**Script:** `scripts/classify_shortterms.py`

## Goal

Process all items in `01_SHORTTERMS` (key `478IFSJ3`) one by one and route them to the correct inbox collection based on their `AI分析` tag status and PDF attachment content.

## Collection Keys

| Collection | Key |
|------------|-----|
| 01_SHORTTERMS (source) | `478IFSJ3` |
| 00_INBOXS_AA (target) | `2PSBFJEI` |
| 00_INBOXS_BB (target) | `866TNWZ9` |
| 00_INBOXS_CC (target) | `H7KTSUR7` |
| 00_INBOXS_DD (target) | `UQDFUUYV` |

## Routing Logic

```
All items in 01_SHORTTERMS (~1021 bibliography items, excluding notes/attachments)
    │
    ├── No "AI分析" tag ───────────────────────────────────────→ 00_INBOXS_AA
    │
    └── Has "AI分析" tag
          │
          ├── 0 PDFs ────────────────────────────────────────→ 00_INBOXS_AA
          │
          ├── 1 PDF
          │    └── DeepSeek classify (extract first 3 pages)
          │         ├── review (综述) ──────────────────────→ 00_INBOXS_BB
          │         ├── SI (支撑信息) ──────────────────────→ 00_INBOXS_AA
          │         └── main paper (正文)
          │              ├── find-pdf-si: download SI if available
          │              └── ────────────────────────────────→ 00_INBOXS_AA
          │
          └── 2+ PDFs
               └── DeepSeek duplicate check (each PDF first 3 pages)
                    ├── no duplicates ──────────────────────→ 00_INBOXS_CC
                    └── has duplicates ─────────────────────→ 00_INBOXS_DD
```

## Technical Design

### PDF Text Extraction

- Library: PyMuPDF (`fitz`)
- Path: `C:/Users/chengliu/Zotero/storage/{att_key}/{filename}`
- Extract first 3 pages, truncate to 2000 chars
- If local file not found: skip DeepSeek, use metadata fallback

### DeepSeek API

- Model: `deepseek-chat`
- Key: `***DEEPSEEK_API_KEY***`
- Base URL: `https://api.deepseek.com`
- Temperature: 0 (deterministic)

**1-PDF classification prompt:**
> 以下是一篇学术文献的前3页内容。请判断它属于哪种类型：
> (A) 综述文章（review article）- 系统回顾某领域研究进展
> (B) 支撑信息（supporting information / supplementary）- 附加数据和方法
> (C) 研究论文正文（research article）- 报告原创实验结果
> 只回答字母 A、B 或 C。

**2+PDF duplicate check prompt:**
> 以下是同一 Zotero 条目中 {N} 个 PDF 文件的前3页内容。
> 请判断这些 PDF 是否是重复文件（即相同文章的不同版本/格式）。
> 如果两个或以上 PDF 是同一篇文章的重复，回答 YES。
> 如果所有 PDF 内容不同（如正文+支撑信息），回答 NO。
> 只回答 YES 或 NO。

### SI Download (for main paper case)

Reuse functions from `download_inboxs_aa_si.py`:
- `detect_publisher(item)` → publisher string
- `get_pii(item)` → Elsevier PII
- `find_elsevier_si(pii, key)` → list of (url, fname, ext)
- `find_rsc_si(doi)` → list of (url, fname)
- `find_acs_si(doi)` → list of file dicts
- `find_springer_si(doi)` → list of (url, fname)
- `download_file(url, dest)` → (bool, size_mb)
- `docx_to_pdf(path)` → Path
- `upload_files(paths, item_key)` → int

SI output directory: `.si-downloads/shortterms/`

### Move Function

```python
def move_item(key, version, from_col, to_col):
    item = zot.item(key)
    cols = item['data']['collections']
    new_cols = list(set(cols + [to_col]) - {from_col})
    zot.update_item({'key': key, 'version': item['version'], 'collections': new_cols})
```

### Output Format

```
[001/1021] [KEY123] (2023) Some Paper Title...
  tags: AI分析, DeepSeek
  PDFs: 1
  🤖 DeepSeek: 正文 (main paper) [C]
  🔍 SI查找 (publisher=elsevier, PII=S...)
  → SI 已上传: mmc1.pdf (1.2 MB)
  ✅ 移动到 00_INBOXS_AA
```

## Files to Create

- `scripts/classify_shortterms.py` — main script (~400 lines)

## Zotero Setup

Dual httpx patch (required for large file uploads):
```python
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
```
