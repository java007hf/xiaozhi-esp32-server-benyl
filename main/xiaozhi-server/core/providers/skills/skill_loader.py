"""Codex-compatible file-based skill loader.

Each skill is a directory containing a required SKILL.md file with YAML
frontmatter and Markdown instructions. Execution still goes through the unified
tool manager, so skills do not introduce a second tool runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Any, Dict, List

import yaml

from config.config_loader import get_project_dir
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


@dataclass
class Skill:
    name: str
    description: str = ""
    functions: List[str] = field(default_factory=list)
    prompt: str = ""
    path: str = ""


class SkillLoader:
    """Loads enabled skills from configured directories."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.skills_config = self.config.get("skills", {}) or {}
        self._skills: List[Skill] | None = None

    def get_enabled_skills(self) -> List[Skill]:
        if self._skills is not None:
            return self._skills

        enabled_names = self.skills_config.get("enabled")
        enabled_set = None
        if enabled_names is not None:
            enabled_set = {str(name) for name in enabled_names}

        skills = []
        for skill_dir in self._get_skill_dirs():
            skill_path = os.path.join(skill_dir, "SKILL.md")
            if not os.path.exists(skill_path):
                continue

            skill = self._load_skill(skill_path)
            if not skill:
                continue

            if enabled_set is not None and skill.name not in enabled_set:
                continue

            skills.append(skill)

        self._skills = skills
        return skills

    def get_enabled_functions(self) -> List[str]:
        functions: List[str] = []
        for skill in self.get_enabled_skills():
            functions.extend(skill.functions)
        return list(dict.fromkeys(functions))

    def get_skill(self, name: str) -> Skill | None:
        name = str(name or "").strip()
        for skill in self.get_enabled_skills():
            if skill.name == name:
                return skill
        return None

    def get_enabled_skill_names(self) -> List[str]:
        return [skill.name for skill in self.get_enabled_skills()]

    def build_catalog_prompt_block(self) -> str:
        skills = self.get_enabled_skills()
        if not skills:
            return ""

        lines = [
            "",
            "# Enabled Skills Catalog",
            "You have file-based skills available. The catalog below is only a routing index, not the full instructions.",
            "When the user's request matches a skill, call `activate_skill` with that skill name before using domain commands or referenced files.",
            "After activation, follow that skill's instructions. If the activated skill points to a reference file, workflow, script, or other local resource, read it with `skill_read_reference` before relying on details from it.",
            "Do not invent command names, flags, schemas, or file paths from the catalog alone.",
            "",
            "Available skills:",
        ]

        for skill in skills:
            lines.append(f"- `{skill.name}`: {skill.description}")

        return "\n".join(lines)

    def build_prompt_block(self) -> str:
        blocks = []
        for skill in self.get_enabled_skills():
            prompt = (skill.prompt or "").strip()
            if not prompt:
                continue
            blocks.append(f"## {skill.name}\n{prompt}")

        if not blocks:
            return ""

        return "\n\n# Enabled Skills\n" + "\n\n".join(blocks)

    def list_skill_resources(self, skill: Skill, max_files: int = 80) -> Dict[str, List[str]]:
        resources: Dict[str, List[str]] = {}
        for dirname in ["references", "scripts", "assets"]:
            root = os.path.join(skill.path, dirname)
            if not os.path.isdir(root):
                continue

            items: List[str] = []
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames.sort()
                filenames.sort()
                for filename in filenames:
                    rel_path = os.path.relpath(
                        os.path.join(dirpath, filename), skill.path
                    ).replace(os.sep, "/")
                    items.append(rel_path)
                    if len(items) >= max_files:
                        items.append("...<resources truncated>")
                        break
                if len(items) > max_files:
                    break
            if items:
                resources[dirname] = items

        return resources

    def _get_skill_dirs(self) -> List[str]:
        project_dir = get_project_dir()
        configured_paths = self.skills_config.get("paths") or ["skills"]
        skill_dirs: List[str] = []

        for path in configured_paths:
            abs_path = path if os.path.isabs(path) else os.path.join(project_dir, path)
            if not os.path.isdir(abs_path):
                continue
            for entry in sorted(os.scandir(abs_path), key=lambda item: item.name):
                if entry.is_dir():
                    skill_dirs.append(entry.path)

        return skill_dirs

    def _load_skill(self, skill_path: str) -> Skill | None:
        try:
            with open(skill_path, "r", encoding="utf-8") as f:
                content = f.read()

            manifest, body = self._split_frontmatter(content)
            if manifest is None:
                logger.bind(tag=TAG).warning(f"Skill missing YAML frontmatter: {skill_path}")
                return None

            name = str(manifest.get("name") or "").strip()
            description = str(manifest.get("description") or "").strip()
            if not name or not description:
                logger.bind(tag=TAG).warning(
                    f"Skill frontmatter requires name and description: {skill_path}"
                )
                return None

            functions = self._get_xiaozhi_functions(manifest)
            if not isinstance(functions, list):
                logger.bind(tag=TAG).warning(
                    f"Skill {name} metadata.xiaozhi.functions must be a list: {skill_path}"
                )
                functions = []

            return Skill(
                name=name,
                description=description,
                functions=[str(function) for function in functions],
                prompt=body,
                path=os.path.dirname(skill_path),
            )
        except Exception as e:
            logger.bind(tag=TAG).error(f"加载 skill 失败 {skill_path}: {e}")
            return None

    def _split_frontmatter(self, content: str) -> tuple[Dict[str, Any] | None, str]:
        lines = content.splitlines()
        if not lines or lines[0].strip() != "---":
            return None, content

        end_index = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_index = i
                break

        if end_index is None:
            return None, content

        frontmatter = "\n".join(lines[1:end_index])
        body = "\n".join(lines[end_index + 1 :]).strip()
        return yaml.safe_load(frontmatter) or {}, body

    def _get_xiaozhi_functions(self, manifest: Dict[str, Any]) -> List[str]:
        """Read XiaoZhi-specific runtime bindings from optional metadata."""
        metadata = manifest.get("metadata") or {}
        if isinstance(metadata, dict):
            xiaozhi = metadata.get("xiaozhi") or {}
            if isinstance(xiaozhi, dict):
                return xiaozhi.get("functions") or []
        return []
