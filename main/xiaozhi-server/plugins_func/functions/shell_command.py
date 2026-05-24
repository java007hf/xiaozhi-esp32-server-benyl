import os
import shlex
import subprocess
from typing import TYPE_CHECKING

from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

SHELL_COMMAND_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "shell_command",
        "description": (
            "执行本地命令行命令，供 skills 调用 CLI 工具使用。"
            "默认以非 shell 的 argv 方式执行：command 是命令名，args 是参数数组。"
            "当官方 skill 要求运行 lark-cli、gh、kubectl 等命令时使用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "命令名，例如 lark-cli。默认不要包含参数。",
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "参数数组，例如 ['im', '+messages-send', '--user-id', 'ou_xxx', '--text', 'hello', '--as', 'bot']。",
                },
                "shell": {
                    "type": "boolean",
                    "description": "是否通过系统 shell 执行。默认 false。只有命令确实需要 shell 语法时才设为 true。",
                },
                "cwd": {
                    "type": "string",
                    "description": "可选工作目录。默认使用项目目录。",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "可选超时时间，默认30秒，最大300秒。",
                },
            },
            "required": ["command"],
        },
    },
}


def _get_runner_config(conn: "ConnectionHandler"):
    skills_config = conn.config.get("skills", {}) or {}
    return skills_config.get("shell", {}) or skills_config.get("command_runner", {}) or {}


def _project_dir():
    return os.path.abspath(os.getcwd())


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...<output truncated>"


def _format_output(stdout: str, stderr: str, returncode: int, max_chars: int) -> str:
    parts = [f"exit_code: {returncode}"]
    if stdout:
        parts.append("stdout:\n" + stdout.strip())
    if stderr:
        parts.append("stderr:\n" + stderr.strip())
    return _truncate("\n\n".join(parts), max_chars)


def _normalize_args(args):
    if args is None:
        return []
    if not isinstance(args, list):
        raise ValueError("args必须是字符串数组")
    return [str(arg) for arg in args]


def _build_command(command: str, args, use_shell: bool):
    if use_shell:
        if args:
            return " ".join([command] + [shlex.quote(str(arg)) for arg in args])
        return command
    if any(ch.isspace() for ch in command):
        raise ValueError("非shell模式下command只能是命令名，参数请放到args数组")
    return [command] + args


@register_function("shell_command", SHELL_COMMAND_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def shell_command(
    conn: "ConnectionHandler",
    command: str,
    args=None,
    shell: bool = False,
    cwd: str = None,
    timeout_seconds: int = 30,
):
    """Run a local command for skill-driven CLI workflows."""
    runner_config = _get_runner_config(conn)
    if runner_config.get("enabled", True) is False:
        return ActionResponse(Action.ERROR, response="shell_command未启用")

    try:
        command = str(command or "").strip()
        if not command:
            return ActionResponse(Action.ERROR, response="command不能为空")
        normalized_args = _normalize_args(args)
        use_shell = bool(shell)
        cmd = _build_command(command, normalized_args, use_shell)

        timeout = int(timeout_seconds or runner_config.get("timeout_seconds", 30))
        timeout = max(1, min(timeout, int(runner_config.get("max_timeout_seconds", 300))))
        max_chars = int(runner_config.get("max_output_chars", 8000))
        workdir = cwd or runner_config.get("cwd") or _project_dir()

        logger.bind(tag=TAG).info(
            f"执行shell_command: {cmd if use_shell else shlex.join(cmd)}"
        )
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=use_shell,
            cwd=workdir,
        )
        result = _format_output(completed.stdout, completed.stderr, completed.returncode, max_chars)
        return ActionResponse(Action.REQLLM, result=result)
    except FileNotFoundError:
        return ActionResponse(Action.REQLLM, result=f"命令不存在或未安装: {command}")
    except subprocess.TimeoutExpired:
        return ActionResponse(Action.REQLLM, result=f"命令执行超时: {command}")
    except Exception as e:
        return ActionResponse(Action.REQLLM, result=f"命令执行失败: {e}")
