package xiaozhi.modules.agent.service.impl;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.repository.IRepository;
import com.fasterxml.jackson.core.type.TypeReference;

import xiaozhi.common.exception.RenException;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.agent.dao.AgentDao;
import xiaozhi.modules.agent.dao.AgentSkillDao;
import xiaozhi.modules.agent.dto.AgentUpdateDTO.AgentSkillItem;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.entity.AgentSkillEntity;
import xiaozhi.modules.agent.service.AgentSkillService;
import xiaozhi.modules.device.service.DeviceService;

@Service
public class AgentSkillServiceImpl extends BaseServiceImpl<AgentSkillDao, AgentSkillEntity> implements AgentSkillService {

    private final DeviceService deviceService;
    private final AgentDao agentDao;
    private final String skillsUploadBase;

    public AgentSkillServiceImpl(DeviceService deviceService, AgentDao agentDao,
            @Value("${agent.skills-upload-base:/uploaded_skills}") String skillsUploadBase) {
        this.deviceService = deviceService;
        this.agentDao = agentDao;
        this.skillsUploadBase = skillsUploadBase;
    }

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

        AgentEntity agent = agentDao.selectById(agentId);
        if (agent != null && StringUtils.isNotBlank(agent.getSandboxConfig())) {
            try {
                result.put("sandbox", JsonUtils.parseMap(agent.getSandboxConfig()));
            } catch (Exception ignored) {
                // 沙箱配置非法时忽略
            }
        }
        // 供 Python 端按 agent 维度扫描上传的技能目录
        result.put("agent_id", agentId);
        return result;
    }

    @Override
    public void deleteByAgentId(String agentId) {
        baseDao.delete(new QueryWrapper<AgentSkillEntity>().eq("agent_id", agentId));
    }

    @Override
    public void uploadSkillFolder(String agentId, Long userId, List<MultipartFile> files) throws IOException {
        if (files == null || files.isEmpty()) {
            throw new RenException("请选择要上传的技能文件夹");
        }
        // 技能文件夹名取首个文件的相对路径首段(webkitdirectory 上传时 originalFilename 含相对路径)
        String folderName = null;
        for (MultipartFile f : files) {
            String rel = normalizeRelPath(f.getOriginalFilename());
            if (rel != null) {
                folderName = rel.split("[/\\\\]", 2)[0];
                break;
            }
        }
        if (StringUtils.isBlank(folderName)) {
            throw new RenException("无法识别技能文件夹");
        }
        validateFolderName(folderName);

        Path base = Paths.get(skillsUploadBase).toAbsolutePath().normalize();
        Path agentDir = base.resolve(agentId).normalize();
        Path skillDir = agentDir.resolve(folderName).normalize();
        if (!skillDir.startsWith(base)) {
            throw new RenException("非法的技能文件夹名");
        }
        Files.createDirectories(skillDir);

        boolean hasSkillMd = false;
        String skillMdContent = null;
        for (MultipartFile f : files) {
            String rel = normalizeRelPath(f.getOriginalFilename());
            if (rel == null) {
                continue;
            }
            String[] parts = rel.split("[/\\\\]", 2);
            String sub = parts.length > 1 ? parts[1] : "";
            if (StringUtils.isBlank(sub)) {
                continue; // 跳过目录占位
            }
            Path target = skillDir.resolve(sub).normalize();
            if (!target.startsWith(skillDir)) {
                continue; // 防目录穿越
            }
            Files.createDirectories(target.getParent());
            try (java.io.InputStream in = f.getInputStream()) {
                Files.copy(in, target, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
            }
            if (rel.toLowerCase().endsWith("skill.md")) {
                hasSkillMd = true;
                skillMdContent = new String(f.getBytes(), StandardCharsets.UTF_8);
            }
        }
        if (!hasSkillMd) {
            deleteDirectory(skillDir);
            throw new RenException("技能文件夹必须包含 SKILL.md");
        }

        String[] meta = parseSkillMeta(skillMdContent);
        String name = StringUtils.isNotBlank(meta[0]) ? meta[0] : folderName;
        String description = meta[1];

        Date now = new Date();
        AgentSkillEntity existing = baseDao.selectOne(
                new QueryWrapper<AgentSkillEntity>().eq("agent_id", agentId).eq("skill_name", folderName));
        if (existing != null) {
            existing.setContent(skillMdContent);
            existing.setDescription(description);
            existing.setEnabled(1);
            existing.setUpdater(userId);
            existing.setUpdatedAt(now);
            baseDao.updateById(existing);
        } else {
            AgentSkillEntity e = new AgentSkillEntity();
            e.setId(UUID.randomUUID().toString().replace("-", ""));
            e.setAgentId(agentId);
            e.setSkillName(folderName);
            e.setDescription(description);
            e.setContent(skillMdContent);
            e.setEnabled(1);
            e.setSort(0);
            e.setCreator(userId);
            e.setCreatedAt(now);
            e.setUpdater(userId);
            e.setUpdatedAt(now);
            baseDao.insert(e);
        }
    }

    @Override
    public void deleteSkillById(String agentId, String skillId) {
        AgentSkillEntity e = baseDao.selectById(skillId);
        if (e == null) {
            return;
        }
        baseDao.deleteById(skillId);
        if (StringUtils.isNotBlank(e.getSkillName())) {
            Path base = Paths.get(skillsUploadBase).toAbsolutePath().normalize();
            Path skillDir = base.resolve(agentId).resolve(e.getSkillName()).normalize();
            if (skillDir.startsWith(base)) {
                deleteDirectory(skillDir);
            }
        }
    }

    private String normalizeRelPath(String original) {
        if (original == null) {
            return null;
        }
        return original.replace('\\', '/');
    }

    private void validateFolderName(String name) {
        if (!name.matches("^[A-Za-z0-9_.\\-]+$")) {
            throw new RenException("非法的技能文件夹名: " + name);
        }
    }

    private String[] parseSkillMeta(String content) {
        String name = "";
        String description = "";
        if (content == null) {
            return new String[] { name, description };
        }
        boolean inFm = false;
        for (String line : content.split("\n")) {
            String t = line.trim();
            if (t.equals("---")) {
                inFm = !inFm;
                continue;
            }
            if (inFm) {
                if (t.startsWith("name:")) {
                    name = t.substring(5).trim();
                } else if (t.startsWith("description:")) {
                    description = t.substring(12).trim();
                }
            }
        }
        return new String[] { name, description };
    }

    private void deleteDirectory(Path dir) {
        try {
            if (!Files.exists(dir)) {
                return;
            }
            Files.walk(dir).sorted(Comparator.reverseOrder()).forEach(p -> {
                try {
                    Files.deleteIfExists(p);
                } catch (IOException ignored) {
                    // 忽略删除失败
                }
            });
        } catch (IOException ignored) {
            // 忽略
        }
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
