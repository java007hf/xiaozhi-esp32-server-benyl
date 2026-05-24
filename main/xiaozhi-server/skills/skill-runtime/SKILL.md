---
name: skill-runtime
version: 1.0.0
description: Runtime support for file-based skills, including reading referenced skill files and retrying correctable tool failures.
metadata:
  xiaozhi:
    functions:
      - activate_skill
      - skill_read_reference
---

# Skill Runtime

This runtime adapts Codex-style file-based skills to Xiaozhi.

When the user request matches an enabled skill from the catalog, call `activate_skill` first. The catalog only contains routing summaries; it is not enough to execute domain-specific commands.

After `activate_skill` returns the skill instructions and available resources, follow those instructions for the current task.

When working with an enabled skill, actively call `skill_read_reference` whenever the skill references another file, a reference document, a workflow, or a `references/*.md` file that may contain the exact command, parameters, required workflow, permissions, or constraints needed for the current task. Do this proactively before executing the domain command when those details matter; do not wait for a tool failure first.

Use `activate_skill` with the exact skill name shown in the catalog. Example:

```json
{
  "skill_name": "lark-im"
}
```

Use `skill_read_reference` with the source skill name and the relative path shown by the skill. Examples:

```json
{
  "skill_name": "lark-im",
  "path": "references/lark-im-messages-send.md"
}
```

```json
{
  "skill_name": "lark-im",
  "path": "../lark-shared/SKILL.md"
}
```

Treat tool outputs as observations. If a tool command fails and the output clearly suggests a fix, do not immediately give the final answer. Use the observation and, when useful, call `skill_read_reference` for the relevant skill reference before retrying with a corrected tool call. Keep retries limited; after repeated failure, summarize the failure briefly.

Final user-facing replies should be short natural language. Do not read raw stdout, stderr, exit_code, JSON, stack traces, or full command output aloud unless the user explicitly asks for command output.
