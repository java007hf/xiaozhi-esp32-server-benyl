import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from core.providers.skills import SkillLoader
from core.providers.skills.skill_source import parse_skill_defs
from core.providers.tools.server_plugins.plugin_executor import ServerPluginExecutor
from plugins_func.functions.activate_skill import activate_skill
from plugins_func.functions.skill_read_reference import skill_read_reference


def memory_skill_def(
    name="memory-skill",
    description="Memory only skill.",
    functions=None,
    files=None,
    body="Memory body instructions.",
):
    functions = functions or ["shell_command"]
    files = files or {"scripts/main.py": "print('hi')"}
    content = (
        f"---\nname: {name}\n"
        f"description: \"{description}\"\n"
        "metadata:\n  xiaozhi:\n    functions:\n"
        + "\n".join(f"      - {fn}" for fn in functions)
        + f"\n---\n\n{body}"
    )
    return {
        "id": "mem-1",
        "name": name,
        "description": description,
        "content": content,
        "functions": functions,
        "files": files,
    }


def write_skill(root: Path, name: str, description: str, body: str, metadata: str = ""):
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    metadata_block = f"\n{metadata.rstrip()}" if metadata else ""
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\nversion: 1.0.0\ndescription: \"{description}\"{metadata_block}\n---\n\n{body}",
        encoding="utf-8",
    )
    return skill_dir


class SkillRuntimeTests(unittest.TestCase):
    def make_config(self, root: Path):
        return {
            "selected_module": {"Intent": "function_call"},
            "Intent": {"function_call": {"functions": []}},
            "skills": {"paths": [str(root)]},
        }

    def test_catalog_prompt_is_routing_index_not_full_skill_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(
                root,
                "demo-skill",
                "Handles demo tasks.",
                "Full instructions contain SECRET_COMMAND and detailed flags.",
            )

            prompt = SkillLoader(self.make_config(root)).build_catalog_prompt_block()

            self.assertIn("`demo-skill`: Handles demo tasks.", prompt)
            self.assertIn("Enabled skills are supported capabilities", prompt)
            self.assertIn("activate_skill", prompt)
            self.assertIn("Do not say you cannot perform a task", prompt)
            self.assertNotIn("SECRET_COMMAND", prompt)

    def test_activate_skill_returns_instructions_and_resource_manifest_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = write_skill(
                root,
                "demo-skill",
                "Handles demo tasks.",
                "Read references/details.md before executing the command.",
            )
            references_dir = skill_dir / "references"
            references_dir.mkdir()
            (references_dir / "details.md").write_text(
                "REFERENCE_SECRET: exact command lives here",
                encoding="utf-8",
            )
            conn = SimpleNamespace(config=self.make_config(root))

            result = activate_skill(conn, "demo-skill")

            self.assertIn("# activated skill: demo-skill", result.result)
            self.assertIn("references/details.md", result.result)
            self.assertIn("Read references/details.md", result.result)
            self.assertNotIn("REFERENCE_SECRET", result.result)

    def test_skill_read_reference_reads_enabled_resource_and_blocks_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root.parent / f"outside-{os.getpid()}.txt"
            outside.write_text("outside", encoding="utf-8")
            try:
                skill_dir = write_skill(
                    root,
                    "demo-skill",
                    "Handles demo tasks.",
                    "Read references/details.md.",
                )
                references_dir = skill_dir / "references"
                references_dir.mkdir()
                (references_dir / "details.md").write_text("exact details", encoding="utf-8")
                conn = SimpleNamespace(config=self.make_config(root))

                ok = skill_read_reference(conn, "demo-skill", "references/details.md")
                blocked = skill_read_reference(conn, "demo-skill", f"../../{outside.name}")

                self.assertIn("exact details", ok.result)
                self.assertIn("拒绝读取", blocked.result)
            finally:
                outside.unlink(missing_ok=True)

    def test_activate_skill_tool_schema_exposes_enabled_skill_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(
                root,
                "skill-runtime",
                "Runtime support.",
                "Runtime instructions.",
                metadata="""
metadata:
  xiaozhi:
    functions:
      - activate_skill
""",
            )
            write_skill(root, "demo-skill", "Handles demo tasks.", "Instructions.")
            conn = SimpleNamespace(config=self.make_config(root))

            tools = ServerPluginExecutor(conn).get_tools()
            skill_name_schema = tools["activate_skill"].description["function"][
                "parameters"
            ]["properties"]["skill_name"]

            self.assertEqual(
                skill_name_schema["enum"],
                ["demo-skill", "skill-runtime"],
            )


