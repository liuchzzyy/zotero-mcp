# Zotero MCP

连接 AI 助手与 Zotero 研究库的 Model Context Protocol 服务器。

## 业务逻辑框架

```
┌───────────────────────────────────────────────────────────
│                   Entry Layer                             
│  ├── server.py (MCP stdio server)                         
│  └── cli.py (CLI)                                         
├───────────────────────────────────────────────────────────
│                   Handlers Layer                          
│  ├── annotations.py  (PDF 注释工具)                        
│  ├── batch.py        (批量操作工具)                        
│  ├── collections.py  (集合管理工具)                        
│  ├── database.py     (语义搜索工具)                        
│  ├── items.py        (条目 CRUD 工具)                      
│  ├── search.py       (搜索工具)                            
│  └── workflow.py     (批量分析工作流工具)                   
├───────────────────────────────────────────────────────────
│                  Services Layer                           
│  ├── zotero/                                              
│  │   ├── ItemService         (CRUD 操作)                  
│  │   ├── SearchService        (关键词/语义搜索)            
│  │   ├── MetadataService      (DOI/元数据补全)             
│  │   ├── MetadataUpdateService (条目元数据更新)            
│  │   ├── SemanticSearch       (ChromaDB 向量搜索)          
│  │   └── DuplicateService      (去重)                     
│  ├── workflow.py      (批量分析 + 检查点)                 
│  └── data_access.py  (本地 DB / Zotero API 门面)           
├──────────────────────────────────────────────────────────
│                  Clients Layer                        
│  ├── zotero/          (Zotero API + 本地 DB)                      
│  ├── database/        (ChromaDB 向量数据库)                     
│  ├── metadata/        (Crossref + OpenAlex APIs)                 
│  └── llm/            (DeepSeek/OpenAI/Gemini/Claude CLI)        
└──────────────────────────────────────────────────────────
```

## 核心服务

### 1. Scanner Service (`scanner.py`)

**业务逻辑**: 扫描库中需要 AI 分析的条目

**实现**:
- `GlobalScanner.scan_and_process()` - 多阶段扫描策略
  1. 优先扫描 `source_collection` (默认: `00_INBOXS`)
  2. 如需更多条目，扫描整个库
  3. 累积候选项直到达到 `treated_limit`
  4. 过滤有 PDF 但缺少"AI分析"标签的条目
  5. 处理最多 `treated_limit` 个条目

**参数** (默认值):
| 参数 | 默认值 | 说明 |
|------|---------|------|
| `scan_limit` | 100 | 每批从 API 获取的条目数 |
| `treated_limit` | 20 | 最多处理的条目总数 |
| `source_collection` | `"00_INBOXS"` | 优先扫描的集合 |
| `target_collection` | `"01_SHORTTERMS"` | 分析后移动到的集合 |
| `dry_run` | `False` | 预览模式，不执行更改 |
| `llm_provider` | `"auto"` | LLM 提供商 |
| `include_multimodal` | `True` | 启用多模态分析 |

**跳过条件**: 条目有"AI分析"标签 或无 PDF 附件

### 2. Metadata Update Service (`metadata_update_service.py`)

**业务逻辑**: 通过 Crossref/OpenAlex API 增强 Zotero 条目元数据

**实现**:
- `_clean_html_title()` - 清理 HTML 标签和实体
- `_fetch_enhanced_metadata()` - 从 API 获取增强元数据
  - 先通过 DOI 查询
  - DOI 不存在时通过标题查询 Crossref
  - 通过 DOI 查询 OpenAlex 获取额外字段
- `_build_updated_item_data()` - 构建更新的条目数据

**参数** (默认值):
| 参数 | 默认值 | 说明 |
|------|---------|------|
| `scan_limit` | 500 | 每批获取的条目数 |
| `treated_limit` | 100 | 最多更新的条目数 |
| `dry_run` | `False` | 预览模式 |
| `skip_tag` | `"AI元数据"` | 跳过已有此标签的条目 |

**字段映射**:
```python
_METADATA_FIELD_MAP = {
    "doi": "DOI",
    "journal": "publicationTitle",
    "publisher": "publisher",
    "volume": "volume",
    "issue": "issue",
    "pages": "pages",
    "abstract": "abstractNote",
}
```

### 3. Duplicate Detection Service (`duplicate_service.py`)

**业务逻辑**: 检测并删除重复的 Zotero 条目

**实现**:
- `find_and_remove_duplicates()` - 扫描并分组重复项
  - 按优先级分组: DOI > 标题 > URL
  - 保留最完整的条目（有附件/笔记）
  - 将重复项移动到回收站集合

**参数** (默认值):
| 参数 | 默认值 | 说明 |
|------|---------|------|
| `collection_key` | `None` | 限制扫描的集合 |
| `scan_limit` | 500 | 每批获取的条目数 |
| `treated_limit` | 1000 | 最多找到的重复项数 |
| `dry_run` | `False` | 预览模式 |
| `trash_collection` | `"06_TRASHES"` | 移动重复项到的集合 |

### 4. Workflow Service (`workflow.py`)

**业务逻辑**: 带检查点/恢复的批量分析

