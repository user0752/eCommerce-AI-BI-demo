import re
from pydantic import BaseModel
from enum import Enum


# ============================================================
# 指标同义词归一化映射（与 sql_executor.py 共享逻辑）
# ============================================================
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
    "客单价": "客单价",
    # ── 转化率类 → "转化率" ──
    "购买转化率": "转化率", "成交转化率": "转化率", "buy转化": "转化率",
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
    "购物车": "加购量",
    # ── 购买量类 → "购买量" ──
    "购买": "购买量", "购买次数": "购买量", "成交笔数": "购买量",
    "实际购买": "购买量", "购买量": "购买量",
    "购买数": "购买量", "买了多少": "购买量",
}

# ============================================================
# 品类关键词映射（简称→数据库存储值）
# ============================================================
CATEGORY_KEYWORD_MAP = {
    # ── 电子数码（数据库值: "电子数码"）──
    "电子数码": "电子数码", "数码": "电子数码", "电子产品": "电子数码",
    "数码产品": "电子数码", "3C": "电子数码", "3c": "电子数码",
    "手机": "电子数码", "电脑": "电子数码", "平板": "电子数码",
    "配件": "电子数码", "外设": "电子数码",
    # ── 家用电器（数据库值: "家用电器"）──
    "家用电器": "家用电器", "家电": "家用电器", "电器": "家用电器",
    "白色家电": "家用电器", "小家电": "家用电器", "大家电": "家用电器",
    "冰箱": "家用电器", "洗衣机": "家用电器", "空调": "家用电器",
    "电视": "家用电器",
    # ── 服饰鞋帽（数据库值: "服饰鞋帽"）──
    "服饰鞋帽": "服饰鞋帽", "服饰": "服饰鞋帽", "服装": "服饰鞋帽",
    "鞋帽": "服饰鞋帽", "衣服": "服饰鞋帽", "穿搭": "服饰鞋帽",
    "鞋": "服饰鞋帽", "帽子": "服饰鞋帽", "运动鞋": "服饰鞋帽",
    "衣服鞋帽": "服饰鞋帽", "时装": "服饰鞋帽",
    "男装": "服饰鞋帽", "女装": "服饰鞋帽", "童装": "母婴用品",
    "外套": "服饰鞋帽", "裤子": "服饰鞋帽", "裙": "服饰鞋帽",
    # ── 美妆护肤（数据库值: "美妆护肤"）──
    "美妆护肤": "美妆护肤", "美妆": "美妆护肤", "护肤": "美妆护肤",
    "化妆品": "美妆护肤", "彩妆": "美妆护肤", "美容": "美妆护肤",
    "护肤品": "美妆护肤", "口红": "美妆护肤", "面膜": "美妆护肤",
    # ── 食品饮料（数据库值: "食品饮料"）──
    "食品饮料": "食品饮料", "食品": "食品饮料", "饮料": "食品饮料",
    "零食": "食品饮料", "吃喝": "食品饮料", "食品饮品": "食品饮料",
    "吃的": "食品饮料", "饮品": "食品饮料", "小吃": "食品饮料",
    # ── 酒类（数据库值: "酒类"）──
    "酒类": "酒类", "酒": "酒类", "白酒": "酒类", "茅台": "酒类",
    "红酒": "酒类", "啤酒": "酒类", "葡萄酒": "酒类",
    "酱酒": "酒类", "烈酒": "酒类", "酒水": "酒类",
    # ── 运动户外（数据库值: "运动户外"）──
    "运动户外": "运动户外", "运动": "运动户外", "户外": "运动户外",
    "运动用品": "运动户外", "户外装备": "运动户外",
    "健身": "运动户外", "体育": "运动户外", "露营": "运动户外",
    "跑步": "运动户外", "登山": "运动户外",
    # ── 母婴用品（数据库值: "母婴用品"）──
    "母婴用品": "母婴用品", "母婴": "母婴用品",
    "婴儿": "母婴用品", "孕婴": "母婴用品", "童装": "母婴用品",
    "奶粉": "母婴用品", "宝宝": "母婴用品", "育儿": "母婴用品",
    # ── 家居日用（数据库值: "家居日用"）──
    "家居日用": "家居日用", "家居": "家居日用", "日用": "家居日用",
    "日用品": "家居日用", "家居用品": "家居日用",
    "生活用品": "家居日用", "家居生活": "家居日用",
    "厨具": "家居日用", "收纳": "家居日用",
    "家具": "家居日用", "家具用品": "家居日用",
    "家具类": "家居日用", "家具产品": "家居日用",
    # ── 农产品（数据库值: "农产品"）──
    "农产品": "农产品", "农产": "农产品", "特产": "农产品",
    "土特产": "农产品", "农副产品": "农产品", "贵州特产": "农产品",
    "茶叶": "农产品", "水果": "农产品", "大米": "农产品",
    "薏仁": "农产品",
    # ── 旅游文创（数据库值: "旅游文创"）──
    "旅游文创": "旅游文创", "文创": "旅游文创", "旅游": "旅游文创",
    "文创产品": "旅游文创", "旅游纪念品": "旅游文创",
    "文创用品": "旅游文创", "纪念品": "旅游文创",
    "手工艺品": "旅游文创", "非遗": "旅游文创",
}


class IntentType(str, Enum):
    SQL_QUERY = "sql_query"
    RAG_RETRIEVAL = "rag_retrieval"
    CLARIFY = "clarify"
    OUT_OF_DOMAIN = "out_of_domain"


