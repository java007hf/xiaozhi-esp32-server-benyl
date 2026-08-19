-- 角色级技能配置表
CREATE TABLE `ai_agent_skill` (
  `id` VARCHAR(32) NOT NULL,
  `agent_id` VARCHAR(32) NOT NULL,
  `skill_name` VARCHAR(64) NOT NULL COMMENT '技能名(对应SKILL.md frontmatter name)',
  `description` VARCHAR(512) DEFAULT NULL COMMENT '技能描述',
  `content` MEDIUMTEXT COMMENT '完整 SKILL.md(含YAML frontmatter)',
  `functions` VARCHAR(1024) DEFAULT NULL COMMENT 'JSON数组: 绑定的函数名',
  `files` MEDIUMTEXT COMMENT 'JSON对象: 相对路径->文件内容(in-memory技能用)',
  `enabled` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  `sort` INT DEFAULT 0,
  `creator` BIGINT DEFAULT NULL,
  `created_at` DATETIME DEFAULT NULL,
  `updater` BIGINT DEFAULT NULL,
  `updated_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_agent_skill_agent` (`agent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体技能配置';

-- 角色级MCP服务配置表
CREATE TABLE `ai_agent_mcp_server` (
  `id` VARCHAR(32) NOT NULL,
  `agent_id` VARCHAR(32) NOT NULL,
  `server_name` VARCHAR(64) NOT NULL COMMENT 'MCP服务名',
  `transport` VARCHAR(32) NOT NULL DEFAULT 'stdio' COMMENT 'stdio|sse|streamable-http',
  `command` VARCHAR(512) DEFAULT NULL COMMENT 'stdio启动命令',
  `args` VARCHAR(1024) DEFAULT NULL COMMENT 'JSON数组: 启动参数',
  `url` VARCHAR(512) DEFAULT NULL COMMENT 'sse/streamable-http地址',
  `env` MEDIUMTEXT COMMENT 'JSON对象: 环境变量',
  `headers` MEDIUMTEXT COMMENT 'JSON对象: 请求头',
  `enabled` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  `sort` INT DEFAULT 0,
  `creator` BIGINT DEFAULT NULL,
  `created_at` DATETIME DEFAULT NULL,
  `updater` BIGINT DEFAULT NULL,
  `updated_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_agent_mcp_agent` (`agent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体MCP服务配置';

-- 角色级沙箱配置列
ALTER TABLE `ai_agent` ADD COLUMN `sandbox_config` MEDIUMTEXT DEFAULT NULL COMMENT 'JSON: 技能沙箱运行配置' AFTER `sort`;