**实现**:
- `analyze_items()` - 批量分析 PDF
  - 检查跳过条件（已有标签、无 PDF）
  - 提取 PDF 内容和图片
  - 调用 LLM 分析
  - 生成结构化笔记
  - 保存笔记并添加标签
- `CheckpointService` - 保存/恢复分析状态

**参数** (默认值):
| 参数 | 默认值 | 说明 |
|------|---------|------|
| `llm_provider` | `"auto"` | LLM 提供商 |
| `multimodal` | `True` | 启用多模态分析 |
| `target_collection` | `"01_SHORTTERMS"` | 分析后移动到的集合 |
| `note_format` | `"html"` | 笔记格式 |

**检查点文件**: `~/.config/zotero-mcp/checkpoints/{workflow_id}.json`

### 5. Semantic Search (`semantic_search.py`)

**业务逻辑**: ChromaDB 向量相似度搜索

**实现**:
- `SemanticSearch.search()` - 向量搜索
  - 查询文本嵌入
  - ChromaDB 相似度搜索
  - 返回带分数的结果

**参数** (默认值):
| 参数 | 默认值 | 说明 |
|------|---------|------|
| `limit` | 10 | 返回结果数 |
| `min_score` | 0.0 | 最低相似度分数 |

**嵌入模型**:
- `default`: 免费模型 (chromadb-default)
- `openai`: `text-embedding-3-small`
- `gemini`: `models/text-embedding-004`

## CLI 命令

### 扫描和分析
```bash
zotero-mcp scan                    # 扫描未处理论文
zotero-mcp scan --treated-limit 10  # 最多处理 10 条
zotero-mcp scan --source-collection "00_INBOXS"
```

### 元数据更新
```bash
zotero-mcp update-metadata                      # 更新元数据
zotero-mcp update-metadata --treated-limit 50   # 最多更新 50 条
zotero-mcp update-metadata --dry-run          # 预览模式
```

### 去重
```bash
zotero-mcp deduplicate                    # 查找并删除重复项
zotero-mcp deduplicate --dry-run          # 预览重复项
zotero-mcp deduplicate --trash-collection "My Trash"
```

### 语义搜索
```bash
zotero-mcp update-db                    # 更新数据库（元数据）
zotero-mcp update-db --fulltext          # 包含全文
zotero-mcp update-db --force-rebuild      # 强制重建
zotero-mcp db-status                      # 检查状态
```

## 环境变量

### Zotero 连接
| 变量 | 默认值 | 说明 |
|------|---------|------|
| `ZOTERO_LOCAL` | `true` | 使用本地 API |
| `ZOTERO_API_KEY` | - | Web API 密钥 |
| `ZOTERO_LIBRARY_ID` | - | Web API 库 ID |
| `ZOTERO_LIBRARY_TYPE` | `user` | 库类型 |

### 语义搜索
| 变量 | 默认值 | 说明 |
|------|---------|------|
| `ZOTERO_EMBEDDING_MODEL` | `default` | 嵌入模型 |
| `OPENAI_API_KEY` | - | OpenAI 密钥 |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI 模型 |
| `GEMINI_API_KEY` | - | Gemini 密钥 |
| `GEMINI_EMBEDDING_MODEL` | `models/text-embedding-004` | Gemini 模型 |

### 批量分析
| 变量 | 默认值 | 说明 |
|------|---------|------|
| `DEEPSEEK_API_KEY` | - | DeepSeek 密钥 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | DeepSeek 模型 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API endpoint |

### 多模态分析
| 变量 | 默认值 | 说明 |
|------|---------|------|
| `ZOTERO_MCP_CLI_LLM_PROVIDER` | `deepseek` | LLM 提供商 |
| `ZOTERO_MCP_CLI_LLM_OCR_ENABLED` | `true` | 启用 OCR |
| `ZOTERO_MCP_CLI_LLM_MAX_PAGES` | `50` | 最大处理页数 |
| `ZOTERO_MCP_CLI_LLM_MAX_IMAGES` | `20` | 最大提取图片数 |

## MCP 工具

### 搜索工具
- `zotero_semantic_search` - 语义搜索
- `zotero_search` - 关键词搜索
- `zotero_advanced_search` - 高级搜索
- `zotero_search_by_tag` - 标签搜索
- `zotero_get_recent` - 最近条目

### 内容访问
- `zotero_get_metadata` - 条目元数据
- `zotero_get_fulltext` - 全文内容
- `zotero_get_bundle` - 完整条目数据
- `zotero_get_children` - 附件和笔记

### 集合和标签
- `zotero_get_collections` - 列出集合
- `zotero_find_collection` - 按名称查找（模糊匹配）
- `zotero_get_tags` - 列出所有标签

### 注释和笔记
- `zotero_get_annotations` - PDF 注释
- `zotero_get_notes` - 获取笔记
- `zotero_search_notes` - 搜索笔记/注释
- `zotero_create_note` - 创建笔记

### 批量工作流
- `zotero_prepare_analysis` - 收集 PDF 内容
- `zotero_batch_analyze_pdfs` - 批量 AI 分析
- `zotero_resume_workflow` - 恢复中断的工作流
- `zotero_list_workflows` - 查看工作流状态
