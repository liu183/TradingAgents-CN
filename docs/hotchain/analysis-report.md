# HotChain — 参考项目对比分析报告

> 对 `ZhuLinsen/daily_stock_analysis (DSA)` 的架构拆解，
> 以及与本仓库 `TradingAgents-CN` 现状的差距对照，
> 用于指导 [HotChain Agent](./spec/requirements.md) 的设计与实现。

---

## 1. TradingAgents-CN 现状回顾

### 1.1 双层架构

| 层 | 路径 | 作用 |
|---|---|---|
| 核心引擎 | `tradingagents/` | 纯 Python 库，可独立运行 |
| Web 后端 | `app/` (FastAPI) | 把核心引擎包装成 API，配 MongoDB + Redis + 队列 |
| 旧版 UI | `web/` | Streamlit |
| 新版 UI | `frontend/` | React + Vite |
| CLI | `cli/main.py` | questionary 交互式 |

### 1.2 多 Agent 流水线（LangGraph）

```
START
  → Market Analyst  ⇄ tools_market → Msg Clear Market
  → Social Analyst  ⇄ tools_social → Msg Clear Social
  → News Analyst    ⇄ tools_news   → Msg Clear News
  → Fundamentals    ⇄ tools_fund   → Msg Clear Fundamentals
  → Bull Researcher ⇄ Bear Researcher  (max_debate_rounds 轮)
  → Research Manager  (生成 investment_plan)
  → Trader            (生成 trader_investment_plan)
  → Risky → Safe → Neutral  (max_risk_discuss_rounds 轮)
  → Risk Judge        (生成 final_trade_decision)
  → END
```

### 1.3 Agent 设计模式

每个 Agent = **闭包工厂函数**，返回 `node(state) -> dict`：

```python
def create_xxx_analyst(llm, toolkit):
    @log_analyst_module("xxx")
    def xxx_node(state):
        # 1) 从 state 取 ticker / trade_date / messages
        # 2) 识别市场 + 公司名
        # 3) 选 toolkit 工具
        # 4) ChatPromptTemplate (system + MessagesPlaceholder)
        # 5) chain = prompt | llm.bind_tools(tools)
        # 6) 处理 Google / DashScope / DeepSeek 特殊路径
        # 7) 返回 {messages, xxx_report, xxx_tool_call_count}
    return xxx_node
```

特色：
- ✅ 强 prompt 约束（"绝对禁止"系列）
- ✅ 预处理强制工具调用（适配国产 LLM）
- ✅ 死循环防护（`xxx_tool_call_count` 计数器）
- ✅ Google 模型分支（`GoogleToolCallHandler`）

### 1.4 状态管理

`AgentState(MessagesState)` 关键字段：
- `company_of_interest`、`trade_date`、`messages`
- `market_report`、`sentiment_report`、`news_report`、`fundamentals_report`
- `*_tool_call_count`（死循环防护）
- `investment_debate_state`、`risk_debate_state`
- `investment_plan`、`trader_investment_plan`、`final_trade_decision`

### 1.5 投资建议输出

通过 `tradingagents/graph/signal_processing.py: SignalProcessor`，把 Trader / Risk Judge 的中文文本结构化成：

```json
{
  "action": "买入/持有/卖出",
  "target_price": 数字,
  "confidence": 0~1,
  "risk_score": 0~1,
  "reasoning": "中文摘要"
}
```

含英文映射、目标价正则提取、智能价格推算。**新 Agent 不需要重写决策逻辑**。

### 1.6 数据层

| 市场 | Provider | 文件 |
|---|---|---|
| **A 股** | Tushare、AKShare、Baostock | `dataflows/providers/china/{tushare,akshare,baostock}.py` |
| **美股** | yfinance、Finnhub、Alpha Vantage | `dataflows/providers/us/*.py` |
| **港股** | AKShare、yfinance | `dataflows/providers/hk/*.py` |
| **新闻** | 东方财富、Google News、Reddit、FinnHub、Alpha Vantage、NewsAPI | `dataflows/news/*.py` |

**Toolkit 统一工具**（`agents/utils/agent_utils.py`）：
- `get_stock_fundamentals_unified`
- `get_stock_market_data_unified`
- `get_stock_news_unified`
- `get_stock_sentiment_unified`

内部根据 `StockUtils.get_market_info(ticker)` 自动分流。

