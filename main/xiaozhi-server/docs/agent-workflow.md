# Agent 工作流程

本文档用于说明当前系统中 Agent 的整体工作流程，以及 Agent 与 ESP32 之间的主要交互链路。

## 总体分层

```text
设备层：ESP32 负责音频采集、播放、OLED 显示、IoT/MCP 能力暴露

连接层：WebSocket 负责 JSON 控制消息 + Opus 二进制音频传输

Agent 层：ASR -> LLM/ReAct 工具循环 -> TTS -> ESP32 输出
```

## 完整流程图

```mermaid
flowchart TD
    A["ESP32 上电 / 联网"] --> B["OTA 检查版本<br/>POST /xiaozhi/ota/"]
    B --> C{"服务端返回连接配置"}
    C -->|websocket| D["ESP32 保存 websocket.url / token"]
    C -->|mqtt| D2["ESP32 保存 MQTT 配置"]
    D --> E["ESP32 建立 WebSocket 连接"]
    D2 --> E

    E --> F["发送 hello<br/>type=hello<br/>audio_params / features"]
    F --> G["服务端 WebSocketServer 接收连接"]
    G --> H["创建 ConnectionHandler<br/>每个设备一个会话对象"]
    H --> I["初始化会话状态<br/>session_id / queues / flags"]
    I --> J["后台初始化组件<br/>ASR / VAD / TTS / LLM / Memory / Intent / Tools / Skills"]
    J --> K["服务端返回 hello<br/>session_id / audio_params"]

    K --> L["ESP32 进入监听状态"]
    L --> M{"ESP32 发来的消息类型"}

    M -->|JSON 文本| N["handleTextMessage"]
    M -->|二进制音频| O["音频进入 asr_audio_queue"]

    N --> N1{"JSON type"}
    N1 -->|hello| N2["处理音频参数和 features<br/>如 mcp=true 则初始化设备 MCP"]
    N1 -->|listen:start| N3["开始监听<br/>重置音频状态"]
    N1 -->|listen:stop| N4["停止监听<br/>触发识别"]
    N1 -->|listen:detect| N5["唤醒词 / 文本直通<br/>可能直接进入对话"]
    N1 -->|abort| N6["打断当前 TTS / 对话"]
    N1 -->|iot| N7["注册或更新 ESP32 IoT 能力"]
    N1 -->|mcp| N8["处理 ESP32 MCP 消息"]
    N1 -->|ping/server| N9["心跳或服务端控制"]

    O --> O1["VAD 判断是否有人声"]
    O1 --> O2["ASR 接收 Opus 音频"]
    O2 --> O3{"是否检测到语音结束"}
    O3 -->|否| O
    O3 -->|是| O4["Opus 解码 / ASR 识别"]
    O4 --> O5["得到用户文本<br/>language / emotion / content"]
    O5 --> P["startToChat"]

    N4 --> O4
    N5 --> P

    P --> P1["发送 STT 给 ESP32<br/>type=stt"]
    P1 --> Q["提交到 Agent 主循环<br/>ConnectionHandler.chat"]

    Q --> R["写入用户消息到 dialogue"]
    R --> S["注入当前轮工具状态提示"]
    S --> T["查询长期记忆 Memory"]
    T --> U["构造 LLM 输入<br/>system prompt + history + memory + skills + tools"]

    U --> V{"是否启用 function_call"}
    V -->|否| W["普通 LLM 流式回复"]
    V -->|是| X["LLM 带 functions/tools 推理"]

    W --> W1["文本片段进入 TTS 队列"]
    W1 --> Z["ESP32 播放语音 / 显示文字"]

    X --> Y{"LLM 输出"}
    Y -->|普通文本| W1
    Y -->|direct_answer| Y1["直接回答<br/>不调用真实工具"]
    Y -->|tool_call| Y2["收集工具调用<br/>name / arguments / id"]

    Y1 --> W1

    Y2 --> AA["UnifiedToolHandler 处理工具调用"]
    AA --> AB["ToolManager 路由工具"]
    AB --> AC{"工具来源"}
    AC -->|server plugin| AC1["本地插件函数"]
    AC -->|skill function| AC2["skills 暴露的函数"]
    AC -->|server MCP| AC3["服务端 MCP 工具"]
    AC -->|device IoT| AC4["ESP32 IoT 控制"]
    AC -->|device MCP| AC5["ESP32 MCP 工具"]

    AC1 --> AD["返回 ActionResponse"]
    AC2 --> AD
    AC3 --> AD
    AC4 --> AD
    AC5 --> AD

    AD --> AE{"Action 类型"}
    AE -->|RESPONSE| AF["工具结果直接回复用户"]
    AE -->|REQLLM| AG["工具结果作为 Observation 写入 dialogue"]
    AE -->|RECORD| AH["记录工具调用链<br/>不再请求 LLM"]
    AE -->|ERROR / NOTFOUND| AI["错误信息进入回复或观察"]

    AF --> W1
    AH --> Z
    AI --> W1

    AG --> AG1["写入 assistant tool_calls"]
    AG1 --> AG2["写入 role=tool 的工具结果"]
    AG2 --> AG3["追加系统提示<br/>把工具输出当作内部观察"]
    AG3 --> Q2["递归 chat(None, depth+1)"]
    Q2 --> T

    Z --> Z1["服务端发送 tts:start"]
    Z1 --> Z2["服务端发送 tts:sentence_start 文本"]
    Z2 --> Z3["服务端发送 Opus 二进制音频"]
    Z3 --> Z4["服务端发送 tts:stop"]
    Z4 --> Z5["ESP32 更新状态<br/>Speaking -> Listening / Idle"]

    Z5 --> L

    H --> CLOSE{"连接断开或超时"}
    CLOSE --> C1["保存会话 / 上报记录 / 清理资源"]
```