class QuestionParseResult(BaseModel):
    intent: IntentType
    slots: dict
    original_question: str


# ============================================================
# 域关键词
# ============================================================
DOMAIN_KEYWORDS = {
    "贵阳", "贵州", "销量", "销售额", "消费", "用户", "商品",
    "品类", "品牌", "付费率", "电商", "订单", "转化", "复购",
    "GMV", "gmv", "成交额", "营收",
    "电子", "数码", "服饰", "鞋帽", "家电", "美妆", "护肤",
    "食品", "饮料", "酒", "运动", "户外", "母婴", "家居",
    "家具",
    "农产品", "旅游", "文创", "产品", "城市",
    "遵义", "六盘水", "毕节", "铜仁", "安顺",
    "黔东南", "黔南", "黔西南",
    "仁怀", "清镇", "盘州", "镇远", "黔西",
    "客单价", "购买力", "均价", "单价", "热度", "评分",
    "排行", "趋势", "分布", "占比", "对比", "增长",
    "交互", "行为", "浏览", "收藏", "加购", "点击",
    "手机", "电脑", "平板", "耳机", "手表", "相机",
    "电视", "冰箱", "洗衣机", "空调", "鞋", "衣服",
    "红酒", "白酒", "奶粉", "茶叶", "零食",
    "PV", "pv", "UV", "uv", "AOV", "aov", "DAU", "dau",
    "MAU", "mau", "3C", "3c",
    "电器", "服装", "红酒", "白酒", "化妆品", "零食",
    "特产", "纪念品", "手机", "电脑", "冰箱",
    "西藏", "北京", "上海", "天津", "重庆",
    "广东", "广州", "深圳", "浙江", "杭州",
    "江苏", "南京", "四川", "成都", "云南", "昆明",
    "湖南", "长沙", "湖北", "武汉", "河南", "郑州",
    "山东", "济南", "全国",
}

# ============================================================
# 城市关键词 → 数据库实际值映射
# ⚠️ 数据库实际存储值可能与行政全称不同（如自治州存的是"黔东南州"而非"黔东南苗族侗族自治州"）
# ============================================================
CITY_KEYWORD_MAP = {
    # ── 6大地级市（核心城市）──
    "贵阳": "贵阳市", "贵阳市": "贵阳市",
    "遵义": "遵义市", "遵义市": "遵义市",
    "六盘水": "六盘水市", "六盘水市": "六盘水市",
    "毕节": "毕节市", "毕节市": "毕节市",
    "铜仁": "铜仁市", "铜仁市": "铜仁市",
    "安顺": "安顺市", "安顺市": "安顺市",
    # 自治州：数据库存的是"XX州"而非行政全称
    "黔东南": "黔东南州", "黔东南州": "黔东南州",
    "黔东南苗族侗族自治州": "黔东南州",
    "黔南": "黔南州", "黔南州": "黔南州",
    "黔南布依族苗族自治州": "黔南州",
    "黔西南": "黔西南州", "黔西南州": "黔西南州",
    "黔西南布依族苗族自治州": "黔西南州",
    # ── 5个县级市/县（数据库也有数据）──
    "仁怀": "仁怀市", "仁怀市": "仁怀市",
    "清镇": "清镇市", "清镇市": "清镇市",
    "盘州": "盘州市", "盘州市": "盘州市",
    "镇远": "镇远县", "镇远县": "镇远县",
    "黔西": "黔西市", "黔西市": "黔西市",
}
CITY_KEYWORDS = set(CITY_KEYWORD_MAP.keys())

# ============================================================
# 非覆盖区域关键词 —— 常见省外城市/省份，不在贵州9城范围内
# 当用户提到这些地区时，标记为 _non_covered_city，走SQL路径触发Level2降级
# ============================================================
NON_COVERED_REGIONS = {
    "西藏", "西藏自治区", "拉萨",
    "北京", "北京市", "上海", "上海市", "天津", "天津市", "重庆", "重庆市",
    "广东", "广东省", "广州", "深圳", "东莞", "佛山",
    "浙江", "浙江省", "杭州", "宁波", "温州",
    "江苏", "江苏省", "南京", "苏州", "无锡",
    "四川", "四川省", "成都", "绵阳",
    "云南", "云南省", "昆明", "大理", "丽江",
    "湖南", "湖南省", "长沙", "株洲",
    "湖北", "湖北省", "武汉", "宜昌",
    "河南", "河南省", "郑州", "洛阳",
    "山东", "山东省", "济南", "青岛",
    "福建", "福建省", "福州", "厦门",
    "安徽", "安徽省", "合肥",
    "江西", "江西省", "南昌",
    "河北", "河北省", "石家庄",
    "山西", "山西省", "太原",
    "辽宁", "辽宁省", "沈阳", "大连",
    "吉林", "吉林省", "长春",
    "黑龙江", "黑龙江省", "哈尔滨",
    "内蒙古", "广西", "海南", "海南岛", "海口", "三亚",
    "新疆", "甘肃", "青海", "宁夏",
    "香港", "澳门", "台湾",
    "全国", "全国各", "全国各省", "各省市", "各省",
}