### 1.7 现有缺口

| 能力 | 状态 |
|---|---|
| 当日热点榜 (行业/概念/人气/财经热搜) | ❌ 完全没有 |
| 公司上下游产业链结构 | ❌ 仅抓了 `industry` 字段 |
| 同行业可比公司分析 | ❌ |
| Skill 机制（自然语言策略） | ❌ |
| SKILL.md 对外暴露 | ❌ |
| 现代 Web 工作台 | ⚠️ 有 frontend/ 但功能基础 |
| MCP server | ❌ |

---

## 2. DSA (daily_stock_analysis) 项目分析

### 2.1 项目定位

面向 **"每日股票分析推送"** 的 AI 系统：
- **输入**：自选股列表（如 `600519,hk00700,AAPL`）
- **核心动作**：每日自动跑一遍 → 生成"决策仪表盘"+"大盘复盘"
- **输出**：Markdown 报告 → 推送到企业微信 / 飞书 / Telegram / Discord / Slack / 邮箱
- **同时支持**：Web 工作台、桌面端、Bot 命令、API、CLI、定时任务、回测

### 2.2 与 TradingAgents-CN 的核心差异

| 维度 | TradingAgents-CN | DSA |
|---|---|---|
| 核心思想 | 多 Agent 辩论（牛/熊/风险三辩） | 单 Agent + 多 Skill 调度 |
| 执行模式 | LangGraph 状态机，重 | LLM Tool Calling，轻 |
| 形态 | Python 库 + FastAPI + Streamlit/React | CLI + FastAPI + React 工作台 + Electron 桌面 + Bot |
| 用户交互 | 主要被动跑分析 | **支持多轮对话问股**（/chat 页 + Bot） |
| 定时任务 | 无 | 强（GitHub Actions / 内置 schedule / Docker） |
| **Skill 机制** | ❌ 无 | ✅ **YAML 自然语言策略**（15 个内置 + 可扩展） |
| 推送通道 | 无 | 6+ 个 IM / 邮件 |

### 2.3 Skill 机制（最值得借鉴的部分）

DSA 的 **Skill = 自然语言策略**，本质是 YAML 文件，结构如下：

```yaml
name: hot_theme              # 唯一 ID
display_name: 热点题材
description: ...
category: framework          # trend / pattern / reversal / framework
core_rules: [2, 3, 5, 7]     # 关联的核心交易理念
required_tools:              # 该策略需要哪些工具
  - get_sector_rankings
  - search_stock_news
aliases: [热点, 题材]
default_priority: 35
market_regimes: [sector_hot]
instructions: |
  # 长篇自然语言提示词，告诉 LLM 这个策略怎么判断、怎么打分
  ...
```

**加载机制**（`src/agent/skills/base.py`）：

1. 启动时扫 `strategies/` 所有 `.yaml`，构建 `SkillManager`
2. 用户在 `/chat` 页或 `/api/v1/agent/chat` 选 skill
3. `Skill.instructions` 被注入 LLM system prompt
4. LLM 通过 `required_tools` 调工具拿数据
5. 也支持 `SKILL.md`（Claude Skill 格式，含 frontmatter + Markdown body）

DSA 的 `SKILL.md`（项目根目录）则是**对外暴露的 Claude Skill 入口**，让 Claude Code 等外部 Agent 能直接调用 DSA 的分析能力。

### 2.4 DSA 多形态部署架构

```
┌─────────────────────────────────────────────────────────────────┐
│                       入口层（多形态）                          │
├─────────────────────────────────────────────────────────────────┤
│  CLI (main.py)  │  Web (apps/dsa-web)  │  Desktop (Electron)    │
│  Bot (DingTalk/Feishu/Telegram/...)  │  GitHub Actions          │
│  Claude Skill (SKILL.md)  │  REST API (FastAPI)                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   API 层 (api/v1/endpoints/)                    │
│  agent.py → /chat/stream (SSE)、/skills、/strategies            │
│  analysis.py → /analyze、/market-review、/tasks/stream          │
│  history、stocks、backtest、portfolio、alerts、alphasift...     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                Agent 层 (src/agent/)                            │
│  skills/  ←── YAML 策略加载                                     │
│  agents/  ←── intel/decision/portfolio/risk/technical 等子 agent │
│  tools/   ←── get_realtime_quote、search_stock_news 等          │
│  orchestrator.py / executor.py / runner.py                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│       数据层 (data_provider/、src/services/、src/repositories)   │
│  AkShare / Tushare / Pytdx / yfinance / Longbridge              │
│  搜索：Anspire / SerpAPI / Tavily / Bocha / Brave / SearXNG     │
└─────────────────────────────────────────────────────────────────┘
```

