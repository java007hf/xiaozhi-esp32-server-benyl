"""In-memory skill definitions sourced from the manager API.

When skills are managed in the console (CRUD in the database) instead of -- or
in addition to -- the file-system ``skills/`` directory, the server receives
their definitions through the agent private config (``skills_definitions``).
These definitions are kept in memory per connection and merged with the
file-system scan by :class:`core.providers.skills.skill_loader.SkillLoader`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SkillDef:
    """A skill definition delivered from the manager (API / DB), not from disk."""

    name: str
    description: str = ""
    content: str = ""  # full SKILL.md text (YAML frontmatter + Markdown body)
    functions: List[str] = field(default_factory=list)
    files: Dict[str, str] = field(default_factory=dict)  # relative path -> file content
    skill_id: str = ""

    @property
    def has_content(self) -> bool:
        return bool(self.content and self.content.strip())


def parse_skill_def(raw: Dict[str, Any]) -> SkillDef | None:
    """Build a :class:`SkillDef` from a raw API dictionary.

    Accepts either a fully-formed ``content`` (the whole SKILL.md) or explicit
    ``name`` / ``description`` / ``functions`` / ``files`` fields. Returns
    ``None`` when the definition carries neither a usable name nor content.
    """
    if not isinstance(raw, dict):
        return None

    name = str(raw.get("name") or "").strip()
    description = str(raw.get("description") or "").strip()
    content = str(raw.get("content") or "")
    functions = raw.get("functions") or []
    if not isinstance(functions, list):
        functions = []
    files = raw.get("files") or {}
    if not isinstance(files, dict):
        files = {}

    # Derive missing basics from the embedded frontmatter when possible.
    if (not name or not description) and content:
        from core.providers.skills.skill_loader import SkillLoader

        probe = SkillLoader({})
        manifest, _ = probe._split_frontmatter(content)
        if manifest:
            name = name or str(manifest.get("name") or "").strip()
            description = description or str(manifest.get("description") or "").strip()

    if not name and not content.strip():
        return None

    return SkillDef(
        name=name,
        description=description,
        content=content,
        functions=[str(item) for item in functions],
        files={str(key): str(value) for key, value in files.items()},
        skill_id=str(raw.get("id") or ""),
    )


def parse_skill_defs(raw_list: Any) -> List[SkillDef]:
    """Parse a list of raw API skill definitions, dropping invalid entries."""
    if not isinstance(raw_list, list):
        return []
    result: List[SkillDef] = []
    for raw in raw_list:
        skill_def = parse_skill_def(raw)
        if skill_def is not None:
            result.append(skill_def)
    return result