# ============================================================
# 政策/知识类关键词 —— 这些问题应直接走RAG路径，而非CLARIFY或SQL
# ============================================================
RAG_PRIORITY_KEYWORDS = {
    "政策", "产业政策", "扶持", "补贴", "数博会", "大数据产业",
    "挑战", "机遇", "面临", "发展方向", "发展前景",
    "影响", "有什么影响", "带来了", "推动了",
    "建议", "对策", "措施", "策略", "规划",
    "电商发展", "行业趋势", "行业现状", "行业概况",
    "发展趋势", "发展情况", "发展现状",
    "市场环境", "营商环境", "投资环境",
    "宏观", "总体情况", "整体情况",
    "报表", "报告", "分析报告", "行业报告", "专题报告",
    "预测", "展望", "未来", "前景", "预估", "走势",
    "总结", "综述", "全貌", "全景",
    "特点", "特色", "特征", "区别", "差异", "不同", "优势", "竞争力",
    "经济发展", "经济特点", "经济现状", "经济形势",
    "产业布局", "产业结构", "产业带", "产业集群",
    "区域特色", "区域差异", "区域优势",
    "发展模式", "发展路径", "发展经验",
}

# ============================================================
# 指标关键词 → (显示名, SQL字段名, 所属表)
# ============================================================
METRIC_KEYWORDS = {
    "销量", "销售额", "用户数", "付费率", "订单数",
    "消费类别", "消费品牌", "转化率", "客单价",
    "点击量", "浏览量", "收藏量", "加购量", "购买量", "订单量",
}

# ============================================================
# 交互指标 → SQL字段 映射（用于传递给下游 sql_executor）
# ============================================================
INTERACTION_METRIC_MAP = {
    "点击量": "pv_count",
    "浏览量": "pv_count",
    "收藏量": "fav_count",
    "加购量": "cart_count",
    "购买量": "buy_count",
    "订单量": "total_order_count",
    "订单数": "total_order_count",
}

# ============================================================
# 指标 → 建议查询表 映射（优先级从高到低）
# 交互指标路由到AIS预聚合表，不再走原始交互表
# ============================================================
METRIC_TABLE_HINT = {
    "点击量": "ais_city_monthly_summary",
    "浏览量": "ais_city_monthly_summary",
    "收藏量": "ais_city_monthly_summary",
    "加购量": "ais_city_monthly_summary",
    "购买量": "ais_city_monthly_summary",
    "客单价": "ais_city_monthly_summary",
    "消费类别": "ais_city_monthly_summary",
    "消费品牌": "ais_city_monthly_summary",
    "付费率": "ais_city_monthly_summary",
}

# ============================================================
# 时间/空间豁免词
# ============================================================
TIME_EXEMPTIONS = {"今年", "去年", "最近", "本年度", "上年度", "近期", "年度", "全年", "一整年", "整年"}
SPACE_EXEMPTIONS = {
    "整体", "全省", "全省汇总", "所有城市", "各城市", "全省各市", "贵州", "各市",
    "全省范围", "各市州", "各州市", "贵州各", "所有地区", "每个城市",
    "贵州全省", "全省各",
}

# ============================================================
# 商品排名查询关键词 —— 识别具体商品排名/爆款类问题
# ============================================================
PRODUCT_RANK_KEYWORDS = {
    "什么手机", "什么电脑", "什么鞋", "什么酒", "什么电视", "什么冰箱",
    "什么洗衣机", "什么空调", "什么平板", "什么耳机", "什么手表",
    "什么相机", "什么化妆品", "什么护肤品", "什么奶粉", "什么茶叶",
    "什么家具", "什么家电", "什么衣服", "什么特产", "什么产品",
    "什么商品", "什么品牌", "什么款式", "什么型号",
    "卖的最好的", "卖得最好的", "销量最好的", "最畅销的",
    "爆款", "热销", "top", "TOP", "排名",
    "什么特产", "什么零食", "什么饮料", "什么衣服", "什么运动鞋",
    "哪款手机", "哪款电脑", "哪款鞋", "哪款酒",
    "哪一款手机", "哪一款电脑",
    "爆款", "热销商品", "畅销商品", "热销产品", "畅销产品",
    "卖得最好的", "卖得最好的是", "卖得最好的手机", "卖得最好的电脑",
    "卖得最好的鞋", "卖得最好的酒",
    "卖的最好的", "卖的最好的是", "卖的最好的手机", "卖的最好的电脑",
    "卖的最好的鞋", "卖的最好的酒",
    "商品排名", "产品排名", "商品排行", "产品排行",
}

# ============================================================
# 聚合查询关键词（触发 GROUP BY + ORDER BY 路径）
# ============================================================
AGGREGATE_KEYWORDS = {
    "排名", "对比", "最好", "最高", "最多", "最低", "最少", "top", "排行",
    "前十", "前五", "前三名", "前五名", "前十名",
    "柱形图", "柱状图", "折线图", "饼图", "雷达图", "散点图", "图表", "可视化", "排行榜",
    "vs", "哪个更高", "哪个最多", "相比", "相比较",
    "哪类", "哪个品类", "各品类", "哪类商品",
    "消费类型", "商品类型", "消费商品类型", "品类分布", "类型分布",
    "哪个城市", "哪个城市的", "各城市", "哪座城市",
    "占比", "比例", "分布情况", "构成", "构成比",
    "趋势", "走势", "变化", "增长", "增幅", "月度",
    "卖得最好", "卖得最多", "最受欢迎", "最畅销",
    "排行", "TOP", "top", "Top",
    "差异", "区别", "不同",
}

