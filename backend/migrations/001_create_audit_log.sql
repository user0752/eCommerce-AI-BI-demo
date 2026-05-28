-- ============================================================
-- 审计日志表
-- 用于记录所有 AI 查询请求，支持数据围栏可视化和知识闭环管理
-- ============================================================
CREATE TABLE IF NOT EXISTS `ai_audit_log` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `query_text` TEXT CHARACTER SET utf8mb4 COMMENT '用户原始问题',
    `intent` VARCHAR(50) COMMENT '识别意图 (sql_query/rag_retrieval/clarify/out_of_domain)',
    `tool_used` VARCHAR(50) COMMENT '使用的工具 (sql/rag/clarify)',
    `status` VARCHAR(20) COMMENT '处理状态 (success/fallback/clarify)',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '查询时间',
    INDEX `idx_status` (`status`),
    INDEX `idx_intent` (`intent`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI查询审计日志表';
