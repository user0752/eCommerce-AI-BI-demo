"""
降级策略模块

职责：
  - 使用策略模式重构四级降级逻辑，每个降级策略封装为独立类
  - 降低代码嵌套深度，提高可维护性和可测试性
  - 支持灵活扩展新的降级策略

设计原则：
  - 每个策略类只负责一个降级级别的逻辑
  - 策略之间通过责任链模式串联，按优先级依次尝试
  - 策略执行结果统一封装为 DegradationResult
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generator, Optional, Any, Dict
from enum import Enum
import pandas as pd


class DegradationLevel(Enum):
    """降级级别枚举"""
    NONE = 0
    LEVEL_1_REMOVE_TIME = 1
    LEVEL_2_REMOVE_CITY = 2
    LEVEL_3_SWITCH_AIS = 3
    LEVEL_4_RAG_FALLBACK = 4


@dataclass
class DegradationContext:
    """降级上下文：包含降级过程中需要的所有信息"""
    question: str
    slots: Dict[str, Any]
    original_table: str
    executor: Any
    thinking_text: str
    original_city: str = ""
    is_non_covered: bool = False
    parse_result: Any = None


@dataclass
class DegradationResult:
    """降级执行结果"""
    success: bool
    level: DegradationLevel
    thinking_text: str
    executor: Optional[Any] = None
    table_name: Optional[str] = None
    sql_result: Optional[pd.DataFrame] = None
    hint_message: Optional[str] = None
    should_continue: bool = True


class DegradationStrategy(ABC):
    """降级策略抽象基类
    
    所有降级策略必须实现 can_execute 和 execute 方法。
    """
    
    @property
    @abstractmethod
    def level(self) -> DegradationLevel:
        """返回策略对应的降级级别"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """返回策略名称（用于日志和调试）"""
        pass
    
    @abstractmethod
    def can_execute(self, context: DegradationContext) -> bool:
        """判断当前策略是否可以执行
        
        Args:
            context: 降级上下文
            
        Returns:
            bool: 是否可以执行该策略
        """
        pass
    
    @abstractmethod
    def execute(self, context: DegradationContext) -> Generator[DegradationResult, None, None]:
        """执行降级策略
        
        Args:
            context: 降级上下文
            
        Yields:
            DegradationResult: 降级执行结果
        """
        pass
    
    def _build_degraded_parse_result(self, slots: Dict[str, Any], question: str):
        """构建降级后的解析结果"""
        from intent_parser import QuestionParseResult
        return QuestionParseResult(
            intent="sql_query",
            slots=slots,
            original_question=question
        )


class Level1RemoveTimeStrategy(DegradationStrategy):
    """Level 1 降级策略：去除时间限制，查询全部历史数据"""
    
    @property
    def level(self) -> DegradationLevel:
        return DegradationLevel.LEVEL_1_REMOVE_TIME
    
    @property
    def name(self) -> str:
        return "去除时间限制"
    
    def can_execute(self, context: DegradationContext) -> bool:
        return context.slots.get("time") is not None
    
    def execute(self, context: DegradationContext) -> Generator[DegradationResult, None, None]:
        original_time = context.slots.get("time", "")
        thinking_text = context.thinking_text + "  ├─ Level 1：移除时间限制，查询全部历史数据...\n"
        yield DegradationResult(
            success=False,
            level=self.level,
            thinking_text=thinking_text,
            should_continue=True
        )
        
        slots_without_time = {
            k: v for k, v in context.slots.items()
            if k != "time" and not k.startswith("_")
        }
        degraded_pr = self._build_degraded_parse_result(slots_without_time, context.question)
        
        try:
            sql_degraded, params_degraded = context.executor.generate_sql(degraded_pr)
            if sql_degraded is not None:
                sql_result_degraded = context.executor.execute_sql(sql_degraded, params_degraded)
                if not sql_result_degraded.empty:
                    thinking_text += "  └─ ✅ Level 1 降级成功 | 🤖 AI 生成回答中...\n"
                    time_hint = f"您指定的时间「{original_time}」不在数据库覆盖范围内" if original_time else "指定时间范围内无数据"
                    hint_message = (
                        f"\n\n💡 **降级提示（Level 1 - 去除时间限制）**：{time_hint}，"
                        f"已自动查询全部历史数据。数据库当前覆盖时间为**2025年1-12月**。"
                    )
                    yield DegradationResult(
                        success=True,
                        level=self.level,
                        thinking_text=thinking_text,
                        executor=context.executor,
                        table_name=context.original_table,
                        sql_result=sql_result_degraded,
                        hint_message=hint_message,
                        should_continue=False
                    )
                    return
        except Exception:
            pass
        
        yield DegradationResult(
            success=False,
            level=self.level,
            thinking_text=thinking_text,
            should_continue=True
        )


class Level2RemoveCityStrategy(DegradationStrategy):
    """Level 2 降级策略：去除城市限制，查询全省聚合数据"""
    
    @property
    def level(self) -> DegradationLevel:
        return DegradationLevel.LEVEL_2_REMOVE_CITY
    
    @property
    def name(self) -> str:
        return "去除城市限制"
    
    def can_execute(self, context: DegradationContext) -> bool:
        city = context.slots.get("city")
        return city is not None and city != "ALL_CITIES"
    
    def execute(self, context: DegradationContext) -> Generator[DegradationResult, None, None]:
        thinking_text = context.thinking_text + "  ├─ Level 2：移除城市限制，查询全省聚合数据...\n"
        yield DegradationResult(
            success=False,
            level=self.level,
            thinking_text=thinking_text,
            should_continue=True
        )
        
        slots_province_aggregate = {
            k: v for k, v in context.slots.items()
            if k != "time" and k != "city" and not k.startswith("_")
        }
        slots_province_aggregate["city"] = "ALL_CITIES"
        slots_province_aggregate["is_aggregate"] = True
        degraded_pr = self._build_degraded_parse_result(slots_province_aggregate, context.question)
        
        try:
            sql_degraded, params_degraded = context.executor.generate_sql(degraded_pr)
            if sql_degraded is not None:
                sql_result_degraded = context.executor.execute_sql(sql_degraded, params_degraded)
                if not sql_result_degraded.empty:
                    thinking_text += "  └─ ✅ Level 2 降级成功 | 🤖 AI 生成回答中...\n"
                    
                    if context.is_non_covered:
                        city_display = context.original_city
                        hint_message = (
                            f"\n\n💡 **降级提示（Level 2 - 去除城市限制）**："
                            f"您查询的地区「{city_display}」不在系统覆盖范围内，"
                            f"当前系统仅覆盖**贵州省9个市州**（贵阳、遵义、六盘水、毕节、铜仁、安顺、黔东南、黔南、黔西南）。"
                            f"已为您展示**贵州省整体数据**作为参考。"
                        )
                    else:
                        city_display = context.original_city.replace("市", "").replace("州", "")
                        hint_message = (
                            f"\n\n💡 **降级提示（Level 2 - 去除城市限制）**："
                            f"「{city_display}」在当前数据表中未找到匹配记录，"
                            f"已为您展示**贵州省整体数据**作为参考。"
                            f"如需查看具体城市数据，可尝试：\"贵阳的销售额\"、\"遵义的消费趋势\""
                        )
                    
                    yield DegradationResult(
                        success=True,
                        level=self.level,
                        thinking_text=thinking_text,
                        executor=context.executor,
                        table_name=context.original_table,
                        sql_result=sql_result_degraded,
                        hint_message=hint_message,
                        should_continue=False
                    )
                    return
        except Exception:
            pass
        
        yield DegradationResult(
            success=False,
            level=self.level,
            thinking_text=thinking_text,
            should_continue=True
        )


class Level3SwitchAISStrategy(DegradationStrategy):
    """Level 3 降级策略：切换到 AIS 预聚合表查询"""
    
    @property
    def level(self) -> DegradationLevel:
        return DegradationLevel.LEVEL_3_SWITCH_AIS
    
    @property
    def name(self) -> str:
        return "切换预聚合表"
    
    def can_execute(self, context: DegradationContext) -> bool:
        return True
    
    def _select_ais_table(self, context: DegradationContext) -> Optional[str]:
        """智能选择 AIS 预聚合表"""
        question = context.question.lower()
        slots = context.slots
        
        if slots.get("category") or any(kw in question for kw in ["品类", "类型", "结构"]):
            if slots.get("city") and slots["city"] != "ALL_CITIES" and not context.is_non_covered:
                return "ais_city_category_summary"
            else:
                return "ais_category_monthly_summary"
        
        if any(kw in question for kw in ["趋势", "月度", "走势", "按月"]):
            return "ais_city_monthly_summary"
        
        if slots.get("city") and slots["city"] != "ALL_CITIES" and not context.is_non_covered:
            return "ais_city_monthly_summary"
        
        return "ais_category_monthly_summary"
    
    def execute(self, context: DegradationContext) -> Generator[DegradationResult, None, None]:
        thinking_text = context.thinking_text + "  ├─ Level 3：切换到AIS预聚合表查询...\n"
        yield DegradationResult(
            success=False,
            level=self.level,
            thinking_text=thinking_text,
            executor=context.executor,
            should_continue=True
        )
        
        ais_table = self._select_ais_table(context)
        
        if not ais_table or ais_table == context.original_table:
            yield DegradationResult(
                success=False,
                level=self.level,
                thinking_text=thinking_text,
                executor=context.executor,
                should_continue=True
            )
            return
        
        try:
            from sql_executor import SQLExecutor
            context.executor.close()
            new_executor = SQLExecutor(table_name=ais_table)
            
            slots_ais_degraded = {
                k: v for k, v in context.slots.items()
                if k != "time" and not k.startswith("_")
            }
            if context.is_non_covered:
                slots_ais_degraded["city"] = "ALL_CITIES"
                slots_ais_degraded["is_aggregate"] = True
            
            degraded_pr = self._build_degraded_parse_result(slots_ais_degraded, context.question)
            sql_ais, params_ais = new_executor.generate_sql(degraded_pr)
            
            if sql_ais is not None:
                sql_result_ais = new_executor.execute_sql(sql_ais, params_ais)
                if not sql_result_ais.empty:
                    thinking_text += f"  └─ ✅ Level 3 降级成功，获取到 {len(sql_result_ais)} 条记录 | 🤖 AI 生成回答中...\n"
                    hint_message = (
                        f"\n\n💡 **降级提示（Level 3 - 切换预聚合表）**："
                        f"原表（{context.original_table}）数据不足，已自动切换到预聚合表（{ais_table}）查询。"
                        f"数据粒度可能有所调整，但能为您提供宏观参考。"
                    )
                    yield DegradationResult(
                        success=True,
                        level=self.level,
                        thinking_text=thinking_text,
                        executor=new_executor,
                        table_name=ais_table,
                        sql_result=sql_result_ais,
                        hint_message=hint_message,
                        should_continue=False
                    )
                    return
                else:
                    yield DegradationResult(
                        success=False,
                        level=self.level,
                        thinking_text=thinking_text,
                        executor=new_executor,
                        should_continue=True
                    )
                    return
        except Exception:
            pass
        
        yield DegradationResult(
            success=False,
            level=self.level,
            thinking_text=thinking_text,
            executor=context.executor,
            should_continue=True
        )


class Level4RAGFallbackStrategy(DegradationStrategy):
    """Level 4 降级策略：RAG 知识库兜底"""
    
    @property
    def level(self) -> DegradationLevel:
        return DegradationLevel.LEVEL_4_RAG_FALLBACK
    
    @property
    def name(self) -> str:
        return "RAG知识库兜底"
    
    def can_execute(self, context: DegradationContext) -> bool:
        return True
    
    def execute(self, context: DegradationContext) -> Generator[DegradationResult, None, None]:
        thinking_text = context.thinking_text + "  ├─ Level 4：结构化数据全部无匹配，切换RAG知识库检索...\n"
        yield DegradationResult(
            success=False,
            level=self.level,
            thinking_text=thinking_text,
            should_continue=True
        )
        
        hint_message = (
            "\n\n💡 **降级提示（Level 4 - RAG知识库兜底）**："
            "前三级结构化查询均未找到匹配数据，已切换到知识库检索。\n\n"
            "📊 **数据覆盖范围**：\n"
            "- 🕐 时间范围：**2025年1-12月**\n"
            "- 📍 地区范围：**贵州省9个市州**（贵阳、遵义、六盘水、毕节、铜仁、安顺、黔东南、黔南、黔西南）\n"
            "- 🏷️ 品类范围：**11个品类**（电子数码、家用电器、服饰鞋帽、美妆护肤、食品饮料、酒类、运动户外、母婴用品、家居日用、农产品、旅游文创）\n\n"
            "💡 **建议**：如需精确数据，请调整查询条件后重试，例如：\n"
            "- \"贵阳2025年的销售额是多少？\"\n"
            "- \"各城市消费趋势\"\n"
            "- \"家用电器品类的销量排名\""
        )
        
        yield DegradationResult(
            success=True,
            level=self.level,
            thinking_text=thinking_text,
            hint_message=hint_message,
            should_continue=False,
            sql_result=pd.DataFrame()
        )