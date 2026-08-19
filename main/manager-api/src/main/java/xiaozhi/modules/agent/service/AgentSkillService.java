package xiaozhi.modules.agent.service;

import java.io.IOException;
import java.util.List;
import java.util.Map;

import org.springframework.web.multipart.MultipartFile;

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

    /**
     * 上传技能文件夹(按 agent 维度落盘到共享卷, 并写/更新技能元数据)
     */
    void uploadSkillFolder(String agentId, Long userId, List<MultipartFile> files) throws IOException;

    /**
     * 删除指定技能(删元数据 + 删磁盘目录)
     */
    void deleteSkillById(String agentId, String skillId);
}
