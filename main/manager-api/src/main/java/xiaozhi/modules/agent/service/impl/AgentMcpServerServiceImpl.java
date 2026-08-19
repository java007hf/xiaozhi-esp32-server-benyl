package xiaozhi.modules.agent.service.impl;

import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.repository.IRepository;
import com.fasterxml.jackson.core.type.TypeReference;

import lombok.AllArgsConstructor;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.agent.dao.AgentMcpServerDao;
import xiaozhi.modules.agent.dto.AgentUpdateDTO.AgentMcpServerItem;
import xiaozhi.modules.agent.entity.AgentMcpServerEntity;
import xiaozhi.modules.agent.service.AgentMcpServerService;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.device.service.DeviceService;

@Service
@AllArgsConstructor
public class AgentMcpServerServiceImpl extends BaseServiceImpl<AgentMcpServerDao, AgentMcpServerEntity> implements AgentMcpServerService {

    private final DeviceService deviceService;
    private final AgentService agentService;

    @Override
    public List<AgentMcpServerEntity> getByAgentId(String agentId) {
        return baseDao.selectList(new QueryWrapper<AgentMcpServerEntity>().eq("agent_id", agentId).orderByAsc("sort"));
    }

    @Override
    public void saveOrUpdateByAgentId(String agentId, List<AgentMcpServerItem> items, Long userId) {
        if (items == null) {
            return;
        }
        List<String> newIds = items.stream()
                .map(AgentMcpServerItem::getId)
                .filter(StringUtils::isNotBlank)
                .toList();

        List<AgentMcpServerEntity> existing = getByAgentId(agentId);
        Map<String, AgentMcpServerEntity> existMap = new HashMap<>();
        existing.forEach(e -> existMap.put(e.getId(), e));

        Date now = new Date();
        List<AgentMcpServerEntity> toInsert = new ArrayList<>();
        List<AgentMcpServerEntity> toUpdate = new ArrayList<>();
        for (AgentMcpServerItem item : items) {
            AgentMcpServerEntity entity = toEntity(item, agentId);
            AgentMcpServerEntity old = StringUtils.isNotBlank(item.getId()) ? existMap.get(item.getId()) : null;
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

        List<String> toDelete = existing.stream()
                .filter(old -> !newIds.contains(old.getId()))
                .map(AgentMcpServerEntity::getId)
                .toList();
        if (!toDelete.isEmpty()) {
            deleteBatchIds(toDelete);
        }
    }

    @Override
    public Map<String, Object> getMcpServersForDevice(String macAddress, String clientId) {
        Map<String, Object> result = new HashMap<>();
        result.put("mcp_servers", new LinkedHashMap<String, Object>());
        String agentId = resolveAgentId(macAddress, clientId);
        if (StringUtils.isBlank(agentId)) {
            return result;
        }

        List<AgentMcpServerEntity> enabled = baseDao.selectList(
                new QueryWrapper<AgentMcpServerEntity>().eq("agent_id", agentId).eq("enabled", 1).orderByAsc("sort"));

        Map<String, Object> servers = new LinkedHashMap<>();
        for (AgentMcpServerEntity e : enabled) {
            Map<String, Object> cfg = new LinkedHashMap<>();
            String transport = StringUtils.isBlank(e.getTransport()) ? "stdio" : e.getTransport();
            if ("stdio".equals(transport)) {
                cfg.put("command", e.getCommand());
                if (StringUtils.isNotBlank(e.getArgs())) {
                    cfg.put("args", parseJsonList(e.getArgs()));
                }
                if (StringUtils.isNotBlank(e.getEnv())) {
                    cfg.put("env", parseJsonMap(e.getEnv()));
                }
            } else {
                cfg.put("url", e.getUrl());
                cfg.put("transport", transport);
                if (StringUtils.isNotBlank(e.getHeaders())) {
                    cfg.put("headers", parseJsonMap(e.getHeaders()));
                }
            }
            servers.put(e.getServerName(), cfg);
        }
        result.put("mcp_servers", servers);
        return result;
    }

    @Override
    public void deleteByAgentId(String agentId) {
        baseDao.delete(new QueryWrapper<AgentMcpServerEntity>().eq("agent_id", agentId));
    }

    private AgentMcpServerEntity toEntity(AgentMcpServerItem item, String agentId) {
        AgentMcpServerEntity entity = new AgentMcpServerEntity();
        entity.setAgentId(agentId);
        entity.setServerName(item.getServerName());
        entity.setTransport(StringUtils.isBlank(item.getTransport()) ? "stdio" : item.getTransport());
        entity.setCommand(item.getCommand());
        entity.setArgs(item.getArgs() == null ? null : JsonUtils.toJsonString(item.getArgs()));
        entity.setUrl(item.getUrl());
        entity.setEnv(item.getEnv() == null ? null : JsonUtils.toJsonString(item.getEnv()));
        entity.setHeaders(item.getHeaders() == null ? null : JsonUtils.toJsonString(item.getHeaders()));
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
        } catch (RuntimeException e) {
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
