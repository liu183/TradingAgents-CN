# HotChain Agent — 需求文档（Requirements）

> 项目代号：**HotChain**（Hot + Industry Chain，热点与产业链投资建议 Agent）
> 基础工程：`TradingAgents-CN`
> 灵感参考：`ZhuLinsen/daily_stock_analysis (DSA)` 的 Skill / CLI / Web / API / Skill 多形态架构

---

## 1. 背景与目标

### 1.1 背景

`TradingAgents-CN` 已具备成熟的多 Agent 牛熊辩论框架（LangGraph + 4 类分析师 + 风险三辩 + Trader），但缺少：

1. **市场热点感知**：当前没有任何接口抓取当日热门行业/概念/人气榜。
2. **产业链分析**：仅在股票基础信息中有 `industry` 字段，没有上下游产业链结构、没有同行业可比公司分析。
3. **Skill 机制**：分析维度被代码硬编码，普通用户无法用自然语言扩展自定义策略。
4. **多形态部署**：Web 端是旧版 Streamlit + 新版 React，没有统一的"产品级工作台"，CLI 弱，没有 SKILL.md 让外部 AI Agent 调用，没有完整流式交互能力。

### 1.2 目标

构建一个 **"热点 + 产业链 + 投资建议" 三位一体的 AI Agent 系统**，并以 **Skill / CLI / Web / API / MCP** 多形态对外暴露。

核心价值：用户输入一只股票代码，系统能：

- **告诉用户当日市场热点是什么**，热点是否与该股票相关；
- **给出该公司的产业链定位**（上游、下游、同行业可比公司、景气度判断）；
- **结合热点与产业链，给出明确投资建议**（买入/持有/卖出 + 目标价 + 止损位 + 时间窗口）；
- 支持**网页交互式操作**：填写表单、点击触发、实时流式查看分析、浏览历史、在线编辑自定义策略。

---

## 2. 用户角色与场景

### 2.1 角色

| 角色 | 描述 |
|---|---|
| 散户投资者 | 想快速判断手里持仓是否在热点中、产业链是否健康 |
| 量化研究员 | 想批量分析自选股池、自定义策略、查看回测 |
| AI Agent 开发者 | 想通过 SKILL.md / MCP 让外部 AI（Claude Code / Kiro）调用 HotChain 能力 |
| 内容创作者 | 想生成结构化分析报告用于公众号 / 知识星球 |

### 2.2 用户故事

| 编号 | 用户故事 | 优先级 |
|---|---|---|
| US-1 | 作为散户，我想输入股票代码，立即看到该股的热点关联与投资建议 | P0 |
| US-2 | 作为散户，我想看到该公司的上下游产业链结构，判断景气度 | P0 |
| US-3 | 作为散户，我想看到当日市场热点榜，并能点击下钻到具体板块成分股 | P0 |
| US-4 | 作为散户，我想在网页填写自定义 Skill（自然语言策略），并立即试运行 | P1 |
| US-5 | 作为散户，我想看到分析过程的流式输出（LLM 调用了哪些工具、拿到了什么数据） | P1 |
| US-6 | 作为研究员，我想用 CLI 批量分析自选股池 | P0 |
| US-7 | 作为研究员，我想分享只读公开报告链接给团队 | P2 |
| US-8 | 作为 AI Agent 开发者，我想通过 SKILL.md 让 Claude 调用 HotChain | P1 |
| US-9 | 作为研究员，我想导出 Markdown / PDF 报告 | P2 |
| US-10 | 作为研究员，我想配置定时任务每日自动分析 + 推送通知 | P2（后续迭代） |

---

## 3. 功能需求（Functional Requirements）

### 3.1 数据获取层（FR-D）

