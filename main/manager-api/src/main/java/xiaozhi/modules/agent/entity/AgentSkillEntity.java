package xiaozhi.modules.agent.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName("ai_agent_skill")
@Schema(description = "智能体技能配置")
public class AgentSkillEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    @Schema(description = "主键")
    private String id;

    @Schema(description = "智能体ID")
    private String agentId;

    @Schema(description = "技能名(对应SKILL.md frontmatter name)")
    private String skillName;

    @Schema(description = "技能描述")
    private String description;

    @Deprecated
    @Schema(description = "历史字段，不再作为技能内容来源")
    private String content;

    @Schema(description = "JSON数组: 绑定的函数名")
    private String functions;

    @Schema(description = "JSON对象: 相对路径->文件内容(仅兼容内存技能)")
    private String files;

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
