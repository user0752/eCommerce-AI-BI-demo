import re
import pymysql
import pandas as pd

from config import MYSQL_CONFIG


# ============================================================
# 动态表结构注册表 —— 替代硬编码，新增表只需在此注册即可
# ============================================================
TABLE_SCHEMA = {
    "ads_region_consume_analysis": {
        "description": "贵州区域消费分析表",
        "metrics": [
            "total_active_user", "total_pay_user", "total_pay_rate",
            "total_order_count", "total_sale_amount", "city_avg_order_value",
            "main_category_avg_price",
        ],
        "dims": ["city_name", "province_name", "main_consume_category", "main_consume_brand", "stat_month"],
        "max_rows": 500,
        "default_order": "total_sale_amount DESC",
        "group_by_dim": "city_name",
        # 指标在该表中对应的字段映射（覆盖全局 METRIC_TO_COLUMN）
        "metric_map": {
            "客单价": "city_avg_order_value",  # region表的客单价字段名不同
            "订单数": "total_order_count",
            "订单量": "total_order_count",
            "用户数": "total_active_user",
            "付费率": "total_pay_rate",
            "销售额": "total_sale_amount",
            "主品类均价": "main_category_avg_price",
            "品类均价": "main_category_avg_price",
            "主力品类均价": "main_category_avg_price",
        },
        # 维度字段映射（当用户问的"指标"实际是维度时，如"消费类别"→main_consume_category）
        "dim_map": {
            "消费类别": "main_consume_category",
            "消费品牌": "main_consume_brand",
        },
    },
    "ads_product_feature_full": {
        "description": "商品特征宽表",
        "metrics": [
            "total_sale_quantity", "total_sale_amount",
            "buy_conversion_rate", "product_rating",
        ],
        "dims": ["product_name", "product_category", "product_brand", "price_level", "hot_level", "stat_month"],
        "max_rows": 200,
        "default_order": "total_sale_amount DESC",
        "group_by_dim": "product_category",
        "metric_map": {
            "销量": "total_sale_quantity",
            "销售额": "total_sale_amount",
            "转化率": "buy_conversion_rate",
        },
        "dim_map": {
            "消费类别": "product_category",
            "消费类型": "product_category",
            "商品类型": "product_category",
            "消费商品类型": "product_category",
            "品类": "product_category",
        },
        "unsupported_metrics": {"客单价"},
    },
    "ads_user_profile_full": {
        "description": "用户画像标签表",
        "metrics": [
            "total_consumption", "avg_order_value", "repurchase_count",
        ],
        "dims": [
            "user_id", "user_gender", "age_group", "user_city",
            "user_occupation", "user_income_level", "membership_level",
            "rfm_segment", "consumption_preference", "user_value_level",
        ],
        "max_rows": 200,
        "default_order": "total_consumption DESC",
        "group_by_dim": "age_group",
    },
    "ads_user_item_interaction_matrix": {
        "description": "用户-商品交互矩阵表",
        "metrics": [
            "interaction_score", "pv_count", "fav_count", "cart_count", "buy_count",
        ],
        "dims": ["user_id", "product_id", "stat_month"],
        "max_rows": 100,
        "default_order": "interaction_score DESC",
        "group_by_dim": None,
        "metric_map": {
            "点击量": "pv_count",
            "浏览量": "pv_count",
            "收藏量": "fav_count",
            "加购量": "cart_count",
            "购买量": "buy_count",
        },
    },
    # ============================================================
    # AIS层预聚合表（新增）
    # ============================================================
    "ais_city_monthly_summary": {
        "description": "城市月度汇总宽表（含交互指标，替代交互表JOIN）",
        "metrics": [
            "total_active_user", "total_pay_user", "total_pay_rate",
            "total_order_count", "total_sale_amount", "city_avg_order_value",
            "main_category_avg_price",
            "total_pv_count", "total_fav_count", "total_cart_count", "total_buy_count",
        ],
        "dims": ["city_name", "province_name", "main_consume_category",
                 "main_consume_brand", "stat_month"],
        "max_rows": 500,
        "default_order": "total_sale_amount DESC",
        "group_by_dim": "city_name",
        "metric_map": {
            "客单价": "city_avg_order_value",
            "订单数": "total_order_count",
            "订单量": "total_order_count",
            "用户数": "total_active_user",
            "付费率": "total_pay_rate",
            "销售额": "total_sale_amount",
            "主品类均价": "main_category_avg_price",
            "品类均价": "main_category_avg_price",
            "主力品类均价": "main_category_avg_price",
            "浏览量": "total_pv_count",
            "点击量": "total_pv_count",
            "收藏量": "total_fav_count",
            "加购量": "total_cart_count",
            "购买量": "total_buy_count",
        },
        "dim_map": {
            "消费类别": "main_consume_category",
            "消费品牌": "main_consume_brand",
        },
    },
    "ais_category_monthly_summary": {
        "description": "品类月度汇总宽表（多指标，支持雷达图/折线图）",
        "metrics": [
            "product_count", "total_sale_quantity", "total_sale_amount",
            "avg_product_rating", "avg_buy_conversion_rate",
            "total_pv_count", "total_fav_count", "total_cart_count", "total_buy_count",
            "hot_product_count", "avg_unit_price",
        ],
        "dims": ["product_category", "stat_month"],
        "max_rows": 200,
        "default_order": "total_sale_amount DESC",
        "group_by_dim": "product_category",
        "metric_map": {
            "销量": "total_sale_quantity",
            "销售额": "total_sale_amount",
            "转化率": "avg_buy_conversion_rate",
            "评分": "avg_product_rating",
            "浏览量": "total_pv_count",
            "点击量": "total_pv_count",
            "收藏量": "total_fav_count",
            "加购量": "total_cart_count",
            "购买量": "total_buy_count",
            "均价": "avg_unit_price",
            "商品数": "product_count",
            "热销商品数": "hot_product_count",
        },
        "dim_map": {
            "品类": "product_category",
            "消费类别": "product_category",
            "消费类型": "product_category",
            "商品类型": "product_category",
        },
    },
    "ais_city_category_summary": {
        "description": "城市×品类交叉汇总表（支持城市级品类分析/饼图）",
        "metrics": [
            "total_sale_quantity", "total_sale_amount",
            "total_pv_count", "total_fav_count", "total_cart_count", "total_buy_count",
            "buy_conversion_rate", "avg_unit_price",
        ],
        "dims": ["city_name", "product_category"],
        "max_rows": 200,
        "default_order": "total_sale_amount DESC",
        "group_by_dim": "product_category",
        "metric_map": {
            "销量": "total_sale_quantity",
            "销售额": "total_sale_amount",
            "转化率": "buy_conversion_rate",
            "浏览量": "total_pv_count",
            "点击量": "total_pv_count",
            "收藏量": "total_fav_count",
            "加购量": "total_cart_count",
            "购买量": "total_buy_count",
            "均价": "avg_unit_price",
        },
        "dim_map": {
            "品类": "product_category",
            "消费类别": "product_category",
            "城市": "city_name",
        },
    },
    "ais_product_top_ranking": {
        "description": "商品品类TOP5排名表（省级，无城市维度，支持具体商品排名查询）",
        "metrics": [
            "total_sale_quantity", "total_sale_amount",
        ],
        "dims": ["product_category", "product_name", "product_brand", "hot_level", "rank_in_category"],
        "max_rows": 60,
        "default_order": "rank_in_category ASC",
        "group_by_dim": "product_category",
        "metric_map": {
            "销量": "total_sale_quantity",
            "销售额": "total_sale_amount",
        },
        "dim_map": {
            "品类": "product_category",
            "商品名": "product_name",
            "品牌": "product_brand",
            "热度": "hot_level",
            "排名": "rank_in_category",
        },
        "unsupported_metrics": {
            "浏览量", "点击量", "收藏量", "加购量", "购买量",
            "客单价", "付费率", "转化率", "用户数", "订单数", "订单量",
        },
    },
}

