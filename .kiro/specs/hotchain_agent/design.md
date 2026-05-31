# HotChain Agent — 设计文档（Design）

> 本文档详细规定 HotChain 各模块的接口、数据结构、调用关系与目录布局。
> 与 `requirements.md` 一一对应，是 `tasks.md` 的依据。

---

## 1. 总体架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                            入口层 (Entry)                            │
├──────────────────────────────────────────────────────────────────────┤
│  CLI                Web (React)            REST API        SKILL.md  │
│  python -m hotchain http://localhost:5173  /api/v1/hotchain/*  对外  │
│  ↓                  ↓                       ↓                ↓       │
└──────────────────────────────────────┬───────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   API 路由 app/routers/hotchain.py                   │
│  POST /analyze, GET /hotspot, GET /industry-chain, GET /skills, ...  │
│  POST /analyze/stream（SSE）                                         │
└──────────────────────────────────────┬───────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│             业务服务 app/services/hotchain_service.py                │
│  HotChainService.analyze() / get_hotspot() / get_industry_chain()    │
│  内部组装 selected_analysts=[..., 'hotspot', 'industry_chain', ...]  │
└──────────────────────────────────────┬───────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│             核心引擎 tradingagents/graph/trading_graph.py            │
│   原图：Market → Social → News → Fundamentals → Bull/Bear → ...      │
│   新图：Market → Social → News → Hotspot → IndustryChain →           │
│         Fundamentals → Bull/Bear → Trader → Risk Judge               │
└──────────────────────────────────────┬───────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  新增 Agent          Skill 注入         数据工具                     │
│  HotspotAnalyst   ← skills.SkillManager  get_market_hotspot_unified  │
│  IndustryChainAnalyst                    get_industry_chain_unified  │
│                                          get_stock_news_unified（已） │
└──────────────────────────────────────┬───────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  数据层 tradingagents/dataflows/providers/china/akshare.py（扩展）   │
│  - get_market_hotspot()   → 行业榜 + 概念榜 + 人气榜 + 百度热搜     │
│  - get_industry_chain()   → 行业 + 同行业可比公司 + 上下游关键词    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. 目录布局（新增/修改）