## ReAct 工具循环

Agent 的核心推理结构接近 ReAct，但不是文本形式的 `Thought / Action / Observation`，而是基于 function calling 的结构化循环。

```mermaid
flowchart LR
    A["用户文本"] --> B["LLM 推理"]
    B --> C{"需要工具吗？"}
    C -->|否| D["直接回答"]
    C -->|是| E["Action: tool_call"]
    E --> F["执行工具"]
    F --> G["Observation: 工具结果"]
    G --> B
    D --> H["TTS / ESP32 输出"]
```

对应关系：

- Reason：LLM 根据 system prompt、history、memory、skills、functions 判断下一步。
- Action：LLM 输出结构化 tool call。
- Observation：工具结果以 `role=tool` 写回 dialogue。
- Final Answer：LLM 基于已有信息生成最终回复，进入 TTS 和 ESP32 输出链路。

## 关键代码入口

- 服务入口：`app.py`
- WebSocket 服务：`core/websocket_server.py`
- 单连接会话对象：`core/connection.py`
- 文本消息处理：`core/handle/textMessageProcessor.py`
- 音频接收与 ASR 触发：`core/handle/receiveAudioHandle.py`
- TTS 与音频发送：`core/handle/sendAudioHandle.py`
- 工具统一入口：`core/providers/tools/unified_tool_handler.py`
- 工具路由管理：`core/providers/tools/unified_tool_manager.py`
- skills 加载：`core/providers/skills/skill_loader.py`
- ESP32 WebSocket 协议：`C:\workspace\xiaozhi_benyl\main\protocols\websocket_protocol.cc`
- ESP32 JSON 分发：`C:\workspace\xiaozhi_benyl\main\application.cc`

## 一句话总结

ESP32 通过 WebSocket 向服务端发送 JSON 控制消息和 Opus 音频；服务端 Agent 完成 ASR、LLM 推理、工具调用和 TTS；最终再通过同一条连接把文字、音频、点阵图、IoT/MCP 命令推送回 ESP32。