| 编号 | 需求 | 验收标准 |
|---|---|---|
| FR-D1 | 获取当日热门行业板块榜（按涨跌幅、成交额、人气） | 接口返回 Top 20 行业板块；含名称、涨跌幅、成交额、龙头股 |
| FR-D2 | 获取当日热门概念板块榜 | 接口返回 Top 20 概念板块；同上 |
| FR-D3 | 获取当日热门个股人气榜 | 接口返回东方财富人气榜 Top 50 |
| FR-D4 | 获取百度财经热搜 | 接口返回当日热搜词 Top 20 |
| FR-D5 | 获取公司所属行业（一级、二级） | 复用现有 `industry` 字段 |
| FR-D6 | 获取公司同行业可比公司列表 | 调用 AKShare `stock_board_industry_cons_em`，返回 Top 20 同行业股票及其涨跌幅 |
| FR-D7 | 获取公司上下游行业关键词 | 第一期用静态 `INDUSTRY_CHAIN_MAP` 字典；第二期用 LLM 推理扩展；第三期可接行业研报数据库 |
| FR-D8 | 数据缓存 | 热点榜数据 5 分钟缓存；产业链数据 1 天缓存（Redis） |

### 3.2 Agent 层（FR-A）

| 编号 | 需求 | 验收标准 |
|---|---|---|
| FR-A1 | 新增 `HotspotAnalyst` 分析师 | 调用 FR-D1~D4 工具，输出 Markdown 热点分析报告，写入 `state["hotspot_report"]` |
| FR-A2 | 新增 `IndustryChainAnalyst` 分析师 | 调用 FR-D5~D7 工具，输出 Markdown 产业链分析报告，写入 `state["industry_chain_report"]` |
| FR-A3 | 两个 Agent 接入主图 | 在 `News Analyst` 之后插入，顺序：Market → Social → News → Hotspot → IndustryChain → Fundamentals |
| FR-A4 | 下游 Agent 读取新报告 | Bull/Bear/Trader/RiskJudge 的 `curr_situation` 拼接需包含 `hotspot_report` 和 `industry_chain_report` |
| FR-A5 | 死循环防护 | 沿用现有 `xxx_tool_call_count` 模式，限制工具调用次数 |
| FR-A6 | 国产 LLM 兼容 | 沿用现有的 DashScope/DeepSeek/Zhipu 预处理强制工具调用模式 |
| FR-A7 | Google 模型兼容 | 沿用现有 `GoogleToolCallHandler` |
| FR-A8 | 投资建议输出 | 复用现有 `SignalProcessor`，最终输出 `{action, target_price, confidence, risk_score, reasoning}` JSON |

### 3.3 Skill 层（FR-S）

| 编号 | 需求 | 验收标准 |
|---|---|---|
| FR-S1 | 实现 `tradingagents/skills/` 模块 | 提供 `Skill` 数据类、`SkillManager`、YAML 加载器（仿 DSA `src/agent/skills/base.py`） |
| FR-S2 | 内置 6+ 个 Skill YAML | 至少包含：hotspot_chase / industry_chain_value / upstream_costdrop / downstream_demand_boom / concept_speculation / policy_driven |
| FR-S3 | Skill 注入 prompt | 选中的 Skill 的 `instructions` 字段被注入到 `IndustryChainAnalyst` 的 system prompt |
| FR-S4 | 自定义 Skill 目录 | 通过环境变量 `HOTCHAIN_SKILL_DIR` 指定额外目录；同名时自定义覆盖内置 |
| FR-S5 | Skill 校验 | 加载时校验 YAML 字段完整性，缺失 `name`/`instructions` 报错 |

### 3.4 SKILL.md（FR-K）

| 编号 | 需求 | 验收标准 |
|---|---|---|
| FR-K1 | 项目根新增 `SKILL.md` | 含 frontmatter（name + description），Body 列出可调用函数 |
| FR-K2 | 暴露 3 个核心函数 | `analyze_with_chain(stock_code, ...)` / `get_today_hotspot()` / `analyze_industry_chain(stock_code)` |
| FR-K3 | 兼容 Claude Skill 协议 | 可被 Claude Code / OpenClaw / Kiro 直接识别和调用 |

### 3.5 CLI 层（FR-C）