```
TradingAgents-CN/
├── SKILL.md                                ← 【新增】对外暴露的 Claude Skill
├── README.md                               ← 【修改】加 HotChain 章节
│
├── tradingagents/
│   ├── agents/
│   │   ├── __init__.py                     ← 【修改】注册新 factory
│   │   ├── analysts/
│   │   │   ├── hotspot_analyst.py          ← 【新增】HotspotAnalyst
│   │   │   └── industry_chain_analyst.py   ← 【新增】IndustryChainAnalyst
│   │   └── utils/
│   │       └── agent_states.py             ← 【修改】加 hotspot_report / industry_chain_report 字段
│   │
│   ├── skills/                             ← 【新增】Skill 机制（仿 DSA）
│   │   ├── __init__.py
│   │   ├── base.py                         ← Skill 数据类 + SkillManager
│   │   ├── loader.py                       ← YAML 加载
│   │   └── builtin/
│   │       ├── hotspot_chase.yaml
│   │       ├── industry_chain_value.yaml
│   │       ├── upstream_costdrop.yaml
│   │       ├── downstream_demand_boom.yaml
│   │       ├── concept_speculation.yaml
│   │       └── policy_driven.yaml
│   │
│   ├── tools/
│   │   └── hotchain_tools.py               ← 【新增】unified 工具（参考 unified_news_tool.py）
│   │
│   ├── agents/utils/
│   │   └── agent_utils.py                  ← 【修改】Toolkit 加 get_market_hotspot_unified / get_industry_chain_unified
│   │
│   ├── graph/
│   │   ├── setup.py                        ← 【修改】加节点和边
│   │   ├── trading_graph.py                ← 【修改】_create_tool_nodes 加 hotspot/industry_chain
│   │   └── conditional_logic.py            ← 【修改】加 should_continue_hotspot / should_continue_industry_chain
│   │
│   ├── agents/researchers/
│   │   ├── bull_researcher.py              ← 【修改】curr_situation 拼接新报告
│   │   └── bear_researcher.py              ← 【修改】同上
│   ├── agents/managers/
│   │   ├── research_manager.py             ← 【修改】curr_situation 拼接新报告
│   │   └── risk_manager.py                 ← 【修改】同上
│   ├── agents/trader/
│   │   └── trader.py                       ← 【修改】curr_situation 拼接新报告
│   │
│   ├── dataflows/
│   │   └── providers/
│   │       └── china/
│   │           └── akshare.py              ← 【修改】加 get_market_hotspot / get_industry_chain 方法
│   │
│   └── industry_chain_map.py               ← 【新增】静态上下游映射字典（申万一级行业为基础）
│
├── app/                                    ← Web 后端（FastAPI）
│   ├── routers/
│   │   └── hotchain.py                     ← 【新增】HotChain REST 路由
│   ├── services/
│   │   └── hotchain_service.py             ← 【新增】业务服务层
│   ├── models/
│   │   └── hotchain.py                     ← 【新增】Pydantic 模型
│   └── main.py                             ← 【修改】注册新 router
│
├── frontend/                               ← Web 前端（React + Vite）
│   ├── src/
│   │   ├── pages/
│   │   │   └── hotchain/                   ← 【新增】所有 HotChain 页面
│   │   │       ├── WorkbenchPage.tsx       ← 工作台
│   │   │       ├── HotspotCenterPage.tsx   ← 热点中心
│   │   │       ├── IndustryChainPage.tsx   ← 产业链可视化
│   │   │       ├── SkillsPage.tsx          ← Skill 管理
│   │   │       ├── ReportsPage.tsx         ← 历史报告列表
│   │   │       └── ReportDetailPage.tsx    ← 报告详情
│   │   ├── components/
│   │   │   └── hotchain/
│   │   │       ├── StockSearchBox.tsx      ← 股票搜索框
│   │   │       ├── SkillSelector.tsx       ← Skill 多选
│   │   │       ├── StreamingReport.tsx     ← SSE 流式报告组件
│   │   │       ├── HotspotPanel.tsx        ← 热点榜单组件
│   │   │       ├── IndustryChainGraph.tsx  ← 产业链图（ECharts）
│   │   │       ├── PeerComparisonTable.tsx ← 同行业对比表
│   │   │       └── YamlEditor.tsx          ← Skill YAML 编辑器（CodeMirror）
│   │   ├── api/
│   │   │   └── hotchain.ts                 ← 调后端 API 的 client
│   │   ├── stores/
│   │   │   └── hotchainStore.ts            ← Zustand store
│   │   └── App.tsx                         ← 【修改】加路由
│   └── package.json                        ← 【修改】新依赖：echarts, react-codemirror, react-markdown
│
├── cli/                                    ← CLI
│   └── hotchain/                           ← 【新增】hotchain CLI 模块
│       ├── __init__.py
│       ├── __main__.py                     ← python -m hotchain
│       ├── analyze.py                      ← hotchain analyze
│       ├── hotspot.py                      ← hotchain hotspot
│       ├── chain.py                        ← hotchain chain
│       ├── web.py                          ← hotchain web
│       └── skill.py                        ← hotchain skill
│
└── .kiro/specs/hotchain_agent/             ← 本 spec
    ├── requirements.md
    ├── design.md
    └── tasks.md
```

---

## 3. 数据结构

### 3.1 AgentState 扩展（`tradingagents/agents/utils/agent_states.py`）

```python
class AgentState(MessagesState):
    # ... 现有字段保留 ...
    company_of_interest: str
    trade_date: str
    market_report: str
    sentiment_report: str
    news_report: str
    fundamentals_report: str

    # ===== 新增字段 =====
    hotspot_report: Annotated[str, "当日热点分析报告"]
    industry_chain_report: Annotated[str, "产业链分析报告"]

    hotspot_tool_call_count: Annotated[int, "Hotspot tool counter"]
    industry_chain_tool_call_count: Annotated[int, "IndustryChain tool counter"]

    # 用户选择的 skill ids
    selected_skills: Annotated[List[str], "User-selected skill ids"]

    # ... 其余保留 ...
```

