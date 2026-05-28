"""
intent_parser.py 单元测试

覆盖范围：
  - 域外问题检测
  - 城市槽位提取（覆盖区域 / 非覆盖区域 / 泛化表达）
  - 时间槽位提取
  - 指标槽位提取（含同义词归一化 / 隐式推断）
  - 品类槽位提取
  - 商品排名检测
  - 多城市对比检测
  - 聚合/维度/图表检测
  - 意图分类（SQL_QUERY / RAG_RETRIEVAL / CLARIFY / OUT_OF_DOMAIN）
  - 表路由策略
  - 缺失槽位检测
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(__file__))

from intent_parser import (
    parse_question,
    IntentType,
    QuestionParseResult,
    _normalize_synonyms,
    _check_domain,
    _extract_city,
    _extract_time,
    _extract_metric,
    _extract_category,
    _detect_product_rank,
    _infer_implicit_metric,
    _detect_multi_city,
    _detect_aggregate_and_dimension,
    _detect_chart_request,
    _classify_intent,
    _detect_missing_slots,
    METRIC_SYNONYMS,
    METRIC_KEYWORDS,
    CITY_KEYWORD_MAP,
    CATEGORY_KEYWORD_MAP,
)


# ============================================================
# _normalize_synonyms
# ============================================================

class TestNormalizeSynonyms:
    def test_gmv_to_sales(self):
        assert "销售额" in _normalize_synonyms("今年GMV是多少")

    def test_aov_to_unit_price(self):
        assert "客单价" in _normalize_synonyms("AOV是多少")

    def test_pv_to_views(self):
        assert "浏览量" in _normalize_synonyms("PV趋势")

    def test_no_change_for_standard(self):
        assert _normalize_synonyms("付费率") == "付费率"

    def test_multiple_synonyms(self):
        result = _normalize_synonyms("GMV和PV")
        assert "销售额" in result
        assert "浏览量" in result


# ============================================================
# _check_domain
# ============================================================

class TestCheckDomain:
    def test_domain_keyword_present(self):
        assert _check_domain("贵阳的销售额") is True

    def test_domain_keyword_guizhou(self):
        assert _check_domain("贵州电商发展") is True

    def test_out_of_domain(self):
        assert _check_domain("今天天气怎么样") is False

    def test_synonym_normalized_domain(self):
        assert _check_domain("UV数据") is True

    def test_non_covered_city_is_domain(self):
        assert _check_domain("北京的消费") is True


# ============================================================
# _extract_city
# ============================================================

class TestExtractCity:
    def test_covered_city_short(self):
        slots = {}
        _extract_city("贵阳的销售额", slots)
        assert slots["city"] == "贵阳市"

    def test_covered_city_full(self):
        slots = {}
        _extract_city("遵义市消费数据", slots)
        assert slots["city"] == "遵义市"

    def test_autonomous_prefecture(self):
        slots = {}
        _extract_city("黔东南的销量", slots)
        assert slots["city"] == "黔东南州"

    def test_autonomous_prefecture_full_name(self):
        slots = {}
        _extract_city("黔东南苗族侗族自治州消费", slots)
        assert slots["city"] == "黔东南州"

    def test_county_level_city(self):
        slots = {}
        _extract_city("仁怀的白酒销量", slots)
        assert slots["city"] == "仁怀市"

    def test_non_covered_region(self):
        slots = {}
        _extract_city("北京的销售额", slots)
        assert slots["city"] == "北京"
        assert slots["_non_covered_city"] is True

    def test_space_exemption_all_cities(self):
        slots = {}
        _extract_city("全省销售额", slots)
        assert slots["city"] == "ALL_CITIES"

    def test_longest_match_priority(self):
        slots = {}
        _extract_city("黔西南的消费", slots)
        assert slots["city"] == "黔西南州"


# ============================================================
# _extract_time
# ============================================================

class TestExtractTime:
    def test_year_month(self):
        slots = {}
        _extract_time("2025年3月销售额", slots)
        assert slots["time"] == "2025年3月"

    def test_year_only(self):
        slots = {}
        _extract_time("2025年销售额", slots)
        assert slots["time"] == "2025年"

    def test_month_only(self):
        slots = {}
        _extract_time("3月销售额", slots)
        assert slots["time"] == "3月"

    def test_recent_days(self):
        slots = {}
        _extract_time("最近7天销售额", slots)
        assert slots.get("_use_latest_time") is True
        assert "time" not in slots

    def test_no_time(self):
        slots = {}
        _extract_time("贵阳的销售额", slots)
        assert "time" not in slots
        assert "_use_latest_time" not in slots


# ============================================================
# _extract_metric
# ============================================================

class TestExtractMetric:
    def test_direct_metric(self):
        slots = {}
        _extract_metric("贵阳的销售额", slots)
        assert slots["metric"] == "销售额"

    def test_synonym_metric(self):
        slots = {}
        _extract_metric("贵阳的GMV", slots)
        assert slots["metric"] == "销售额"

    def test_multiple_metrics(self):
        result = parse_question("贵阳浏览量和加购量对比")
        assert result.slots.get("metric") is not None
        assert "extra_metrics" in result.slots

    def test_interaction_metric_field(self):
        slots = {}
        _extract_metric("浏览量趋势", slots)
        assert slots["metric"] == "浏览量"
        assert slots["metric_field"] == "pv_count"

    def test_fallback_synonym(self):
        slots = {}
        _extract_metric("成交额是多少", slots)
        assert slots["metric"] == "销售额"


# ============================================================
# _extract_category
# ============================================================

class TestExtractCategory:
    def test_direct_category(self):
        slots = {}
        _extract_category("电子数码的销量", slots)
        assert slots["category"] == "电子数码"

    def test_short_category(self):
        slots = {}
        _extract_category("家电销量", slots)
        assert slots["category"] == "家用电器"

    def test_deduplication(self):
        slots = {}
        _extract_category("运动户外销量", slots)
        assert slots["category"] == "运动户外"

    def test_no_category(self):
        slots = {}
        _extract_category("贵阳的销售额", slots)
        assert "category" not in slots


# ============================================================
# _detect_product_rank
# ============================================================

class TestDetectProductRank:
    def test_product_rank_query(self):
        slots = {}
        _detect_product_rank("什么手机卖得最好", slots)
        assert slots["_product_rank_query"] is True
        assert slots["table_hint"] == "ais_product_top_ranking"

    def test_product_rank_default_metric(self):
        slots = {}
        _detect_product_rank("什么手机卖得最好", slots)
        assert slots["metric"] == "销量"

    def test_product_rank_with_city(self):
        slots = {"city": "贵阳市"}
        _detect_product_rank("贵阳什么手机卖得最好", slots)
        assert slots["_city_product_query"] is True

    def test_not_product_rank(self):
        slots = {}
        _detect_product_rank("贵阳的销售额", slots)
        assert "_product_rank_query" not in slots


# ============================================================
# _infer_implicit_metric
# ============================================================

class TestInferImplicitMetric:
    def test_best_selling(self):
        slots = {}
        _infer_implicit_metric("卖得最好的商品", slots)
        assert slots["metric"] == "销量"

    def test_consumption_ability(self):
        slots = {}
        _infer_implicit_metric("消费能力怎么样", slots)
        assert slots["metric"] == "客单价"

    def test_trend_default(self):
        slots = {}
        _infer_implicit_metric("消费趋势", slots)
        assert slots["metric"] == "销售额"

    def test_skip_if_metric_exists(self):
        slots = {"metric": "销售额"}
        _infer_implicit_metric("卖得最好的商品", slots)
        assert slots["metric"] == "销售额"

    def test_hot_keyword(self):
        slots = {}
        _infer_implicit_metric("热门品类", slots)
        assert slots["metric"] == "浏览量"

    def test_best_selling_over_hot(self):
        slots = {}
        _infer_implicit_metric("最热门的品类", slots)
        assert slots["metric"] == "销量"


# ============================================================
# _detect_multi_city
# ============================================================

class TestDetectMultiCity:
    def test_multi_city(self):
        slots = {}
        result = _detect_multi_city("贵阳和遵义的销售额对比", slots)
        assert len(result) >= 2
        assert slots["city"] == "ALL_CITIES"
        assert slots["is_aggregate"] is True
        assert "filter_cities" in slots

    def test_single_city(self):
        slots = {"city": "贵阳市"}
        result = _detect_multi_city("贵阳的销售额", slots)
        assert len(result) == 1

    def test_no_city(self):
        slots = {}
        result = _detect_multi_city("全省销售额", slots)
        assert len(result) == 0


# ============================================================
# _detect_aggregate_and_dimension
# ============================================================

class TestDetectAggregateAndDimension:
    def test_ranking_keyword(self):
        slots = {}
        result = _detect_aggregate_and_dimension("各城市销售额排名", slots, False)
        assert result is True

    def test_dimension_hint(self):
        slots = {}
        result = _detect_aggregate_and_dimension("哪类商品卖得最好", slots, False)
        assert result is True
        assert slots["group_by_hint"] == "product_category"

    def test_multi_city_skip_category_dim(self):
        slots = {}
        result = _detect_aggregate_and_dimension("哪类商品卖得最好", slots, True)
        assert "group_by_hint" not in slots or slots.get("group_by_hint") != "product_category"

    def test_no_aggregate(self):
        slots = {}
        result = _detect_aggregate_and_dimension("贵阳的销售额", slots, False)
        assert result is False


# ============================================================
# _detect_chart_request
# ============================================================

class TestDetectChartRequest:
    def test_bar_chart(self):
        need_chart, chart_type = _detect_chart_request("各城市销售额柱状图")
        assert need_chart is True
        assert chart_type == "柱状图"

    def test_radar_chart(self):
        need_chart, chart_type = _detect_chart_request("品类雷达图")
        assert need_chart is True
        assert chart_type == "雷达图"

    def test_no_chart(self):
        need_chart, chart_type = _detect_chart_request("贵阳的销售额")
        assert need_chart is False
        assert chart_type is None


# ============================================================
# parse_question - 意图分类集成测试
# ============================================================

class TestParseQuestionIntent:
    def test_out_of_domain(self):
        result = parse_question("今天天气怎么样")
        assert result.intent == IntentType.OUT_OF_DOMAIN

    def test_sql_query_with_city_and_metric(self):
        result = parse_question("贵阳的销售额是多少")
        assert result.intent == IntentType.SQL_QUERY
        assert result.slots["city"] == "贵阳市"
        assert result.slots["metric"] == "销售额"

    def test_sql_query_with_time(self):
        result = parse_question("贵阳2025年3月的销售额")
        assert result.intent == IntentType.SQL_QUERY
        assert result.slots["time"] == "2025年3月"

    def test_rag_retrieval_policy(self):
        result = parse_question("贵州电商发展政策有哪些")
        assert result.intent == IntentType.RAG_RETRIEVAL

    def test_rag_retrieval_why(self):
        result = parse_question("为什么电商发展快")
        assert result.intent == IntentType.RAG_RETRIEVAL

    def test_clarify_missing_city(self):
        result = parse_question("销售额是多少")
        assert result.intent == IntentType.CLARIFY
        assert "城市/区域" in result.slots.get("missing", [])

    def test_clarify_missing_metric(self):
        result = parse_question("贵阳")
        assert result.intent == IntentType.CLARIFY
        assert "查询指标/意图" in result.slots.get("missing", [])

    def test_sql_aggregate(self):
        result = parse_question("各城市销售额排名")
        assert result.intent == IntentType.SQL_QUERY
        assert result.slots.get("is_aggregate") is True

    def test_sql_product_rank(self):
        result = parse_question("什么手机卖得最好")
        assert result.intent == IntentType.SQL_QUERY
        assert result.slots.get("_product_rank_query") is True

    def test_sql_multi_city(self):
        result = parse_question("贵阳和遵义的销售额对比")
        assert result.intent == IntentType.SQL_QUERY
        assert result.slots.get("is_aggregate") is True

    def test_non_covered_city_clarify(self):
        result = parse_question("北京")
        assert result.intent == IntentType.CLARIFY

    def test_trend_with_city_is_sql(self):
        result = parse_question("贵阳消费趋势")
        assert result.intent == IntentType.SQL_QUERY

    def test_trend_without_context_is_rag(self):
        result = parse_question("电商发展趋势")
        assert result.intent == IntentType.RAG_RETRIEVAL

    def test_analysis_is_rag(self):
        result = parse_question("贵州电商分析")
        assert result.intent == IntentType.RAG_RETRIEVAL

    def test_sql_with_category(self):
        result = parse_question("贵阳电子数码的销量")
        assert result.intent == IntentType.SQL_QUERY
        assert result.slots.get("category") == "电子数码"

    def test_category_without_city_is_clarify(self):
        result = parse_question("电子数码的销量")
        assert result.intent == IntentType.CLARIFY


# ============================================================
# parse_question - 表路由集成测试
# ============================================================

class TestParseQuestionTableRouting:
    def test_product_rank_table(self):
        result = parse_question("什么手机卖得最好")
        assert result.slots.get("table_hint") == "ais_product_top_ranking"

    def test_city_monthly_for_trend(self):
        result = parse_question("贵阳消费趋势折线图")
        assert result.slots.get("table_hint") in ("ais_city_monthly_summary", "ais_city_category_summary")

    def test_radar_chart_table(self):
        result = parse_question("各品类雷达图")
        assert result.slots.get("table_hint") == "ais_category_monthly_summary"

    def test_city_category_cross_table(self):
        result = parse_question("贵阳电子数码消费类型")
        assert result.slots.get("table_hint") in ("ais_city_category_summary", "ais_category_monthly_summary")


# ============================================================
# parse_question - 槽位完整性集成测试
# ============================================================

class TestParseQuestionSlots:
    def test_all_slots_populated(self):
        result = parse_question("贵阳2025年3月电子数码的销售额")
        assert result.slots.get("city") == "贵阳市"
        assert result.slots.get("time") == "2025年3月"
        assert result.slots.get("category") == "电子数码"
        assert result.slots.get("metric") == "销售额"

    def test_synonym_normalized_in_slots(self):
        result = parse_question("贵阳的GMV")
        assert result.slots.get("metric") == "销售额"

    def test_chart_type_hint(self):
        result = parse_question("各城市销售额柱状图")
        assert result.slots.get("chart_type_hint") == "柱状图"
        assert result.slots.get("need_chart") is True

    def test_implicit_metric_inferred(self):
        result = parse_question("贵阳卖得最好的商品")
        assert result.slots.get("metric") is not None

    def test_filter_cities_for_multi_city(self):
        result = parse_question("贵阳和遵义的销售额对比")
        filter_cities = result.slots.get("filter_cities", [])
        assert "贵阳市" in filter_cities
        assert "遵义市" in filter_cities


# ============================================================
# _detect_missing_slots
# ============================================================

class TestDetectMissingSlots:
    def test_missing_city(self):
        slots = {"metric": "销售额"}
        critical, suggested = _detect_missing_slots("销售额是多少", slots)
        assert "城市/区域" in critical

    def test_missing_time_suggested(self):
        slots = {"metric": "销售额", "city": "贵阳市"}
        critical, suggested = _detect_missing_slots("贵阳的销售额", slots)
        assert "时间范围" in suggested

    def test_no_missing_with_exemption(self):
        slots = {"metric": "销售额", "city": "贵阳市"}
        critical, suggested = _detect_missing_slots("贵阳今年的销售额", slots)
        assert len(critical) == 0

    def test_no_missing_for_product_rank(self):
        slots = {"_product_rank_query": True, "table_hint": "ais_product_top_ranking"}
        critical, suggested = _detect_missing_slots("什么手机卖得最好", slots)
        assert "城市/区域" not in critical


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
