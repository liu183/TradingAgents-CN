# HotChain Agent — 任务拆分（Tasks）

> 与 `requirements.md` / `design.md` 一一对应。
> 每个 Task 一行，含验收标准与依赖。任务粒度按"半天 ~ 1 天"切分。

---

## 阶段 0：准备与基础设施

- [ ] **T0.1** 创建分支 `feature/hotchain` 并锁定 spec 三件套
  - 验收：`.kiro/specs/hotchain_agent/{requirements,design,tasks}.md` 已合入
- [ ] **T0.2** 在 `.env.example` 追加 HotChain 相关变量
  - `HOTCHAIN_ENABLED`、`HOTCHAIN_SKILL_DIR`、`HOTCHAIN_DEFAULT_SKILLS`、`HOTCHAIN_HOTSPOT_CACHE_TTL`、`HOTCHAIN_CHAIN_CACHE_TTL`
- [ ] **T0.3** 在 `pyproject.toml` / `requirements.txt` 检查依赖：`pyyaml`、`click`/`typer`（CLI 用）；前端 `package.json` 加 `echarts`、`@uiw/react-codemirror`、`react-markdown`、`remark-gfm`
- [ ] **T0.4** 写一份 `tradingagents/industry_chain_map.py`，覆盖至少 30 个常见申万一级行业的上下游关键词
  - 验收：`from tradingagents.industry_chain_map import INDUSTRY_CHAIN_MAP` 能拿到 ≥30 项

---

## 阶段 1：数据 Provider 扩展（FR-D）

- [ ] **T1.1** 在 `tradingagents/dataflows/providers/china/akshare.py` 新增 `get_market_hotspot(top_n=20)`
  - 调用 `ak.stock_board_industry_name_em`、`ak.stock_board_concept_name_em`、`ak.stock_hot_rank_em`、`ak.news_economic_baidu`
  - 单独的 try/except，单源失败不影响整体
  - 验收：单元测试 `tests/dataflows/test_market_hotspot.py` 跑通；缺网络时优雅降级
- [ ] **T1.2** 在同文件新增 `get_industry_chain(symbol)`
  - 内部调 `get_stock_basic_info` 拿 industry → 调 `ak.stock_board_industry_cons_em` 拿同行业成分股 → 查静态字典拿上下游关键词
  - 验收：单测 `tests/dataflows/test_industry_chain.py`
- [ ] **T1.3** 加 Redis 缓存装饰器（沿用现有 `app/core/redis_client.py`）
  - 热点榜 5 分钟、产业链 1 天

---

## 阶段 2：Toolkit 工具（FR-A 数据访问入口）

- [ ] **T2.1** 在 `tradingagents/agents/utils/agent_utils.py` Toolkit 类新增 `get_market_hotspot_unified` `@tool`
  - 内部调 Provider，把数据格式化为 LLM 友好的 Markdown
  - 验收：通过 `Toolkit().get_market_hotspot_unified.invoke({...})` 能拿到 Markdown 字符串
- [ ] **T2.2** 同上新增 `get_industry_chain_unified`
- [ ] **T2.3** （可选）抽出公共逻辑到 `tradingagents/tools/hotchain_tools.py`，参考 `unified_news_tool.py` 的实现风格
  - 验收：两个 tool 都通过 `Toolkit` 暴露，名称在 `_create_tool_nodes` 里能引用

---

## 阶段 3：Agent 实现（FR-A 核心）

- [ ] **T3.1** 在 `tradingagents/agents/utils/agent_states.py` 给 `AgentState` 添加 4 个字段
  - `hotspot_report`、`industry_chain_report`、`hotspot_tool_call_count`、`industry_chain_tool_call_count`、`selected_skills`
- [ ] **T3.2** 实现 `tradingagents/agents/analysts/hotspot_analyst.py`
  - 复用 `news_analyst.py` 模板（含死循环防护、Google 模型分支、DashScope/DeepSeek 预处理）
  - 验收：单独跑能输出 Markdown 报告
- [ ] **T3.3** 实现 `tradingagents/agents/analysts/industry_chain_analyst.py`
  - 同上，且 prompt 中接 `state["hotspot_report"]` 作为上下文
- [ ] **T3.4** 在 `tradingagents/agents/__init__.py` 注册两个 factory
  - 加到 `_EXPORTS` 字典
- [ ] **T3.5** 在 `tradingagents/graph/conditional_logic.py` 实现两个条件判断
  - `should_continue_hotspot` / `should_continue_industry_chain`
- [ ] **T3.6** 在 `tradingagents/graph/trading_graph.py: _create_tool_nodes` 加两个 ToolNode
- [ ] **T3.7** 修改 `tradingagents/graph/setup.py` 把两个 Agent 接入主图
  - 默认顺序：market → social → news → hotspot → industry_chain → fundamentals
  - 通过 `selected_analysts` 列表可选启用
