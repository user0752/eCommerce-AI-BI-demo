-- 用户认证表迁移脚本
-- 创建 users 表，支持管理员和普通用户角色

CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    `password_hash` VARCHAR(255) NOT NULL COMMENT 'bcrypt加密密码',
    `role` VARCHAR(20) NOT NULL DEFAULT 'user' COMMENT '角色: admin / user',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `last_login_at` TIMESTAMP NULL COMMENT '最后登录时间',
    INDEX `idx_username` (`username`),
    INDEX `idx_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户认证表';
