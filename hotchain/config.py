"""
HotChain CLI 配置构建。

从环境变量 / CLI 选项构建传给 TradingAgentsGraph 的 config。
所有重依赖（tradingagents.default_config）均惰性导入，
使得无依赖环境下 `python -m hotchain --help` 仍可运行。
"""

import os
from typing import List, Optional


# HotChain 分析默认启用的分析师（含热点 + 产业链）
DEFAULT_ANALYSTS: List[str] = ["market", "news", "hotspot", "industry_chain", "fundamentals"]


def resolve_llm_settings(
    provider: Optional[str] = None,
    quick_model: Optional[str] = None,
    deep_model: Optional[str] = None,
    backend_url: Optional[str] = None,
):
    """解析 LLM 设置：CLI 选项 > 环境变量 > DEFAULT_CONFIG。"""
    from tradingagents.default_config import DEFAULT_CONFIG

    provider = (
        provider
        or os.getenv("HOTCHAIN_LLM_PROVIDER")
        or os.getenv("LLM_PROVIDER")
        or DEFAULT_CONFIG.get("llm_provider", "openai")
    )
    quick_model = (
        quick_model
        or os.getenv("HOTCHAIN_QUICK_MODEL")
        or os.getenv("QUICK_THINK_LLM")
        or DEFAULT_CONFIG.get("quick_think_llm")
    )
    deep_model = (
        deep_model
        or os.getenv("HOTCHAIN_DEEP_MODEL")
        or os.getenv("DEEP_THINK_LLM")
        or DEFAULT_CONFIG.get("deep_think_llm")
    )
    backend_url = (
        backend_url
        or os.getenv("HOTCHAIN_BACKEND_URL")
        or os.getenv("BACKEND_URL")
        or DEFAULT_CONFIG.get("backend_url")
    )
    return provider, quick_model, deep_model, backend_url


def build_config(
    provider: Optional[str] = None,
    quick_model: Optional[str] = None,
    deep_model: Optional[str] = None,
    backend_url: Optional[str] = None,
    research_depth: int = 1,
    online_tools: bool = True,
) -> dict:
    """构建 TradingAgentsGraph 的 config（基于 DEFAULT_CONFIG）。"""
    from tradingagents.default_config import DEFAULT_CONFIG

    provider, quick_model, deep_model, backend_url = resolve_llm_settings(
        provider, quick_model, deep_model, backend_url
    )

    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = provider
    if quick_model:
        config["quick_think_llm"] = quick_model
    if deep_model:
        config["deep_think_llm"] = deep_model
    if backend_url:
        config["backend_url"] = backend_url
    config["online_tools"] = online_tools
    # 快速分析配置：辩论轮次最小，加快 MVP 验证
    config["max_debate_rounds"] = 1 if research_depth <= 2 else 2
    config["max_risk_discuss_rounds"] = 1 if research_depth <= 2 else 2
    config["research_depth"] = research_depth
    return config