### 3.2 Skill 数据类（`tradingagents/skills/base.py`）

```python
@dataclass
class Skill:
    name: str                          # 唯一 ID
    display_name: str                  # 中文名
    description: str
    instructions: str                  # 注入 prompt 的自然语言指令
    category: str = "framework"        # trend/pattern/reversal/framework
    core_rules: List[int] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    market_regimes: List[str] = field(default_factory=list)
    default_priority: int = 100
    enabled: bool = True
    source: str = "builtin"            # "builtin" | "custom"
    file_path: str = ""

class SkillManager:
    def __init__(self, builtin_dir: Path, custom_dir: Optional[Path] = None): ...
    def list_skills(self) -> List[Skill]: ...
    def get_skill(self, name: str) -> Optional[Skill]: ...
    def get_skills_by_ids(self, ids: List[str]) -> List[Skill]: ...
    def render_instructions(self, ids: List[str]) -> str: ...
    def reload(self) -> None: ...
```

### 3.3 上下游映射字典（`tradingagents/industry_chain_map.py`）

```python
# 基于申万一级行业的静态字典，第一期 MVP
INDUSTRY_CHAIN_MAP: Dict[str, Dict[str, List[str]]] = {
    "半导体": {
        "upstream": ["硅片", "光刻胶", "电子特气", "半导体设备"],
        "downstream": ["消费电子", "汽车电子", "通信设备", "数据中心"],
    },
    "光伏设备": {
        "upstream": ["多晶硅", "硅料", "EVA 树脂"],
        "downstream": ["电力运营", "新能源汽车", "储能"],
    },
    "白酒": {
        "upstream": ["包装材料（玻璃瓶/纸箱）", "高粱", "粮食"],
        "downstream": ["商超零售", "餐饮", "电商平台"],
    },
    # ... 至少覆盖 30+ 个常见行业
}
```

### 3.4 API 数据模型（`app/models/hotchain.py`）

```python
class AnalyzeRequest(BaseModel):
    stock_code: str
    market: Literal["a", "hk", "us"] = "a"
    skills: List[str] = []                # skill ids
    async_mode: bool = True
    debug: bool = False

class AnalyzeResponse(BaseModel):
    task_id: str
    stock_code: str
    stock_name: Optional[str]
    status: Literal["pending", "running", "completed", "failed"]
    hotspot_report: Optional[str]
    industry_chain_report: Optional[str]
    final_decision: Optional[Decision]    # 复用 SignalProcessor 输出
    full_report_md: Optional[str]
    created_at: datetime
    error: Optional[str]

class Decision(BaseModel):
    action: Literal["买入", "持有", "卖出"]
    target_price: Optional[float]
    confidence: float                     # 0~1
    risk_score: float                     # 0~1
    reasoning: str

class HotspotItem(BaseModel):
    type: Literal["industry", "concept", "popular", "search"]
    name: str
    change_pct: Optional[float]
    turnover: Optional[float]
    leading_stocks: List[str] = []
    rank: int

class HotspotResponse(BaseModel):
    trade_date: str
    industries: List[HotspotItem]
    concepts: List[HotspotItem]
    popular_stocks: List[HotspotItem]
    search_terms: List[str]
    cached_at: datetime

class IndustryChainResponse(BaseModel):
    ticker: str
    company_name: str
    industry: str
    sub_industry: Optional[str]
    upstream: List[str]                   # 关键词
    downstream: List[str]
    peers: List[PeerCompany]              # 同行业可比公司
    cached_at: datetime

class PeerCompany(BaseModel):
    code: str
    name: str
    change_pct: Optional[float]
    pe: Optional[float]
    market_cap: Optional[float]

class SkillSchema(BaseModel):
    name: str
    display_name: str
    description: str
    category: str
    enabled: bool
    source: str                           # "builtin" | "custom"
    instructions: str                     # 完整 prompt
```

---

## 4. 关键模块设计

### 4.1 数据 Provider 扩展（`tradingagents/dataflows/providers/china/akshare.py`）