class InMemorySkillTests(unittest.TestCase):
    """Skills delivered from the manager API (DB) instead of the file system."""

    def test_memory_skill_loaded_with_functions(self):
        loader = SkillLoader({"skills": {"paths": []}}, skill_definitions=[memory_skill_def()])
        skills = loader.get_enabled_skills()

        self.assertEqual(len(skills), 1)
        skill = skills[0]
        self.assertEqual(skill.name, "memory-skill")
        self.assertEqual(skill.source, "memory")
        self.assertEqual(skill.functions, ["shell_command"])
        self.assertIn("print('hi')", skill.files["scripts/main.py"])

    def test_memory_skill_appears_in_catalog(self):
        loader = SkillLoader({"skills": {"paths": []}}, skill_definitions=[memory_skill_def()])
        catalog = loader.build_catalog_prompt_block()

        self.assertIn("`memory-skill`: Memory only skill.", catalog)
        self.assertIn("activate_skill", catalog)

    def test_memory_skill_resources_from_files(self):
        loader = SkillLoader({"skills": {"paths": []}}, skill_definitions=[memory_skill_def()])
        skill = loader.get_skill("memory-skill")
        resources = loader.list_skill_resources(skill)

        self.assertIn("scripts", resources)
        self.assertIn("scripts/main.py", resources["scripts"])

    def test_filesystem_and_memory_skills_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "fs-skill", "From disk.", "Disk instructions.")

            loader = SkillLoader(
                {"skills": {"paths": [str(root)]}},
                skill_definitions=[memory_skill_def()],
            )
            names = {s.name for s in loader.get_enabled_skills()}

            self.assertEqual(names, {"fs-skill", "memory-skill"})

    def test_memory_skills_bypass_global_enabled_allowlist(self):
        # Role-level (in-memory) skills are already filtered by their own
        # `enabled` flag on the manager side, so they must NOT be silently
        # hidden by the global file-system allow-list. See skill_loader.py
        # get_enabled_skills(): the allow-list only restricts file-system skills.
        loader = SkillLoader(
            {"skills": {"enabled": ["memory-skill"]}},
            skill_definitions=[memory_skill_def(), memory_skill_def(name="other-skill", description="Other.")],
        )
        names = {s.name for s in loader.get_enabled_skills()}

        self.assertEqual(names, {"memory-skill", "other-skill"})

    def test_parse_skill_defs_drops_invalid_entries(self):
        raw = [
            memory_skill_def(),
            {"id": "bad"},
            "not-a-dict",
            None,
        ]
        parsed = parse_skill_defs(raw)

        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].name, "memory-skill")

    def test_activate_skill_reads_memory_skill(self):
        config = {"skills": {"paths": []}, "skills_definitions": [memory_skill_def()]}
        conn = SimpleNamespace(config=config)

        result = activate_skill(conn, "memory-skill")

        self.assertIn("# activated skill: memory-skill", result.result)
        self.assertIn("(in-memory)", result.result)
        self.assertIn("scripts/main.py", result.result)
        self.assertIn("Memory body instructions.", result.result)

    def test_skill_read_reference_reads_memory_file(self):
        config = {"skills": {"paths": []}, "skills_definitions": [memory_skill_def()]}
        conn = SimpleNamespace(config=config)

        ok = skill_read_reference(conn, "memory-skill", "scripts/main.py")
        missing = skill_read_reference(conn, "memory-skill", "scripts/nope.py")

        self.assertIn("print('hi')", ok.result)
        self.assertIn("引用文件不存在(in-memory)", missing.result)


if __name__ == "__main__":
    unittest.main()