**关键技术栈**：

- **后端**：FastAPI + uvicorn + SSE + 异步任务队列
- **前端**：React 19 + TypeScript + Vite + Tailwind + Zustand + Recharts
- **桌面**：Electron（复用前端）
- **协议**：REST + SSE（流式输出）
- **LLM**：OpenAI 兼容 / Gemini / Claude / Anspire / DeepSeek / 通义千问 / Ollama

---

## 3. 差距对照与目标系统的能力映射

| 能力 | TradingAgents-CN | DSA | HotChain（目标） |
|---|---|---|---|
| 多 Agent 分析 | ✅ 强 | ⚠️ 弱 | ✅ **保留并扩展** |
| 热点获取 | ❌ | ✅ `get_sector_rankings` | ✅ **新增** |
| 上下游产业链 | ❌ | ⚠️ 部分（hot_theme 提及） | ✅ **新增** |
| Skill 机制 | ❌ | ✅ YAML | ✅ **新增（仿 DSA）** |
| Claude SKILL.md | ❌ | ✅ | ✅ **新增** |
| CLI | ⚠️ 弱 | ✅ 完善 | ✅ **增强** |
| Web 端 | ⚠️ 旧+新 | ✅ 现代 | ✅ **整合扩展** |
| 网页可操作能力 | ❌ | ⚠️ 仅展示 | ✅ **新增（重点）** |
| Bot | ❌ | ✅ | ⏸️ 后续 |
| 定时推送 | ❌ | ✅ | ⏸️ 后续 |
| 桌面端 | ❌ | ✅ Electron | ⏸️ 后续 |

---

## 4. 关键设计决策

### 4.1 不重写，做扩展

**决策**：不做独立项目，作为 TradingAgents-CN 的扩展模块。

**理由**：

- 多 Agent 辩论（牛 / 熊 / 风险三辩）是 TradingAgents-CN 的核心优势，DSA 没有
- `SignalProcessor` 已能处理"中文文本 → 结构化决策"，零重写
- LangGraph 流水线成熟，加 2 个新分析师只需要插入到现有图中

### 4.2 Skill 仿 DSA，但融入 LangGraph

**决策**：新增 `tradingagents/skills/`，模仿 DSA 的 `Skill` + `SkillManager` + YAML 设计。

但**注入位置**不同：

- DSA：注入到单 Agent 的 system prompt
- HotChain：注入到 `HotspotAnalyst` / `IndustryChainAnalyst` 的 system prompt（在 LangGraph 节点内）

这样既能复用 DSA 的"自然语言策略"易用性，又能保留 TradingAgents-CN 的多 Agent 协作。

### 4.3 多形态入口，逐步推进

**决策**：

- **v0.1**：CLI + API 最小可用（1 周）
- **v0.2**：Skill 机制 + 完整 Web 工作台（2 周）
- **v0.3**：SKILL.md + 完整产业链可视化（3 周）
- **v0.4**：MCP server + 桌面端（4 周）

每阶段独立成 PR，每阶段都可发布。

### 4.4 网页可操作能力

**决策**：Web 端不只是展示报告，要支持：

- ✅ 表单填写：股票代码（自动补全）、日期选择、市场切换、Skill 多选
- ✅ 点击操作：一键分析 / 重新分析 / 收藏 / 分享 / 导出 PDF
- ✅ 流式展示：SSE 实时推送 LLM 工具调用过程 + 报告
- ✅ 浏览：分页 / 搜索 / 标签筛选历史报告
- ✅ 编辑：在线 YAML 编辑器写自定义 Skill（语法校验 + 实时预览）
- ✅ 分享：生成只读公开链接

### 4.5 静态产业链字典先行

**决策**：第一期用静态 `INDUSTRY_CHAIN_MAP` 字典覆盖 30+ 申万一级行业，后续迭代再用 LLM 推理扩展、最终接研报数据库。

**理由**：pragmatic 起步，避免一开始就做"完美的产业链知识图谱"导致项目 stuck。

---

## 5. 关键扩展点（落地清单）

