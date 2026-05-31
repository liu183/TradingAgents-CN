# HotChain v0.1 MVP — 实现说明

> 对应 [`spec/tasks.md`](./spec/tasks.md) 的阶段 0~3 + 最小 CLI。
> 本文记录本次 MVP 实际落地的代码改动与使用方法。

## 范围

本次 MVP 完成：

1. ✅ **数据 Provider 扩展** — `get_market_hotspot` + `get_industry_chain`
2. ✅ **2 个新 Agent** — `HotspotAnalyst` + `IndustryChainAnalyst`，并接入现有 LangGraph 主图
3. ✅ **最小 CLI** — `python -m hotchain analyze 600519`（外加 `hotspot` / `chain` 子命令）
4. ✅ **下游决策链打通** — 牛熊辩论 / 投研经理 / 交易员 / 风险经理均纳入热点 + 产业链报告

> Skill 机制（YAML 策略）、Web 工作台、REST API、SKILL.md 属于后续阶段（v0.2+），不在本 MVP。

## 改动清单

### 新增文件

| 文件 | 说明 |
|---|---|
| `tradingagents/industry_chain_map.py` | 34 个行业的上下游静态映射 + `lookup_industry_chain()` 三级降级匹配 |
| `tradingagents/agents/analysts/hotspot_analyst.py` | 热点分析师（`create_hotspot_analyst`） |
| `tradingagents/agents/analysts/industry_chain_analyst.py` | 产业链分析师（`create_industry_chain_analyst`） |
| `hotchain/__init__.py` `__main__.py` `config.py` `cli.py` | CLI 包（`python -m hotchain`） |
| `tests/test_hotchain_industry_chain_map.py` | 无依赖单测（8 用例全过） |

### 修改文件

| 文件 | 改动 |
|---|---|
| `tradingagents/dataflows/providers/china/akshare.py` | `AKShareProvider` 新增 `get_market_hotspot` / `get_industry_chain`，模块级加 `_safe_float` / `_safe_int` |
| `tradingagents/agents/utils/agent_utils.py` | `Toolkit` 新增 `get_market_hotspot_unified` / `get_industry_chain_unified`，模块级加 2 个 Markdown 格式化函数 |
| `tradingagents/agents/utils/agent_states.py` | `AgentState` 加 `hotspot_report` / `industry_chain_report` / `selected_skills` / 2 个计数器 |
| `tradingagents/graph/propagation.py` | `create_initial_state` 初始化新字段 |
| `tradingagents/agents/__init__.py` | 注册 2 个 factory |
| `tradingagents/graph/conditional_logic.py` | 加 `should_continue_hotspot` / `should_continue_industry_chain` |
| `tradingagents/graph/trading_graph.py` | `_create_tool_nodes` 加 2 个 ToolNode |
| `tradingagents/graph/setup.py` | import + 建节点 + 顺序规范化（hotspot 必在 industry_chain 前） |
| `tradingagents/agents/researchers/{bull,bear}_researcher.py` | `curr_situation` + prompt 纳入新报告 |
| `tradingagents/agents/managers/{research_manager,risk_manager}.py` | 同上 |
| `tradingagents/agents/trader/trader.py` | `curr_situation` 纳入新报告 |
| `.env.example` | 追加 HotChain 配置项 |

## 数据流

```
TradingAgentsGraph(selected_analysts=[market, news, hotspot, industry_chain, fundamentals])
   │
   ├─ HotspotAnalyst        → get_market_hotspot_unified → state["hotspot_report"]
   ├─ IndustryChainAnalyst  → get_industry_chain_unified（读 hotspot_report 作上下文）
   │                          → state["industry_chain_report"]
   ▼
Bull/Bear 辩论 → Research Manager（投资计划）→ Trader → Risk Judge
   （以上节点的 curr_situation / prompt 均已纳入热点 + 产业链报告）
   ▼
SignalProcessor → {action: 买入/持有/卖出, target_price, confidence, risk_score, reasoning}
```

## 使用方法

```bash
# 完整分析（需安装依赖 + 配置 LLM/数据源 API Key）
python -m hotchain analyze 600519
python -m hotchain analyze 600519 --depth 3 --output md
python -m hotchain analyze 000001 --provider dashscope --quick-model qwen-turbo --deep-model qwen-plus

# 仅看当日热点（仅需 AKShare，不调 LLM）
python -m hotchain hotspot
python -m hotchain hotspot --top-n 20 --output json

# 仅看产业链（仅需 AKShare，不调 LLM）
python -m hotchain chain 600519
```

CLI 通过环境变量或命令行选项解析 LLM 设置，优先级：**CLI 选项 > 环境变量 > `DEFAULT_CONFIG`**。
相关环境变量见 `.env.example` 的 HotChain 段（`HOTCHAIN_LLM_PROVIDER` / `HOTCHAIN_QUICK_MODEL` / `HOTCHAIN_DEEP_MODEL` / `HOTCHAIN_BACKEND_URL`）。

## Live 运行前置条件

本次开发沙箱为离线环境（`INTEGRATIONS_ONLY`），仅能做静态校验，**未执行真实 live run**。真实运行需要：

1. 安装依赖：`pip install -r requirements.txt`（akshare / langchain / langgraph / pandas / toml 等）
2. 配置 LLM API Key（如 `DASHSCOPE_API_KEY` / `DEEPSEEK_API_KEY` / `OPENAI_API_KEY` 等）
3. 联网访问 AKShare（东方财富 / 百度财经）数据接口
4. 运行：`python -m hotchain analyze 600519`

## 已验证项（离线）

- ✅ 全部 20 个改动文件通过 `ast.parse` 语法校验
- ✅ `industry_chain_map` 8 个单测全过（含别名 / 包含 / 边界）
- ✅ Markdown 格式化函数（热点 / 产业链）逻辑验证通过
- ✅ `python -m hotchain --help` / `analyze --help` 正常；缺依赖时 `analyze` 优雅报错（exit 2）

## 兼容性 & 安全

- 新分析师通过 `selected_analysts` 列表**可选启用**，旧流程（仅 market/social/news/fundamentals）完全不受影响。
- 数据接口单源 try/except 降级，单一数据源失败不阻塞整体分析。
- CLI 重依赖全部惰性导入，裸环境可显示帮助而不崩溃。
- 产业链工具对非 A 股标的返回"暂不支持"提示，不报错。

## 后续（v0.2+）

见 [`spec/tasks.md`](./spec/tasks.md) 阶段 4~10：Skill 机制、REST API + SSE、Web 工作台、SKILL.md、MCP server。