# ============================================================
# 隐式聚合维度关键词（暗示按某维度聚合）
# ============================================================
DIMENSION_HINT_KEYWORDS = {
    "哪类": "product_category",
    "哪个品类": "product_category",
    "各品类": "product_category",
    "哪类商品": "product_category",
    "哪类商品的用户": "product_category",
    "消费类型": "product_category",
    "商品类型": "product_category",
    "消费商品类型": "product_category",
    "品类分布": "product_category",
    "类型分布": "product_category",
    "品类占比": "product_category",
    "品类构成": "product_category",
    "哪个城市": "city_name",
    "哪个城市的": "city_name",
    "各城市": "city_name",
    "哪座城市": "city_name",
}

# ============================================================
# 图表相关关键词
# ============================================================
CHART_KEYWORDS = {
    "柱形图", "柱状图", "折线图", "饼图", "雷达图", "散点图",
    "图表", "可视化", "画图", "图", "曲线图", "面积图", "环形图",
}
CHART_TYPE_PRIORITY = ["雷达图", "柱形图", "柱状图", "折线图", "饼图", "散点图"]

# ============================================================
# 预计算：按长度降序排列的关键词列表（用于最长匹配）
# ============================================================
SORTED_CITY_KEYWORDS = sorted(CITY_KEYWORD_MAP.keys(), key=len, reverse=True)
SORTED_CATEGORY_KEYWORDS = sorted(CATEGORY_KEYWORD_MAP.keys(), key=len, reverse=True)
SORTED_NON_COVERED_REGIONS = sorted(NON_COVERED_REGIONS, key=len, reverse=True)


# ============================================================
# 内部辅助函数
# ============================================================

def _normalize_synonyms(text: str) -> str:
    """
    将文本中的指标同义词替换为标准指标名。

    替换策略：按同义词长度降序替换，避免短词截断长词
    （例如先替换"销售额"再替换"销售"，防止"销售额"变成"销售额额"）。
    跳过已是标准指标名的词（METRIC_KEYWORDS 中的词无需替换）。
    """
    result = text
    for synonym, standard_name in sorted(METRIC_SYNONYMS.items(), key=lambda x: len(x[0]), reverse=True):
        if synonym in result and synonym not in METRIC_KEYWORDS:
            result = result.replace(synonym, standard_name)
    return result


def _check_domain(question: str) -> bool:
    """
    判断问题是否属于电商数据域。

    检测策略：
    1. 先对原始问题做关键词匹配
    2. 若未命中，对同义词归一化后的问题再做一次匹配
       （如用户说"UV"→归一化为"浏览量"后命中域关键词）
    """
    if any(keyword in question for keyword in DOMAIN_KEYWORDS):
        return True
    normalized = _normalize_synonyms(question)
    return any(keyword in normalized for keyword in DOMAIN_KEYWORDS)


def _extract_city(question: str, slots: dict) -> None:
    """
    提取城市槽位，按优先级依次检测：

    1. 覆盖区域内城市（映射为数据库全称，如"贵阳"→"贵阳市"）
    2. 非覆盖区域（标记 _non_covered_city，走SQL路径触发Level2降级）
    3. 泛化城市表达（如"全省"、"各城市" → ALL_CITIES）

    采用最长匹配策略，避免"黔东南"被"黔东"截断。
    """
    for city_short in SORTED_CITY_KEYWORDS:
        if city_short in question:
            slots["city"] = CITY_KEYWORD_MAP[city_short]
            break

    if not slots.get("city"):
        for region in SORTED_NON_COVERED_REGIONS:
            if region in question:
                slots["city"] = region
                slots["_non_covered_city"] = True
                break

    if not slots.get("city"):
        if any(ex in question for ex in SPACE_EXEMPTIONS):
            slots["city"] = "ALL_CITIES"


def _extract_time(question: str, slots: dict) -> None:
    """
    提取时间槽位。

    支持格式：
    - "2025年3月" / "2025年" / "3月"
    - "最近N天" → 标记 _use_latest_time（让下游用默认最新数据）
    """
    time_match = re.search(r"\d{4}年\d+月|\d{4}年|\d+月", question)
    if time_match:
        slots["time"] = time_match.group()
    elif re.search(r"最近\d+天|近\d+天", question):
        slots["_use_latest_time"] = True


def _extract_metric(question: str, slots: dict) -> None:
    """
    提取指标槽位，流程：

    1. 同义词归一化（将"GMV"→"销售额"等）
    2. 遍历 METRIC_KEYWORDS 收集所有命中指标
    3. 第一个为主指标，其余为附加指标（extra_metrics）
    4. 兜底：旧版同义词映射（用于 METRIC_SYNONYMS 未覆盖的情况）
    5. 交互指标 → 传递 metric_field 给下游 sql_executor
    """
    normalized_question = _normalize_synonyms(question)

    found_metrics = []
    for metric in METRIC_KEYWORDS:
        if metric in normalized_question and metric not in found_metrics:
            found_metrics.append(metric)

    if found_metrics:
        slots["metric"] = found_metrics[0]
        if len(found_metrics) > 1:
            slots["extra_metrics"] = found_metrics[1:]

    # 兜底：旧版同义词映射
    if not slots.get("metric"):
        for synonym in ["GMV", "gmv", "成交额", "营收"]:
            if synonym in question:
                slots["metric"] = "销售额"
                break

    # 交互指标 → 传递 metric_field 给下游
    if slots.get("metric") and slots["metric"] in INTERACTION_METRIC_MAP:
        slots["metric_field"] = INTERACTION_METRIC_MAP[slots["metric"]]