新增两个异步方法：

```python
async def get_market_hotspot(self, top_n: int = 20) -> Dict[str, Any]:
    """
    获取当日市场热点
    Returns:
        {
          "industries": [{"name", "change_pct", "turnover", "leading_stocks": [...]}],
          "concepts": [...],
          "popular_stocks": [{"code", "name", "rank", "change_pct"}],
          "search_terms": ["AI", "光伏", ...],
        }
    """
    import akshare as ak
    industries = ak.stock_board_industry_name_em().head(top_n)
    concepts = ak.stock_board_concept_name_em().head(top_n)
    popular = ak.stock_hot_rank_em().head(50)
    try:
        search = ak.news_economic_baidu()  # 容错：可能因网络/接口变更失败
    except Exception:
        search = None
    # ... 标准化为 dict ...
    return {...}

async def get_industry_chain(self, symbol: str) -> Dict[str, Any]:
    """
    获取公司产业链
    Returns:
        {
          "industry": "半导体",
          "sub_industry": "...",
          "upstream": ["硅片", "光刻胶", ...],
          "downstream": ["消费电子", ...],
          "peers": [{"code", "name", "change_pct", "pe", ...}, ...],
        }
    """
    info = await self.get_stock_basic_info(symbol)
    industry = info.get("industry", "")
    # 同行业成分股
    try:
        peers_df = ak.stock_board_industry_cons_em(symbol=industry)
        peers = peers_df.head(20).to_dict(orient="records")
    except Exception:
        peers = []
    # 静态上下游映射
    from tradingagents.industry_chain_map import INDUSTRY_CHAIN_MAP
    chain = INDUSTRY_CHAIN_MAP.get(industry, {})
    return {
        "industry": industry,
        "upstream": chain.get("upstream", []),
        "downstream": chain.get("downstream", []),
        "peers": peers,
    }
```

### 4.2 Toolkit 工具（`tradingagents/agents/utils/agent_utils.py`）

新增两个 `@tool`，参考 `get_stock_news_unified` 模板：

```python
@staticmethod
@tool
@log_tool_call(tool_name="get_market_hotspot_unified", log_args=True)
def get_market_hotspot_unified(
    curr_date: Annotated[str, "当前日期 YYYY-MM-DD"],
    top_n: Annotated[int, "返回 Top N 条"] = 20,
) -> str:
    """获取当日市场热点：行业榜/概念榜/人气榜/百度热搜。"""
    from tradingagents.dataflows.providers.china.akshare import AKShareProvider
    # ... 异步调用 + 格式化为 Markdown ...
    return formatted_markdown

@staticmethod
@tool
@log_tool_call(tool_name="get_industry_chain_unified", log_args=True)
def get_industry_chain_unified(
    ticker: Annotated[str, "股票代码"],
    curr_date: Annotated[str, "当前日期"],
) -> str:
    """获取公司所属行业、上下游、同行业可比公司。"""
    # ... 同上 ...
    return formatted_markdown
```

### 4.3 HotspotAnalyst（`tradingagents/agents/analysts/hotspot_analyst.py`）

```python
def create_hotspot_analyst(llm, toolkit, skill_manager=None):
    @log_analyst_module("hotspot")
    def node(state):
        ticker = state["company_of_interest"]
        current_date = state["trade_date"]
        selected_skills = state.get("selected_skills", [])

        # 工具
        tools = [toolkit.get_market_hotspot_unified, toolkit.get_stock_news_unified]

        # Skill 注入
        skill_block = ""
        if skill_manager and selected_skills:
            skill_block = skill_manager.render_instructions(selected_skills)

        system_message = f"""你是一位专业的市场热点分析师。
任务：判断当日热点，并分析 {ticker} 与热点的关联度。

{skill_block}

执行步骤：
1. 调用 get_market_hotspot_unified 获取当日热点榜
2. 判断热点处于 启动/扩散/分化/退潮 哪个阶段
3. 找 {ticker} 是否在人气榜、行业榜对应位置
4. 输出 Markdown 报告（含热点阶段、关联度、是否龙头）
"""
        # ... 标准 chain.invoke + 死循环防护 + Google 模型分支 ...

        return {
            "messages": [clean_message],
            "hotspot_report": report,
            "hotspot_tool_call_count": tool_call_count + 1,
        }
    return node
```

