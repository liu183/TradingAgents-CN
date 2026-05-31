"""
产业链上下游静态映射字典（HotChain v0.1 MVP）

第一期使用静态字典覆盖常见行业的上下游关键词，作为 IndustryChainAnalyst
的基础知识。后续迭代可用 LLM 推理扩展，或接入行业研报数据库。

数据结构：
    INDUSTRY_CHAIN_MAP[行业名] = {
        "upstream":   [上游环节/原材料/供应商行业关键词],
        "downstream": [下游环节/应用领域/客户行业关键词],
        "aliases":    [该行业的别名/近似行业名，用于模糊匹配],
    }

注意：
- AKShare 个股 "所属行业" 字段（stock_individual_info_em）返回的是
  东方财富行业分类，名称未必与申万一致，因此提供 aliases 做模糊匹配。
- 查询时请使用 lookup_industry_chain() 函数，它会做精确匹配 + 别名匹配 +
  关键词包含匹配三级降级。
"""

from typing import Dict, List, Optional

# 行业 -> 上下游映射
INDUSTRY_CHAIN_MAP: Dict[str, Dict[str, List[str]]] = {
    "半导体": {
        "upstream": ["硅片", "光刻胶", "电子特气", "半导体设备", "光掩模", "靶材"],
        "downstream": ["消费电子", "汽车电子", "通信设备", "数据中心", "工业控制"],
        "aliases": ["集成电路", "芯片", "IC设计", "半导体设备", "半导体材料"],
    },
    "光伏设备": {
        "upstream": ["多晶硅", "硅料", "硅片", "EVA树脂", "光伏玻璃"],
        "downstream": ["电力运营", "新能源汽车", "储能", "电网", "分布式光伏"],
        "aliases": ["光伏", "太阳能", "光伏概念", "光伏产业"],
    },
    "电池": {
        "upstream": ["锂矿", "正极材料", "负极材料", "隔膜", "电解液", "钴", "镍"],
        "downstream": ["新能源汽车", "储能", "消费电子", "电动两轮车"],
        "aliases": ["锂电池", "动力电池", "储能电池", "电池概念"],
    },
    "新能源汽车": {
        "upstream": ["动力电池", "电机电控", "汽车芯片", "车身材料", "汽车零部件"],
        "downstream": ["汽车销售", "充电桩", "汽车后市场", "出行服务"],
        "aliases": ["新能源车", "电动车", "整车", "汽车整车", "乘用车"],
    },
    "汽车零部件": {
        "upstream": ["钢铁", "铝合金", "塑料", "汽车芯片", "电子元件"],
        "downstream": ["汽车整车", "新能源汽车", "汽车后市场"],
        "aliases": ["汽车零件", "汽车配件", "零部件"],
    },
    "白酒": {
        "upstream": ["包装材料", "玻璃瓶", "高粱", "粮食", "纸箱"],
        "downstream": ["商超零售", "餐饮", "电商平台", "酒类流通"],
        "aliases": ["酿酒行业", "白酒概念", "食品饮料", "酒类"],
    },
    "饮料制造": {
        "upstream": ["包装材料", "糖", "农产品", "添加剂"],
        "downstream": ["商超零售", "便利店", "餐饮", "电商平台"],
        "aliases": ["饮料", "软饮料", "乳制品", "啤酒"],
    },
    "医药制造": {
        "upstream": ["原料药", "医药中间体", "化工原料", "生物制品"],
        "downstream": ["医院", "药店", "医药流通", "医保"],
        "aliases": ["医药", "制药", "生物医药", "化学制药", "中药"],
    },
    "医疗器械": {
        "upstream": ["精密制造", "电子元件", "高分子材料", "传感器"],
        "downstream": ["医院", "体检机构", "诊所", "家用医疗"],
        "aliases": ["医疗设备", "器械", "医疗器材"],
    },
    "银行": {
        "upstream": ["央行货币政策", "同业拆借", "存款"],
        "downstream": ["企业贷款", "个人信贷", "房地产", "基建", "制造业"],
        "aliases": ["银行业", "商业银行", "股份制银行", "城商行"],
    },
    "证券": {
        "upstream": ["交易所", "金融数据服务", "IT系统"],
        "downstream": ["机构投资者", "散户", "上市公司", "资管"],
        "aliases": ["券商", "证券业", "投资银行"],
    },
    "保险": {
        "upstream": ["再保险", "资产管理", "精算服务"],
        "downstream": ["个人客户", "企业客户", "健康医疗", "养老"],
        "aliases": ["保险业", "寿险", "财险"],
    },
    "房地产开发": {
        "upstream": ["建筑材料", "钢铁", "水泥", "工程机械", "土地"],
        "downstream": ["物业管理", "家居家电", "装修装饰", "购房者"],
        "aliases": ["房地产", "地产", "房企", "不动产"],
    },
    "建筑材料": {
        "upstream": ["矿石", "煤炭", "石灰石", "能源"],
        "downstream": ["房地产开发", "基建", "市政工程"],
        "aliases": ["建材", "水泥", "玻璃", "陶瓷"],
    },
    "钢铁": {
        "upstream": ["铁矿石", "焦炭", "煤炭", "废钢"],
        "downstream": ["房地产开发", "汽车", "机械制造", "造船", "基建"],
        "aliases": ["钢铁行业", "特钢", "普钢", "黑色金属"],
    },
    "有色金属": {
        "upstream": ["矿石", "采矿", "能源"],
        "downstream": ["电池", "电子", "建筑", "汽车", "光伏"],
        "aliases": ["铜", "铝", "锂", "稀土", "金属", "贵金属"],
    },
    "煤炭": {
        "upstream": ["采矿设备", "矿山服务"],
        "downstream": ["电力", "钢铁", "化工", "建材"],
        "aliases": ["煤炭开采", "焦煤", "动力煤", "煤炭行业"],
    },
    "石油石化": {
        "upstream": ["油气勘探", "原油", "天然气"],
        "downstream": ["化工", "塑料", "化纤", "成品油", "交通运输"],
        "aliases": ["石油", "石化", "炼化", "油气"],
    },
    "化工": {
        "upstream": ["原油", "煤炭", "天然气", "矿石"],
        "downstream": ["塑料制品", "纺织", "农业", "建材", "电子材料"],
        "aliases": ["基础化工", "化学制品", "精细化工", "化学原料"],
    },
    "电力": {
        "upstream": ["煤炭", "天然气", "光伏", "风电", "水电设备"],
        "downstream": ["工业用电", "居民用电", "数据中心", "充电桩"],
        "aliases": ["电力行业", "公用事业", "发电", "电力运营"],
    },
    "风电设备": {
        "upstream": ["钢材", "碳纤维", "齿轮箱", "轴承", "稀土永磁"],
        "downstream": ["电力运营", "电网", "储能"],
        "aliases": ["风电", "风能", "海上风电", "风力发电"],
    },
    "通信设备": {
        "upstream": ["半导体", "光模块", "PCB", "电子元件"],
        "downstream": ["电信运营商", "数据中心", "物联网", "智能终端"],
        "aliases": ["通信", "5G", "通讯设备", "通信工程"],
    },
    "计算机设备": {
        "upstream": ["半导体", "存储芯片", "显示面板", "电子元件"],
        "downstream": ["政企客户", "消费者", "数据中心", "云计算"],
        "aliases": ["计算机", "服务器", "PC", "硬件"],
    },
    "软件开发": {
        "upstream": ["云计算资源", "芯片算力", "开源框架"],
        "downstream": ["政府", "金融", "企业", "制造业", "消费者"],
        "aliases": ["软件", "SaaS", "信息技术", "IT服务", "云计算"],
    },
    "消费电子": {
        "upstream": ["半导体", "显示面板", "电池", "光学元件", "结构件"],
        "downstream": ["品牌厂商", "零售渠道", "电商平台", "消费者"],
        "aliases": ["消费电子产品", "电子制造", "手机产业链", "可穿戴"],
    },
    "面板": {
        "upstream": ["玻璃基板", "偏光片", "驱动IC", "液晶材料"],
        "downstream": ["电视", "手机", "笔记本", "车载显示"],
        "aliases": ["显示面板", "LCD", "OLED", "光电显示"],
    },
    "食品加工": {
        "upstream": ["农产品", "畜牧", "包装材料", "添加剂"],
        "downstream": ["商超零售", "餐饮", "电商平台", "便利店"],
        "aliases": ["食品", "食品制造", "休闲食品", "调味品"],
    },
    "农业": {
        "upstream": ["种子", "化肥", "农药", "农机"],
        "downstream": ["食品加工", "饲料", "养殖", "粮食流通"],
        "aliases": ["农林牧渔", "种植业", "养殖业", "农产品"],
    },
    "纺织服装": {
        "upstream": ["棉花", "化纤", "面料", "染料"],
        "downstream": ["品牌服装", "零售渠道", "电商平台", "出口贸易"],
        "aliases": ["纺织", "服装", "服饰", "纺织制造"],
    },
    "家电": {
        "upstream": ["钢材", "铜", "塑料", "压缩机", "芯片", "面板"],
        "downstream": ["商超零售", "电商平台", "房地产", "消费者"],
        "aliases": ["家用电器", "白色家电", "黑色家电", "小家电"],
    },
    "机械设备": {
        "upstream": ["钢铁", "有色金属", "液压件", "轴承", "电机"],
        "downstream": ["制造业", "基建", "矿山", "农业", "汽车"],
        "aliases": ["通用机械", "专用设备", "工程机械", "机械制造"],
    },
    "国防军工": {
        "upstream": ["特种材料", "电子元件", "高端制造", "钛合金"],
        "downstream": ["军队", "航天", "航空", "船舶"],
        "aliases": ["军工", "航空航天", "兵器", "国防"],
    },
    "传媒": {
        "upstream": ["内容创作", "版权", "算力", "通信带宽"],
        "downstream": ["广告主", "消费者", "平台分发"],
        "aliases": ["传媒娱乐", "影视", "游戏", "广告营销", "出版"],
    },
    "物流": {
        "upstream": ["运输设备", "燃油", "仓储设施", "信息系统"],
        "downstream": ["电商", "制造业", "零售", "消费者"],
        "aliases": ["物流运输", "快递", "供应链", "仓储"],
    },
}


