-- Switch Volcengine bidirectional streaming TTS console fields to the new API Key auth.
-- Runtime keeps appid/access_token compatibility for existing old-console configs.

UPDATE `ai_model_provider`
SET `fields` = '[
  {"key": "ws_url", "type": "string", "label": "WebSocket地址"},
  {"key": "api_key", "type": "string", "label": "API Key"},
  {"key": "resource_id", "type": "string", "label": "资源ID"},
  {"key": "speaker", "type": "string", "label": "默认音色"},
  {"key": "enable_ws_reuse", "type": "boolean", "label": "是否开启链接复用", "default": true},
  {"key": "audio_params", "type": "dict", "label": "音频输出配置"},
  {"key": "additions", "type": "dict", "label": "高级文本处理配置"},
  {"key": "mix_speaker", "type": "dict", "label": "混音控制配置"}
]'
WHERE `id` = 'SYSTEM_TTS_HSDSTTS';

UPDATE `ai_model_config`
SET `config_json` = JSON_SET(`config_json`, '$.api_key', COALESCE(JSON_UNQUOTE(JSON_EXTRACT(`config_json`, '$.api_key')), ''))
WHERE `id` IN ('TTS_HuoshanDoubleStreamTTS', 'TTS_HSDSTTS_V2');

UPDATE `ai_model_config`
SET `remark` = '火山引擎双向流式TTS配置说明：
1. 访问 https://www.volcengine.com/ 注册并开通火山引擎账号
2. 访问火山语音服务控制台开通语音合成大模型并购买音色
3. 新版控制台请填写 API Key；旧版 appid/access_token 配置仍可由服务端兼容读取
4. 资源ID示例：volc.service_type.10029（大模型语音合成及混音）、seed-tts-2.0（豆包语音合成模型2.0）
5. 开启 WebSocket 连接复用可减少建连损耗，但空闲连接会占用并发数

详细参数文档：https://www.volcengine.com/docs/6561/1329505

audio_params：音频输出配置，可添加火山引擎支持的音频参数，例如：
  {"speech_rate": 10, "loudness_rate": 5, "emotion": "happy", "emotion_scale": 4}

additions：高级文本处理配置，例如：
  {"post_process": {"pitch": 2}, "aigc_metadata": {}, "cache_config": {}}

mix_speaker：混音控制配置，主要适用于 TTS 1.0，使用时通常需要将 speaker 设置为 custom_mix_bigtts。'
WHERE `id` IN ('TTS_HuoshanDoubleStreamTTS', 'TTS_HSDSTTS_V2');