| 编号 | 需求 | 验收标准 |
|---|---|---|
| FR-C1 | `python -m hotchain analyze STOCK_CODE` | 单股分析，输出到 stdout（带颜色） |
| FR-C2 | `python -m hotchain analyze a,b,c` | 批量分析 |
| FR-C3 | `--skills SKILL1,SKILL2` 参数 | 选择启用的 Skill |
| FR-C4 | `--market a/hk/us` | 指定市场 |
| FR-C5 | `--output md/json/pdf` | 输出格式 |
| FR-C6 | `python -m hotchain hotspot` | 仅看当日热点 |
| FR-C7 | `python -m hotchain chain STOCK_CODE` | 仅看产业链 |
| FR-C8 | `python -m hotchain web --port 8000` | 启动 Web 服务 |
| FR-C9 | `python -m hotchain skill list/create/edit` | 管理自定义 skill |
| FR-C10 | `--debug` / `--dry-run` 参数 | 调试模式 / 仅获取数据不调 LLM |

### 3.6 API 层（FR-API）

| 编号 | 需求 | 验收标准 |
|---|---|---|
| FR-API1 | `POST /api/v1/hotchain/analyze` | 触发分析；body 含 `stock_code`、`skills`、`async_mode` |
| FR-API2 | `POST /api/v1/hotchain/analyze/stream` | SSE 流式分析；事件类型：`tool_start`/`tool_done`/`thinking`/`generating`/`done`/`error` |
| FR-API3 | `GET /api/v1/hotchain/hotspot` | 当日热点榜 |
| FR-API4 | `GET /api/v1/hotchain/industry-chain/{ticker}` | 公司产业链 |
| FR-API5 | `GET /api/v1/hotchain/skills` | 列出所有 Skill |
| FR-API6 | `POST /api/v1/hotchain/skills` | 创建/更新自定义 Skill |
| FR-API7 | `DELETE /api/v1/hotchain/skills/{name}` | 删除自定义 Skill |
| FR-API8 | `GET /api/v1/hotchain/reports` | 历史报告列表（分页、按股票/日期筛选） |
| FR-API9 | `GET /api/v1/hotchain/reports/{id}` | 报告详情（含 Markdown） |
| FR-API10 | `POST /api/v1/hotchain/reports/{id}/share` | 生成只读公开链接（带过期时间） |
| FR-API11 | OpenAPI 文档 | 在 `/docs` 自动生成 Swagger |

### 3.7 Web UI 层（FR-W）

| 编号 | 需求 | 验收标准 |
|---|---|---|
| FR-W1 | 工作台首页 `/hotchain` | 含输入框（股票代码自动补全）、Skill 多选、市场切换、"开始分析"按钮 |
| FR-W2 | 流式分析视图 | 点击"开始分析"后，右侧实时显示 LLM 工具调用日志 + 最终报告 Markdown 渲染 |
| FR-W3 | 热点中心 `/hotchain/hotspot` | 三栏布局：行业榜 / 概念榜 / 人气榜；自动 60 秒刷新；点击行业可下钻 |
| FR-W4 | 产业链可视化 `/hotchain/chain/:ticker` | 用 ECharts/Mermaid 渲染上下游产业链图；同行业对比表（按 PE/涨跌幅排序） |
| FR-W5 | Skill 管理 `/hotchain/skills` | 列表 + 启用/禁用切换 + "新建" 按钮打开 YAML 编辑器（CodeMirror） |
| FR-W6 | YAML 编辑器 | 含语法高亮、字段校验、"试运行"按钮 |
| FR-W7 | 历史报告 `/hotchain/reports` | 表格分页；筛选：股票代码、日期范围、Skill；操作：查看 / 导出 / 分享 / 删除 |
| FR-W8 | 报告详情 | Markdown 渲染、目录导航、"重新分析"按钮、"分享"按钮 |
| FR-W9 | 主题切换 | 浅色 / 深色 / 跟随系统 |
| FR-W10 | 响应式 | 桌面、平板、手机三档断点 |
| FR-W11 | 国际化 | 至少中文优先；预留 i18n 框架 |

### 3.8 MCP 层（FR-M，可选 P2）

| 编号 | 需求 | 验收标准 |
|---|---|---|
| FR-M1 | 提供 MCP server 入口 | `python -m hotchain.mcp` 启动 stdio MCP server |
| FR-M2 | 暴露 3 个 MCP tool | 同 SKILL.md 的 3 个函数 |

---

## 4. 非功能需求（Non-Functional Requirements）

### 4.1 性能