def _deduplicate_keywords(keywords: list) -> list:
    """
    去重关键词列表：去掉被更长名包含的短名。

    例如："运动"被"运动户外"包含，则去掉"运动"；
          "黔东南"包含"黔东"，则去掉"黔东"。
    """
    deduped = []
    for keyword in keywords:
        if not any(keyword != other and keyword in other for other in keywords):
            deduped.append(keyword)
    return deduped


def _extract_category(question: str, slots: dict) -> None:
    """
    提取品类槽位，支持多品类检测。

    去重逻辑：去掉被更长名包含的短名（如"运动"被"运动户外"包含）。
    第一个映射品类为主品类，2个及以上时设置 filter_categories。
    """
    mentioned = [category for category in SORTED_CATEGORY_KEYWORDS if category in question]
    mentioned = _deduplicate_keywords(mentioned)

    if mentioned:
        mapped_cats = [CATEGORY_KEYWORD_MAP[c] for c in mentioned]
        slots["category"] = mapped_cats[0]
        if len(mapped_cats) >= 2:
            slots["filter_categories"] = mapped_cats


def _detect_product_rank(question: str, slots: dict) -> None:
    """
    检测商品排名查询意图（如"什么手机卖得最好"）。

    处理逻辑：
    - 标记 _product_rank_query 并路由到 ais_product_top_ranking 表
    - 若无明确指标，默认设为"销量"
    - 若同时有城市限制，标记 _city_product_query
      （ais_product_top_ranking 无城市维度，需下游特殊处理）
    """
    if not any(keyword in question for keyword in PRODUCT_RANK_KEYWORDS):
        return

    slots["_product_rank_query"] = True
    slots["table_hint"] = "ais_product_top_ranking"
    if not slots.get("metric"):
        slots["metric"] = "销量"
    if slots.get("city") and slots["city"] != "ALL_CITIES":
        slots["_city_product_query"] = True


def _infer_implicit_metric(question: str, slots: dict) -> None:
    """
    隐式指标推断：当用户没有明确指标词时，从上下文推断。

    按优先级依次匹配关键词模式，例如：
    - "卖得最好" → 销量
    - "消费能力" → 客单价
    - "趋势" → 销售额
    - "热度" → 浏览量
    """
    if slots.get("metric"):
        return

    if any(kw in question for kw in [
        "卖得最好", "卖得最多", "销量最高", "卖最多",
        "最畅销", "最热门", "卖得火",
        "卖的最好", "卖的最多", "卖的火",
    ]):
        slots["metric"] = "销量"
    elif any(kw in question for kw in ["销售额最高", "营收最高", "GMV最高", "消费最高"]):
        slots["metric"] = "销售额"
    elif any(kw in question for kw in [
        "交互行为", "交互", "行为趋势", "用户行为", "浏览行为", "互动",
    ]):
        slots["metric"] = "浏览量"
    elif any(kw in question for kw in ["消费能力", "消费水平", "购买力"]):
        slots["metric"] = "客单价"
    elif any(kw in question for kw in ["消费情况", "消费额", "消费金额", "消费数据"]):
        slots["metric"] = "销售额"
    elif (
        "消费" in question
        and slots.get("city")
        and not any(kw in question for kw in ["消费能力", "消费水平", "消费趋势"])
    ):
        # "XX市旅游文创消费" → 有城市+品类但无明确指标，默认推断为销售额
        slots["metric"] = "销售额"
    elif "趋势" in question:
        # "消费趋势"/"销售趋势"/"增长趋势" → 默认销售额
        slots["metric"] = "销售额"
    elif any(kw in question for kw in ["付费情况", "付费能力", "付费意愿"]):
        slots["metric"] = "付费率"
    elif any(kw in question for kw in ["下单情况", "下单量", "订单"]):
        slots["metric"] = "订单数"
    elif any(kw in question for kw in ["热度", "热门", "火爆"]):
        slots["metric"] = "浏览量"
    elif any(kw in question for kw in ["价格", "均价", "单价"]):
        slots["metric"] = "客单价"


def _detect_multi_city(question: str, slots: dict) -> list:
    """
    检测多城市对比场景。

    当问题中出现2个及以上城市名时：
    - 自动将 city 设为 ALL_CITIES（触发聚合查询）
    - 标记 is_aggregate = True
    - 记录 filter_cities（映射为数据库全称），方便下游筛选

    返回去重后的城市关键词列表，供意图分类使用。
    """
    mentioned = [city for city in SORTED_CITY_KEYWORDS if city in question]
    mentioned = _deduplicate_keywords(mentioned)

    if len(mentioned) >= 2:
        slots["city"] = "ALL_CITIES"
        slots["is_aggregate"] = True
        slots["filter_cities"] = [CITY_KEYWORD_MAP[city] for city in mentioned]

    return mentioned


def _detect_aggregate_and_dimension(question: str, slots: dict, has_multi_city: bool) -> bool:
    """
    检测聚合意图和隐式维度提示。

    聚合检测：问题中是否包含排名/对比/趋势等关键词（不区分大小写）。
    维度提示：如"哪类商品"暗示按品类聚合，"哪个城市"暗示按城市聚合。

    多城市对比时，主维度应为城市而非品类，跳过品类维度提示。

    返回 is_aggregate 布尔值。
    """
    is_aggregate = any(keyword in question.lower() for keyword in AGGREGATE_KEYWORDS)

    for dim_keyword, dim_value in DIMENSION_HINT_KEYWORDS.items():
        if dim_keyword in question:
            # 多城市对比时，主维度应为城市而非品类，跳过品类维度提示
            if has_multi_city and dim_value == "product_category":
                continue
            slots["group_by_hint"] = dim_value
            if not is_aggregate:
                is_aggregate = True
            break

    return is_aggregate