### 4.4 IndustryChainAnalyst（`tradingagents/agents/analysts/industry_chain_analyst.py`）

```python
def create_industry_chain_analyst(llm, toolkit, skill_manager=None):
    @log_analyst_module("industry_chain")
    def node(state):
        ticker = state["company_of_interest"]
        current_date = state["trade_date"]
        hotspot_report = state.get("hotspot_report", "")
        selected_skills = state.get("selected_skills", [])

        tools = [toolkit.get_industry_chain_unified, toolkit.get_stock_news_unified]

        skill_block = ""
        if skill_manager and selected_skills:
            skill_block = skill_manager.render_instructions(selected_skills)

        system_message = f"""你是产业链分析师。
任务：分析 {ticker} 的产业链定位与景气度。

热点上下文（来自 HotspotAnalyst）：
{hotspot_report[:2000]}

{skill_block}

执行步骤：
1. 调用 get_industry_chain_unified 拿产业链结构
2. 输出报告：
   ## 一、行业定位
   ## 二、上游分析（成本压力 / 供应商集中度）
   ## 三、下游分析（需求景气度 / 客户集中度）
   ## 四、同行业横向对比（PE / 涨跌幅）
   ## 五、产业链视角的投资建议（买/持/卖 + 目标价）
"""
        # ... 标准模板 ...
        return {
            "messages": [clean_message],
            "industry_chain_report": report,
            "industry_chain_tool_call_count": tool_call_count + 1,
        }
    return node
```

### 4.5 LangGraph 改造（`tradingagents/graph/setup.py`）

在 `setup_graph` 中：

```python
# 在现有 selected_analysts 处理中加：
if "hotspot" in selected_analysts:
    analyst_nodes["hotspot"] = create_hotspot_analyst(
        self.quick_thinking_llm, self.toolkit, self.skill_manager
    )
    # ... + delete_node + tool_node

if "industry_chain" in selected_analysts:
    analyst_nodes["industry_chain"] = create_industry_chain_analyst(
        self.quick_thinking_llm, self.toolkit, self.skill_manager
    )

# 默认顺序：market → social → news → hotspot → industry_chain → fundamentals
DEFAULT_ORDER = ["market", "social", "news", "hotspot", "industry_chain", "fundamentals"]
ordered = [a for a in DEFAULT_ORDER if a in selected_analysts]
```

`conditional_logic.py` 加：
```python
def should_continue_hotspot(self, state):
    # 仿 should_continue_news
def should_continue_industry_chain(self, state):
    # 仿 should_continue_news
```

`trading_graph.py: _create_tool_nodes` 加：
```python
"hotspot": ToolNode([self.toolkit.get_market_hotspot_unified, self.toolkit.get_stock_news_unified]),
"industry_chain": ToolNode([self.toolkit.get_industry_chain_unified, self.toolkit.get_stock_news_unified]),
```

### 4.6 下游 Agent 拼接（5 个文件最小改动）

`bull_researcher.py` / `bear_researcher.py` / `research_manager.py` / `risk_manager.py` / `trader.py`：

```python
hotspot_report = state.get("hotspot_report", "")
industry_chain_report = state.get("industry_chain_report", "")
curr_situation = (
    f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n"
    f"{hotspot_report}\n\n{industry_chain_report}\n\n{fundamentals_report}"
)
# prompt 中提一句 "请综合热点驱动与产业链景气度做判断"
```

### 4.7 后端服务（`app/services/hotchain_service.py`）