- [ ] **T3.8** 修改下游 5 个 Agent 拼接 `curr_situation`
  - `bull_researcher.py` / `bear_researcher.py` / `research_manager.py` / `risk_manager.py` / `trader.py`
  - 在 prompt 适当处提一句 "请综合热点驱动与产业链景气度做判断"
- [ ] **T3.9** 端到端集成测试：手动 `python main.py` 跑一次 `600519`，确认两个新报告都生成且最终决策不变质量
  - 验收：`results/` 下有完整报告，最终 `final_decision.action` 不为空

---

## 阶段 4：Skill 机制（FR-S）

- [ ] **T4.1** 实现 `tradingagents/skills/base.py` 的 `Skill` 数据类与 `SkillManager`
  - 参考 DSA `src/agent/skills/base.py`，但不引入 SKILL.md frontmatter（第一期只支持 YAML）
- [ ] **T4.2** 实现 `tradingagents/skills/loader.py` 的 YAML 加载逻辑
  - 校验必填字段：`name`、`instructions`
- [ ] **T4.3** 编写 6 个内置 skill YAML（`tradingagents/skills/builtin/`）
  - hotspot_chase / industry_chain_value / upstream_costdrop / downstream_demand_boom / concept_speculation / policy_driven
  - 每个含完整 instructions（≥ 200 字）和评分调整规则
- [ ] **T4.4** 在 `HotspotAnalyst` / `IndustryChainAnalyst` 中接入 SkillManager
  - 根据 `state["selected_skills"]` 渲染 instructions 注入 prompt
- [ ] **T4.5** 自定义 skill 目录支持
  - 通过环境变量 `HOTCHAIN_SKILL_DIR` 加载

---

## 阶段 5：CLI 实现（FR-C）

- [ ] **T5.1** 创建 `cli/hotchain/__init__.py` + `__main__.py`，使用 `typer` 或 `click`
- [ ] **T5.2** 实现 `analyze` 子命令
  - 入参：stock_code、`--market`、`--skills`、`--output`、`--debug`、`--dry-run`
  - 输出：彩色终端 / Markdown 文件 / JSON
- [ ] **T5.3** 实现 `hotspot` 子命令（仅看热点）
- [ ] **T5.4** 实现 `chain` 子命令（仅看产业链）
- [ ] **T5.5** 实现 `web` 子命令（启动 FastAPI + 前端）
- [ ] **T5.6** 实现 `skill` 子命令组（list/create/edit/delete）
- [ ] **T5.7** 编写 CLI 自测脚本 `scripts/smoke_cli.sh`
  - 验收：每个子命令至少跑通一次

---

## 阶段 6：API 实现（FR-API）

- [ ] **T6.1** 实现 `app/models/hotchain.py`（Pydantic 模型）
- [ ] **T6.2** 实现 `app/services/hotchain_service.py`
  - `analyze` / `get_hotspot` / `get_industry_chain` / `list_skills` / `save_skill`
- [ ] **T6.3** 实现 `app/routers/hotchain.py`，注册到 `app/main.py`
- [ ] **T6.4** 实现 `/analyze/stream` SSE 端点
  - 事件类型：`thinking` / `tool_start` / `tool_done` / `report_chunk` / `done` / `error`
  - 复用现有 `RedisProgressTracker` 或新写 `HotChainProgressTracker`
- [ ] **T6.5** 实现 `/reports` 历史接口（落 MongoDB）
- [ ] **T6.6** 实现 `/reports/{id}/share` 签名分享链接
- [ ] **T6.7** API 集成测试：`tests/api/test_hotchain.py`
  - 验收：所有端点 200 响应；SSE 能收到 `done` 事件

---

## 阶段 7：Web 前端（FR-W）

- [ ] **T7.1** 在 `frontend/package.json` 加依赖：`echarts`、`@uiw/react-codemirror`、`react-markdown`、`remark-gfm`
- [ ] **T7.2** 实现 `frontend/src/api/hotchain.ts`（API client）
- [ ] **T7.3** 实现 `frontend/src/stores/hotchainStore.ts`（Zustand store，存当前任务、历史报告等）
- [ ] **T7.4** 实现 `frontend/src/components/hotchain/StockSearchBox.tsx`
  - 输入即搜索（防抖）；调 `/api/v1/stocks/search`
- [ ] **T7.5** 实现 `frontend/src/components/hotchain/SkillSelector.tsx`
  - 多选 + Tooltip 显示 skill 描述
- [ ] **T7.6** 实现 `frontend/src/components/hotchain/StreamingReport.tsx`
  - 用 `EventSource` 接 SSE；事件分流到不同 UI 区域
- [ ] **T7.7** 实现 `frontend/src/components/hotchain/HotspotPanel.tsx`
  - 三栏：行业榜 / 概念榜 / 人气榜；自动 60s 刷新
- [ ] **T7.8** 实现 `frontend/src/components/hotchain/IndustryChainGraph.tsx`
  - 用 ECharts `tree` 渲染上下游
