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

import xiaozhi.modules.agent.dao.AgentMcpServerDao;
import xiaozhi.modules.agent.dto.AgentUpdateDTO.AgentMcpServerItem;
import xiaozhi.modules.agent.entity.AgentMcpServerEntity;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceService;

@SuppressWarnings({"unchecked", "rawtypes"})
class AgentMcpServerServiceImplTest {

    private AgentMcpServerServiceImpl build(AgentMcpServerDao dao, DeviceService deviceService, AgentService agentService) {
        AgentMcpServerServiceImpl service = new AgentMcpServerServiceImpl(deviceService, agentService);
        ReflectionTestUtils.setField(service, "baseDao", dao);
        return service;
    }

    private AgentMcpServerServiceImpl spyService(AgentMcpServerServiceImpl real) {
        AgentMcpServerServiceImpl spy = spy(real);
        doReturn(true).when(spy).insertBatch(anyList(), anyInt());
        doReturn(true).when(spy).updateBatchById(anyList(), anyInt());
        doReturn(true).when(spy).deleteBatchIds(any());
        return spy;
    }

    @Test
    void getByAgentId_delegatesToDao() {
        AgentMcpServerDao dao = mock(AgentMcpServerDao.class);
        AgentMcpServerEntity e = new AgentMcpServerEntity();
        when(dao.selectList(any())).thenReturn(List.of(e));
        AgentMcpServerServiceImpl service = build(dao, mock(DeviceService.class), mock(AgentService.class));

        List<AgentMcpServerEntity> result = service.getByAgentId("a1");

        assertSame(e, result.get(0));
        verify(dao).selectList(any());
    }

    @Test
    void saveOrUpdate_insertsNewServersAndSerializesFieldsToJson() {
        AgentMcpServerDao dao = mock(AgentMcpServerDao.class);
        AgentMcpServerServiceImpl real = build(dao, mock(DeviceService.class), mock(AgentService.class));
        AgentMcpServerServiceImpl service = spyService(real);
        when(dao.selectList(any())).thenReturn(List.of());

        AgentMcpServerItem item = new AgentMcpServerItem();
        item.setServerName("filesystem");
        item.setTransport("stdio");
        item.setCommand("npx");
        item.setArgs(List.of("-y", "@modelcontextprotocol/server-filesystem"));
        item.setEnv(Map.of("TOKEN", "abc"));
        item.setEnabled(true);
        item.setSort(0);

        service.saveOrUpdateByAgentId("a1", List.of(item), 7L);

        ArgumentCaptor<List<AgentMcpServerEntity>> insertCaptor = ArgumentCaptor.forClass(List.class);
        verify(service).insertBatch(insertCaptor.capture(), anyInt());
        assertEquals(1, insertCaptor.getValue().size());
        AgentMcpServerEntity ent = insertCaptor.getValue().get(0);
        assertEquals("a1", ent.getAgentId());
        assertEquals("filesystem", ent.getServerName());
        assertEquals("stdio", ent.getTransport());
        assertEquals("npx", ent.getCommand());
        assertEquals(1, (int) ent.getEnabled());
        assertEquals("[\"-y\",\"@modelcontextprotocol/server-filesystem\"]", ent.getArgs());
        assertEquals("{\"TOKEN\":\"abc\"}", ent.getEnv());
        assertEquals(7L, (long) ent.getCreator());

        verify(service, never()).updateBatchById(anyList(), anyInt());
        verify(service, never()).deleteBatchIds(any());
    }

    @Test
    void saveOrUpdate_updatesExistingAndDeletesMissing() {
        AgentMcpServerDao dao = mock(AgentMcpServerDao.class);
        AgentMcpServerServiceImpl real = build(dao, mock(DeviceService.class), mock(AgentService.class));
        AgentMcpServerServiceImpl service = spyService(real);

        AgentMcpServerEntity existing1 = new AgentMcpServerEntity();
        existing1.setId("e1");
        existing1.setAgentId("a1");
        existing1.setServerName("keep");
        AgentMcpServerEntity existing2 = new AgentMcpServerEntity();
        existing2.setId("e2");
        existing2.setAgentId("a1");
        existing2.setServerName("drop");
        when(dao.selectList(any())).thenReturn(List.of(existing1, existing2));

        AgentMcpServerItem keep = new AgentMcpServerItem();
        keep.setId("e1");
        keep.setServerName("keep-updated");
        keep.setEnabled(false);
        keep.setSort(1);
        AgentMcpServerItem fresh = new AgentMcpServerItem();
        fresh.setServerName("fresh");
        fresh.setEnabled(true);
        fresh.setSort(2);

        service.saveOrUpdateByAgentId("a1", List.of(keep, fresh), 7L);

        ArgumentCaptor<List<AgentMcpServerEntity>> updCaptor = ArgumentCaptor.forClass(List.class);
        verify(service).updateBatchById(updCaptor.capture(), anyInt());
        assertEquals(1, updCaptor.getValue().size());
        assertEquals("e1", updCaptor.getValue().get(0).getId());
        assertEquals("keep-updated", updCaptor.getValue().get(0).getServerName());
        assertEquals(0, (int) updCaptor.getValue().get(0).getEnabled());

        ArgumentCaptor<List<AgentMcpServerEntity>> insCaptor = ArgumentCaptor.forClass(List.class);
        verify(service).insertBatch(insCaptor.capture(), anyInt());
        assertEquals(1, insCaptor.getValue().size());
        assertEquals("fresh", insCaptor.getValue().get(0).getServerName());

        ArgumentCaptor<Collection<? extends Serializable>> delCaptor = ArgumentCaptor.forClass(Collection.class);
        verify(service).deleteBatchIds(delCaptor.capture());
        assertEquals(List.of("e2"), delCaptor.getValue());
    }