```python
class HotChainService:
    def __init__(self):
        self.skill_manager = SkillManager(...)
        self._graph_cache = {}

    def analyze(self, stock_code, skills, market="a", task_id=None,
                progress_callback=None) -> AnalyzeResponse:
        config = create_analysis_config(
            selected_analysts=["market", "news", "hotspot", "industry_chain", "fundamentals"],
            market_type=market,
            ...
        )
        graph = self._get_graph(config)
        # 注入 skills 到初始 state
        init_state = {..., "selected_skills": skills}
        _, decision = graph.propagate(stock_code, today, progress_callback)
        return self._build_response(decision)

    def get_hotspot(self) -> HotspotResponse:
        # 直接调 Provider，不走 LLM（带 5 分钟 Redis 缓存）
        ...

    def get_industry_chain(self, ticker) -> IndustryChainResponse:
        # 同上
        ...
```

### 4.8 REST 路由（`app/routers/hotchain.py`）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/hotchain/analyze` | 异步触发，返回 `task_id` |
| POST | `/api/v1/hotchain/analyze/stream` | SSE 流式，事件类型同 DSA |
| GET | `/api/v1/hotchain/tasks/{task_id}` | 查询任务状态 |
| GET | `/api/v1/hotchain/hotspot` | 当日热点（带缓存） |
| GET | `/api/v1/hotchain/industry-chain/{ticker}` | 产业链 |
| GET | `/api/v1/hotchain/skills` | 列 skill |
| POST | `/api/v1/hotchain/skills` | 创建/更新 skill（自定义） |
| DELETE | `/api/v1/hotchain/skills/{name}` | 删 skill |
| GET | `/api/v1/hotchain/reports` | 历史列表（分页） |
| GET | `/api/v1/hotchain/reports/{id}` | 详情 |
| POST | `/api/v1/hotchain/reports/{id}/share` | 分享链接 |

SSE 事件结构：
```
event: thinking
data: {"step": "调用工具 get_market_hotspot_unified"}

event: tool_start
data: {"tool": "get_market_hotspot_unified", "args": {...}}

event: tool_done
data: {"tool": "get_market_hotspot_unified", "duration_ms": 1234, "result_preview": "..."}

event: report_chunk
data: {"section": "hotspot_report", "content_delta": "..."}

event: done
data: {"task_id": "...", "final_decision": {...}, "full_report_md": "..."}

event: error
data: {"message": "..."}
```

### 4.9 前端 Web UI（基于 React + Vite + Zustand）

#### 路由（`frontend/src/App.tsx` 修改）：
```tsx
<Route path="/hotchain" element={<WorkbenchPage />} />
<Route path="/hotchain/hotspot" element={<HotspotCenterPage />} />
<Route path="/hotchain/chain/:ticker" element={<IndustryChainPage />} />
<Route path="/hotchain/skills" element={<SkillsPage />} />
<Route path="/hotchain/reports" element={<ReportsPage />} />
<Route path="/hotchain/reports/:id" element={<ReportDetailPage />} />
```

#### WorkbenchPage 结构：
```
┌──────────────────────────────────────────────────────┐
│ HotChain 工作台                                       │
├──────────────────────────────────────────────────────┤
│ [股票输入: ____________ 🔍] (StockSearchBox)         │
│ 市场: ◉ A股 ○ 港股 ○ 美股                          │
│ 启用 Skill: ☑ hotspot_chase ☑ industry_chain_value  │
│             ☐ upstream_costdrop ...                  │
│ [开始分析]    [仅看热点]    [仅看产业链]            │
├──────────────────────────────────────────────────────┤
│ ▼ 实时执行流（SSE）                                  │
│  🤔 思考中：调用 get_market_hotspot_unified          │
│  🔧 工具调用：get_market_hotspot_unified（1.2s）    │
│  ✅ 工具完成：返回 20 行业 + 20 概念                │
│  🔧 工具调用：get_industry_chain_unified（0.8s）   │
│  📝 生成报告中...                                    │
├──────────────────────────────────────────────────────┤
│ ▼ 报告（Markdown 渲染）                              │
│  ## 一、市场热点概况                                 │
│  ## 二、产业链定位                                  │
│  ## 三、投资建议：买入 ¥1850 (置信度 0.78)         │
│  [导出 PDF] [分享] [重新分析]                        │
└──────────────────────────────────────────────────────┘
```

#### HotspotCenterPage：三栏（行业 / 概念 / 人气），点击行业可下钻到成分股。