# 指标关键词到 SQL 字段的全局映射（兜底，优先使用表级 metric_map）
METRIC_TO_COLUMN = {
    "销量": "total_sale_quantity",
    "销售额": "total_sale_amount",
    "用户数": "total_active_user",
    "付费率": "total_pay_rate",
    "订单数": "total_order_count",
    "订单量": "total_order_count",
    "转化率": "buy_conversion_rate",
    "客单价": "avg_order_value",
    "消费金额": "total_consumption",
    # 交互行为指标
    "点击量": "pv_count",
    "浏览量": "pv_count",
    "收藏量": "fav_count",
    "加购量": "cart_count",
    "购买量": "buy_count",
}

# ============================================================
# 指标同义词归一化映射 —— 扩展用户表达覆盖面
# ============================================================
# 归一化策略：
#   用户输入的指标关键词先通过此字典归一化为标准指标名，
#   再通过 _resolve_metric_col() 查找对应的SQL字段。
#   例如：用户说"GMV" → 归一化为"销售额" → 查找 total_sale_amount 字段。
METRIC_SYNONYMS = {
    # ── 销售额类 → "销售额" ──
    "GMV": "销售额", "gmv": "销售额", "成交额": "销售额",
    "营收": "销售额", "消费金额": "销售额", "交易额": "销售额",
    "销售总额": "销售额", "卖了多少钱": "销售额",
    "销售金额": "销售额", "总额": "销售额", "销售": "销售额",
    "营业额": "销售额", "收入": "销售额", "流水": "销售额",
    "卖了": "销售额", "卖了多少": "销售额",
    # ── 销量类 → "销量" ──
    "销售量": "销量", "出货量": "销量", "成交件数": "销量",
    "售出数量": "销量", "卖了多少件": "销量",
    "卖出数量": "销量", "卖出的": "销量", "出货": "销量",
    "件数": "销量",
    # ── 用户数类 → "用户数" ──
    "活跃用户": "用户数", "用户量": "用户数", "客户数": "用户数",
    "消费者数量": "用户数", "有多少用户": "用户数",
    "用户规模": "用户数", "活跃人数": "用户数", "人数": "用户数",
    "付费用户": "用户数",
    # ── 付费率类 → "付费率" ──
    "支付率": "付费率", "转化付费率": "付费率", "购买率": "付费率",
    "付款率": "付费率", "下单转化率": "付费率",
    "付费比例": "付费率", "付费占比": "付费率",
    # ── 订单数类 → "订单数" ──
    "订单量": "订单数", "成交单数": "订单数", "下单量": "订单数",
    "交易笔数": "订单数",
    "订单总数": "订单数", "下单数": "订单数",
    # ── 客单价类 → "客单价" ──
    "平均客单价": "客单价", "每单均价": "客单价", "人均消费": "客单价",
    "单笔均价": "客单价", "AOV": "客单价", "aov": "客单价",
    "平均消费": "客单价", "每单消费": "客单价",
    "平均单价": "客单价", "均单价": "客单价", "均价": "客单价",
    # ── 转化率类 → "转化率" ──
    "购买转化率": "转化率", "下单转化率": "转化率", "成交转化率": "转化率",
    "buy转化": "转化率",
    "转化": "转化率", "转化占比": "转化率",
    # ── 点击量/浏览量类 → "浏览量" ──
    "PV": "浏览量", "pv": "浏览量", "页面浏览": "浏览量",
    "访问量": "浏览量", "浏览次数": "浏览量", "浏览数": "浏览量",
    "浏览": "浏览量", "uv": "浏览量", "UV": "浏览量",
    "点击": "点击量", "点击数": "点击量", "点击次数": "点击量",
    "点击热度": "点击量", "点击量": "点击量",
    # ── 收藏量类 → "收藏量" ──
    "收藏": "收藏量", "收藏数": "收藏量", "加收藏": "收藏量",
    "收藏次数": "收藏量", "收藏量": "收藏量",
    # ── 加购量类 → "加购量" ──
    "加购": "加购量", "加入购物车": "加购量", "加购数": "加购量",
    "购物车添加": "加购量", "加购量": "加购量",
    "加入购物车次数": "加购量",
    # ── 购买量类 → "购买量" ──
    "购买": "购买量", "购买次数": "购买量", "成交笔数": "购买量",
    "实际购买": "购买量", "购买量": "购买量",
    "购买数": "购买量", "买了多少": "购买量",
}

