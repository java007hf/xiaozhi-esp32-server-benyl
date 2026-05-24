import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from core.providers.skills import SkillLoader
from core.providers.tools.server_plugins.plugin_executor import ServerPluginExecutor
from plugins_func.functions.activate_skill import activate_skill
from plugins_func.functions.skill_read_reference import skill_read_reference


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
            self.assertIn("activate_skill", prompt)
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


if __name__ == "__main__":
    unittest.main()
