"""
结构化数据格式化器

职责：
  - 将 SQL 查询结果（DataFrame）转换为结构化的、带语义标注的数据格式
  - 数值格式化（金额千分位、百分比、小数精度）
  - 列名语义化（中文化、友好命名）
  - 空值/异常值处理
  - 数据类型标注（销售额、销量、用户数等）

设计原则：
  - RAG 与 SQL 完全解耦，SQL 结果经过标准化处理后传给 LLM
  - 格式化后的数据包含语义信息，便于 LLM 理解和生成准确的回答
"""
import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ColumnMeta:
    """列元数据：描述单列数据的语义信息"""
    original_name: str
    friendly_name: str
    data_type: str
    unit: Optional[str] = None
    description: Optional[str] = None
    format_pattern: Optional[str] = None


@dataclass
class FormattedData:
    """格式化后的结构化数据"""
    summary: str
    columns: List[ColumnMeta]
    rows: List[Dict[str, Any]]
    total_rows: int
    data_source: str
    formatted_text: str


FIELD_METADATA: Dict[str, ColumnMeta] = {
    "total_sale_amount": ColumnMeta(
        original_name="total_sale_amount",
        friendly_name="销售额",
        data_type="currency",
        unit="元",
        description="总销售金额（GMV）",
        format_pattern="currency"
    ),
    "total_sale_quantity": ColumnMeta(
        original_name="total_sale_quantity",
        friendly_name="销量",
        data_type="integer",
        unit="件",
        description="售出商品总数量",
        format_pattern="integer"
    ),
    "total_active_user": ColumnMeta(
        original_name="total_active_user",
        friendly_name="活跃用户数",
        data_type="integer",
        unit="人",
        description="活跃用户总数",
        format_pattern="integer"
    ),
    "total_pay_user": ColumnMeta(
        original_name="total_pay_user",
        friendly_name="付费用户数",
        data_type="integer",
        unit="人",
        description="有消费行为的用户数",
        format_pattern="integer"
    ),
    "total_pay_rate": ColumnMeta(
        original_name="total_pay_rate",
        friendly_name="付费率",
        data_type="percentage",
        unit="%",
        description="付费用户占活跃用户的比例",
        format_pattern="percentage"
    ),
    "total_order_count": ColumnMeta(
        original_name="total_order_count",
        friendly_name="订单数",
        data_type="integer",
        unit="单",
        description="成交订单总数",
        format_pattern="integer"
    ),
    "city_avg_order_value": ColumnMeta(
        original_name="city_avg_order_value",
        friendly_name="客单价",
        data_type="currency",
        unit="元",
        description="平均每单消费金额",
        format_pattern="currency"
    ),
    "avg_order_value": ColumnMeta(
        original_name="avg_order_value",
        friendly_name="客单价",
        data_type="currency",
        unit="元",
        description="平均每单消费金额",
        format_pattern="currency"
    ),
    "buy_conversion_rate": ColumnMeta(
        original_name="buy_conversion_rate",
        friendly_name="转化率",
        data_type="percentage",
        unit="%",
        description="浏览到购买的转化比例",
        format_pattern="percentage"
    ),
    "avg_buy_conversion_rate": ColumnMeta(
        original_name="avg_buy_conversion_rate",
        friendly_name="平均转化率",
        data_type="percentage",
        unit="%",
        description="品类平均购买转化率",
        format_pattern="percentage"
    ),
    "avg_product_rating": ColumnMeta(
        original_name="avg_product_rating",
        friendly_name="平均评分",
        data_type="decimal",
        unit="分",
        description="商品平均评分（满分5分）",
        format_pattern="rating"
    ),
    "product_count": ColumnMeta(
        original_name="product_count",
        friendly_name="商品数量",
        data_type="integer",
        unit="个",
        description="该品类下的商品总数",
        format_pattern="integer"
    ),
    "avg_unit_price": ColumnMeta(
        original_name="avg_unit_price",
        friendly_name="平均单价",
        data_type="currency",
        unit="元",
        description="商品平均单价",
        format_pattern="currency"
    ),
    "hot_product_count": ColumnMeta(
        original_name="hot_product_count",
        friendly_name="热销商品数",
        data_type="integer",
        unit="个",
        description="热销商品数量",
        format_pattern="integer"
    ),
    "main_category_avg_price": ColumnMeta(
        original_name="main_category_avg_price",
        friendly_name="主力品类均价",
        data_type="currency",
        unit="元",
        description="主力消费品类的平均价格",
        format_pattern="currency"
    ),
    "total_pv_count": ColumnMeta(
        original_name="total_pv_count",
        friendly_name="浏览量",
        data_type="integer",
        unit="次",
        description="页面浏览总次数",
        format_pattern="integer"
    ),
    "total_fav_count": ColumnMeta(
        original_name="total_fav_count",
        friendly_name="收藏量",
        data_type="integer",
        unit="次",
        description="商品收藏总次数",
        format_pattern="integer"
    ),
    "total_cart_count": ColumnMeta(
        original_name="total_cart_count",
        friendly_name="加购量",
        data_type="integer",
        unit="次",
        description="加入购物车总次数",
        format_pattern="integer"
    ),
    "total_buy_count": ColumnMeta(
        original_name="total_buy_count",
        friendly_name="购买量",
        data_type="integer",
        unit="次",
        description="购买行为总次数",
        format_pattern="integer"
    ),
    "pv_count": ColumnMeta(
        original_name="pv_count",
        friendly_name="浏览量",
        data_type="integer",
        unit="次",
        description="页面浏览次数",
        format_pattern="integer"
    ),
    "fav_count": ColumnMeta(
        original_name="fav_count",
        friendly_name="收藏量",
        data_type="integer",
        unit="次",
        description="收藏次数",
        format_pattern="integer"
    ),
    "cart_count": ColumnMeta(
        original_name="cart_count",
        friendly_name="加购量",
        data_type="integer",
        unit="次",
        description="加购次数",
        format_pattern="integer"
    ),
    "buy_count": ColumnMeta(
        original_name="buy_count",
        friendly_name="购买量",
        data_type="integer",
        unit="次",
        description="购买次数",
        format_pattern="integer"
    ),
    "interaction_score": ColumnMeta(
        original_name="interaction_score",
        friendly_name="交互得分",
        data_type="decimal",
        unit="分",
        description="用户与商品的交互综合得分",
        format_pattern="decimal"
    ),
    "product_rating": ColumnMeta(
        original_name="product_rating",
        friendly_name="商品评分",
        data_type="decimal",
        unit="分",
        description="商品评分（满分5分）",
        format_pattern="rating"
    ),
    "total_consumption": ColumnMeta(
        original_name="total_consumption",
        friendly_name="消费总额",
        data_type="currency",
        unit="元",
        description="用户累计消费金额",
        format_pattern="currency"
    ),
    "repurchase_count": ColumnMeta(
        original_name="repurchase_count",
        friendly_name="复购次数",
        data_type="integer",
        unit="次",
        description="用户重复购买次数",
        format_pattern="integer"
    ),
    "维度": ColumnMeta(
        original_name="维度",
        friendly_name="维度",
        data_type="dimension",
        unit=None,
        description="聚合维度（城市/品类/月份等）",
        format_pattern=None
    ),
    "city_name": ColumnMeta(
        original_name="city_name",
        friendly_name="城市",
        data_type="dimension",
        unit=None,
        description="城市名称",
        format_pattern=None
    ),
    "product_category": ColumnMeta(
        original_name="product_category",
        friendly_name="品类",
        data_type="dimension",
        unit=None,
        description="商品品类名称",
        format_pattern=None
    ),
    "product_name": ColumnMeta(
        original_name="product_name",
        friendly_name="商品名称",
        data_type="dimension",
        unit=None,
        description="商品名称",
        format_pattern=None
    ),
    "product_brand": ColumnMeta(
        original_name="product_brand",
        friendly_name="品牌",
        data_type="dimension",
        unit=None,
        description="商品品牌",
        format_pattern=None
    ),
    "stat_month": ColumnMeta(
        original_name="stat_month",
        friendly_name="统计月份",
        data_type="dimension",
        unit=None,
        description="统计月份（YYYY-MM格式）",
        format_pattern=None
    ),
    "rank_in_category": ColumnMeta(
        original_name="rank_in_category",
        friendly_name="排名",
        data_type="integer",
        unit="名",
        description="在品类内的排名",
        format_pattern="rank"
    ),
    "hot_level": ColumnMeta(
        original_name="hot_level",
        friendly_name="热度等级",
        data_type="dimension",
        unit=None,
        description="热销等级（爆款/热销/普通）",
        format_pattern=None
    ),
}