def _normalize(text: str) -> str:
    """归一化行业名，去掉常见后缀和空白。"""
    if not text:
        return ""
    text = text.strip()
    for suffix in ("行业", "板块", "产业", "概念"):
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)]
    return text


def lookup_industry_chain(industry: Optional[str]) -> Dict[str, List[str]]:
    """
    根据行业名查询上下游映射，支持三级降级匹配：
    1. 精确匹配
    2. 别名匹配（aliases）
    3. 关键词包含匹配（双向子串）

    Args:
        industry: 行业名（可能来自 AKShare 个股信息，名称不规范）

    Returns:
        {"upstream": [...], "downstream": [...], "matched": "匹配到的行业名 或 ''"}
        未匹配时 upstream/downstream 为空列表。
    """
    empty = {"upstream": [], "downstream": [], "matched": ""}
    if not industry:
        return empty

    raw = industry.strip()
    norm = _normalize(raw)

    # 空白输入（strip 后为空）直接返回空，避免空串子串误匹配
    if not raw or not norm:
        return empty

    # 1. 精确匹配（原值 / 归一化值）
    for key in (raw, norm):
        if key in INDUSTRY_CHAIN_MAP:
            entry = INDUSTRY_CHAIN_MAP[key]
            return {
                "upstream": list(entry.get("upstream", [])),
                "downstream": list(entry.get("downstream", [])),
                "matched": key,
            }

    # 2. 别名匹配
    for key, entry in INDUSTRY_CHAIN_MAP.items():
        aliases = entry.get("aliases", [])
        for alias in aliases:
            if alias == raw or alias == norm or _normalize(alias) == norm:
                return {
                    "upstream": list(entry.get("upstream", [])),
                    "downstream": list(entry.get("downstream", [])),
                    "matched": key,
                }

    # 3. 关键词包含匹配（双向子串）
    for key, entry in INDUSTRY_CHAIN_MAP.items():
        candidates = [key] + entry.get("aliases", [])
        for cand in candidates:
            cand_norm = _normalize(cand)
            if not cand_norm:
                continue
            if cand_norm in norm or norm in cand_norm:
                return {
                    "upstream": list(entry.get("upstream", [])),
                    "downstream": list(entry.get("downstream", [])),
                    "matched": key,
                }

    return empty
