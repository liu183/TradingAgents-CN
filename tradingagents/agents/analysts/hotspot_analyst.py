"""
热点分析师（HotChain v0.1）

职责：获取当日市场热点（行业榜/概念榜/人气榜/财经热搜），
判断热点轮动阶段，并分析目标个股与当前热点的关联度。

输出写入 state["hotspot_report"]。
设计模板参考 social_media_analyst.py（含死循环防护 + Google 模型分支）。
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.agents.utils.google_tool_handler import GoogleToolCallHandler
from tradingagents.agents.utils.instrument_utils import build_instrument_context

logger = get_logger("analysts.hotspot")


def _get_company_name(ticker: str, market_info: dict) -> str:
    """获取公司名称（A股优先用统一接口，其余降级）。"""
    try:
        if market_info.get("is_china"):
            from tradingagents.dataflows.interface import get_china_stock_info_unified
            stock_info = get_china_stock_info_unified(ticker)
            if stock_info and "股票名称:" in stock_info:
                return stock_info.split("股票名称:")[1].split("\n")[0].strip()
            return f"股票代码{ticker}"
        elif market_info.get("is_hk"):
            clean = ticker.replace(".HK", "").replace(".hk", "")
            return f"港股{clean}"
        elif market_info.get("is_us"):
            return f"美股{ticker}"
        return f"股票{ticker}"
    except Exception as e:
        logger.error(f"❌ [热点分析师] 获取公司名称失败: {e}")
        return f"股票{ticker}"


def create_hotspot_analyst(llm, toolkit):
    @log_analyst_module("hotspot")
    def hotspot_analyst_node(state):
        # 🔧 死循环防护
        tool_call_count = state.get("hotspot_tool_call_count", 0)
        max_tool_calls = 2
        logger.info(f"🔧 [热点分析师] 当前工具调用次数: {tool_call_count}/{max_tool_calls}")

        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        from tradingagents.utils.stock_utils import StockUtils
        market_info = StockUtils.get_market_info(ticker)
        company_name = _get_company_name(ticker, market_info)
        instrument_context = build_instrument_context(ticker)
        logger.info(f"[热点分析师] 分析 {company_name}({ticker}) 的热点关联，日期: {current_date}")

        # 工具：市场热点 + 新闻（用于补充热点驱动事件）
        tools = [toolkit.get_market_hotspot_unified, toolkit.get_stock_news_unified]

        system_message = (
            """您是一位专业的市场热点分析师，负责捕捉当日 A 股市场资金涌入的方向，并判断目标个股与热点的关联度。

您的主要职责：
1. 调用 get_market_hotspot_unified 获取当日热门行业板块、概念板块、个股人气榜和财经热搜
2. 判断当前热点处于哪个阶段：启动 → 扩散 → 分化 → 退潮
3. 分析目标个股是否处于热点之中（所属行业/概念是否上榜、是否进入人气榜、是否为板块龙头）
4. 必要时调用 get_stock_news_unified 补充热点背后的驱动事件（政策、订单、事件催化）

分析要点：
- 热点的持续性与轮动节奏（是普涨还是分化？资金是流入还是退潮？）
- 目标个股与热点的关联强度（强相关 / 弱相关 / 无关）
- 个股在热点中的地位（龙头 / 跟风 / 补涨）
- 热点对该股短期（1-5 个交易日）股价的潜在影响

输出要求：
- 用中文撰写详细分析报告
- 明确给出"热点关联度评级"（强 / 中 / 弱 / 无）和"热点阶段判断"
- 给出基于热点视角的短期操作倾向（偏多 / 中性 / 偏空），并说明理由
- 不允许回复"无法判断"或"需要更多信息"
- 报告末尾附 Markdown 表格总结关键发现"""
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "您是一位专业的市场热点分析师，与其他分析师协作进行股票分析。"
                    " 请优先调用工具获取真实的当日热点数据，再基于数据进行分析，不要凭空臆测。"
                    " 您可以访问以下工具：{tool_names}。\n标的约束：{instrument_context}\n{system_message}"
                    "供您参考，当前日期是{current_date}。我们要分析的当前公司是{company_name}（{ticker}）。请用中文撰写所有分析内容。",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        tool_names = []
        for tool in tools:
            if hasattr(tool, "name"):
                tool_names.append(tool.name)
            elif hasattr(tool, "__name__"):
                tool_names.append(tool.__name__)
            else:
                tool_names.append(str(tool))
        prompt = prompt.partial(tool_names=", ".join(tool_names))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)
        prompt = prompt.partial(company_name=company_name)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke({"messages": state["messages"]})

        if GoogleToolCallHandler.is_google_model(llm):
            logger.info("📊 [热点分析师] 检测到Google模型，使用统一工具调用处理器")
            analysis_prompt_template = GoogleToolCallHandler.create_analysis_prompt(
                ticker=ticker,
                company_name=company_name,
                analyst_type="市场热点分析",
                specific_requirements="重点关注当日热门行业/概念、个股人气榜、热点轮动阶段及目标股的关联度。",
            )
            report, messages = GoogleToolCallHandler.handle_google_tool_calls(
                result=result,
                llm=llm,
                tools=tools,
                state=state,
                analysis_prompt_template=analysis_prompt_template,
                analyst_name="热点分析师",
            )
        else:
            logger.debug(f"📊 [热点分析师] 非Google模型 ({llm.__class__.__name__})，标准处理")
            report = ""
            if len(result.tool_calls) == 0:
                report = result.content

        return {
            "messages": [result],
            "hotspot_report": report,
            "hotspot_tool_call_count": tool_call_count + 1,
        }

    return hotspot_analyst_node
