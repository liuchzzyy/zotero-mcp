# Zotero MCP v3.0 架构指南

## 1. 项目概览

Zotero MCP 是一个基于 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 的服务器，将 AI 助手与 [Zotero](https://www.zotero.org/) 学术文献库连接起来。支持语义搜索、PDF 智能分析、RSS 自动采集、Gmail 文献处理等功能。

**技术栈**: Python 3.10+ / FastMCP / Pydantic v2 / ChromaDB / PyMuPDF / uv

### 1.1 模块化架构（v3.0 新增）

v3.0 将单体代码库拆分为 4 个独立模块，每个模块可独立安装使用：

```
zotero-mcp/
├── src/zotero_mcp/           # 主应用 — MCP 服务器 + 集成层
├── external/paper-feed/      # 独立模块 — 论文采集（RSS/Gmail）
├── modules/zotero-core/      # 独立模块 — Zotero 数据访问（CRUD/搜索）
└── modules/paper-analyzer/   # 独立模块 — PDF 分析引擎（LLM）
```

| 模块 | 包名 | 职责 | 安装方式 |
|------|------|------|----------|
| paper-feed | `paper_feed` | RSS 解析、多级过滤、OPML 支持、导出适配器 | `pip install paper-feed` |
| zotero-core | `zotero_core` | Zotero Web API 完整 CRUD、关键词/语义/混合搜索 | `pip install zotero-core` |
| paper-analyzer | `paper_analyzer` | PDF 提取（PyMuPDF）、LLM 分析、模板系统 | `pip install paper-analyzer` |
| zotero-mcp | `zotero_mcp` | MCP 服务器、CLI、所有模块集成、工作流编排 | `pip install zotero-mcp` |

---

## 2. 主应用架构（src/zotero_mcp/）

采用严格的分层架构，每层只能调用下一层：

```
┌──────────────────────────────────────────────────┐
│  入口层  server.py / cli.py / __main__.py        │
├──────────────────────────────────────────────────┤
│  工具层  tools/*.py  (@mcp.tool 装饰器，薄封装)    │
├──────────────────────────────────────────────────┤
│  服务层  services/**  (核心业务逻辑)               │
├──────────────────────────────────────────────────┤
│  客户端层  clients/**  (外部服务通信)              │
├──────────────────────────────────────────────────┤
│  模型层  models/**  (Pydantic 数据模型)           │
├──────────────────────────────────────────────────┤
│  工具库  utils/** / formatters/  (配置/格式化/辅助) │
├──────────────────────────────────────────────────┤
│  集成层  integration/**  (v3.0 模块桥接)          │
│  配置    config.py  (v3.0 Pydantic 环境配置)      │
└──────────────────────────────────────────────────┘
```

### 2.1 入口层

| 文件 | 职责 |
|------|------|
| `server.py` | FastMCP 服务器初始化：创建 `FastMCP("Zotero")` 实例 → 初始化日志 → 加载配置 → `register_all_tools(mcp)` 注册所有工具 |
| `cli.py` | 命令行入口：`main()` 函数使用 argparse 解析子命令（serve/setup/scan/update-db/deduplicate 等） |
| `__main__.py` | `python -m zotero_mcp` 入口，调用 `cli.main()` |

**启动流程**:
```
cli.main() → parser.parse_args()
  ├── "serve" → server.run() → mcp.run()  (启动 MCP 服务器)
  ├── "setup" → 交互式配置向导
  ├── "scan"  → ScannerService → WorkflowService
  ├── "update-db" → SemanticSearch.update_database()
  └── "rss fetch" → RSSService.process_rss_workflow()
```

### 2.2 工具层（tools/）

每个文件定义一个 `register_*_tools(mcp)` 函数，内部使用 `@mcp.tool` 装饰器注册工具。工具层是**薄封装**，仅做参数验证和格式化，核心逻辑全部委托给服务层。

| 文件 | 注册函数 | 提供的 MCP 工具 |
|------|----------|----------------|
| `search.py` | `register_search_tools` | `zotero_search` / `zotero_search_by_tag` / `zotero_advanced_search` / `zotero_semantic_search` / `zotero_get_recent` |
| `items.py` | `register_item_tools` | `zotero_get_metadata` / `zotero_get_fulltext` / `zotero_get_bundle` / `zotero_get_children` |
| `annotations.py` | `register_annotation_tools` | `zotero_get_annotations` / `zotero_get_notes` / `zotero_search_notes` / `zotero_create_note` |
| `collections.py` | `register_collection_tools` | `zotero_get_collections` / `zotero_get_collection_items` / `zotero_find_collection` / `zotero_get_tags` |
| `database.py` | `register_database_tools` | `zotero_update_db` / `zotero_db_status` |
| `batch.py` | `register_batch_tools` | `zotero_prepare_analysis` |
| `workflow.py` | `register_workflow_tools` | `zotero_batch_analyze_pdfs` / `zotero_analyze_pdf` / `zotero_resume_workflow` / `zotero_list_workflows` |
| `rss.py` | `register_rss_tools` | `rss_fetch_feed` / `rss_fetch_from_opml` |

**注册入口** `__init__.py`:
```python
def register_all_tools(mcp: FastMCP) -> None:
    register_search_tools(mcp)
    register_item_tools(mcp)
    register_annotation_tools(mcp)
    register_collection_tools(mcp)
    register_database_tools(mcp)
    register_batch_tools(mcp)
    register_workflow_tools(mcp)
    register_rss_tools(mcp)
```

### 2.3 服务层（services/）

服务层包含所有业务逻辑，是整个应用的核心。

#### 2.3.1 统一数据访问（Facade 模式）

```python
# services/data_access.py
class DataAccessService:
    """统一数据访问门面，自动选择最佳后端"""
    # 后端优先级：Local DB（快速读取）> Better BibTeX（引用键）> Zotero API（写操作/兜底）

    # 委托给专门的子服务：
    item_service: ItemService     # CRUD、集合、标签
    search_service: SearchService # 搜索操作
    metadata_service: MetadataService # 元数据增强
```

`get_data_service()` 工厂函数返回全局单例。

#### 2.3.2 Zotero 领域服务（services/zotero/）

| 服务 | 职责 |
|------|------|
| `ItemService` | 条目 CRUD（获取/创建/更新/删除）、集合管理、标签操作、批量获取 |
| `SearchService` | 关键词搜索、标签搜索、高级多字段搜索、语义搜索代理 |
| `SemanticSearch` | ChromaDB 向量数据库管理、嵌入生成、相似度搜索 |
| `MetadataService` | 通过 Crossref/OpenAlex API 查找和增强元数据（DOI 查询） |
| `MetadataUpdateService` | 批量元数据更新（集合扫描 + 逐条更新） |
| `DuplicateService` | 智能去重（DOI > 标题 > URL 优先级匹配）、安全删除到回收集合 |

#### 2.3.3 采集服务

| 服务 | 位置 | 职责 |
|------|------|------|
| `RSSFetcher` | `services/rss/rss_fetcher.py` | 获取并解析 RSS 订阅源 |
| `RSSService` | `services/rss/rss_service.py` | 编排完整流程：获取 → AI 过滤 → 元数据增强 → Zotero 导入 |
| `GmailFetcher` | `services/gmail/gmail_fetcher.py` | 获取邮件、解析 HTML 正文 |
| `GmailService` | `services/gmail/gmail_service.py` | 编排邮件处理：获取 → 过滤 → 导入 → 删除已处理邮件 |

#### 2.3.4 工作流服务

| 服务 | 位置 | 职责 |
|------|------|------|
| `WorkflowService` | `services/workflow.py` | 批量 PDF 分析，支持断点续传。核心方法：`prepare_analysis()` → `batch_analyze()` → `_analyze_single_item()` |
| `CheckpointService` | `services/checkpoint.py` | 持久化工作流进度（JSON 文件），支持中断后恢复 |
| `ScannerService` | `services/scanner.py` | 扫描库中未分析的论文，调度分析任务 |

#### 2.3.5 公共服务（services/common/）

| 服务 | 职责 |
|------|------|
| `collection_scanner.py` | 通用集合扫描工具 `scan_collections()`，支持分页、跳过逻辑、treated_limit |
| `ai_filter.py` | AI 驱动的关键词过滤（用于 RSS/Gmail 文献筛选） |
| `zotero_item_creator.py` | 统一的 Zotero 条目创建逻辑，包含查重、API 429 安全处理 |
| `retry.py` | 指数退避重试装饰器 |

### 2.4 客户端层（clients/）

客户端层封装所有外部服务通信。

| 目录 | 客户端 | 外部服务 |
|------|--------|----------|
| `clients/zotero/` | `ZoteroAPIClient` | Zotero Web API（via pyzotero） |
| | `LocalDatabaseClient` | Zotero 本地 SQLite 数据库 |
| | `BetterBibTeXClient` | Better BibTeX 插件 API |
| | `PDFExtractorClient` | 本地 PDF 注释提取 |
| | `MarkdownConverter` | HTML → Markdown 转换 |
| `clients/database/` | `ChromaDBClient` | ChromaDB 向量数据库 |
| `clients/llm/` | `BaseLLMClient` (抽象) | LLM 提供商统一接口 |
| | `DeepSeekClient` | DeepSeek API |
| | `OpenAIClient` | OpenAI / 兼容 API |
| | `ClaudeCliClient` | Claude CLI（多模态分析） |
| | `capabilities.py` | LLM 能力注册表（视觉支持等） |
| `clients/metadata/` | `CrossrefClient` | Crossref DOI 查询 API |
| | `OpenAlexClient` | OpenAlex 学术元数据 API |
| `clients/gmail/` | `GmailClient` | Gmail API (OAuth2) |

### 2.5 模型层（models/）

所有数据模型使用 Pydantic v2 `BaseModel`，提供类型安全和自动验证。

| 目录 | 模型 | 用途 |
|------|------|------|
| `models/common/` | `BaseInput` / `BaseResponse` / `SearchResponse` / `SearchResultItem` / `ResponseFormat` | 公共基础模型 |
| `models/zotero/` | `items.py` / `collections.py` / `annotations.py` / `note_structure.py` | Zotero 领域输入模型 |
| `models/workflow/` | `analysis.py` / `batch.py` | 工作流和批量分析模型 |
| `models/search/` | `queries.py` | 各种搜索查询输入模型 |
| `models/ingestion/` | `rss.py` / `gmail.py` | RSS/Gmail 采集模型 |
| `models/database/` | `semantic.py` | 语义搜索数据库模型 |

### 2.6 工具库

#### formatters/ — 输出格式化器

| 文件 | 职责 |
|------|------|
| `base.py` | 格式化器基类 |
| `markdown.py` | Markdown 格式输出 |
| `json_formatter.py` | JSON 格式输出 |
| `bibtex.py` | BibTeX 引用格式 |

#### utils/ — 工具函数

| 目录 | 内容 |
|------|------|
| `utils/config/` | `config.py` — 配置加载（JSON）、`logging.py` — 日志初始化 |
| `utils/data/` | `mapper.py` — 数据映射、`templates.py` — 分析模板（HTML/提示词） |
| `utils/formatting/` | `helpers.py` — 通用格式化辅助、`beautify.py` — AI 笔记美化、`markdown.py` — Markdown ↔ HTML |
| `utils/async_helpers/` | `batch_loader.py` — 异步批量加载器、`cache.py` — MCP 工具缓存装饰器 |
| `utils/system/` | `errors.py` — 自定义异常、`setup.py` — 安装向导、`updater.py` — 自动更新 |

### 2.7 集成层（v3.0 新增）

集成层是 v3.0 新增的桥接模块，将独立子模块连接到 MCP 服务器。

```
integration/
├── __init__.py               # 导出 MCPTools, ZoteroIntegration, AnalyzerIntegration
├── zotero_integration.py     # 封装 zotero-core → MCP 接口
├── analyzer_integration.py   # 封装 paper-analyzer → MCP 接口
└── mcp_tools.py              # MCPTools 类 — 注册集成层 MCP 工具
```

**config.py** — v3.0 统一配置:
```python
class Config(BaseModel):
    # Zotero 连接
    zotero_library_id / zotero_api_key / zotero_library_type
    # LLM 配置
    llm_provider / llm_api_key / llm_base_url / llm_model
    # 语义搜索
    chromadb_persist_dir / embedding_provider / embedding_api_key / embedding_model
    # 日志
    log_level / debug

    @classmethod
    def from_env(cls) -> Config:  # 从环境变量创建
    @classmethod
    def load(cls) -> Config:      # .env 文件 + 环境变量

# get_config() 全局单例
```

**ZoteroIntegration** — 封装 zotero-core:
```python
class ZoteroIntegration:
    def __init__(self, config: Config):
        client = ZoteroClient(library_id=..., api_key=..., library_type=...)
        self.item_service = ItemService(client)
        self.search_service = SearchService(client)

    async def get_items() / get_item() / create_item() / search()
    async def get_collections() / create_collection()
    @staticmethod format_items() / format_item() / format_collections()
```

**AnalyzerIntegration** — 封装 paper-analyzer:
```python
class AnalyzerIntegration:
    def __init__(self, config: Config):
        llm_client = self._create_llm_client(config)  # 工厂方法
        self.analyzer = PDFAnalyzer(llm_client=llm_client, ...)

    async def analyze_pdf(file_path, template_name, extract_images)
    async def analyze_text(text, title, template_name)
    @staticmethod format_result() / format_batch_results()
```

**MCPTools** — MCP 工具注册:
```python
class MCPTools:
    def register_tools(self, mcp: FastMCP):
        self._register_item_tools(mcp)       # get_items / get_item / create_item
        self._register_collection_tools(mcp)  # get_collections / create_collection
        self._register_search_tools(mcp)      # search_items
        self._register_analysis_tools(mcp)    # analyze_paper / analyze_text
```

---

## 3. 独立模块详解

### 3.1 paper-feed（论文采集框架）

**位置**: `external/paper-feed/`

```
paper_feed/
├── core/
│   ├── base.py          # 抽象基类: PaperSource, ExportAdapter
│   └── models.py        # 数据模型: PaperItem, FilterCriteria, FilterResult
├── sources/
│   ├── rss.py           # RSSSource — RSS 订阅源解析
│   ├── rss_parser.py    # RSS XML 解析器（支持 arXiv/bioRxiv/Nature/Science 等）
│   └── opml.py          # OPML 文件解析，批量加载 RSS 源
├── filters/
│   ├── keyword.py       # KeywordFilter — 关键词匹配过滤
│   └── pipeline.py      # FilterPipeline — 多级过滤管道
└── adapters/
    ├── json.py          # JSONAdapter — 导出为 JSON 文件
    └── zotero.py        # ZoteroAdapter — 直接导入到 Zotero 库
```

**数据流**:
```
RSSSource.fetch_papers(url, limit)
  → rss_parser 解析 XML → List[PaperItem]
    → FilterPipeline.filter(papers, criteria)
      → KeywordFilter 匹配 → FilterResult
        → JSONAdapter.export() 或 ZoteroAdapter.export()
```

**核心模型**:
```python
class PaperItem(BaseModel):
    title: str
    authors: List[str]
    abstract: str
    url: str
    doi: Optional[str]
    published_date: Optional[datetime]
    source: str        # RSS 源标识
    categories: List[str]

class FilterCriteria(BaseModel):
    keywords: List[str]
    categories: List[str]
    authors: List[str]
    date_from: Optional[datetime]
    date_to: Optional[datetime]
```

### 3.2 zotero-core（Zotero 数据访问库）

**位置**: `modules/zotero-core/`

```
zotero_core/
├── clients/
│   └── zotero_client.py  # ZoteroClient — Zotero Web API 完整封装
├── models/
│   ├── base.py           # 基础模型
│   ├── item.py           # Item, ItemData, Creator 等
│   ├── collection.py     # Collection, CollectionData
│   ├── search.py         # SearchQuery, SearchResults, SearchMode
│   └── tag.py            # Tag
└── services/
    ├── item_service.py      # ItemService — CRUD 操作
    ├── search_service.py    # SearchService — 关键词搜索
    ├── semantic_search.py   # SemanticSearchService — 向量搜索
    └── hybrid_search.py     # HybridSearchService — 混合搜索（RRF 算法）
```

**HybridSearchService — 互反排序融合（RRF）算法**:
```python
class HybridSearchService:
    """组合关键词搜索和语义搜索结果"""

    def __init__(self, keyword_search, semantic_search, k=60):
        self.k = k  # RRF 参数

    async def search(self, query, search_mode="hybrid"):
        # search_mode: "keyword" | "semantic" | "hybrid"
        if search_mode == "hybrid":
            keyword_results = await self.keyword_search.search(query)
            semantic_results = await self.semantic_search.search(query)
            return self._rrf_merge(keyword_results, semantic_results)

    def _rrf_merge(self, *result_lists):
        # RRF 分数 = Σ 1/(k + rank_i)
        # k=60 是默认参数，平衡高排名和低排名结果的权重
```

### 3.3 paper-analyzer（PDF 分析引擎）

**位置**: `modules/paper-analyzer/`

```
paper_analyzer/
├── extractors/
│   └── pdf_extractor.py    # PDFExtractor — PyMuPDF 内容提取
├── clients/
│   ├── base.py             # BaseLLMClient — 抽象基类
│   ├── openai_client.py    # OpenAIClient — OpenAI / 兼容 API
│   └── deepseek.py         # DeepSeekClient — DeepSeek API
├── analyzers/
│   └── pdf_analyzer.py     # PDFAnalyzer — 分析编排器
├── templates/
│   └── template_manager.py # TemplateManager — 内置 + 自定义模板
└── models/
    ├── content.py           # PDFContent, ImageBlock, TableBlock
    ├── template.py          # AnalysisTemplate
    ├── result.py            # AnalysisResult
    └── checkpoint.py        # CheckpointData
```

**分析流水线**:
```
PDFAnalyzer.analyze(file_path, template_name)
  1. PDFExtractor.extract(file_path)
     → PyMuPDF (fitz) 提取文本 + 图片(base64) + 表格
     → 返回 PDFContent
  2. TemplateManager.get_template(template_name)
     → 获取分析模板（default/multimodal/structured）
  3. template.render(text=..., title=..., images=...)
     → 生成 LLM 提示词
  4. llm_client.analyze(prompt, images)
     → 调用 LLM API
  5. _parse_result(raw_output, template)
     → JSON 解析 或 Markdown 分段解析
     → 返回 AnalysisResult
```

**三种内置模板**:

| 模板 | 输出格式 | 多模态 | 用途 |
|------|---------|--------|------|
| `default` | Markdown | 否 | 通用论文分析 |
| `multimodal` | Markdown | 是 | 含图表的论文 |
| `structured` | JSON | 否 | 程序化处理 |

**PDFExtractor 实现细节**:
```python
class PDFExtractor:
    async def extract(self, file_path, max_pages=50, extract_images=True):
        # 使用 asyncio.to_thread 包装同步 PyMuPDF 操作
        return await asyncio.to_thread(self._extract_sync, file_path, ...)

    def _extract_sync(self, file_path, max_pages, extract_images):
        doc = fitz.open(file_path)
        for page in doc[:max_pages]:
            text += page.get_text()
            if extract_images:
                for img in page.get_images():
                    # 提取图片 → base64 编码 → ImageBlock
            # 表格检测：基于水平/垂直线段的启发式算法
        return PDFContent(text=text, images=images, tables=tables)
```

---

## 4. 核心数据流

### 4.1 搜索请求流程

```
AI 助手调用 zotero_search("machine learning")
  │
  ▼
tools/search.py → @mcp.tool zotero_search(params: SearchItemsInput)
  │  参数验证（Pydantic）
  ▼
services/ → get_data_service() → DataAccessService
  │  自动选择后端
  ▼
services/zotero/search_service.py → SearchService.search()
  │
  ├─ 本地模式 → clients/zotero/local_db.py → SQLite 查询
  └─ API 模式  → clients/zotero/api_client.py → Zotero Web API
  │
  ▼
SearchResponse(items=[SearchResultItem(...), ...])
  │
  ▼
formatters/markdown.py → 格式化为 Markdown 返回给 AI 助手
```

### 4.2 PDF 分析流程（主应用工作流）

```
CLI: zotero-mcp scan --llm-provider auto --multimodal
  │
  ▼
services/scanner.py → ScannerService
  │  扫描集合中未分析的论文（检查 "AI分析" 标签）
  ▼
services/workflow.py → WorkflowService.batch_analyze()
  │
  ├─ _should_skip_item()     # 检查是否已分析
  ├─ _extract_bundle_context() # 获取 PDF 文本/附件
  ├─ _validate_context()      # 验证内容有效性
  │
  ▼  LLM 提供商自动选择（auto 模式）
  ├─ PDF 有图片 → claude-cli（多模态分析）
  └─ 纯文本    → deepseek（快速/低成本）
  │
  ├─ _call_llm_analysis()    # 调用 LLM
  ├─ _delete_old_notes()     # 删除旧分析笔记
  ├─ _generate_html_note()   # 生成 HTML 笔记
  └─ _save_note()            # 保存到 Zotero + 添加 "AI分析" 标签
  │
  ▼
  CheckpointService 持久化进度 → 支持断点续传
```

### 4.3 RSS 采集流程

```
CLI: zotero-mcp rss fetch
  │
  ▼
services/rss/rss_service.py → RSSService.process_rss_workflow()
  │
  ├─ 1. RSSFetcher.fetch_feeds()    # 获取 RSS XML
  │     └─ 解析 arXiv/bioRxiv/Nature 等源
  │
  ├─ 2. PaperFilter.filter()        # AI 关键词过滤
  │     └─ services/common/ai_filter.py
  │
  ├─ 3. MetadataService.enhance()   # Crossref/OpenAlex 元数据增强
  │
  └─ 4. ZoteroItemCreator.create()  # 导入到 Zotero 收件箱集合
        └─ 包含查重（_safe_search）
        └─ API 429 保护（1s 间隔）
```

### 4.4 语义搜索流程

```
AI 助手调用 zotero_semantic_search("transformer attention mechanism")
  │
  ▼
services/zotero/semantic_search.py → SemanticSearch.search()
  │
  ├─ 1. 生成查询向量
  │     └─ OpenAI text-embedding-3-small / Gemini / 默认嵌入
  │
  ├─ 2. ChromaDB 向量检索
  │     └─ clients/database/chroma.py → ChromaDBClient.query()
  │
  └─ 3. 返回相似度排序结果 + 分数
```

---

## 5. 配置管理

### 5.1 配置优先级

```
环境变量 > .env 文件 > ~/.config/zotero-mcp/config.json > 代码默认值
```

### 5.2 关键配置项

| 类别 | 环境变量 | 说明 |
|------|----------|------|
| **Zotero 连接** | `ZOTERO_LOCAL=true` | 使用本地 API（需要 Zotero 7+） |
| | `ZOTERO_API_KEY` | Web API 密钥 |
| | `ZOTERO_LIBRARY_ID` | 库 ID |
| **语义搜索** | `ZOTERO_EMBEDDING_MODEL` | 嵌入模型（default/openai/gemini） |
| | `OPENAI_API_KEY` | OpenAI 嵌入 API 密钥 |
| **PDF 分析** | `DEEPSEEK_API_KEY` | DeepSeek 分析 API 密钥 |
| | `ZOTERO_MCP_CLI_LLM_PROVIDER` | LLM 提供商（deepseek/openai/claude-cli） |
| | `ZOTERO_MCP_CLI_LLM_OCR_ENABLED` | 启用 OCR |
| **采集** | `RSS_PROMPT` | RSS 过滤关键词 |
| | `ZOTERO_INBOX_COLLECTION` | 收件箱集合名 |

### 5.3 双配置系统

- **v2.x 配置**（`utils/config/config.py`）: 从 JSON 文件加载，`load_config()` 函数
- **v3.0 配置**（`config.py`）: Pydantic `Config` 模型，从 `.env` + 环境变量加载，`get_config()` 单例

两套系统并存，v3.0 集成层使用新配置，原有工具层使用旧配置。

---

## 6. 测试架构

```
tests/
├── clients/           # 客户端层单元测试
│   ├── llm/          # LLM 客户端测试
│   └── zotero/       # Zotero 客户端测试
├── services/          # 服务层单元测试
├── tools/             # 工具层测试
├── utils/             # 工具库测试
├── integration/       # v3.0 集成层测试
│   ├── test_config.py               # 7 个配置测试
│   └── test_integration_layer.py    # 8 个集成测试
│
modules/paper-analyzer/tests/
└── unit/
    ├── test_models.py           # 16 个模型测试
    ├── test_template_manager.py # 7 个模板测试
    ├── test_clients.py          # 11 个 LLM 客户端测试
    └── test_analyzer.py         # 5 个分析器测试（MockLLMClient）

modules/zotero-core/tests/
└── unit/
    ├── test_models.py          # 模型测试
    ├── test_item_service.py    # ItemService 测试
    └── test_hybrid_search.py   # 混合搜索/RRF 测试

external/paper-feed/tests/
└── unit/
    ├── test_rss_source.py      # RSS 源测试
    ├── test_filters.py         # 过滤器测试
    └── test_adapters.py        # 适配器测试
```

**测试运行**:
```bash
# 全部测试
uv run pytest -v

# 单模块测试
cd modules/paper-analyzer && uv run pytest -v
cd modules/zotero-core && uv run pytest -v
```

---

## 7. 设计模式总结

| 模式 | 应用位置 | 说明 |
|------|----------|------|
| **Facade（门面）** | `DataAccessService` | 统一多后端访问接口 |
| **Factory（工厂）** | `get_data_service()` / `get_config()` / `_create_llm_client()` | 单例创建和依赖注入 |
| **Strategy（策略）** | LLM 客户端 / 嵌入模型 / 搜索模式 | 可切换的算法实现 |
| **Template Method** | `AnalysisTemplate.render()` | 可定制的分析模板 |
| **Pipeline（管道）** | `FilterPipeline` / RSS 采集 / PDF 分析 | 多阶段数据处理 |
| **Decorator（装饰器）** | `@mcp.tool` / `@cached_tool` / `@retry` | 横切关注点 |
| **Checkpoint/Resume** | `CheckpointService` | 持久化状态，支持中断恢复 |
| **Adapter（适配器）** | `JSONAdapter` / `ZoteroAdapter` / 集成层 | 接口转换 |

---

## 8. 关键实现细节

### 8.1 pyzotero 429 限流处理

pyzotero v1.8.0 会静默吞掉 HTTP 429 错误，返回 int 类型而非 dict，导致下游崩溃。

**三层防御**:
1. **API 客户端层** (`clients/zotero/api_client.py`): `_check_api_result()` 将 int 状态码转为 `RuntimeError`
2. **服务层** (`services/zotero/search_service.py`): `isinstance(items, int)` 防御性检查
3. **调用层** (`services/common/zotero_item_creator.py`): `_safe_search()` 包装所有搜索调用，429 后等待 5s

### 8.2 异步设计

所有 I/O 操作使用 `async/await`。PyMuPDF 是同步库，通过 `asyncio.to_thread()` 包装：

```python
async def extract(self, file_path):
    return await asyncio.to_thread(self._extract_sync, file_path)
```

### 8.3 批量扫描逻辑

`scan_limit` 和 `treated_limit` 两个参数控制批量操作：

```python
while processed_count < treated_limit:
    items = fetch(scan_limit, offset)    # 每批获取 scan_limit 条
    for item in items:
        if should_skip(item):            # 已有标签 → 跳过（不计数）
            continue
        process(item)                    # 处理
        processed_count += 1             # 计数
    if len(items) < scan_limit:          # 集合耗尽
        break
```

### 8.4 多模态 LLM 自动选择

```python
if llm_provider == "auto":
    if pdf_has_images:
        use claude-cli  # 支持视觉
    else:
        use deepseek    # 纯文本，更快更便宜
```
