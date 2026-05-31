"""
HotChain 产业链映射单元测试（无第三方重依赖，可在裸环境运行）。

仅依赖标准库 + 被测模块 tradingagents.industry_chain_map。
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tradingagents.industry_chain_map import (  # noqa: E402
    INDUSTRY_CHAIN_MAP,
    lookup_industry_chain,
)


def test_map_has_enough_industries():
    """字典应覆盖至少 30 个行业（spec 要求）。"""
    assert len(INDUSTRY_CHAIN_MAP) >= 30


def test_each_entry_has_upstream_and_downstream():
    """每个行业条目必须含 upstream / downstream 且非空。"""
    for name, entry in INDUSTRY_CHAIN_MAP.items():
        assert entry.get("upstream"), f"{name} 缺少 upstream"
        assert entry.get("downstream"), f"{name} 缺少 downstream"


def test_exact_match():
    result = lookup_industry_chain("半导体")
    assert result["matched"] == "半导体"
    assert "硅片" in result["upstream"]


def test_alias_match():
    """别名匹配：'白酒概念' -> 白酒。"""
    result = lookup_industry_chain("白酒概念")
    assert result["matched"] == "白酒"


def test_alias_match_baijiu_from_akshare_field():
    """AKShare 个股'所属行业'常返回'酿酒行业'，应匹配到白酒。"""
    result = lookup_industry_chain("酿酒行业")
    assert result["matched"] == "白酒"
    assert "包装材料" in result["upstream"]


def test_substring_match():
    """包含匹配：'锂电池行业' -> 电池。"""
    result = lookup_industry_chain("锂电池行业")
    assert result["matched"] == "电池"


def test_unknown_industry_returns_empty():
    result = lookup_industry_chain("某不存在的行业XYZ")
    assert result["matched"] == ""
    assert result["upstream"] == []
    assert result["downstream"] == []


def test_none_and_empty_input():
    for bad in (None, "", "   "):
        result = lookup_industry_chain(bad)
        assert result["matched"] == ""
        assert result["upstream"] == []


if __name__ == "__main__":
    # 允许直接 `python tests/test_hotchain_industry_chain_map.py` 运行
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        passed += 1
        print(f"✅ {fn.__name__}")
    print(f"\n{passed}/{len(fns)} 测试通过")
