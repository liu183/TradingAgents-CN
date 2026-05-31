"""
产业链分析师（HotChain v0.1）

职责：分析目标公司所属行业的上下游产业链定位、同行业可比公司、
产业链景气度，并结合热点上下文给出产业链视角的投资倾向。

输出写入 state["industry_chain_report"]。
设计模板参考 social_media_analyst.py（含死循环防护 + Google 模型分支）。
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.agents.utils.google_tool_handler import GoogleToolCallHandler
from tradingagents.agents.utils.instrument_utils import build_instrument_context

logger = get_logger("analysts.industry_chain")


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
        logger.error(f"❌ [产业链分析师] 获取公司名称失败: {e}")
        return f"股票{ticker}"


def create_industry_chain_analyst(llm, toolkit):
    @log_analyst_module("industry_chain")
    def industry_chain_analyst_node(state):
        # 🔧 死循环防护
        tool_call_count = state.get("industry_chain_tool_call_count", 0)
        max_tool_calls = 2
        logger.info(f"🔧 [产业链分析师] 当前工具调用次数: {tool_call_count}/{max_tool_calls}")

        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        from tradingagents.utils.stock_utils import StockUtils
        market_info = StockUtils.get_market_info(ticker)
        company_name = _get_company_name(ticker, market_info)
        instrument_context = build_instrument_context(ticker)

        # 热点上下文（来自 HotspotAnalyst，可能为空）
        hotspot_report = state.get("hotspot_report", "") or ""
        hotspot_context = hotspot_report[:2000] if hotspot_report else "（暂无热点分析上下文）"

        logger.info(f"[产业链分析师] 分析 {company_name}({ticker}) 的产业链，日期: {current_date}")

        # 工具：产业链 + 新闻（用于补充上下游景气度新闻）
        tools = [toolkit.get_industry_chain_unified, toolkit.get_stock_news_unified]

        system_message = (
            """您是一位专业的产业链分析师，负责分析目标公司在产业链中的定位与景气度。

您的主要职责：
1. 调用 get_industry_chain_unified 获取公司所属行业、上下游产业链关键词、同行业可比公司
2. 必要时调用 get_stock_news_unified 补充上下游景气度相关的新闻（原材料涨跌、下游需求、订单）
3. 输出结构化的产业链分析报告

报告必须包含以下结构：
## 一、行业定位
- 公司所属行业及在产业链中的位置

## 二、上游分析
- 主要原材料/供应商环节
- 上游成本压力（原材料涨跌对毛利的影响）、供应商议价能力

## 三、下游分析
- 主要客户/应用领域
- 下游需求景气度（终端市场扩张还是萎缩）、客户集中度风险

## 四、同行业横向对比
- 结合同行业可比公司的涨跌幅、估值（PE），判断公司在板块中的相对强弱

## 五、产业链景气度判断
- 综合上中下游，给出产业链景气度评级（高景气 / 中性 / 低景气）
- 公司在产业链中的议价能力与护城河

## 六、产业链视角的投资建议
- 明确给出：买入 / 持有 / 卖出
- 给出基于产业链景气度的目标价区间（使用对应货币单位）
- 说明主要的产业链催化剂与风险点

要求：
- 全部使用中文
- 投资建议必须使用中文：买入 / 持有 / 卖出（禁止 buy/hold/sell）
- 不允许回复"无法判断"或"需要更多信息"
- 优先基于工具返回的真实数据进行分析
- 报告末尾附 Markdown 表格总结关键发现"""
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "您是一位专业的产业链分析师，与其他分析师协作进行股票分析。"
                    " 请优先调用工具获取真实的产业链数据，再结合提供的热点上下文进行分析。"
                    " 您可以访问以下工具：{tool_names}。\n标的约束：{instrument_context}\n{system_message}"
                    "\n\n【热点分析上下文（供参考）】\n{hotspot_context}"
                    "\n\n供您参考，当前日期是{current_date}。我们要分析的当前公司是{company_name}（{ticker}）。请用中文撰写所有分析内容。",
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
        prompt = prompt.partial(hotspot_context=hotspot_context)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke({"messages": state["messages"]})

        if GoogleToolCallHandler.is_google_model(llm):
            logger.info("📊 [产业链分析师] 检测到Google模型，使用统一工具调用处理器")
            analysis_prompt_template = GoogleToolCallHandler.create_analysis_prompt(
                ticker=ticker,
                company_name=company_name,
                analyst_type="产业链分析",
                specific_requirements="重点关注上下游产业链定位、同行业对比、产业链景气度及产业链视角的投资建议。",
            )
            report, messages = GoogleToolCallHandler.handle_google_tool_calls(
                result=result,
                llm=llm,
                tools=tools,
                state=state,
                analysis_prompt_template=analysis_prompt_template,
                analyst_name="产业链分析师",
            )
        else:
            logger.debug(f"📊 [产业链分析师] 非Google模型 ({llm.__class__.__name__})，标准处理")
            report = ""
            if len(result.tool_calls) == 0:
                report = result.content

        return {
            "messages": [result],
            "industry_chain_report": report,
            "industry_chain_tool_call_count": tool_call_count + 1,
        }

    return industry_chain_analyst_node
