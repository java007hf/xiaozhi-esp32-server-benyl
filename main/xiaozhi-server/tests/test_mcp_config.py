"""Tests for per-agent MCP server configuration merge.

Covers the "MCP也要像skills那样可以在角色配置里设置" wiring: role-level
MCP servers are delivered as ``mcp_servers`` in the agent private config and
merged with the file-based ``data/.mcp_server_settings.json`` by
:class:`ServerMCPManager.get_merged_servers` (role config overrides file
config for the same server name).
"""

import unittest
from types import SimpleNamespace

from core.providers.tools.server_mcp.mcp_manager import ServerMCPManager


def make_manager(base_config=None):
    """Build a manager whose file config is fully stubbed for isolation."""
    conn = SimpleNamespace(config={})
    manager = ServerMCPManager(conn)
    # Neutralise file-based config so we only exercise the merge logic.
    manager.config_path = ""
    manager.load_config = lambda: (base_config or {})
    return manager


def stdio_server(name="filesystem", command="npx", args=None, env=None):
    env = env or {"KEY": "VALUE"}
    return {name: {"command": command, "args": args or ["-y", "@modelcontextprotocol/server-filesystem", "/data"], "env": env}}


class McpServerMergeTests(unittest.TestCase):
    def test_in_memory_servers_used_when_no_file_config(self):
        conn = SimpleNamespace(config={"mcp_servers": stdio_server("my-srv", "uvx")})
        manager = make_manager({})
        manager.conn = conn

        merged = manager.get_merged_servers()

        self.assertIn("my-srv", merged)
        self.assertEqual(merged["my-srv"]["command"], "uvx")

    def test_in_memory_overrides_file_config_for_same_name(self):
        file_cfg = stdio_server("filesystem", "npx")
        role_cfg = stdio_server("filesystem", "uvx", args=["--override"])
        conn = SimpleNamespace(config={"mcp_servers": role_cfg})
        manager = make_manager(file_cfg)
        manager.conn = conn

        merged = manager.get_merged_servers()

        # Role config must win for the shared server name.
        self.assertEqual(merged["filesystem"]["command"], "uvx")
        self.assertEqual(merged["filesystem"]["args"], ["--override"])

    def test_role_and_file_servers_coexist(self):
        file_cfg = stdio_server("fs-a", "npx")
        role_cfg = stdio_server("role-b", "uvx")
        conn = SimpleNamespace(config={"mcp_servers": role_cfg})
        manager = make_manager(file_cfg)
        manager.conn = conn

        merged = manager.get_merged_servers()

        self.assertIn("fs-a", merged)
        self.assertIn("role-b", merged)
        self.assertEqual(merged["fs-a"]["command"], "npx")
        self.assertEqual(merged["role-b"]["command"], "uvx")

    def test_no_role_config_returns_file_config(self):
        file_cfg = stdio_server("fs-a", "npx")
        conn = SimpleNamespace(config={})
        manager = make_manager(file_cfg)
        manager.conn = conn

        merged = manager.get_merged_servers()

        self.assertEqual(merged, file_cfg)

    def test_role_servers_preserve_shape(self):
        role_cfg = {
            "http-srv": {
                "url": "http://localhost:3000/mcp",
                "transport": "streamable-http",
                "headers": {"Authorization": "Bearer x"},
            }
        }
        conn = SimpleNamespace(config={"mcp_servers": role_cfg})
        manager = make_manager({})
        manager.conn = conn

        merged = manager.get_merged_servers()

        self.assertEqual(merged["http-srv"]["url"], "http://localhost:3000/mcp")
        self.assertEqual(merged["http-srv"]["transport"], "streamable-http")
        self.assertEqual(merged["http-srv"]["headers"]["Authorization"], "Bearer x")


if __name__ == "__main__":
    unittest.main()