#### IndustryChainPage：用 ECharts `tree` 或 Mermaid 渲染上下游链路；下方表格列出同行业可比公司，可按列排序。

#### SkillsPage：列表 + Toggle 启用/禁用 + "新建" 按钮 → 弹出 Drawer 包含 CodeMirror YAML 编辑器 + "试运行"。

---

## 5. SKILL.md 设计

```markdown
---
name: "hotchain_analyzer"
description: "热点+产业链+投资建议分析。输入股票代码，输出当日热点关联度、上下游产业链定位、明确买卖建议。"
---

# HotChain 分析器

## 函数

### 1. analyze_with_chain(stock_code, market="a", skills=None)
完整三段分析。
**输入**：stock_code（必填）、market（a/hk/us）、skills（list）
**输出**：含 hotspot_report、industry_chain_report、final_decision 的对象

**示例**：
```python
from app.services.hotchain_service import HotChainService
svc = HotChainService()
result = svc.analyze("600519", skills=["hotspot_chase"])
print(result.final_decision.action, result.final_decision.target_price)
```

### 2. get_today_hotspot()
仅返回当日热点榜。

### 3. analyze_industry_chain(stock_code)
仅返回产业链结构。
```

---

## 6. CLI 设计

```bash
# 命令骨架（用 click / typer 实现）
python -m hotchain analyze STOCK_CODE [--market a/hk/us] [--skills SKILL1,SKILL2]
                                       [--output md/json] [--debug] [--dry-run]
python -m hotchain hotspot
python -m hotchain chain STOCK_CODE
python -m hotchain web [--port 8000] [--host 0.0.0.0]
python -m hotchain skill list
python -m hotchain skill create NAME [--from-template framework]
python -m hotchain skill edit NAME
```

---

## 7. 缓存策略

| 数据 | 缓存层 | TTL |
|---|---|---|
| 热点榜 | Redis `hotchain:hotspot:{date}` | 5 分钟 |
| 产业链结构 | Redis `hotchain:chain:{ticker}` | 1 天 |
| 同行业可比公司 | Redis `hotchain:peers:{industry}` | 1 小时 |
| 完整分析报告 | MongoDB `hotchain_reports` | 永久 |

---

## 8. 配置（`.env.example` 追加）

```env
# HotChain
HOTCHAIN_ENABLED=true
HOTCHAIN_SKILL_DIR=                       # 自定义 skill 目录（可选）
HOTCHAIN_DEFAULT_SKILLS=hotspot_chase,industry_chain_value
HOTCHAIN_HOTSPOT_CACHE_TTL=300
HOTCHAIN_CHAIN_CACHE_TTL=86400
```

---

## 9. 演进路线

| 版本 | 范围 |
|---|---|
| **v0.1（MVP，1 周）** | Provider 扩展 + 2 个 Agent + 接入主图 + 1 个 CLI 命令 + 1 个 API（最小可用） |
| **v0.2（2 周）** | Skill 机制 + 6 个内置 YAML + Web 工作台基础页（输入框 + 流式输出 + Markdown 渲染） |
| **v0.3（3 周）** | 完整 Web（热点中心、产业链可视化、Skill 管理、历史报告、分享）+ SKILL.md |
| **v0.4（4 周）** | MCP server + 桌面端打包 + 单测覆盖 + 文档完善 |

---

## 10. 风险与对策

| 风险 | 对策 |
|---|---|
| AKShare 接口不稳定 | 多源降级（Tushare 备份）+ 5 分钟缓存 + 失败时返回 stale 数据 |
| 上下游静态字典精度有限 | 第二期用 LLM 辅助扩展；第三期接行业研报数据库 |
| 国产 LLM tool calling 不稳定 | 沿用现有的"预处理强制工具调用"模式 |
| 流式输出兼容性 | 使用标准 SSE，前端 EventSource API 支持所有现代浏览器 |
| YAML Skill 注入 prompt 注入风险 | 仅作为字符串注入，不执行；前端编辑器加 max-length 限制 |
| Web 端用户操作不熟悉股票分析 | 新手引导 Tour + 默认 Skill 预选 + 完整示例 |
