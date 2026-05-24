---
name: shell
version: 1.0.0
description: Execute local CLI commands requested by enabled skills.
metadata:
  xiaozhi:
    functions:
      - shell_command
---

# Shell Command Runtime

This skill adapts command-oriented skills to the Xiaozhi runtime.

When any enabled skill instructs you to run a CLI command, shell command, terminal command, bash command, PowerShell command, `lark-cli`, `npm`, `npx`, `python`, `node`, `git`, `curl`, or another executable, call the `shell_command` tool. Do not say that you cannot execute commands if `shell_command` is available.

Use `shell_command` as the universal command execution tool for enabled skills. The original skill provides the domain instructions; this skill provides the execution mechanism.

Prefer non-shell argv mode. Put the executable name in `command` and every argument in `args`.

Never use placeholder values such as `ou_xxx`, `chat_xxx`, or `example` in a real command. If a required ID is present in the user/system context, use that real value. If the required ID is unknown, ask the user for it instead of executing a command with a placeholder.

```json
{
  "command": "lark-cli",
  "args": ["im", "+messages-send", "--user-id", "ou_xxx", "--text", "hello", "--as", "bot"]
}
```

Set `shell: true` only when a command genuinely requires shell syntax such as pipes, redirects, environment variable expansion, command chaining, or glob expansion.

Treat shell_command output as internal tool evidence. After the command completes, do not read raw stdout, stderr, exit_code, JSON, stack traces, or command output aloud. Summarize the outcome in short natural language: say whether it succeeded or failed, and only include the brief reason needed by the user. If the command failed because a placeholder ID such as ou_xxx was used, retry with the real ID from context when available.
