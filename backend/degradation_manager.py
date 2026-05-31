"""
降级策略管理器

职责：
  - 统一管理所有降级策略，按优先级依次执行
  - 提供统一的降级流程入口
  - 支持动态添加/移除策略

设计原则：
  - 责任链模式：策略按顺序执行，任一策略成功则终止
  - 管理器只负责编排，不参与具体降级逻辑
"""
from typing import List, Generator, Optional, Any
from dataclasses import dataclass

from degradation_strategies import (
    DegradationStrategy,
    DegradationContext,
    DegradationResult,
    DegradationLevel,
    Level1RemoveTimeStrategy,
    Level2RemoveCityStrategy,
    Level3SwitchAISStrategy,
    Level4RAGFallbackStrategy,
)


@dataclass
class DegradationExecutionReport:
    """降级执行报告"""
    final_level: DegradationLevel
    success: bool
    strategies_attempted: List[str]
    strategies_succeeded: List[str]
    thinking_text: str


class DegradationStrategyManager:
    """降级策略管理器
    
    按优先级依次执行降级策略，任一策略成功则终止流程。
    """
    
    def __init__(self, strategies: Optional[List[DegradationStrategy]] = None):
        """初始化管理器
        
        Args:
            strategies: 自定义策略列表，为空时使用默认四级策略
        """
        if strategies is None:
            self.strategies = [
                Level1RemoveTimeStrategy(),
                Level2RemoveCityStrategy(),
                Level3SwitchAISStrategy(),
                Level4RAGFallbackStrategy(),
            ]
        else:
            self.strategies = strategies
    
    def add_strategy(self, strategy: DegradationStrategy, position: Optional[int] = None):
        """添加策略
        
        Args:
            strategy: 要添加的策略
            position: 插入位置，为空时添加到末尾
        """
        if position is None:
            self.strategies.append(strategy)
        else:
            self.strategies.insert(position, strategy)
    
    def remove_strategy(self, level: DegradationLevel) -> bool:
        """移除指定级别的策略
        
        Args:
            level: 要移除的策略级别
            
        Returns:
            bool: 是否成功移除
        """
        for i, strategy in enumerate(self.strategies):
            if strategy.level == level:
                self.strategies.pop(i)
                return True
        return False
    
    def execute(self, context: DegradationContext) -> Generator[DegradationResult, None, None]:
        """执行降级流程
        
        按策略顺序依次尝试，任一策略成功则终止。
        
        Args:
            context: 降级上下文
            
        Yields:
            DegradationResult: 每个策略的执行结果
        """
        for strategy in self.strategies:
            if not strategy.can_execute(context):
                continue
            
            result = None
            for partial_result in strategy.execute(context):
                result = partial_result
                yield partial_result
            
            if result and result.success:
                return
    
    def execute_with_report(self, context: DegradationContext) -> Generator[DegradationResult, None, DegradationExecutionReport]:
        """执行降级流程并返回执行报告
        
        Args:
            context: 降级上下文
            
        Yields:
            DegradationResult: 每个策略的执行结果
            
        Returns:
            DegradationExecutionReport: 执行报告
        """
        strategies_attempted = []
        strategies_succeeded = []
        final_result = None
        thinking_text = context.thinking_text
        
        for strategy in self.strategies:
            if not strategy.can_execute(context):
                continue
            
            strategies_attempted.append(strategy.name)
            result = None
            
            for partial_result in strategy.execute(context):
                result = partial_result
                thinking_text = partial_result.thinking_text
                yield partial_result
            
            if result and result.success:
                strategies_succeeded.append(strategy.name)
                final_result = result
                break
        
        return DegradationExecutionReport(
            final_level=final_result.level if final_result else DegradationLevel.NONE,
            success=bool(strategies_succeeded),
            strategies_attempted=strategies_attempted,
            strategies_succeeded=strategies_succeeded,
            thinking_text=thinking_text
        )
    
    def get_strategy_by_level(self, level: DegradationLevel) -> Optional[DegradationStrategy]:
        """根据级别获取策略
        
        Args:
            level: 策略级别
            
        Returns:
            Optional[DegradationStrategy]: 对应的策略，不存在时返回 None
        """
        for strategy in self.strategies:
            if strategy.level == level:
                return strategy
        return None
    
    def list_strategies(self) -> List[str]:
        """列出所有策略名称"""
        return [f"[{s.level.value}] {s.name}" for s in self.strategies]


def create_degradation_context(
    question: str,
    slots: dict,
    original_table: str,
    executor: Any,
    thinking_text: str,
    parse_result: Any = None
) -> DegradationContext:
    """创建降级上下文的便捷函数
    
    Args:
        question: 用户原始问题
        slots: 槽位信息
        original_table: 原始查询表名
        executor: SQL 执行器
        thinking_text: 思考过程文本
        parse_result: 解析结果
        
    Returns:
        DegradationContext: 降级上下文
    """
    original_city = slots.get("city", "")
    is_non_covered = slots.get("_non_covered_city", False)
    
    return DegradationContext(
        question=question,
        slots=slots,
        original_table=original_table,
        executor=executor,
        thinking_text=thinking_text,
        original_city=original_city,
        is_non_covered=is_non_covered,
        parse_result=parse_result
    )