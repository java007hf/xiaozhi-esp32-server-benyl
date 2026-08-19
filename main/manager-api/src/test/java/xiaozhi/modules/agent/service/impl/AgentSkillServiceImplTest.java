package xiaozhi.modules.agent.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.spy;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.io.Serializable;
import java.util.Collection;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

import xiaozhi.modules.agent.dao.AgentSkillDao;
import xiaozhi.modules.agent.dto.AgentUpdateDTO.AgentSkillItem;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.entity.AgentSkillEntity;
import xiaozhi.modules.agent.vo.AgentInfoVO;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceService;

@SuppressWarnings({"unchecked", "rawtypes"})
class AgentSkillServiceImplTest {

    private AgentSkillServiceImpl build(AgentSkillDao dao, DeviceService deviceService, AgentService agentService) {
        AgentSkillServiceImpl service = new AgentSkillServiceImpl(deviceService, agentService);
        ReflectionTestUtils.setField(service, "baseDao", dao);
        return service;
    }

    private AgentSkillServiceImpl spyService(AgentSkillServiceImpl real) {
        AgentSkillServiceImpl spy = spy(real);
        doReturn(true).when(spy).insertBatch(anyList(), anyInt());
        doReturn(true).when(spy).updateBatchById(anyList(), anyInt());
        doReturn(true).when(spy).deleteBatchIds(any());
        return spy;
    }

    @Test
    void getByAgentId_delegatesToDao() {
        AgentSkillDao dao = mock(AgentSkillDao.class);
        AgentSkillEntity e = new AgentSkillEntity();
        when(dao.selectList(any())).thenReturn(List.of(e));
        AgentSkillServiceImpl service = build(dao, mock(DeviceService.class), mock(AgentService.class));

        List<AgentSkillEntity> result = service.getByAgentId("a1");

        assertSame(e, result.get(0));
        verify(dao).selectList(any());
    }

    @Test
    void saveOrUpdate_insertsNewSkillsAndSerializesFieldsToJson() {
        AgentSkillDao dao = mock(AgentSkillDao.class);
        AgentSkillServiceImpl real = build(dao, mock(DeviceService.class), mock(AgentService.class));
        AgentSkillServiceImpl service = spyService(real);
        when(dao.selectList(any())).thenReturn(List.of());

        AgentSkillItem item = new AgentSkillItem();
        item.setSkillName("weather");
        item.setDescription("天气");
        item.setContent("---\nname: weather\n---");
        item.setFunctions(List.of("shell_command"));
        item.setFiles(Map.of("scripts/w.py", "print(1)"));
        item.setEnabled(true);
        item.setSort(0);

        service.saveOrUpdateByAgentId("a1", List.of(item), 7L);

        ArgumentCaptor<List<AgentSkillEntity>> insertCaptor = ArgumentCaptor.forClass(List.class);
        verify(service).insertBatch(insertCaptor.capture(), anyInt());
        assertEquals(1, insertCaptor.getValue().size());
        AgentSkillEntity ent = insertCaptor.getValue().get(0);
        assertEquals("a1", ent.getAgentId());
        assertEquals("weather", ent.getSkillName());
        assertEquals(1, (int) ent.getEnabled());
        assertEquals("[\"shell_command\"]", ent.getFunctions());
        assertEquals("{\"scripts/w.py\":\"print(1)\"}", ent.getFiles());
        assertEquals(7L, (long) ent.getCreator());

        verify(service, never()).updateBatchById(anyList(), anyInt());
        verify(service, never()).deleteBatchIds(any());
    }

