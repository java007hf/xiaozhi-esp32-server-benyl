package xiaozhi.modules.config.controller;

import java.util.List;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.AllArgsConstructor;
import xiaozhi.common.utils.Result;
import xiaozhi.common.validator.ValidatorUtils;
import xiaozhi.modules.agent.service.AgentMcpServerService;
import xiaozhi.modules.agent.service.AgentSkillService;
import xiaozhi.modules.config.dto.AgentModelsDTO;
import xiaozhi.modules.config.dto.AgentSkillMcpDTO;
import xiaozhi.modules.config.dto.CorrectWordsDTO;
import xiaozhi.modules.config.service.ConfigService;

/**
 * xiaozhi-server 配置获取
 *
 * @since 1.0.0
 */
@RestController
@RequestMapping("config")
@Tag(name = "参数管理")
@AllArgsConstructor
public class ConfigController {
    private final ConfigService configService;
    private final AgentSkillService agentSkillService;
    private final AgentMcpServerService agentMcpServerService;

    @PostMapping("server-base")
    @Operation(summary = "服务端获取配置接口")
    public Result<Object> getConfig() {
        Object config = configService.getConfig(true);
        return new Result<Object>().ok(config);
    }

    @PostMapping("agent-models")
    @Operation(summary = "获取智能体模型")
    public Result<Object> getAgentModels(@Valid @RequestBody AgentModelsDTO dto) {
        // 效验数据
        ValidatorUtils.validateEntity(dto);
        Object models = configService.getAgentModels(dto.getMacAddress(), dto.getSelectedModule());
        return new Result<Object>().ok(models);
    }

    @PostMapping("correct-words")
    @Operation(summary = "获取智能体替换词")
    public Result<Object> getCorrectWords(@Valid @RequestBody CorrectWordsDTO dto) {
        ValidatorUtils.validateEntity(dto);
        List<String> list = configService.getCorrectWords(dto.getMacAddress());
        return new Result<Object>().ok(list);
    }

    @PostMapping("agent-skills")
    @Operation(summary = "服务端获取角色级技能配置(含沙箱)")
    public Result<Object> getAgentSkills(@Valid @RequestBody AgentSkillMcpDTO dto) {
        ValidatorUtils.validateEntity(dto);
        return new Result<Object>().ok(agentSkillService.getSkillsDefinitionsForDevice(dto.getMacAddress(), dto.getClientId()));
    }

    @PostMapping("agent-mcp")
    @Operation(summary = "服务端获取角色级MCP服务配置")
    public Result<Object> getAgentMcp(@Valid @RequestBody AgentSkillMcpDTO dto) {
        ValidatorUtils.validateEntity(dto);
        return new Result<Object>().ok(agentMcpServerService.getMcpServersForDevice(dto.getMacAddress(), dto.getClientId()));
    }
}
