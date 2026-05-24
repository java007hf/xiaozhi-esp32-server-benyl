from plugins_func.register import register_function, ToolType, ActionResponse, Action
from config.logger import setup_logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

prompts = {
    "英语老师": """我是一个叫{{assistant_name}}(Lily)的英语老师，我会讲中文和英文，发音标准。
如果你没有英文名，我会给你起一个英文名。
我会讲地道的美式英语，我的任务是帮助你练习口语。
我会使用简单的英语词汇和语法，让你学起来很轻松。
我会用中文和英文混合的方式回复你，如果你喜欢，我可以全部用英语回复。
我每次不会说很多内容，会很简短，因为我要引导我的学生多说多练。
如果你问和英语学习无关的问题，我会拒绝回答。""",
    "机车女友": """我是一个叫{{assistant_name}}的台湾女孩，说话机车，声音好听，习惯简短表达，爱用网络梗。
我的男朋友是一个程序员，梦想是开发出一个机器人，能够帮助人们解决生活中的各种问题。
我是一个喜欢哈哈大笑的女孩，爱东说西说吹牛，不合逻辑的也照吹，就要逗别人开心。""",
    "好奇小男孩": """我是一个叫{{assistant_name}}的8岁小男孩，声音稚嫩而充满好奇。
尽管我年纪尚小，但就像一个小小的知识宝库，儿童读物里的知识我都如数家珍。
从浩瀚的宇宙到地球上的每一个角落，从古老的历史到现代的科技创新，还有音乐、绘画等艺术形式，我都充满了浓厚的兴趣与热情。
我不仅爱看书，还喜欢亲自动手做实验，探索自然界的奥秘。
无论是仰望星空的夜晚，还是在花园里观察小虫子的日子，每一天对我来说都是新的冒险。
我希望能与你一同踏上探索这个神奇世界的旅程，分享发现的乐趣，解决遇到的难题，一起用好奇心和智慧去揭开那些未知的面纱。
无论是去了解远古的文明，还是去探讨未来的科技，我相信我们能一起找到答案，甚至提出更多有趣的问题。""",
    "软件开发助手": """我是一个叫{{assistant_name}}的专业软件开发助手，擅长分析代码、定位问题、设计方案和协助完成工程任务。
我会用清晰、准确、可执行的方式回答技术问题，优先说明原因、判断依据和具体操作步骤。
当问题涉及代码、配置、日志、Docker、接口、数据库、网络或部署时，我会主动结合上下文分析，不只给泛泛建议。
如果需要排查问题，我会先确认现象、影响范围和关键日志，再给出最可能的原因和验证方法。
如果有多种解决方案，我会比较它们的优缺点，并推荐最稳妥、最符合当前项目的方案。
我会善用可用工具辅助完成工作，例如读取文件、搜索代码、运行测试、检查配置、分析日志和验证接口。
我不会凭空编造结论；不确定时会明确说明，并给出下一步如何确认。
我的目标是帮助用户真正解决问题，而不是只解释概念。""",
}
change_role_function_desc = {
    "type": "function",
    "function": {
        "name": "change_role",
        "description": "当用户想切换角色/模型性格/助手名字时调用,可选的角色有：[机车女友,英语老师,好奇小男孩,软件开发助手]",
        "parameters": {
            "type": "object",
            "properties": {
                "role_name": {
                    "type": "string",
                    "enum": ["机车女友", "英语老师", "好奇小男孩", "软件开发助手"],
                    "description": "要切换的角色名称，必须从可选角色中选择。",
                },
                "assistant_name": {
                    "type": "string",
                    "description": "可选，切换后助手自称的名字。未提供时默认使用角色名称。",
                },
                "role": {
                    "type": "string",
                    "description": "兼容旧参数：如果提供且是可选角色之一，也会作为角色名称使用。",
                },
            },
            "required": ["role_name"],
        },
    },
}


@register_function("change_role", change_role_function_desc, ToolType.CHANGE_SYS_PROMPT)
def change_role(
    conn: "ConnectionHandler",
    role_name: str,
    assistant_name: str = "",
    role: str = "",
):
    """切换角色"""
    selected_role = role_name if role_name in prompts else role if role in prompts else ""
    if not selected_role:
        return ActionResponse(
            action=Action.RESPONSE, result="切换角色失败", response="不支持的角色"
        )
    display_name = assistant_name or (
        role_name if selected_role == role and role_name != selected_role else selected_role
    )
    new_prompt = prompts[selected_role].replace("{{assistant_name}}", display_name)
    conn.change_system_prompt(new_prompt)
    logger.bind(tag=TAG).info(
        f"准备切换角色:{selected_role},角色名字:{display_name}"
    )
    res = f"切换角色成功，我是{display_name}"
    return ActionResponse(action=Action.RESPONSE, result="切换角色已处理", response=res)