    @Test
    void saveOrUpdate_updatesExistingAndDeletesMissing() {
        AgentSkillDao dao = mock(AgentSkillDao.class);
        AgentSkillServiceImpl real = build(dao, mock(DeviceService.class), mock(AgentService.class));
        AgentSkillServiceImpl service = spyService(real);

        AgentSkillEntity existing1 = new AgentSkillEntity();
        existing1.setId("e1");
        existing1.setAgentId("a1");
        existing1.setSkillName("keep");
        AgentSkillEntity existing2 = new AgentSkillEntity();
        existing2.setId("e2");
        existing2.setAgentId("a1");
        existing2.setSkillName("drop");
        when(dao.selectList(any())).thenReturn(List.of(existing1, existing2));

        AgentSkillItem keep = new AgentSkillItem();
        keep.setId("e1");
        keep.setSkillName("keep-updated");
        keep.setEnabled(false);
        keep.setSort(1);
        AgentSkillItem fresh = new AgentSkillItem();
        fresh.setSkillName("fresh");
        fresh.setEnabled(true);
        fresh.setSort(2);

        service.saveOrUpdateByAgentId("a1", List.of(keep, fresh), 7L);

        ArgumentCaptor<List<AgentSkillEntity>> updCaptor = ArgumentCaptor.forClass(List.class);
        verify(service).updateBatchById(updCaptor.capture(), anyInt());
        assertEquals(1, updCaptor.getValue().size());
        assertEquals("e1", updCaptor.getValue().get(0).getId());
        assertEquals("keep-updated", updCaptor.getValue().get(0).getSkillName());
        assertEquals(0, (int) updCaptor.getValue().get(0).getEnabled());

        ArgumentCaptor<List<AgentSkillEntity>> insCaptor = ArgumentCaptor.forClass(List.class);
        verify(service).insertBatch(insCaptor.capture(), anyInt());
        assertEquals(1, insCaptor.getValue().size());
        assertEquals("fresh", insCaptor.getValue().get(0).getSkillName());

        ArgumentCaptor<Collection<? extends Serializable>> delCaptor = ArgumentCaptor.forClass(Collection.class);
        verify(service).deleteBatchIds(delCaptor.capture());
        assertEquals(List.of("e2"), delCaptor.getValue());
    }

    @Test
    void saveOrUpdate_nullItemsReturnsEarly() {
        AgentSkillDao dao = mock(AgentSkillDao.class);
        AgentSkillServiceImpl real = build(dao, mock(DeviceService.class), mock(AgentService.class));
        AgentSkillServiceImpl service = spyService(real);

        service.saveOrUpdateByAgentId("a1", null, 7L);

        verify(dao, never()).selectList(any());
        verify(service, never()).insertBatch(anyList(), anyInt());
    }

    @Test
    void getSkillsDefinitionsForDevice_returnsEnabledDefinitionsAndSandbox() {
        AgentSkillDao dao = mock(AgentSkillDao.class);
        DeviceService deviceService = mock(DeviceService.class);
        AgentService agentService = mock(AgentService.class);

        DeviceEntity device = new DeviceEntity();
        device.setAgentId("a1");
        when(deviceService.getDeviceByMacAddress("AA:BB")).thenReturn(device);

        AgentSkillEntity enabled = new AgentSkillEntity();
        enabled.setId("s1");
        enabled.setSkillName("weather");
        enabled.setDescription("d");
        enabled.setContent("c");
        enabled.setFunctions("[\"shell_command\"]");
        enabled.setFiles("{\"a/b\":\"x\"}");
        enabled.setEnabled(1);
        when(dao.selectList(any())).thenReturn(List.of(enabled));

        AgentInfoVO agent = new AgentInfoVO();
        agent.setSandboxConfig("{\"enabled\":true,\"network\":false,\"timeout\":30}");
        when(agentService.getAgentById("a1")).thenReturn(agent);

        AgentSkillServiceImpl service = build(dao, deviceService, agentService);
        Map<String, Object> result = service.getSkillsDefinitionsForDevice("AA:BB", "cid");

        List<?> defs = (List<?>) result.get("skills_definitions");
        assertEquals(1, defs.size());
        Map<?, ?> def = (Map<?, ?>) defs.get(0);
        assertEquals("weather", def.get("name"));
        assertEquals(List.of("shell_command"), def.get("functions"));
        assertEquals(Map.of("a/b", "x"), def.get("files"));
        assertTrue(result.containsKey("sandbox"));
    }

    @Test
    void getSkillsDefinitionsForDevice_unknownMacReturnsEmpty() {
        AgentSkillDao dao = mock(AgentSkillDao.class);
        DeviceService deviceService = mock(DeviceService.class);
        when(deviceService.getDeviceByMacAddress("ZZ")).thenReturn(null);
        AgentSkillServiceImpl service = build(dao, deviceService, mock(AgentService.class));

        Map<String, Object> result = service.getSkillsDefinitionsForDevice("ZZ", "cid");

        List<?> defs = (List<?>) result.get("skills_definitions");
        assertTrue(defs.isEmpty());
        assertFalse(result.containsKey("sandbox"));
    }

    @Test
    void deleteByAgentId_deletesByAgentId() {
        AgentSkillDao dao = mock(AgentSkillDao.class);
        AgentSkillServiceImpl service = build(dao, mock(DeviceService.class), mock(AgentService.class));

        service.deleteByAgentId("a1");

        verify(dao).delete(any());
    }
}