### 5.1 数据层（`tradingagents/dataflows/providers/china/akshare.py`）

新增 2 个异步方法：
- `get_market_hotspot(top_n=20)` — 行业榜 + 概念榜 + 人气榜 + 百度热搜
- `get_industry_chain(symbol)` — 行业 + 同行业可比公司 + 上下游关键词

底层调用：`ak.stock_board_industry_name_em` / `ak.stock_board_concept_name_em` / `ak.stock_hot_rank_em` / `ak.stock_board_industry_cons_em` / `ak.news_economic_baidu`。

### 5.2 工具层（`tradingagents/agents/utils/agent_utils.py`）

新增 2 个 `@tool`：
- `get_market_hotspot_unified` — 给 HotspotAnalyst
- `get_industry_chain_unified` — 给 IndustryChainAnalyst

风格参考现有 `get_stock_news_unified`（Markdown 格式化、容错降级）。

### 5.3 Agent 层

| 文件 | 类型 | 说明 |
|---|---|---|
| `tradingagents/agents/analysts/hotspot_analyst.py` | 新增 | 输出 `state["hotspot_report"]` |
| `tradingagents/agents/analysts/industry_chain_analyst.py` | 新增 | 输出 `state["industry_chain_report"]` |
| `tradingagents/agents/utils/agent_states.py` | 修改 | 加 4 个状态字段 |
| `tradingagents/agents/__init__.py` | 修改 | 注册 factory |
| `tradingagents/graph/setup.py` | 修改 | 接入主图 |
| `tradingagents/graph/conditional_logic.py` | 修改 | 加条件判断 |
| `tradingagents/graph/trading_graph.py` | 修改 | 加 ToolNode |
| `tradingagents/agents/{researchers,managers,trader}/*.py` | 修改 5 文件 | 拼接 `curr_situation`、prompt 提一句 |

### 5.4 Skill 系统（`tradingagents/skills/`）

```
tradingagents/skills/
├── base.py              # Skill + SkillManager
├── loader.py            # YAML 加载
└── builtin/
    ├── hotspot_chase.yaml          # 热点追击
    ├── industry_chain_value.yaml   # 产业链价值挖掘
    ├── upstream_costdrop.yaml      # 上游成本下降受益
    ├── downstream_demand_boom.yaml # 下游需求爆发受益
    ├── concept_speculation.yaml    # 概念炒作（短线）
    └── policy_driven.yaml          # 政策驱动
```

### 5.5 多形态入口

| 入口 | 路径 | 说明 |
|---|---|---|
| CLI | `cli/hotchain/` | typer/click，支持 `analyze` / `hotspot` / `chain` / `web` / `skill` |
| API | `app/routers/hotchain.py` | REST + SSE 流式 |
| Web | `frontend/src/pages/hotchain/` | 工作台 / 热点中心 / 产业链 / Skill 管理 / 历史报告 |
| SKILL.md | `SKILL.md` | 项目根，对外暴露给 Claude Code / Kiro |
| MCP | `tradingagents/mcp/hotchain_server.py` | P2 可选 |

---

## 6. 风险与对策

| 风险 | 对策 |
|---|---|
| AKShare 接口不稳定 | 多源降级 + 5 分钟缓存 + 失败时 stale 兜底 |
| 静态产业链字典精度有限 | 第二迭代用 LLM 辅助；第三迭代接研报数据库 |
| 国产 LLM tool calling 不稳定 | 沿用现有 DashScope/DeepSeek 预处理强制工具调用 |
| LangGraph 改动影响现有功能 | 新分析师可选启用（`selected_analysts` 列表），旧流程不变 |
| 流式输出兼容性 | 标准 SSE，前端 EventSource 全浏览器支持 |
| YAML Skill prompt 注入风险 | 仅作为字符串注入，不执行；前端编辑器加 max-length |
| Web 用户不熟悉股票分析 | 新手引导 + 默认 Skill 预选 + 完整示例 |

---

## 7. 结论

**HotChain = TradingAgents-CN 的多 Agent 优势 + DSA 的 Skill 机制 + 多形态入口 + 网页可操作能力**。

实现路径已在 [`spec/tasks.md`](./spec/tasks.md) 拆分为 10 个阶段、约 14 天工作量。建议从 **v0.1 MVP**（阶段 0~3）切入，1 周内端到端跑通后再迭代后续形态。
