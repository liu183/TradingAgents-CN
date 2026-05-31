# HotChain Agent — Spec 索引

本目录包含"热点 + 产业链 + 投资建议 AI Agent"完整规格。

| 文件 | 说明 |
|---|---|
| [`requirements.md`](./requirements.md) | 需求文档：背景、用户故事、功能需求 / 非功能需求、范围与边界、验收标准 |
| [`design.md`](./design.md) | 设计文档：架构、目录布局、数据结构、关键模块接口、SSE 协议、缓存、配置、演进路线 |
| [`tasks.md`](./tasks.md) | 任务拆分：10 阶段任务清单、估时、依赖图、风险 |

## 快速概览

**HotChain** 是基于 `TradingAgents-CN` 现有多 Agent 框架，并参考 `ZhuLinsen/daily_stock_analysis (DSA)` 的 Skill / 多形态架构，扩展出来的：

- ✅ 当日市场热点感知（行业榜 / 概念榜 / 人气榜 / 财经热搜）
- ✅ 公司上下游产业链分析（含同行业可比对照）
- ✅ 综合"热点 + 产业链 + 牛熊辩论 + 风险三辩"输出投资建议（买/持/卖 + 目标价）
- ✅ Skill 机制（自然语言 YAML 自定义策略）
- ✅ 5 种入口形态：CLI / Web / API / SKILL.md / MCP

## 与现有项目的关系

- **不破坏现有功能**：新分析师 `HotspotAnalyst` / `IndustryChainAnalyst` 通过 `selected_analysts` 列表可选启用，旧流程完全保留。
- **复用核心引擎**：基于 `TradingAgentsGraph`、`SignalProcessor`、`Toolkit`、`AgentState`。
- **扩展数据层**：在 `tradingagents/dataflows/providers/china/akshare.py` 新增两个方法。
- **新增 Skill 系统**：`tradingagents/skills/` 仿 DSA 设计。
- **复用前端工程**：基于 `frontend/`（React + Vite）扩展新页面。
- **复用后端工程**：基于 `app/`（FastAPI）扩展新路由。

## 推进建议

按 `tasks.md` 阶段顺序推进，每阶段独立成 PR。
v0.1 MVP 优先（约 1 周）：阶段 0~3 走通后即可在 CLI 上用，是最小可演示版本。