def _detect_chart_request(question: str) -> tuple:
    """
    检测图表请求。

    返回 (need_chart, chart_type_hint) 元组：
    - need_chart: 是否需要生成图表
    - chart_type_hint: 具体图表类型（如"雷达图"、"折线图"），无则为 None
    """
    need_chart = any(keyword in question for keyword in CHART_KEYWORDS)

    chart_type_hint = None
    for chart_type in CHART_TYPE_PRIORITY:
        if chart_type in question:
            chart_type_hint = chart_type
            break

    return need_chart, chart_type_hint


def _classify_intent(question: str, slots: dict, is_aggregate: bool,
                     mentioned_cities: list) -> IntentType:
    """
    意图分类（优先级从高到低）。

    分类规则：
    ① 多城市对比 → SQL_QUERY
    ② 政策/知识类问题 → RAG_RETRIEVAL
    ③ 聚合关键词 + 域信号 → SQL_QUERY
    ④ 泛化分析类（为什么/原因/如何/规律）→ RAG_RETRIEVAL
    ④.5 "趋势"类：有结构化信号 → SQL_QUERY，否则 → RAG_RETRIEVAL
    ⑤ "分析"类问题 → RAG_RETRIEVAL
    ⑥ 有指标 + 有城市/时间 → SQL_QUERY
    ⑦ 有指标 + 聚合意图 → SQL_QUERY
    ⑧ 有指标 + 有品类 → SQL_QUERY
    ⑨ 有指标 + 无城市/时间/品类 → CLARIFY
    ⑩ 仅有城市名、无指标 → CLARIFY 或 RAG_RETRIEVAL
    ⑪ 默认 → RAG_RETRIEVAL
    """
    # ① 多城市对比 → 强制 SQL + 聚合
    if len(mentioned_cities) >= 2:
        return IntentType.SQL_QUERY

    # ② 政策/知识类问题 → 直接 RAG（优先级最高，避免被CLARIFY拦截）
    if any(keyword in question for keyword in RAG_PRIORITY_KEYWORDS):
        return IntentType.RAG_RETRIEVAL

    # ③ 聚合关键词 + 域信号（有指标/城市/时间任意一个）→ 强制 SQL
    if is_aggregate and (
        slots.get("metric") or slots.get("city")
        or slots.get("time") or slots.get("_use_latest_time")
    ):
        return IntentType.SQL_QUERY

    # ④ 泛化分析类（为什么/原因/如何/规律）→ RAG
    if any(keyword in question for keyword in ["为什么", "原因", "如何", "规律", "洞察", "解读"]):
        return IntentType.RAG_RETRIEVAL

    # ④.5 "趋势"类：有结构化信号（城市/时间/图表/品类）→ SQL，否则→ RAG
    if "趋势" in question:
        has_structural_signal = (
            slots.get("city") or slots.get("time") or slots.get("_use_latest_time")
            or slots.get("need_chart") or slots.get("category") or is_aggregate
        )
        return IntentType.SQL_QUERY if has_structural_signal else IntentType.RAG_RETRIEVAL

    # ⑤ "分析"类问题：无明确聚合/排名意图 → RAG
    if "分析" in question and not is_aggregate:
        return IntentType.RAG_RETRIEVAL

    # ⑥ 有指标 + 有城市/时间 → SQL
    if slots.get("metric") and (
        slots.get("city") or slots.get("time") or slots.get("_use_latest_time")
    ):
        return IntentType.SQL_QUERY

    # ⑦ 有指标 + 聚合意图 → SQL（即使没有城市/时间也走SQL）
    if slots.get("metric") and is_aggregate:
        return IntentType.SQL_QUERY

    # ⑧ 有指标 + 有品类 → SQL（品类维度足够走查询）
    if slots.get("metric") and slots.get("category"):
        return IntentType.SQL_QUERY

    # ⑨ 有指标 + 无城市/时间/品类 → CLARIFY（缺少关键筛选条件）
    if slots.get("metric") and not slots.get("city") and not slots.get("time"):
        return IntentType.CLARIFY

    # ⑩ 仅有城市名、无指标、无分析意图 → CLARIFY（缺少查询目标）
    if (
        slots.get("city")
        and not slots.get("metric")
        and not slots.get("category")
        and not is_aggregate
    ):
        # 非覆盖城市 + 无指标 → 也走CLARIFY，提示中说明该地区不在覆盖范围
        if slots.get("_non_covered_city"):
            return IntentType.CLARIFY
        # 排除有明确分析意图的短输入（如"贵阳消费"已有隐式指标推断）
        has_analysis_intent = any(
            keyword in question
            for keyword in ["为什么", "原因", "如何", "规律", "洞察", "解读", "分析", "趋势", "情况", "概况", "介绍"]
        )
        return IntentType.RAG_RETRIEVAL if has_analysis_intent else IntentType.CLARIFY

    # ⑪ 默认 → RAG
    return IntentType.RAG_RETRIEVAL


