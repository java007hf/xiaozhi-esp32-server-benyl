-- 智能体 MCP 配置(JSON, 标准 mcpServers 格式)
ALTER TABLE `ai_agent` ADD COLUMN `mcp_config` MEDIUMTEXT DEFAULT NULL COMMENT 'MCP服务配置(JSON, 标准 mcpServers 格式)' AFTER `sandbox_config`;
