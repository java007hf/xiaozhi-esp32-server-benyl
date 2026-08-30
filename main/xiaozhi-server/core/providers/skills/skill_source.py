"""Skill metadata sourced from the manager API.

The manager API provides the enabled skill index for an agent. The full
SKILL.md and resource files are loaded from the shared filesystem by
:class:`core.providers.skills.skill_loader.SkillLoader`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SkillDef:
    """Skill metadata delivered from the manager API."""

    name: str
    description: str = ""
    directory: str = ""  # agent skill directory name on the shared filesystem
    content: str = ""  # legacy in-memory skills only
    functions: List[str] = field(default_factory=list)
    files: Dict[str, str] = field(default_factory=dict)  # relative path -> file content
    skill_id: str = ""

    @property
    def has_content(self) -> bool:
        return bool(self.content and self.content.strip())


def parse_skill_def(raw: Dict[str, Any]) -> SkillDef | None:
    """Build a :class:`SkillDef` from a raw API dictionary.

    Accepts metadata from the manager API. ``content`` remains supported for
    legacy in-memory callers, but uploaded skills must be loaded from disk.
    """
    if not isinstance(raw, dict):
        return None

    name = str(raw.get("name") or "").strip()
    description = str(raw.get("description") or "").strip()
    directory = str(raw.get("directory") or raw.get("skill_name") or name).strip()
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
        directory=directory,
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
