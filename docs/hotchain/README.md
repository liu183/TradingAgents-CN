# HotChain Agent — 文档索引

> **HotChain** = Hot（热点）+ Industry Chain（产业链）+ 投资建议
>
> 基于 `TradingAgents-CN` 现有多 Agent 框架扩展的"热点 + 产业链 + 投资建议"AI Agent 系统，
> 支持 **CLI / Web / API / Skill (SKILL.md) / MCP** 五种形态。

## 文档结构

| 文档 | 说明 |
|---|---|
| [`analysis-report.md`](./analysis-report.md) | **参考项目对比分析报告** — 对 `daily_stock_analysis (DSA)` 的拆解、与 `TradingAgents-CN` 的差距对照 |
| [`mvp-implementation.md`](./mvp-implementation.md) | **v0.1 MVP 实现说明** — 本次落地的代码改动、使用方法、live 运行前置条件 |
| [`spec/requirements.md`](./spec/requirements.md) | **需求规格** — 用户故事、功能需求 / 非功能需求、范围与验收标准 |
| [`spec/design.md`](./spec/design.md) | **设计文档** — 架构、目录、数据结构、关键模块接口、SSE 协议、缓存、演进路线 |
| [`spec/tasks.md`](./spec/tasks.md) | **任务拆分** — 10 阶段任务清单、估时、依赖图、风险 |

> 同样的 spec 也镜像在 `.kiro/specs/hotchain_agent/`，供 Kiro 等 Spec-driven Agent 工具识别。

## 快速入门（计划落地形态）

```bash
# CLI
python -m hotchain analyze 600519 --skills hotspot_chase,industry_chain_value

# Web
python -m hotchain web --port 8000   # 浏览器打开 http://localhost:5173/hotchain

# REST API
curl -X POST http://localhost:8000/api/v1/hotchain/analyze \
  -H "Content-Type: application/json" \
  -d '{"stock_code":"600519","skills":["hotspot_chase"]}'

# 作为 Claude Skill
# 项目根 SKILL.md 自动被 Claude Code / Kiro 识别
```

## 与现有项目的关系

- ✅ **不破坏现有功能**：新分析师通过 `selected_analysts` 列表可选启用，旧流程完全保留
- ✅ **复用核心引擎**：基于 `TradingAgentsGraph`、`SignalProcessor`、`Toolkit`、`AgentState`
- ✅ **扩展数据层**：在 `tradingagents/dataflows/providers/china/akshare.py` 新增 2 个方法
- ✅ **新增 Skill 系统**：`tradingagents/skills/` 仿 DSA 设计
- ✅ **复用前后端工程**：基于 `app/` (FastAPI) + `frontend/` (React + Vite) 扩展

## 演进路线

| 版本 | 范围 | 估时 |
|---|---|---|
| **v0.1 (MVP)** | 数据层 + 2 个 Agent + 接入主图 + CLI 最小命令 | 1 周 |
| **v0.2** | Skill 机制 + 6 个内置 YAML + Web 工作台基础页 | 2 周 |
| **v0.3** | 完整 Web（热点中心 / 产业链可视化 / Skill 管理 / 历史报告 / 分享）+ SKILL.md | 3 周 |
| **v0.4** | MCP server + 桌面端打包 + 单测覆盖 + 文档完善 | 4 周 |

## 状态

📐 **Spec 已锁定**。**v0.1 MVP 已实现**（数据 Provider + 2 个 Agent + 接入主图 + CLI），详见 [`mvp-implementation.md`](./mvp-implementation.md)。后续阶段（Skill / API / Web / SKILL.md / MCP）见 [`spec/tasks.md`](./spec/tasks.md)。