def _build_clarify_result(question: str, slots: dict, intent: IntentType) -> QuestionParseResult:
    """
    根据 CLARIFY 意图和当前槽位，构建澄清结果。

    不同场景下缺失槽位不同：
    - ⑨ 有指标无城市 → 缺少"城市/区域"
    - ⑩ 非覆盖城市无指标 → 缺少"查询指标/意图"，带 _non_covered_hint
    - ⑩ 普通城市无指标 → 缺少"查询指标/意图"
    """
    if slots.get("metric") and not slots.get("city") and not slots.get("time"):
        # 场景⑨：有指标但缺少城市/时间
        return QuestionParseResult(
            intent=IntentType.CLARIFY,
            slots={"missing": ["城市/区域"], "partial": slots},
            original_question=question,
        )

    if slots.get("city") and not slots.get("metric") and not slots.get("category"):
        # 场景⑩：有城市但缺少指标
        if slots.get("_non_covered_city"):
            return QuestionParseResult(
                intent=IntentType.CLARIFY,
                slots={"missing": ["查询指标/意图"], "partial": {**slots, "_non_covered_hint": True}},
                original_question=question,
            )
        return QuestionParseResult(
            intent=IntentType.CLARIFY,
            slots={"missing": ["查询指标/意图"], "partial": slots},
            original_question=question,
        )

    # 兜底（理论上不应到达）
    return QuestionParseResult(
        intent=IntentType.CLARIFY,
        slots={"missing": ["更多信息"], "partial": slots},
        original_question=question,
    )


def _apply_metric_table_hint(slots: dict) -> None:
    """
    根据指标设置建议查询表（但商品排名查询的 table_hint 优先级更高，不覆盖）。
    """
    if slots.get("metric") and slots["metric"] in METRIC_TABLE_HINT:
        if slots.get("table_hint") != "ais_product_top_ranking":
            slots["table_hint"] = METRIC_TABLE_HINT[slots["metric"]]


def _apply_table_routing(question: str, slots: dict, is_aggregate: bool,
                         chart_type_hint: str | None) -> None:
    """
    应用表路由策略：根据槽位组合选择最优数据表。

    路由优先级（从高到低）：
    1. 消费类别/消费品牌 + 聚合 → AIS品类交叉表或品类月度表
    2. 消费类型/商品类型关键词 → AIS品类交叉表或品类月度表
    3. 雷达图请求 → AIS品类月度表（有完整多指标列）
    4. 品类 + 城市 → AIS城市×品类交叉表
    5. 品类 + 无城市 → AIS品类月度表
    6. 趋势 + 城市 → AIS城市月度汇总表（按月折线图）
    """
    has_multi_city_compare = (
        slots.get("filter_cities") and len(slots.get("filter_cities", [])) >= 2
    )
    has_city_group = slots.get("group_by_hint") == "city_name"

    # ── 路由1：消费类别/消费品牌 + 聚合意图 ──
    # 有城市时用 ais_city_category_summary（支持城市维度筛选），否则用 ais_category_monthly_summary
    if slots.get("metric") in ("消费类别", "消费品牌") and slots.get("is_aggregate"):
        if slots.get("city") and slots["city"] != "ALL_CITIES":
            slots["table_hint"] = "ais_city_category_summary"
        else:
            slots["table_hint"] = "ais_category_monthly_summary"
        slots["group_by_hint"] = "product_category"
        if slots["metric"] == "消费类别":
            slots["metric"] = "销售额"

    # ── 路由2：消费类型/商品类型/品类分布关键词 ──
    # 有城市时用交叉表（支持城市级品类分析），否则用品类月度表
    category_type_keywords = {"消费类型", "商品类型", "消费商品类型", "品类分布", "类型分布"}
    if any(kw in question for kw in category_type_keywords) and not has_multi_city_compare:
        if slots.get("city") and slots["city"] != "ALL_CITIES":
            slots["table_hint"] = "ais_city_category_summary"
        else:
            slots["table_hint"] = "ais_category_monthly_summary"
        slots["group_by_hint"] = "product_category"
        if not slots.get("metric") or slots["metric"] == "销售额":
            slots["metric"] = "销售额"

    # ── 路由3：雷达图请求 → 强制 need_chart + 传递图表类型 + 路由到品类月度表 ──
    if chart_type_hint:
        slots["need_chart"] = True
        slots["chart_type_hint"] = chart_type_hint
        if chart_type_hint == "雷达图" and not has_multi_city_compare:
            # 雷达图默认按品类维度分组
            if not slots.get("group_by_hint"):
                slots["group_by_hint"] = "product_category"
            # 雷达图走AIS品类月度表（有完整多指标列：销量+销售额+转化率+PV+收藏量等）
            overridable_tables = (
                "ads_region_consume_analysis", "ads_product_feature_full",
                "ais_city_monthly_summary",
            )
            if not slots.get("table_hint") or slots["table_hint"] in overridable_tables:
                slots["table_hint"] = "ais_category_monthly_summary"

    # ── 路由4：品类 + 城市 → 城市×品类交叉表（最关键的智能路由） ──
    # 当用户同时提到品类和城市时，ais_city_category_summary 是最佳选择
    if slots.get("category") and (slots.get("city") or has_city_group):
        overridable_tables = (
            "ads_region_consume_analysis", "ads_product_feature_full",
            "ais_city_monthly_summary", "ais_category_monthly_summary",
        )
        if not slots.get("table_hint") or slots["table_hint"] in overridable_tables:
            slots["table_hint"] = "ais_city_category_summary"
            # 如果是"哪个城市"类问题，按城市分组；否则按品类分组
            if not has_city_group:
                slots["group_by_hint"] = "product_category"

    # ── 路由5：品类 + 无城市（全省） → 品类月度表 ──
    elif slots.get("category") and not slots.get("city") and not has_city_group:
        overridable_tables = ("ads_region_consume_analysis", "ads_product_feature_full")
        if not slots.get("table_hint") or slots["table_hint"] in overridable_tables:
            slots["table_hint"] = "ais_category_monthly_summary"
            if not slots.get("group_by_hint"):
                slots["group_by_hint"] = "product_category"

    # ── 路由6：趋势类查询 → 城市月度汇总表（按月折线图） ──
    if "趋势" in question and slots.get("city") and slots["city"] != "ALL_CITIES":
        overridable_tables = ("ads_region_consume_analysis", "ads_product_feature_full")
        if not slots.get("table_hint") or slots["table_hint"] in overridable_tables:
            slots["table_hint"] = "ais_city_monthly_summary"
            slots["group_by_hint"] = "stat_month"


