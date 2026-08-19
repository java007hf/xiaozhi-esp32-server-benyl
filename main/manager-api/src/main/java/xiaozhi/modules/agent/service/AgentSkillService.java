package xiaozhi.modules.agent.service;

import java.util.List;
import java.util.Map;

import xiaozhi.common.service.BaseService;
import xiaozhi.modules.agent.dto.AgentUpdateDTO.AgentSkillItem;
import xiaozhi.modules.agent.entity.AgentSkillEntity;

public interface AgentSkillService extends BaseService<AgentSkillEntity> {

    /**
     * 根据智能体ID获取技能配置列表
     */
    List<AgentSkillEntity> getByAgentId(String agentId);

    /**
     * 对账保存角色级技能配置(插入新的、更新已有的、删除未提交的)
     */
    void saveOrUpdateByAgentId(String agentId, List<AgentSkillItem> items, Long userId);

    /**
     * 供 Python 服务端下发: 返回启用的技能定义与沙箱配置
     */
    Map<String, Object> getSkillsDefinitionsForDevice(String macAddress, String clientId);

    /**
     * 根据智能体ID级联删除
     */
    void deleteByAgentId(String agentId);
}
