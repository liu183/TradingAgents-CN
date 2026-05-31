"""
HotChain 命令行界面（基于 click）。

命令：
    analyze STOCK_CODE    完整分析（热点 + 产业链 + 投资建议）
    hotspot               仅获取当日市场热点
    chain   STOCK_CODE    仅获取公司产业链

重依赖（tradingagents.*）均在命令执行体内惰性导入，
保证无依赖环境下 `python -m hotchain --help` 也能正常显示帮助。
"""

import json
import sys
from datetime import datetime

import click

from hotchain.config import DEFAULT_ANALYSTS, build_config


@click.group(help="HotChain — 热点 + 产业链 + 投资建议 Agent CLI")
@click.version_option(package_name=None, version="0.1.0", prog_name="hotchain")
def cli():
    pass


@cli.command(help="完整分析：热点 + 产业链 + 投资建议")
@click.argument("stock_code")
@click.option("--date", "trade_date", default=None, help="分析日期 YYYY-MM-DD，默认今天")
@click.option("--provider", default=None, help="LLM 供应商（默认读环境变量/DEFAULT_CONFIG）")
@click.option("--quick-model", default=None, help="快速思考模型")
@click.option("--deep-model", default=None, help="深度思考模型")
@click.option("--depth", "research_depth", default=1, type=click.IntRange(1, 5), help="研究深度 1-5（默认 1 快速）")
@click.option("--output", "output_fmt", default="text", type=click.Choice(["text", "json", "md"]), help="输出格式")
@click.option("--debug", is_flag=True, default=False, help="调试模式")
def analyze(stock_code, trade_date, provider, quick_model, deep_model, research_depth, output_fmt, debug):
    """对单只股票运行 HotChain 分析。"""
    trade_date = trade_date or datetime.now().strftime("%Y-%m-%d")
    click.echo(f"🔥 HotChain 分析: {stock_code} @ {trade_date}", err=True)
    click.echo(f"   分析师: {', '.join(DEFAULT_ANALYSTS)}", err=True)

    try:
        from tradingagents.graph.trading_graph import TradingAgentsGraph
    except Exception as e:
        click.echo(
            "❌ 无法导入 TradingAgentsGraph，请先安装项目依赖：\n"
            "   pip install -r requirements.txt\n"
            f"   原始错误: {e}",
            err=True,
        )
        sys.exit(2)

    config = build_config(
        provider=provider,
        quick_model=quick_model,
        deep_model=deep_model,
        research_depth=research_depth,
    )
    click.echo(
        f"   LLM: provider={config['llm_provider']}, "
        f"quick={config.get('quick_think_llm')}, deep={config.get('deep_think_llm')}",
        err=True,
    )

    def _progress(msg, *args, **kwargs):
        click.echo(f"   … {msg}", err=True)

    try:
        graph = TradingAgentsGraph(
            selected_analysts=DEFAULT_ANALYSTS,
            debug=debug,
            config=config,
        )
        state, decision = graph.propagate(stock_code, trade_date, _progress)
    except Exception as e:
        click.echo(f"❌ 分析失败: {e}", err=True)
        if debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    _render_result(stock_code, trade_date, state, decision, output_fmt)


@cli.command(help="仅获取当日市场热点（行业/概念/人气/热搜）")
@click.option("--top-n", default=15, type=int, help="每类榜单 Top N")
@click.option("--output", "output_fmt", default="md", type=click.Choice(["md", "json"]), help="输出格式")
def hotspot(top_n, output_fmt):
    """获取当日市场热点（不调用 LLM，仅取数据）。"""
    try:
        from tradingagents.dataflows.providers.china.akshare import get_akshare_provider
        import asyncio
    except Exception as e:
        click.echo(f"❌ 无法导入数据 Provider，请先安装依赖: {e}", err=True)
        sys.exit(2)

    provider = get_akshare_provider()
    data = asyncio.run(provider.get_market_hotspot(top_n=top_n))

    if output_fmt == "json":
        click.echo(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    else:
        from tradingagents.agents.utils.agent_utils import _format_hotspot_markdown
        click.echo(_format_hotspot_markdown(data))


@cli.command(help="仅获取公司上下游产业链")
@click.argument("stock_code")
@click.option("--date", "curr_date", default=None, help="日期 YYYY-MM-DD，默认今天")
@click.option("--output", "output_fmt", default="md", type=click.Choice(["md", "json"]), help="输出格式")
def chain(stock_code, curr_date, output_fmt):
    """获取公司产业链结构（不调用 LLM，仅取数据）。"""
    curr_date = curr_date or datetime.now().strftime("%Y-%m-%d")
    try:
        from tradingagents.dataflows.providers.china.akshare import get_akshare_provider
        import asyncio
    except Exception as e:
        click.echo(f"❌ 无法导入数据 Provider，请先安装依赖: {e}", err=True)
        sys.exit(2)

    provider = get_akshare_provider()
    data = asyncio.run(provider.get_industry_chain(stock_code))

    if output_fmt == "json":
        click.echo(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    else:
        from tradingagents.agents.utils.agent_utils import _format_industry_chain_markdown
        click.echo(_format_industry_chain_markdown(data, curr_date))


def _render_result(stock_code, trade_date, state, decision, output_fmt):
    """渲染分析结果到 stdout。"""
    hotspot_report = (state or {}).get("hotspot_report", "") if isinstance(state, dict) else ""
    industry_chain_report = (state or {}).get("industry_chain_report", "") if isinstance(state, dict) else ""

    if output_fmt == "json":
        payload = {
            "stock_code": stock_code,
            "trade_date": trade_date,
            "decision": decision,
            "hotspot_report": hotspot_report,
            "industry_chain_report": industry_chain_report,
        }
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return

    if output_fmt == "md":
        parts = [f"# HotChain 分析报告：{stock_code}（{trade_date}）", ""]
        if hotspot_report:
            parts += ["## 市场热点", "", hotspot_report, ""]
        if industry_chain_report:
            parts += ["## 产业链分析", "", industry_chain_report, ""]
        parts += ["## 投资决策", "", _decision_to_md(decision)]
        click.echo("\n".join(parts))
        return

    # text
    click.echo("=" * 60)
    click.echo(f"HotChain 分析报告：{stock_code}（{trade_date}）")
    click.echo("=" * 60)
    if hotspot_report:
        click.echo("\n【市场热点】\n" + hotspot_report)
    if industry_chain_report:
        click.echo("\n【产业链分析】\n" + industry_chain_report)
    click.echo("\n【投资决策】\n" + _decision_to_md(decision))


def _decision_to_md(decision) -> str:
    """把 SignalProcessor 的决策 dict 渲染为可读文本。"""
    if isinstance(decision, dict):
        lines = []
        action = decision.get("action")
        if action is not None:
            lines.append(f"- 投资建议: **{action}**")
        if decision.get("target_price") is not None:
            lines.append(f"- 目标价: {decision.get('target_price')}")
        if decision.get("confidence") is not None:
            lines.append(f"- 置信度: {decision.get('confidence')}")
        if decision.get("risk_score") is not None:
            lines.append(f"- 风险评分: {decision.get('risk_score')}")
        if decision.get("reasoning"):
            lines.append(f"- 理由: {decision.get('reasoning')}")
        return "\n".join(lines) if lines else str(decision)
    return str(decision)


if __name__ == "__main__":
    cli()
