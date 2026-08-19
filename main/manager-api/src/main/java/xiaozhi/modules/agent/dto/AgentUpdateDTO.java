package xiaozhi.modules.agent.dto;

import java.io.Serializable;
import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.core.type.TypeReference;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import xiaozhi.common.utils.JsonUtils;

/**
 * 智能体更新DTO
 * 专用于更新智能体，id字段是必需的，用于标识要更新的智能体
 * 其他字段均为非必填，只更新提供的字段
 */
@Data
@Schema(description = "智能体更新对象")
public class AgentUpdateDTO implements Serializable {
    private static final long serialVersionUID = 1L;

    @Schema(description = "智能体编码", example = "AGT_1234567890", nullable = true)
    private String agentCode;

    @Schema(description = "智能体名称", example = "客服助手", nullable = true)
    private String agentName;

    @Schema(description = "语音识别模型标识", example = "asr_model_02", nullable = true)
    private String asrModelId;

    @Schema(description = "语音活动检测标识", example = "vad_model_02", nullable = true)
    private String vadModelId;

    @Schema(description = "大语言模型标识", example = "llm_model_02", nullable = true)
    private String llmModelId;

    @Schema(description = "小模型标识", example = "slm_model_02", nullable = true)
    private String slmModelId;

    @Schema(description = "VLLM模型标识", example = "vllm_model_02", requiredMode = Schema.RequiredMode.NOT_REQUIRED)
    private String vllmModelId;

    @Schema(description = "语音合成模型标识", example = "tts_model_02", requiredMode = Schema.RequiredMode.NOT_REQUIRED)
    private String ttsModelId;

    @Schema(description = "音色标识", example = "voice_02", nullable = true)
    private String ttsVoiceId;

    @Schema(description = "音色语言", example = "普通话", nullable = true)
    private String ttsLanguage;

    @Schema(description = "TTS音量", example = "50", nullable = true)
    private Integer ttsVolume;

    @Schema(description = "TTS语速", example = "50", nullable = true)
    private Integer ttsRate;

    @Schema(description = "TTS音调", example = "50", nullable = true)
    private Integer ttsPitch;

    @Schema(description = "记忆模型标识", example = "mem_model_02", nullable = true)
    private String memModelId;

    @Schema(description = "意图模型标识", example = "intent_model_02", nullable = true)
    private String intentModelId;

    @Schema(description = "插件函数信息", nullable = true)
    private List<FunctionInfo> functions;

    @Schema(description = "角色设定参数", example = "你是一个专业的客服助手，负责回答用户问题并提供帮助", nullable = true)
    private String systemPrompt;

    @Schema(description = "总结记忆", example = "构建可生长的动态记忆网络，在有限空间内保留关键信息的同时，智能维护信息演变轨迹\n"
            + "根据对话记录，总结user的重要信息，以便在未来的对话中提供更个性化的服务", nullable = true)
    private String summaryMemory;

    @Schema(description = "聊天记录配置（0不记录 1仅记录文本 2记录文本和语音）", example = "3", nullable = true)
    private Integer chatHistoryConf;

    @Schema(description = "语言编码", example = "zh_CN", nullable = true)
    private String langCode;

    @Schema(description = "交互语种", example = "中文", nullable = true)
    private String language;

    @Schema(description = "排序", example = "1", nullable = true)
    private Integer sort;

    @Schema(description = "上下文源配置", nullable = true)
    private List<ContextProviderDTO> contextProviders;

    @Schema(description = "替换词文件ID列表", nullable = true)
    private List<String> correctWordFileIds;

    @Schema(description = "标签名称列表", nullable = true)
    private List<String> tagNames;

    @Schema(description = "标签ID列表", nullable = true)
    private List<String> tagIds;

    @Schema(description = "角色级技能配置", nullable = true)
    private List<AgentSkillItem> skills;

    @Schema(description = "角色级MCP服务配置", nullable = true)
    private List<AgentMcpServerItem> mcpServers;

    @Schema(description = "技能沙箱运行配置(JSON字符串)", nullable = true)
    private String sandboxConfig;

    @Data
    @Schema(description = "插件函数信息")
    public static class FunctionInfo implements Serializable {
        private static final TypeReference<HashMap<String, Object>> PARAM_INFO_TYPE = new TypeReference<>() {
        };

        @Schema(description = "插件ID", example = "plugin_01")
        private String pluginId;

        @Schema(description = "函数参数信息", nullable = true)
        private HashMap<String, Object> paramInfo = new HashMap<>();

        public void setParamInfo(Object paramInfo) {
            this.paramInfo = normalizeParamInfo(paramInfo);
        }

        private static HashMap<String, Object> normalizeParamInfo(Object paramInfo) {
            if (paramInfo == null) {
                return new HashMap<>();
            }
            if (paramInfo instanceof String value) {
                if (value.trim().isEmpty()) {
                    return new HashMap<>();
                }
                return JsonUtils.parseObject(value, PARAM_INFO_TYPE);
            }
            if (paramInfo instanceof Map<?, ?> value) {
                HashMap<String, Object> normalized = new HashMap<>();
                value.forEach((key, val) -> {
                    if (key != null) {
                        normalized.put(String.valueOf(key), val);
                    }
                });
                return normalized;
            }
            return JsonUtils.parseObject(JsonUtils.toJsonString(paramInfo), PARAM_INFO_TYPE);
        }

        private static final long serialVersionUID = 1L;
    }

    @Data
    @Schema(description = "角色级技能配置项")
    public static class AgentSkillItem implements Serializable {
        private static final long serialVersionUID = 1L;

        @Schema(description = "主键(更新时必填)")
        private String id;

        @Schema(description = "技能名(对应SKILL.md frontmatter name)", example = "weather")
        private String skillName;

        @Schema(description = "技能描述", example = "查询天气")
        private String description;

        @Schema(description = "完整 SKILL.md(含YAML frontmatter)")
        private String content;

        @Schema(description = "绑定的函数名列表")
        private List<String> functions;

        @Schema(description = "相对路径->文件内容(in-memory技能用)")
        private Map<String, String> files;

        @Schema(description = "是否启用", example = "true")
        private Boolean enabled;

        @Schema(description = "排序", example = "0")
        private Integer sort;
    }

    @Data
    @Schema(description = "角色级MCP服务配置项")
    public static class AgentMcpServerItem implements Serializable {
        private static final long serialVersionUID = 1L;

        @Schema(description = "主键(更新时必填)")
        private String id;

        @Schema(description = "MCP服务名", example = "filesystem")
        private String serverName;

        @Schema(description = "传输方式: stdio|sse|streamable-http", example = "stdio")
        private String transport;

        @Schema(description = "stdio启动命令", example = "npx")
        private String command;

        @Schema(description = "启动参数列表")
        private List<String> args;

        @Schema(description = "sse/streamable-http地址")
        private String url;

        @Schema(description = "环境变量")
        private Map<String, String> env;

        @Schema(description = "请求头")
        private Map<String, String> headers;

        @Schema(description = "是否启用", example = "true")
        private Boolean enabled;

        @Schema(description = "排序", example = "0")
        private Integer sort;
    }
}
