"""Tests for manager-delivered (role-level) skill configuration.

These cover the wiring introduced for "按角色配置技能": the manager API
delivers per-agent skills as ``skills_definitions`` in the agent private
config, and :class:`SkillLoader` must pick them up (the ``config`` fallback
path used by ``connection.py``) without being hidden by the file-system
global allow-list.
"""

import unittest
from types import SimpleNamespace

from core.providers.skills import SkillLoader
from core.providers.skills.skill_source import parse_skill_def, parse_skill_defs


def manager_skill_def(
    name="mgr-skill",
    description="Delivered from the manager.",
    functions=None,
    files=None,
):
    functions = functions or ["shell_command", "activate_skill"]
    files = files or {"references/notes.md": "# notes"}
    content = (
        f"---\nname: {name}\n"
        f"description: \"{description}\"\n"
        "metadata:\n  xiaozhi:\n    functions:\n"
        + "\n".join(f"      - {fn}" for fn in functions)
        + "\n---\n\nBody for the manager skill."
    )
    return {
        "id": "mgr-1",
        "name": name,
        "description": description,
        "content": content,
        "functions": functions,
        "files": files,
        "enabled": True,
    }


class SkillConfigManagerFeedTests(unittest.TestCase):
    def test_skills_definitions_picked_up_via_config_fallback(self):
        # connection.py sets conn.config["skills_definitions"]; SkillLoader must
        # read it even when no explicit skill_definitions argument is passed.
        config = {"skills": {"paths": []}, "skills_definitions": [manager_skill_def()]}
        loader = SkillLoader(config)

        skills = loader.get_enabled_skills()

        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0].name, "mgr-skill")
        self.assertEqual(skills[0].source, "memory")
        self.assertEqual(skills[0].functions, ["shell_command", "activate_skill"])
        self.assertIn("# notes", skills[0].files["references/notes.md"])

    def test_skills_definitions_merge_with_filesystem_skills(self):
        config = {"skills": {"paths": []}, "skills_definitions": [manager_skill_def()]}
        conn = SimpleNamespace(config=config)

        # activate_skill reads the loader from conn.config["skills_definitions"]
        from plugins_func.functions.activate_skill import activate_skill

        result = activate_skill(conn, "mgr-skill")

        self.assertIn("# activated skill: mgr-skill", result.result)
        self.assertIn("references/notes.md", result.result)

    def test_memory_skills_bypass_global_allowlist(self):
        # Global allow-list only restricts file-system skills; role-level
        # skills delivered via skills_definitions must always be available.
        config = {
            "skills": {"enabled": ["some-other-skill"]},
            "skills_definitions": [
                manager_skill_def(),
                manager_skill_def(name="second-skill", description="Second."),
            ],
        }
        loader = SkillLoader(config)
        names = {s.name for s in loader.get_enabled_skills()}

        self.assertEqual(names, {"mgr-skill", "second-skill"})

    def test_parse_skill_def_accepts_manager_shape(self):
        raw = manager_skill_def()
        skill_def = parse_skill_def(raw)

        self.assertIsNotNone(skill_def)
        self.assertEqual(skill_def.name, "mgr-skill")
        self.assertEqual(skill_def.skill_id, "mgr-1")
        self.assertEqual(skill_def.functions, ["shell_command", "activate_skill"])
        self.assertEqual(skill_def.files, {"references/notes.md": "# notes"})
        self.assertTrue(skill_def.has_content)

    def test_parse_skill_defs_filters_invalid(self):
        raw = [
            manager_skill_def(),
            {"id": "no-name-no-content"},
            "broken",
            None,
        ]
        parsed = parse_skill_defs(raw)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].name, "mgr-skill")


if __name__ == "__main__":
    unittest.main()