# ============================================================
# 预聚合表路由映射 —— 关键词命中直接锁定表，绕过加权评分
# ============================================================
PREAGG_TABLE_ROUTE = {
    # ── 城市+月度维度 → ais_city_monthly_summary ──
    "月度趋势": "ais_city_monthly_summary",
    "月度变化": "ais_city_monthly_summary",
    "月度走势": "ais_city_monthly_summary",
    "按月": "ais_city_monthly_summary",
    "逐月": "ais_city_monthly_summary",
    "城市对比": "ais_city_monthly_summary",
    "城市排名": "ais_city_monthly_summary",
    "城市排行": "ais_city_monthly_summary",
    "付费率对比": "ais_city_monthly_summary",
    "客单价排行": "ais_city_monthly_summary",
    "消费趋势": "ais_city_monthly_summary",
    "交互行为月度": "ais_city_monthly_summary",
    "浏览趋势": "ais_city_monthly_summary",
    "购买趋势": "ais_city_monthly_summary",
    "销售额趋势": "ais_city_monthly_summary",
    "销量趋势": "ais_city_monthly_summary",
    "用户数趋势": "ais_city_monthly_summary",

    # ── 品类维度 → ais_category_monthly_summary ──
    "品类排名": "ais_category_monthly_summary",
    "品类排行": "ais_category_monthly_summary",
    "品类对比": "ais_category_monthly_summary",
    "品类趋势": "ais_category_monthly_summary",
    "哪类商品": "ais_category_monthly_summary",
    "哪个品类": "ais_category_monthly_summary",
    "品类占比": "ais_category_monthly_summary",
    "品类结构": "ais_category_monthly_summary",
    "各品类": "ais_category_monthly_summary",
    "雷达图": "ais_category_monthly_summary",
    # 注意："品类分布"和"消费类型"等词在有城市时应走交叉表，
    # 但PREAGG_TABLE_ROUTE无法做条件判断，因此这里默认品类表，
    # 条件路由由intent_parser的table_hint覆盖（优先级P1 > P0的加权评分）

    # ── 城市×品类交叉 → ais_city_category_summary ──
    "贵阳消费类型": "ais_city_category_summary",
    "城市品类": "ais_city_category_summary",
    "什么品类": "ais_city_category_summary",
    "品类分布对比": "ais_city_category_summary",
    "消费结构": "ais_city_category_summary",
    "商品构成": "ais_city_category_summary",
    "品类构成": "ais_city_category_summary",
    # 带城市+品类意图的通用路由
    "消费类型": "ais_city_category_summary",   # 修复：有城市时用交叉表
    "商品类型": "ais_city_category_summary",   # 修复：有城市时用交叉表
    "品类分布": "ais_city_category_summary",   # 修复：有城市时用交叉表

    # ── 商品排名 → ais_product_top_ranking ──
    "卖的最好": "ais_product_top_ranking",
    "卖得最好": "ais_product_top_ranking",
    "爆款": "ais_product_top_ranking",
    "热销": "ais_product_top_ranking",
    "畅销": "ais_product_top_ranking",
    "什么手机": "ais_product_top_ranking",
    "什么电脑": "ais_product_top_ranking",
    "什么鞋": "ais_product_top_ranking",
    "什么酒": "ais_product_top_ranking",
    "哪个商品": "ais_product_top_ranking",
    "哪个产品": "ais_product_top_ranking",
    "商品排名": "ais_product_top_ranking",
    "产品排名": "ais_product_top_ranking",
    "哪款": "ais_product_top_ranking",
    "哪一款": "ais_product_top_ranking",
    "TOP": "ais_product_top_ranking",
    "排名前": "ais_product_top_ranking",
}