    @Test
    void saveOrUpdate_nullItemsReturnsEarly() {
        AgentMcpServerDao dao = mock(AgentMcpServerDao.class);
        AgentMcpServerServiceImpl real = build(dao, mock(DeviceService.class), mock(AgentService.class));
        AgentMcpServerServiceImpl service = spyService(real);

        service.saveOrUpdateByAgentId("a1", null, 7L);

        verify(dao, never()).selectList(any());
        verify(service, never()).insertBatch(anyList(), anyInt());
    }

    @Test
    void getMcpServersForDevice_returnsEnabledServersWithStdioConfig() {
        AgentMcpServerDao dao = mock(AgentMcpServerDao.class);
        DeviceService deviceService = mock(DeviceService.class);
        AgentService agentService = mock(AgentService.class);

        DeviceEntity device = new DeviceEntity();
        device.setAgentId("a1");
        when(deviceService.getDeviceByMacAddress("AA:BB")).thenReturn(device);

        AgentMcpServerEntity enabled = new AgentMcpServerEntity();
        enabled.setId("m1");
        enabled.setServerName("filesystem");
        enabled.setTransport("stdio");
        enabled.setCommand("npx");
        enabled.setArgs("[\"-y\",\"@modelcontextprotocol/server-filesystem\"]");
        enabled.setEnv("{\"TOKEN\":\"abc\"}");
        enabled.setEnabled(1);
        when(dao.selectList(any())).thenReturn(List.of(enabled));

        AgentMcpServerServiceImpl service = build(dao, deviceService, agentService);
        Map<String, Object> result = service.getMcpServersForDevice("AA:BB", "cid");

        Map<String, Object> servers = (Map<String, Object>) result.get("mcp_servers");
        assertEquals(1, servers.size());
        assertTrue(servers.containsKey("filesystem"));
        Map<?, ?> cfg = (Map<?, ?>) servers.get("filesystem");
        assertEquals("npx", cfg.get("command"));
        assertEquals(List.of("-y", "@modelcontextprotocol/server-filesystem"), cfg.get("args"));
        assertEquals(Map.of("TOKEN", "abc"), cfg.get("env"));
    }

    @Test
    void getMcpServersForDevice_returnsSseConfigForHttpTransports() {
        AgentMcpServerDao dao = mock(AgentMcpServerDao.class);
        DeviceService deviceService = mock(DeviceService.class);
        AgentService agentService = mock(AgentService.class);

        DeviceEntity device = new DeviceEntity();
        device.setAgentId("a1");
        when(deviceService.getDeviceByMacAddress("AA:BB")).thenReturn(device);

        AgentMcpServerEntity sse = new AgentMcpServerEntity();
        sse.setId("m1");
        sse.setServerName("remote");
        sse.setTransport("sse");
        sse.setUrl("http://localhost:9000/sse");
        sse.setHeaders("{\"Authorization\":\"Bearer x\"}");
        sse.setEnabled(1);
        when(dao.selectList(any())).thenReturn(List.of(sse));

        AgentMcpServerServiceImpl service = build(dao, deviceService, agentService);
        Map<String, Object> result = service.getMcpServersForDevice("AA:BB", "cid");

        Map<String, Object> servers = (Map<String, Object>) result.get("mcp_servers");
        Map<?, ?> cfg = (Map<?, ?>) servers.get("remote");
        assertEquals("http://localhost:9000/sse", cfg.get("url"));
        assertEquals("sse", cfg.get("transport"));
        assertEquals(Map.of("Authorization", "Bearer x"), cfg.get("headers"));
        assertFalse(cfg.containsKey("command"));
    }

    @Test
    void getMcpServersForDevice_unknownMacReturnsEmpty() {
        AgentMcpServerDao dao = mock(AgentMcpServerDao.class);
        DeviceService deviceService = mock(DeviceService.class);
        when(deviceService.getDeviceByMacAddress("ZZ")).thenReturn(null);
        AgentMcpServerServiceImpl service = build(dao, deviceService, mock(AgentService.class));

        Map<String, Object> result = service.getMcpServersForDevice("ZZ", "cid");

        Map<String, Object> servers = (Map<String, Object>) result.get("mcp_servers");
        assertTrue(servers.isEmpty());
    }

    @Test
    void deleteByAgentId_deletesByAgentId() {
        AgentMcpServerDao dao = mock(AgentMcpServerDao.class);
        AgentMcpServerServiceImpl service = build(dao, mock(DeviceService.class), mock(AgentService.class));

        service.deleteByAgentId("a1");

        verify(dao).delete(any());
    }
}
