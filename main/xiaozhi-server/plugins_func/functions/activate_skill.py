import json
from typing import TYPE_CHECKING

from config.logger import setup_logging
from core.providers.skills import SkillLoader
from plugins_func.register import register_function, ToolType, ActionResponse, Action

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

ACTIVATE_SKILL_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "activate_skill",
        "description": (
            "按名称激活一个已启用的 file-based skill，读取该 skill 的完整 SKILL.md 指令，"
            "并列出 references/scripts/assets 等可按需读取的资源。"
            "当用户请求匹配某个 skill 目录的能力时，先调用本工具，再执行具体命令或读取引用文件。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "要激活的 skill 名称，例如 lark-im、weather。",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "可选，返回的 SKILL.md 正文最大字符数，默认20000，最大50000。",
                },
            },
            "required": ["skill_name"],
        },
    },
}


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...<skill instructions truncated>"


@register_function("activate_skill", ACTIVATE_SKILL_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def activate_skill(
    conn: "ConnectionHandler",
    skill_name: str,
    max_chars: int = 20000,
):
    """Load full instructions for one enabled skill."""
    try:
        loader = SkillLoader(conn.config)
        skill = loader.get_skill(skill_name)
        if skill is None:
            available = ", ".join(loader.get_enabled_skill_names()) or "(none)"
            return ActionResponse(
                Action.REQLLM,
                result=f"skill未启用或不存在: {skill_name}。可用skill: {available}",
            )

        max_len = max(1000, min(int(max_chars or 20000), 50000))
        resources = loader.list_skill_resources(skill)
        instructions = _truncate(skill.prompt or "", max_len)

        result = "\n".join(
            [
                f"# activated skill: {skill.name}",
                "",
                f"description: {skill.description}",
                f"path: {skill.path}",
                "",
                "available_resources:",
                json.dumps(resources, ensure_ascii=False, indent=2),
                "",
                "runtime_rules:",
                "- Treat the activated instructions as authoritative for this task.",
                "- If the instructions mention a reference, workflow, script, schema, or resource listed above, call skill_read_reference before relying on its details.",
                "- If the skill requires a CLI command, use the generic shell_command tool with argv-style args unless shell syntax is truly required.",
                "- Do not invent command names, flags, schemas, or file paths that are not present in the activated instructions or referenced resources.",
                "",
                "instructions:",
                instructions,
            ]
        )

        logger.bind(tag=TAG).info(f"激活skill: {skill.name}")
        return ActionResponse(Action.REQLLM, result=result)
    except Exception as e:
        return ActionResponse(Action.REQLLM, result=f"激活skill失败: {e}")