# ============================================================
# 交互表查询保护 —— 无精确主键时禁止路由到交互表
# ============================================================
# 保护机制：
#   ads_user_item_interaction_matrix 表需要 user_id 或 product_id 精确主键，
#   否则全表扫描会拖垮数据库。无精确主键时自动降级到 ais_city_monthly_summary。
#   判断逻辑在 RAGChatbot._select_table() 中实现。
INTERACTION_TABLE_GUARD = {
    "table": "ads_user_item_interaction_matrix",
    "required_slots": ["user_id", "product_id"],  # 必须有精确主键
    "fallback_table": "ais_city_monthly_summary",  # 降级到预聚合表
}

# 均值型指标：聚合时用 AVG 而非 SUM（如客单价、付费率、评分等不应累加）
AVG_TYPE_METRICS = {"客单价", "付费率", "转化率", "评分", "主品类均价", "品类均价", "主力品类均价"}


class SQLExecutor:
    """
    安全 SQL 执行器（支持 context manager）。
    - 白名单字段过滤，防止 SELECT * 拖垮数据库
    - 参数化查询，防 SQL 注入
    - 强制 LIMIT 熔断，保护线上数据库
    - 支持聚合查询（GROUP BY + ORDER BY）
    - 指标字段校验：如果指标在该表不存在，返回空结果并标记
    """

    def __init__(self, table_name="ads_region_consume_analysis"):
        self.table_name = table_name
        self.schema = TABLE_SCHEMA.get(table_name)
        self.conn = None
        self.cursor = None

        if not self.schema:
            raise ValueError(f"数据表 '{table_name}' 未在 TABLE_SCHEMA 中注册")

        self.conn = pymysql.connect(**MYSQL_CONFIG, charset='utf8mb4')
        self.cursor = self.conn.cursor(pymysql.cursors.DictCursor)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def generate_sql(self, parse_result, table_name=None):
        """
        根据意图解析结果自动生成参数化 SQL。
        返回 (sql, params) 元组。

        支持三种模式：
        1. 聚合查询：is_aggregate → GROUP BY + ORDER BY
        2. 交互表品类聚合：metric_field 指向交互指标 → JOIN 商品表按品类聚合
        3. 单城市查询：指定城市 → WHERE city_name = ? + 限制行数
        """
        if table_name:
            self.table_name = table_name
            self.schema = TABLE_SCHEMA.get(table_name)
            if not self.schema:
                raise ValueError(f"数据表 '{table_name}' 未在 TABLE_SCHEMA 中注册")

        slots = parse_result.slots
        table = self.table_name
        schema = self.schema

        # ---- 聚合查询分支 ----
        # ais_product_top_ranking 是已预聚合的TOP5表，不需要再GROUP BY
        if slots.get("is_aggregate") and table != "ais_product_top_ranking":
            return self._generate_aggregate_sql(slots, table, schema, parse_result)

        # ---- 常规查询分支 ----
        return self._generate_standard_sql(slots, parse_result, table, schema)

    def _resolve_metric_col(self, metric_keyword, schema):
        """
        解析指标对应的SQL字段名。

        三级查找流程：
          L1: 表级不支持列表（unsupported_metrics）→ 命中则返回 None
          L2: 表级映射（metric_map）→ 命中则返回对应字段
          L3: 维度映射（dim_map）→ 命中则返回维度字段（is_dim=True）
          L4: 全局映射兜底（METRIC_TO_COLUMN）→ 命中且字段在表中则返回
          均未命中 → 返回 (None, False)

        返回: (col_name, is_dim) 元组，is_dim=True表示该字段是维度而非指标
        """
        # 先检查表级不支持列表
        unsupported = schema.get("unsupported_metrics", set())
        if metric_keyword in unsupported:
            return None, False

        # 表级映射优先
        table_map = schema.get("metric_map", {})
        if metric_keyword in table_map:
            col = table_map[metric_keyword]
            if col in schema["metrics"]:
                return col, False

        # 维度映射（如"消费类别"→main_consume_category）
        dim_map = schema.get("dim_map", {})
        if metric_keyword in dim_map:
            col = dim_map[metric_keyword]
            if col in schema.get("dims", []):
                return col, True

        # 全局映射兜底
        col = METRIC_TO_COLUMN.get(metric_keyword)
        if col and col in schema["metrics"]:
            return col, False

        # 指标在该表不存在
        return None, False

    def _resolve_group_dim(self, slots, table, schema, is_line_chart):
        """
        确定聚合查询的分组维度。

        优先级：
          1. 折线图路径：is_line_chart=True 且表有 stat_month 维度 → 强制 stat_month
          2. group_by_hint 精确匹配 dims
          3. group_by_hint 走 DIM_ALIAS_MAP 映射
          4. 默认取 schema["group_by_dim"]

        返回: group_dim 字符串，或 None（调用方负责降级到标准查询）
        """
        group_dim = schema.get("group_by_dim")

        if is_line_chart and "stat_month" in schema.get("dims", []):
            group_dim = "stat_month"

        if slots.get("group_by_hint") and not is_line_chart:
            hint = slots["group_by_hint"]
            if hint in schema.get("dims", []):
                group_dim = hint
            else:
                DIM_ALIAS_MAP = {
                    "product_category": {
                        "ads_region_consume_analysis": "main_consume_category",
                        "ads_product_feature_full": "product_category",
                        "ais_city_monthly_summary": "main_consume_category",
                        "ais_category_monthly_summary": "product_category",
                        "ais_city_category_summary": "product_category",
                    },
                }
                if hint in DIM_ALIAS_MAP and table in DIM_ALIAS_MAP[hint]:
                    mapped_dim = DIM_ALIAS_MAP[hint][table]
                    if mapped_dim in schema.get("dims", []):
                        group_dim = mapped_dim

        return group_dim

    def _build_select_columns(self, all_metrics, group_dim, schema):
        """
        构建聚合查询的 SELECT 列。

        逻辑：
          - 初始列 [{group_dim} as 维度]
          - 遍历 all_metrics，同义词归一化后调用 _resolve_metric_col
          - 有效指标：根据 AVG_TYPE_METRICS 选择 SUM/AVG，
            格式化为 {agg_func}({metric_col}) as {m_normalized}

        返回: (select_cols, valid_metrics) 元组；无有效指标时返回 ([], [])
        """
        select_cols = [f"`{group_dim}` as `维度`"]
        valid_metrics = []

        for m in all_metrics:
            m_normalized = METRIC_SYNONYMS.get(m, m)
            metric_col, is_dim = self._resolve_metric_col(m_normalized, schema)
            if metric_col and not is_dim:
                agg_func = "AVG" if m_normalized in AVG_TYPE_METRICS else "SUM"
                select_cols.append(f"{agg_func}(`{metric_col}`) as `{m_normalized}`")
                valid_metrics.append(m_normalized)

        return select_cols, valid_metrics

    def _build_where_clause(self, slots, schema, group_dim):
        """
        构建聚合查询的 WHERE 条件子句。

        逻辑：
          - 初始 WHERE 1=1
          - 城市过滤：city 不为空且不为 ALL_CITIES，且表有 city_name 维度
          - 品类过滤：filter_categories 用 IN，category 用 =，但分组维度是品类时跳过
          - 多城市筛选：filter_cities 用 IN
          - 时间过滤：time 格式化后用 LIKE

        返回: (where_sql, params) 元组
        """
        sql = "WHERE 1=1"
        params = []

        if slots.get("city") and slots["city"] != "ALL_CITIES":
            if "city_name" in schema["dims"]:
                sql += " AND `city_name` = %s"
                params.append(slots["city"])

        if slots.get("filter_categories") and "product_category" in schema["dims"]:
            if group_dim != "product_category":
                placeholders = ", ".join(["%s"] * len(slots["filter_categories"]))
                sql += f" AND `product_category` IN ({placeholders})"
                params.extend(slots["filter_categories"])
        elif slots.get("category") and "product_category" in schema["dims"]:
            if group_dim != "product_category":
                sql += " AND `product_category` = %s"
                params.append(slots["category"])

        if slots.get("filter_cities") and "city_name" in schema["dims"]:
            placeholders = ", ".join(["%s"] * len(slots["filter_cities"]))
            sql += f" AND `city_name` IN ({placeholders})"
            params.extend(slots["filter_cities"])

        if slots.get("time"):
            fmt_time = self._format_time(slots["time"])
            if fmt_time and "stat_month" in schema["dims"]:
                sql += " AND `stat_month` LIKE %s"
                params.append(f"{fmt_time}%")

        return sql, params

    def _generate_aggregate_sql(self, slots, table, schema, parse_result=None):
        """
        生成聚合查询 SQL（GROUP BY + ORDER BY DESC）。
        编排方法：依次调用 _resolve_group_dim → _build_select_columns → _build_where_clause，
        最后拼接 GROUP BY + ORDER BY + LIMIT。
        """
        metric_keyword = slots.get("metric", "销售额")
        metric_keyword = METRIC_SYNONYMS.get(metric_keyword, metric_keyword)

        if (table == "ads_user_item_interaction_matrix"
                and slots.get("group_by_hint") == "product_category"):
            return self._generate_interaction_category_sql(slots, metric_keyword)

        chart_type = slots.get("chart_type_hint", "")
        is_line_chart = any(kw in chart_type for kw in ["折线", "趋势", "走势", "变化"])

        group_dim = self._resolve_group_dim(slots, table, schema, is_line_chart)
        if not group_dim:
            from intent_parser import QuestionParseResult
            minimal_pr = QuestionParseResult(
                intent="sql_query",
                slots={**slots, "city": None, "is_aggregate": False},
                original_question=parse_result.original_question if parse_result else ""
            )
            return self._generate_standard_sql(
                {**slots, "city": None, "is_aggregate": False},
                minimal_pr, table, schema
            )

        all_metrics = [metric_keyword] + slots.get("extra_metrics", [])
        select_cols, valid_metrics = self._build_select_columns(all_metrics, group_dim, schema)
        if not valid_metrics:
            return None, []

        where_sql, params = self._build_where_clause(slots, schema, group_dim)

        sql = f"SELECT {', '.join(select_cols)} FROM `{table}` {where_sql}"
        sql += f" GROUP BY `{group_dim}`"

        if is_line_chart:
            sql += f" ORDER BY `{group_dim}` ASC"
        else:
            first_metric = valid_metrics[0]
            first_col, _ = self._resolve_metric_col(first_metric, schema)
            agg_func = "AVG" if first_metric in AVG_TYPE_METRICS else "SUM"
            sql += f" ORDER BY {agg_func}(`{first_col}`) DESC"

        sql += " LIMIT 20"
        return sql, params

    def _generate_interaction_category_sql(self, slots, metric_keyword):
        """
        交互指标 + 品类聚合专用SQL。
        通过JOIN商品表获取品类维度，按品类聚合交互指标。
        """
        metric_col = METRIC_TO_COLUMN.get(metric_keyword, "pv_count")
        metric_alias = metric_keyword

        sql = (
            f"SELECT p.product_category as `维度`, "
            f"SUM(i.{metric_col}) as `{metric_alias}` "
            f"FROM ads_user_item_interaction_matrix i "
            f"JOIN ads_product_feature_full p ON i.product_id = p.product_id "
            f"WHERE 1=1"
        )
        params = []

        # 时间过滤
        if slots.get("time"):
            fmt_time = self._format_time(slots["time"])
            if fmt_time:
                sql += " AND i.stat_month LIKE %s"
                params.append(f"{fmt_time}%")

        sql += f" GROUP BY p.product_category ORDER BY `{metric_alias}` DESC LIMIT 20"
        return sql, params

    def _generate_standard_sql(self, slots, parse_result, table, schema):
        """生成常规查询 SQL（单城市/时间过滤）"""
        metric_keyword = slots.get("metric", "")

        # 如果指标在该表不支持，提前返回空标记
        metric_is_dim = False
        if metric_keyword:
            metric_col, metric_is_dim = self._resolve_metric_col(metric_keyword, schema)
            if metric_col is None and not metric_is_dim:
                return None, []

        # 白名单列 —— 只查注册过的字段
        select_cols = schema["metrics"] + schema["dims"]
        sql = f"SELECT {', '.join(select_cols)} FROM `{table}` WHERE 1=1"
        params = []

        # 安全追加条件（只允许白名单字段）
        if slots.get("city") and slots["city"] != "ALL_CITIES":
            if "city_name" in schema["dims"]:
                sql += " AND `city_name` = %s"
                params.append(slots["city"])

        # 品类过滤（新增：当用户提到具体品类时，支持多品类IN查询）
        if slots.get("filter_categories") and "product_category" in schema["dims"]:
            placeholders = ", ".join(["%s"] * len(slots["filter_categories"]))
            sql += f" AND `product_category` IN ({placeholders})"
            params.extend(slots["filter_categories"])
        elif slots.get("category") and "product_category" in schema["dims"]:
            sql += " AND `product_category` = %s"
            params.append(slots["category"])

        if slots.get("time"):
            fmt_time = self._format_time(slots["time"])
            if fmt_time:
                if "stat_month" in schema["dims"]:
                    sql += " AND `stat_month` LIKE %s"
                    params.append(f"{fmt_time}%")
                else:
                    print(f"警告: 表 {table} 没有 stat_month 字段，时间过滤已跳过")

        # 排序逻辑
        original_q = parse_result.original_question if parse_result else ""
        if any(kw in original_q for kw in ["最高", "最好", "最多", "排名第一", "top"]):
            if metric_keyword and not metric_is_dim:
                metric_col, _ = self._resolve_metric_col(metric_keyword, schema)
                if metric_col:
                    sql += f" ORDER BY `{metric_col}` DESC"
                else:
                    sql += f" ORDER BY {schema['default_order']}"
            else:
                sql += f" ORDER BY {schema['default_order']}"
        elif slots.get("city") and not slots.get("metric"):
            pass  # 指定城市查询不需要排序

        # 安全熔断：强制限制返回行数
        if slots.get("city") and not slots.get("metric"):
            sql += " LIMIT 1"
        else:
            sql += f" LIMIT {schema['max_rows']}"

        return sql, params

    def _format_time(self, time_str):
        """格式化时间字符串为 stat_month LIKE 前缀（适配 YYYY-MM 格式）"""
        match = re.match(r"(\d{4})年(\d+)月", time_str)
        if match:
            year, month = match.groups()
            return f"{year}-{month.zfill(2)}"

        match = re.match(r"(\d{4})年", time_str)
        if match:
            return f"{match.group(1)}-"

        match = re.match(r"(\d+)月", time_str)
        if match:
            return f"-{match.group(1).zfill(2)}"

        return None

    def execute_sql(self, sql: str, params: list) -> pd.DataFrame:
        """安全执行 SQL，返回 DataFrame"""
        try:
            self.cursor.execute(sql, params)
            result = self.cursor.fetchall()
            return pd.DataFrame(result)
        except Exception as e:
            print(f"SQL执行错误: {e}")
            return pd.DataFrame()

    def close(self):
        """安全关闭连接"""
        try:
            if self.cursor:
                self.cursor.close()
        except Exception:
            pass
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass
