package xiaozhi.modules.agent.service.impl;

import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.repository.IRepository;
import com.fasterxml.jackson.core.type.TypeReference;

import lombok.AllArgsConstructor;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.agent.dao.AgentSkillDao;
import xiaozhi.modules.agent.dto.AgentUpdateDTO.AgentSkillItem;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.entity.AgentSkillEntity;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.agent.service.AgentSkillService;
import xiaozhi.modules.device.service.DeviceService;

@Service
@AllArgsConstructor
public class AgentSkillServiceImpl extends BaseServiceImpl<AgentSkillDao, AgentSkillEntity> implements AgentSkillService {

    private final DeviceService deviceService;
    private final AgentService agentService;

    @Override
    public List<AgentSkillEntity> getByAgentId(String agentId) {
        return baseDao.selectList(new QueryWrapper<AgentSkillEntity>().eq("agent_id", agentId).orderByAsc("sort"));
    }

    @Override
    public void saveOrUpdateByAgentId(String agentId, List<AgentSkillItem> items, Long userId) {
        if (items == null) {
            return;
        }
        // 收集本次提交的 id
        List<String> newIds = items.stream()
                .map(AgentSkillItem::getId)
                .filter(StringUtils::isNotBlank)
                .toList();

        // 查询现有
        List<AgentSkillEntity> existing = getByAgentId(agentId);
        Map<String, AgentSkillEntity> existMap = new HashMap<>();
        existing.forEach(e -> existMap.put(e.getId(), e));

        Date now = new Date();
        List<AgentSkillEntity> toInsert = new ArrayList<>();
        List<AgentSkillEntity> toUpdate = new ArrayList<>();
        for (AgentSkillItem item : items) {
            AgentSkillEntity entity = toEntity(item, agentId);
            AgentSkillEntity old = StringUtils.isNotBlank(item.getId()) ? existMap.get(item.getId()) : null;
            if (old != null) {
                entity.setId(old.getId());
                entity.setCreatedAt(old.getCreatedAt());
                entity.setCreator(old.getCreator());
                entity.setUpdatedAt(now);
                entity.setUpdater(userId);
                toUpdate.add(entity);
            } else {
                entity.setCreatedAt(now);
                entity.setCreator(userId);
                entity.setUpdatedAt(now);
                entity.setUpdater(userId);
                toInsert.add(entity);
            }
        }

        if (!toUpdate.isEmpty()) {
            updateBatchById(toUpdate, IRepository.DEFAULT_BATCH_SIZE);
        }
        if (!toInsert.isEmpty()) {
            insertBatch(toInsert, IRepository.DEFAULT_BATCH_SIZE);
        }

        // 删除本次未提交的
        List<String> toDelete = existing.stream()
                .filter(old -> !newIds.contains(old.getId()))
                .map(AgentSkillEntity::getId)
                .toList();
        if (!toDelete.isEmpty()) {
            deleteBatchIds(toDelete);
        }
    }

    @Override
    public Map<String, Object> getSkillsDefinitionsForDevice(String macAddress, String clientId) {
        Map<String, Object> result = new HashMap<>();
        result.put("skills_definitions", new ArrayList<>());
        String agentId = resolveAgentId(macAddress, clientId);
        if (StringUtils.isBlank(agentId)) {
            return result;
        }

        List<AgentSkillEntity> enabled = baseDao.selectList(
                new QueryWrapper<AgentSkillEntity>().eq("agent_id", agentId).eq("enabled", 1).orderByAsc("sort"));

        List<Map<String, Object>> definitions = new ArrayList<>();
        for (AgentSkillEntity e : enabled) {
            Map<String, Object> def = new HashMap<>();
            def.put("id", e.getId());
            def.put("name", e.getSkillName());
            def.put("description", e.getDescription());
            def.put("content", e.getContent());
            def.put("functions", parseJsonList(e.getFunctions()));
            def.put("files", parseJsonMap(e.getFiles()));
            definitions.add(def);
        }
        result.put("skills_definitions", definitions);

        AgentEntity agent = agentService.getAgentById(agentId);
        if (agent != null && StringUtils.isNotBlank(agent.getSandboxConfig())) {
            try {
                result.put("sandbox", JsonUtils.parseMap(agent.getSandboxConfig()));
            } catch (Exception ignored) {
                // 沙箱配置非法时忽略
            }
        }
        return result;
    }

    @Override
    public void deleteByAgentId(String agentId) {
        baseDao.delete(new QueryWrapper<AgentSkillEntity>().eq("agent_id", agentId));
    }

    private AgentSkillEntity toEntity(AgentSkillItem item, String agentId) {
        AgentSkillEntity entity = new AgentSkillEntity();
        entity.setAgentId(agentId);
        entity.setSkillName(item.getSkillName());
        entity.setDescription(item.getDescription());
        entity.setContent(item.getContent());
        entity.setFunctions(item.getFunctions() == null ? null : JsonUtils.toJsonString(item.getFunctions()));
        entity.setFiles(item.getFiles() == null ? null : JsonUtils.toJsonString(item.getFiles()));
        entity.setEnabled(item.getEnabled() != null && item.getEnabled() ? 1 : 0);
        entity.setSort(item.getSort() == null ? 0 : item.getSort());
        return entity;
    }

    private String resolveAgentId(String macAddress, String clientId) {
        if (StringUtils.isBlank(macAddress)) {
            return null;
        }
        try {
            var device = deviceService.getDeviceByMacAddress(macAddress);
            if (device == null || StringUtils.isBlank(device.getAgentId())) {
                return null;
            }
            return device.getAgentId();
        } catch (RenException e) {
            return null;
        }
    }

    private List<String> parseJsonList(String json) {
        if (StringUtils.isBlank(json)) {
            return new ArrayList<>();
        }
        try {
            return JsonUtils.parseObject(json, new TypeReference<List<String>>() {
            });
        } catch (Exception e) {
            return new ArrayList<>();
        }
    }

    private Map<String, String> parseJsonMap(String json) {
        if (StringUtils.isBlank(json)) {
            return new HashMap<>();
        }
        try {
            return JsonUtils.parseObject(json, new TypeReference<Map<String, String>>() {
            });
        } catch (Exception e) {
            return new HashMap<>();
        }
    }
}
