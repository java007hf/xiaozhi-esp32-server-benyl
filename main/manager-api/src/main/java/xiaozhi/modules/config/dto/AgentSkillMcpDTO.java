package xiaozhi.modules.config.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
@Schema(description = "服务端获取角色级技能/MCP配置DTO")
public class AgentSkillMcpDTO {
    @NotBlank(message = "设备MAC地址不能为空")
    @Schema(description = "设备MAC地址")
    private String macAddress;

    @NotBlank(message = "客户端ID不能为空")
    @Schema(description = "客户端ID")
    private String clientId;
}
