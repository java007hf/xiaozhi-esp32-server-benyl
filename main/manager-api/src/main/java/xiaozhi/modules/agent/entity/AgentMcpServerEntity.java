package xiaozhi.modules.agent.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName("ai_agent_mcp_server")
@Schema(description = "智能体MCP服务配置")
public class AgentMcpServerEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    @Schema(description = "主键")
    private String id;

    @Schema(description = "智能体ID")
    private String agentId;

    @Schema(description = "MCP服务名")
    private String serverName;

    @Schema(description = "传输方式: stdio|sse|streamable-http")
    private String transport;

    @Schema(description = "stdio启动命令")
    private String command;

    @Schema(description = "JSON数组: 启动参数")
    private String args;

    @Schema(description = "sse/streamable-http地址")
    private String url;

    @Schema(description = "JSON对象: 环境变量")
    private String env;

    @Schema(description = "JSON对象: 请求头")
    private String headers;

    @Schema(description = "是否启用")
    private Integer enabled;

    @Schema(description = "排序")
    private Integer sort;

    @Schema(description = "创建者")
    private Long creator;

    @Schema(description = "创建时间")
    private Date createdAt;

    @Schema(description = "更新者")
    private Long updater;

    @Schema(description = "更新时间")
    private Date updatedAt;
}
