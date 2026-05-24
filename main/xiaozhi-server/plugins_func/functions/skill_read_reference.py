import os
from typing import TYPE_CHECKING

from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from core.providers.skills import SkillLoader

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

SKILL_READ_REFERENCE_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "skill_read_reference",
        "description": (
            "读取已启用 skill 目录内的引用文件，例如 references/*.md 或 ../other-skill/SKILL.md。"
            "当 skill 要求先读取参考文档、workflow、reference 文件时使用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "发起引用的 skill 名称，例如 lark-im。",
                },
                "path": {
                    "type": "string",
                    "description": "相对该 skill 目录的文件路径，例如 references/lark-im-messages-send.md 或 ../lark-shared/SKILL.md。",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "可选，最大读取字符数，默认12000。",
                },
            },
            "required": ["skill_name", "path"],
        },
    },
}


def _is_within(path: str, root: str) -> bool:
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        return False


@register_function("skill_read_reference", SKILL_READ_REFERENCE_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def skill_read_reference(
    conn: "ConnectionHandler",
    skill_name: str,
    path: str,
    max_chars: int = 12000,
):
    """Read a reference file from an enabled skill directory."""
    try:
        skill_name = str(skill_name or "").strip()
        rel_path = str(path or "").strip().replace("\\", os.sep).replace("/", os.sep)
        if not skill_name or not rel_path:
            return ActionResponse(Action.REQLLM, result="skill_name和path不能为空")

        loader = SkillLoader(conn.config)
        skills = loader.get_enabled_skills()
        skill_by_name = {skill.name: skill for skill in skills}
        source_skill = skill_by_name.get(skill_name)
        if source_skill is None:
            return ActionResponse(Action.REQLLM, result=f"skill未启用或不存在: {skill_name}")

        enabled_roots = [os.path.realpath(skill.path) for skill in skills]
        candidate = os.path.realpath(os.path.join(source_skill.path, rel_path))
        if not any(_is_within(candidate, root) for root in enabled_roots):
            return ActionResponse(
                Action.REQLLM,
                result="拒绝读取未启用skill目录之外的文件",
            )
        if not os.path.isfile(candidate):
            return ActionResponse(Action.REQLLM, result=f"引用文件不存在: {path}")

        max_len = max(1000, min(int(max_chars or 12000), 30000))
        with open(candidate, "r", encoding="utf-8-sig") as f:
            content = f.read(max_len + 1)

        truncated = len(content) > max_len
        if truncated:
            content = content[:max_len] + "\n...<reference truncated>"

        logger.bind(tag=TAG).info(f"读取skill引用文件: {skill_name}:{path}")
        result = f"# skill reference: {skill_name}/{path}\n\n{content}"
        return ActionResponse(Action.REQLLM, result=result)
    except Exception as e:
        return ActionResponse(Action.REQLLM, result=f"读取skill引用文件失败: {e}")