def _detect_missing_slots(question: str, slots: dict) -> tuple:
    """
    检测SQL查询路径下缺失的关键槽位。

    返回 (critical_missing, suggested_missing)：
      - critical_missing: 强制缺失项，缺失则触发澄清
      - suggested_missing: 建议补充项，缺失时自动用默认值查询
    """
    critical = []
    suggested = []

    # 城市：如果问题有聚合意图（如"哪类商品"），则城市不是必须的
    # 商品排名查询（ais_product_top_ranking）无城市维度，也不需要城市
    has_agg_dim = any(keyword in question for keyword in DIMENSION_HINT_KEYWORDS)
    has_space_exemption = any(ex in question for ex in SPACE_EXEMPTIONS)
    is_product_rank = (
        slots.get("_product_rank_query") or slots.get("table_hint") == "ais_product_top_ranking"
    )
    if not slots.get("city") and not has_space_exemption and not has_agg_dim and not is_product_rank:
        critical.append("城市/区域")

    # 时间：建议补充
    has_time_exemption = any(ex in question for ex in TIME_EXEMPTIONS)
    has_general_intent = any(kw in question for kw in ["主要", "是什么", "有哪些", "大概", "整体"])
    if (
        not slots.get("time")
        and not has_time_exemption
        and not has_general_intent
        and not slots.get("_use_latest_time")
    ):
        suggested.append("时间范围")

    return critical, suggested


# ============================================================
# 主入口函数
# ============================================================

def parse_question(question: str) -> QuestionParseResult:
    """
    解析用户问题，进行意图分类和槽位提取。

    处理流程：
    1. 域外检测 → 不属于电商领域则直接返回 OUT_OF_DOMAIN
    2. 槽位提取 → 城市、时间、指标、品类
    3. 特殊意图检测 → 商品排名、隐式指标推断
    4. 多城市检测 → 自动走聚合对比
    5. 聚合/维度/图表检测
    6. 意图分类 → SQL_QUERY / RAG_RETRIEVAL / CLARIFY
    7. 缺失槽位检测 → SQL_QUERY 路径下检查是否缺少关键信息
    8. 表路由策略 → 根据槽位组合选择最优数据表
    """
    slots = {}

    # ── 步骤1：域外问题判断 ──
    if not _check_domain(question):
        return QuestionParseResult(
            intent=IntentType.OUT_OF_DOMAIN,
            slots={},
            original_question=question,
        )

    # ── 步骤2：槽位提取 ──
    _extract_city(question, slots)
    _extract_time(question, slots)
    _extract_metric(question, slots)
    _extract_category(question, slots)

    # ── 步骤3：特殊意图检测 ──
    _detect_product_rank(question, slots)
    _infer_implicit_metric(question, slots)

    # ── 步骤4：指标 → 建议查询表（商品排名的 table_hint 优先级更高，不覆盖） ──
    _apply_metric_table_hint(slots)

    # ── 步骤5：多城市检测 ──
    mentioned_cities = _detect_multi_city(question, slots)
    has_multi_city = len(mentioned_cities) >= 2

    # ── 步骤6：聚合/维度/图表检测 ──
    is_aggregate = _detect_aggregate_and_dimension(question, slots, has_multi_city)
    need_chart, chart_type_hint = _detect_chart_request(question)

    # ── 步骤7：意图分类 ──
    intent = _classify_intent(question, slots, is_aggregate, mentioned_cities)

    # CLARIFY 意图：构建澄清结果并提前返回
    if intent == IntentType.CLARIFY:
        return _build_clarify_result(question, slots, intent)

    # ── 步骤8：SQL_QUERY 路径下的缺失槽位检测 ──
    # 仅非聚合、非多城市对比的 SQL 查询路径做缺失检测
    if intent == IntentType.SQL_QUERY and not is_aggregate and not slots.get("is_aggregate"):
        critical_missing, suggested_missing = _detect_missing_slots(question, slots)
        # "强制缺失项"触发澄清
        if critical_missing:
            return QuestionParseResult(
                intent=IntentType.CLARIFY,
                slots={"missing": critical_missing, "partial": slots},
                original_question=question,
            )
        # 有"建议缺失项"时，标记给下游自动填充默认值
        if suggested_missing:
            slots["_use_default_time"] = True

    # ── 步骤9：标记传播 ──
    if is_aggregate and intent == IntentType.SQL_QUERY:
        slots["is_aggregate"] = True
    if need_chart and intent == IntentType.SQL_QUERY:
        slots["need_chart"] = True

    # ── 步骤10：表路由策略 ──
    _apply_table_routing(question, slots, is_aggregate, chart_type_hint)

    return QuestionParseResult(
        intent=intent,
        slots=slots,
        original_question=question,
    )