DIMENSION_FIELDS = {"维度", "city_name", "product_category", "product_name", 
                    "product_brand", "stat_month", "hot_level", "user_id", "product_id"}


class StructuredDataFormatter:
    """结构化数据格式化器
    
    将 SQL 查询结果转换为结构化的、带语义标注的数据格式，
    便于 LLM 理解数据含义并生成准确的回答。
    """
    
    def __init__(self):
        self.field_metadata = FIELD_METADATA
    
    def format(self, df: pd.DataFrame, table_name: str, metric_hint: str = None) -> FormattedData:
        """格式化 DataFrame 为结构化数据
        
        Args:
            df: SQL 查询结果 DataFrame
            table_name: 数据来源表名
            metric_hint: 用户查询的主要指标（用于生成摘要）
            
        Returns:
            FormattedData: 格式化后的结构化数据
        """
        if df.empty:
            return self._format_empty_result(table_name)
        
        columns = self._extract_column_metadata(df.columns)
        rows = self._format_rows(df, columns)
        summary = self._generate_summary(df, columns, metric_hint)
        formatted_text = self._build_formatted_text(summary, columns, rows, table_name)
        
        return FormattedData(
            summary=summary,
            columns=columns,
            rows=rows,
            total_rows=len(rows),
            data_source=table_name,
            formatted_text=formatted_text
        )
    
    def _format_empty_result(self, table_name: str) -> FormattedData:
        """格式化空结果"""
        return FormattedData(
            summary="查询结果为空，未找到匹配数据",
            columns=[],
            rows=[],
            total_rows=0,
            data_source=table_name,
            formatted_text="【查询结果】：无数据\n【数据来源】：{table_name}"
        )
    
    def _extract_column_metadata(self, column_names: List[str]) -> List[ColumnMeta]:
        """提取列元数据"""
        columns = []
        for col in column_names:
            if col in self.field_metadata:
                columns.append(self.field_metadata[col])
            else:
                columns.append(ColumnMeta(
                    original_name=col,
                    friendly_name=col,
                    data_type="unknown",
                    unit=None,
                    description=None,
                    format_pattern=None
                ))
        return columns
    
    def _format_rows(self, df: pd.DataFrame, columns: List[ColumnMeta]) -> List[Dict[str, Any]]:
        """格式化每一行数据"""
        rows = []
        for idx, row in df.iterrows():
            formatted_row = {}
            for col_meta in columns:
                original_name = col_meta.original_name
                value = row.get(original_name)
                
                if pd.isna(value) or value is None:
                    formatted_row[original_name] = {"raw": None, "display": "无数据", "type": "null"}
                else:
                    formatted_value = self._format_value(value, col_meta)
                    formatted_row[original_name] = formatted_value
            rows.append(formatted_row)
        return rows
    
    def _format_value(self, value: Any, col_meta: ColumnMeta) -> Dict[str, Any]:
        """格式化单个值"""
        raw_value = value
        display_value = str(value)
        
        if col_meta.format_pattern == "currency":
            try:
                num_value = float(value)
                if num_value >= 10000:
                    display_value = f"{num_value/10000:.2f}万元"
                else:
                    display_value = f"{num_value:,.2f}元"
            except (ValueError, TypeError):
                pass
        
        elif col_meta.format_pattern == "percentage":
            try:
                num_value = float(value)
                display_value = f"{num_value:.2f}%"
            except (ValueError, TypeError):
                pass
        
        elif col_meta.format_pattern == "integer":
            try:
                num_value = int(value)
                display_value = f"{num_value:,}{col_meta.unit or ''}"
            except (ValueError, TypeError):
                pass
        
        elif col_meta.format_pattern == "rating":
            try:
                num_value = float(value)
                display_value = f"{num_value:.1f}分"
            except (ValueError, TypeError):
                pass
        
        elif col_meta.format_pattern == "decimal":
            try:
                num_value = float(value)
                display_value = f"{num_value:.2f}"
            except (ValueError, TypeError):
                pass
        
        elif col_meta.format_pattern == "rank":
            try:
                num_value = int(value)
                display_value = f"第{num_value}名"
            except (ValueError, TypeError):
                pass
        
        return {
            "raw": raw_value,
            "display": display_value,
            "type": col_meta.data_type,
            "unit": col_meta.unit,
            "description": col_meta.description
        }
    
    def _generate_summary(self, df: pd.DataFrame, columns: List[ColumnMeta], 
                          metric_hint: str = None) -> str:
        """生成数据摘要"""
        summary_parts = []
        
        summary_parts.append(f"查询返回 {len(df)} 条数据记录。")
        
        metric_columns = [c for c in columns if c.data_type not in ("dimension", "unknown", "null")]
        if metric_columns:
            metric_names = [c.friendly_name for c in metric_columns[:5]]
            summary_parts.append(f"包含指标：{', '.join(metric_names)}。")
        
        dim_columns = [c for c in columns if c.data_type == "dimension"]
        if dim_columns:
            dim_names = [c.friendly_name for c in dim_columns[:3]]
            summary_parts.append(f"维度字段：{', '.join(dim_names)}。")
        
        if metric_hint and metric_columns:
            primary_metric = self._find_primary_metric(metric_columns, metric_hint)
            if primary_metric and len(df) > 0:
                try:
                    col_name = primary_metric.original_name
                    values = df[col_name].dropna()
                    if len(values) > 0:
                        total = values.sum() if primary_metric.data_type in ("integer", "currency") else values.mean()
                        formatted_total = self._format_value(total, primary_metric)["display"]
                        summary_parts.append(f"{primary_metric.friendly_name}汇总：{formatted_total}。")
                except Exception:
                    pass
        
        return "".join(summary_parts)
    
    def _find_primary_metric(self, metric_columns: List[ColumnMeta], metric_hint: str) -> Optional[ColumnMeta]:
        """根据用户查询的指标提示找到主要指标列"""
        metric_hint_lower = metric_hint.lower()
        for col in metric_columns:
            if col.friendly_name.lower() in metric_hint_lower or metric_hint_lower in col.friendly_name.lower():
                return col
            if col.original_name.lower() in metric_hint_lower:
                return col
        return metric_columns[0] if metric_columns else None
    
    def _build_formatted_text(self, summary: str, columns: List[ColumnMeta], 
                               rows: List[Dict[str, Any]], table_name: str) -> str:
        """构建格式化文本，用于传给 LLM"""
        text_parts = []
        
        text_parts.append("【数据摘要】")
        text_parts.append(summary)
        text_parts.append("")
        
        text_parts.append("【字段说明】")
        for col in columns:
            if col.description:
                text_parts.append(f"- {col.friendly_name}（{col.original_name}）：{col.description}")
            else:
                text_parts.append(f"- {col.friendly_name}（{col.original_name}）")
        text_parts.append("")
        
        text_parts.append("【数据详情】")
        for idx, row in enumerate(rows[:20], 1):
            row_parts = []
            for col in columns:
                field_data = row.get(col.original_name, {})
                display = field_data.get("display", "无数据")
                row_parts.append(f"{col.friendly_name}={display}")
            text_parts.append(f"第{idx}条：{', '.join(row_parts)}")
        
        if len(rows) > 20:
            text_parts.append(f"... 共 {len(rows)} 条数据，仅展示前20条")
        
        text_parts.append("")
        text_parts.append(f"【数据来源】：{table_name}")
        
        return "\n".join(text_parts)
    
    def to_llm_context(self, formatted_data: FormattedData) -> str:
        """转换为 LLM 可理解的上下文文本
        
        这是传给 LLM 的最终格式，包含：
        - 数据摘要（便于快速理解）
        - 字段语义说明（便于理解每个字段的含义）
        - 格式化后的数据行（便于引用具体数值）
        """
        return formatted_data.formatted_text