| 编号 | 需求 |
|---|---|
| NFR-P1 | 单股完整分析（含 LLM）≤ 90 秒（P95）|
| NFR-P2 | 仅热点榜接口 ≤ 500ms（带缓存）/ ≤ 3s（无缓存）|
| NFR-P3 | 仅产业链接口 ≤ 1s（带缓存）/ ≤ 5s（无缓存）|
| NFR-P4 | SSE 首字节时间 ≤ 2s |

### 4.2 可靠性

| 编号 | 需求 |
|---|---|
| NFR-R1 | 单一数据源失败不应阻塞整体分析（多源降级） |
| NFR-R2 | LLM 调用失败有重试（最多 3 次）+ 兜底默认建议 |
| NFR-R3 | 工具调用次数有上限，防止死循环 |

### 4.3 安全

| 编号 | 需求 |
|---|---|
| NFR-S1 | API Key 仅从环境变量 / `.env` 读取，禁止硬编码 |
| NFR-S2 | 自定义 Skill YAML 不允许执行任意 Python 代码（仅作为 prompt 文本注入）|
| NFR-S3 | Web 端可选启用认证（复用现有 `app/middleware/`）|
| NFR-S4 | 分享链接需带签名 + 过期时间 |

### 4.4 兼容性

| 编号 | 需求 |
|---|---|
| NFR-C1 | Python ≥ 3.10 |
| NFR-C2 | 与现有 `TradingAgentsGraph` 完全兼容；新分析师可选启用，不破坏旧流程 |
| NFR-C3 | LLM 兼容：OpenAI / DeepSeek / 通义千问 / Zhipu / Gemini / Claude / Anspire |
| NFR-C4 | 浏览器：Chrome / Edge / Safari 最近 2 个大版本 |

### 4.5 可观测性

| 编号 | 需求 |
|---|---|
| NFR-O1 | 沿用现有 `tradingagents.utils.logging_init` 日志系统 |
| NFR-O2 | 工具调用、LLM 耗时、token 用量打日志 |
| NFR-O3 | 失败任务可在 `/hotchain/reports` 看到错误详情 |

### 4.6 可维护性

| 编号 | 需求 |
|---|---|
| NFR-M1 | 不破坏现有目录结构，新增代码集中在 `tradingagents/agents/analysts/`、`tradingagents/skills/`、`tradingagents/dataflows/providers/china/`、`app/routers/hotchain.py`、`frontend/src/pages/hotchain/` |
| NFR-M2 | 关键模块单测覆盖 ≥ 60% |
| NFR-M3 | 文档：本 spec + design + tasks + 用户手册（README 章节） |

---

## 5. 范围与边界

### 5.1 In Scope（当前迭代）

- 第一期：核心 Agent + Skill + CLI + API + 基础 Web 工作台
- 第二期：完整 Web 工作台（含 YAML 编辑器、产业链可视化、分享）
- 第三期：SKILL.md + MCP server + 桌面端打包

### 5.2 Out of Scope（不在本次范围）

- ❌ Bot（钉钉/飞书/Telegram）集成
- ❌ 定时任务 + 通知推送
- ❌ 完整回测系统
- ❌ 移动端原生 App
- ❌ 多用户/多租户管理（默认单租户）

---

## 6. 验收标准（Definition of Done）

完成本 spec 当且仅当：

1. ✅ 用户能在 Web 端输入 `600519` 并在 90 秒内看到完整的"热点 + 产业链 + 投资建议"报告（含流式过程）
2. ✅ 用户能在 Web 端 `/hotchain/hotspot` 看到当日热门行业/概念/人气榜
3. ✅ 用户能在 Web 端 `/hotchain/chain/600519` 看到产业链可视化图
4. ✅ 用户能用 CLI `python -m hotchain analyze 600519` 拿到同样结果
5. ✅ 用户能在 `/hotchain/skills` 创建一个自定义 Skill 并立即生效
6. ✅ 外部 AI Agent 能通过 `SKILL.md` 调用 `analyze_with_chain` 函数
7. ✅ 所有现有 TradingAgents-CN 功能（牛熊辩论、风险三辩、Trader）保持不变
8. ✅ 关键路径有单测；CI 通过；README 有使用说明
