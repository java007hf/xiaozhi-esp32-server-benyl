package xiaozhi.modules.agent.service;

import java.util.List;
import java.util.Map;

import xiaozhi.common.service.BaseService;
import xiaozhi.modules.agent.dto.AgentUpdateDTO.AgentMcpServerItem;
import xiaozhi.modules.agent.entity.AgentMcpServerEntity;

public interface AgentMcpServerService extends BaseService<AgentMcpServerEntity> {

    /**
     * 根据智能体ID获取MCP服务配置列表
     */
    List<AgentMcpServerEntity> getByAgentId(String agentId);

    /**
     * 对账保存角色级MCP服务配置(插入新的、更新已有的、删除未提交的)
     */
    void saveOrUpdateByAgentId(String agentId, List<AgentMcpServerItem> items, Long userId);

    /**
     * 供 Python 服务端下发: 返回启用的 MCP 服务配置
     */
    Map<String, Object> getMcpServersForDevice(String macAddress, String clientId);

    /**
     * 根据智能体ID级联删除
     */
    void deleteByAgentId(String agentId);
}