- [ ] **T7.9** 实现 `frontend/src/components/hotchain/PeerComparisonTable.tsx`
  - 同行业对比表，按 PE / 涨跌幅排序
- [ ] **T7.10** 实现 `frontend/src/components/hotchain/YamlEditor.tsx`
  - CodeMirror + YAML 模式 + 语法校验
- [ ] **T7.11** 实现 `frontend/src/pages/hotchain/WorkbenchPage.tsx`
- [ ] **T7.12** 实现 `frontend/src/pages/hotchain/HotspotCenterPage.tsx`
- [ ] **T7.13** 实现 `frontend/src/pages/hotchain/IndustryChainPage.tsx`
- [ ] **T7.14** 实现 `frontend/src/pages/hotchain/SkillsPage.tsx`
- [ ] **T7.15** 实现 `frontend/src/pages/hotchain/ReportsPage.tsx` + `ReportDetailPage.tsx`
- [ ] **T7.16** 在 `frontend/src/App.tsx` 注册新路由 + 在主菜单加导航入口
- [ ] **T7.17** 主题切换 + 响应式 CSS 验收
- [ ] **T7.18** 端到端 Playwright 测试 `frontend/tests/e2e/hotchain.spec.ts`
  - 验收：用户能完成"输入 600519 → 选 hotspot_chase → 点开始 → 看到报告"完整流程

---

## 阶段 8：SKILL.md 与对外暴露（FR-K）

- [ ] **T8.1** 在项目根创建 `SKILL.md`
  - frontmatter（name + description）+ Body 列出 3 个核心函数 + 调用示例
- [ ] **T8.2** 在 `app/services/hotchain_service.py` 暴露公开函数
  - `analyze_with_chain` / `get_today_hotspot` / `analyze_industry_chain` 作为顶层模块函数
- [ ] **T8.3** 用 Claude Code 验证 SKILL.md 可被识别
  - 验收：`claude --skill hotchain_analyzer` 能调通

---

## 阶段 9：MCP Server（FR-M，P2 可选）

- [ ] **T9.1** 实现 `tradingagents/mcp/hotchain_server.py`（基于 `mcp` Python SDK）
- [ ] **T9.2** 暴露 3 个 MCP tool（与 SKILL.md 对应）
- [ ] **T9.3** 编写 `python -m hotchain.mcp` 入口

---

## 阶段 10：测试 / 文档 / 发布

- [ ] **T10.1** 单元测试：覆盖 Provider、Toolkit、SkillManager、SignalProcessor 集成
  - 目标 ≥ 60% 覆盖
- [ ] **T10.2** 集成测试：完整 `analyze` 端到端，含 SSE
- [ ] **T10.3** 在 `README.md` 增加 "🔥 HotChain：热点+产业链+投资建议" 章节
  - 含 Web 演示 GIF + CLI 截图
- [ ] **T10.4** 在 `docs/` 下新增 `docs/hotchain.md` 详细使用手册
- [ ] **T10.5** 写 `docs/hotchain_skills.md` 介绍如何写自定义 Skill
- [ ] **T10.6** CHANGELOG 记录
- [ ] **T10.7** 跑全套 CI；性能压测：`/hotspot` QPS ≥ 50（带缓存）
- [ ] **T10.8** PR 与 review，合并到 main

---

## 任务依赖图

```
T0.* ── T1.* ── T2.* ── T3.* ──┬── T4.* ──┐
                                │          ├── T6.* ── T7.* ── T10.*
                                └── T5.*  ─┘            └── T8.*
                                                         T9.*（可选）
```

---

## 估时（按 1 人全职）

| 阶段 | 估时 |
|---|---|
| T0 准备 | 0.5 天 |
| T1 Provider | 1 天 |
| T2 Toolkit | 0.5 天 |
| T3 Agent + 接入图 | 2 天 |
| T4 Skill 机制 + 6 个内置 | 1.5 天 |
| T5 CLI | 1 天 |
| T6 API | 1.5 天 |
| T7 Web 前端 | 4 天 |
| T8 SKILL.md | 0.5 天 |
| T9 MCP（可选） | 1 天 |
| T10 测试与文档 | 1.5 天 |
| **合计** | **~14 天**（约 3 周） |

---

## 风险点与缓解

| 风险 | 缓解策略 |
|---|---|
| AKShare 接口变更或限流 | 多源降级 + 缓存兜底 |
| 静态产业链字典精度低 | 第二迭代用 LLM 辅助生成；第三迭代接研报数据库 |
| LangGraph 图改动影响现有功能 | 新分析师可选启用，不破坏旧流程；保留单元测试快照 |
| 国产 LLM tool calling 不稳定 | 沿用现有 DashScope/DeepSeek 预处理逻辑 |
| 前端 SSE 浏览器兼容 | 使用标准 EventSource；关键路径有 polling 兜底 |
| 工时偏差 | 按阶段分批 PR；每阶段独立可发布 |
