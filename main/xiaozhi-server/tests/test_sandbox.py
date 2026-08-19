"""Tests for skill sandbox execution.

Per the "skills支持沙箱运行" requirement, when the per-agent sandbox is
enabled (``conn.config["skills"]["sandbox"]["enabled"]``) the
``shell_command`` tool must run *all* commands -- not just Python -- through
``run_sandboxed`` (which applies resource limits / privilege drop / optional
network isolation). These tests verify that routing and the runner itself.
"""

import sys
import unittest
from types import SimpleNamespace
from unittest import mock

from plugins_func.functions.shell_command import shell_command
from core.providers.tools.sandbox.runner import SandboxResult, run_sandboxed


def make_conn(sandbox_enabled=True, network=False, timeout=30, runner_enabled=True):
    return SimpleNamespace(
        config={
            "skills": {
                "shell": {"enabled": runner_enabled, "timeout_seconds": timeout},
                "sandbox": {"enabled": sandbox_enabled, "network": network, "timeout": timeout},
            }
        }
    )


class ShellCommandSandboxRoutingTests(unittest.TestCase):
    def test_sandbox_applies_to_non_python_command(self):
        conn = make_conn(sandbox_enabled=True)
        with mock.patch(
            "plugins_func.functions.shell_command.run_sandboxed"
        ) as run_mock:
            run_mock.return_value = SandboxResult(
                stdout="ok", stderr="", returncode=0, sandbox_applied=True
            )

            shell_command(conn, "lark-cli", args=["im", "+messages-send", "--text", "hi"])

            self.assertTrue(run_mock.called)
            argv = run_mock.call_args.args[0]
            self.assertEqual(argv, ["lark-cli", "im", "+messages-send", "--text", "hi"])

    def test_sandbox_applies_to_python_command(self):
        conn = make_conn(sandbox_enabled=True)
        with mock.patch(
            "plugins_func.functions.shell_command.run_sandboxed"
        ) as run_mock:
            run_mock.return_value = SandboxResult(stdout="", stderr="", returncode=0)

            shell_command(conn, "python", args=["-c", "print('x')"])

            self.assertTrue(run_mock.called)
            argv = run_mock.call_args.args[0]
            self.assertEqual(argv, ["python", "-c", "print('x')"])

    def test_sandbox_shell_true_builds_sh_c_argv(self):
        conn = make_conn(sandbox_enabled=True)
        with mock.patch(
            "plugins_func.functions.shell_command.run_sandboxed"
        ) as run_mock:
            run_mock.return_value = SandboxResult(stdout="", stderr="", returncode=0)

            shell_command(conn, "cat", args=["/etc/hosts"], shell=True)

            self.assertTrue(run_mock.called)
            argv = run_mock.call_args.args[0]
            self.assertEqual(argv[0], "sh")
            self.assertEqual(argv[1], "-c")
            # The remaining arg is the quoted shell command string.
            self.assertIn("cat", argv[2])
            self.assertIn("/etc/hosts", argv[2])

    def test_sandbox_passes_network_flag_to_runner(self):
        conn = make_conn(sandbox_enabled=True, network=True)
        with mock.patch(
            "plugins_func.functions.shell_command.run_sandboxed"
        ) as run_mock:
            run_mock.return_value = SandboxResult(stdout="", stderr="", returncode=0)

            shell_command(conn, "echo", args=["hi"])

            cfg = run_mock.call_args.kwargs["config"]
            self.assertTrue(cfg["enabled"])
            self.assertTrue(cfg["network"])

    def test_no_sandbox_runs_plain_subprocess(self):
        import subprocess

        conn = make_conn(sandbox_enabled=False)
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="plain", stderr="")
        with mock.patch(
            "plugins_func.functions.shell_command.run_sandboxed"
        ) as run_mock, mock.patch(
            "plugins_func.functions.shell_command.subprocess.run", return_value=fake
        ) as sub_mock:
            result = shell_command(conn, "echo", args=["hi"])

            run_mock.assert_not_called()
            self.assertTrue(sub_mock.called)
            self.assertIn("plain", result.result)

    def test_sandbox_disabled_returns_outside_sandbox(self):
        import subprocess

        conn = make_conn(sandbox_enabled=False)
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="x", stderr="")
        with mock.patch(
            "plugins_func.functions.shell_command.subprocess.run", return_value=fake
        ):
            result = shell_command(conn, "echo", args=["hi"])
            self.assertIn("exit_code: 0", result.result)


class SandboxRunnerTests(unittest.TestCase):
    def test_run_sandboxed_executes_real_command(self):
        # Cross-platform: python is always available, so exercise a real run.
        result = run_sandboxed(
            [sys.executable, "-c", "print('sandbox-ok')"], config={"enabled": True}
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("sandbox-ok", result.stdout)
        self.assertTrue(result.sandbox_applied)

    def test_run_sandboxed_propagates_timeout_config(self):
        # The manager delivers ``timeout`` (alias of ``timeout_seconds``).
        result = run_sandboxed(
            [sys.executable, "-c", "import time; time.sleep(5)"],
            config={"enabled": True, "timeout": 1},
        )
        self.assertTrue(result.timed_out)
        self.assertEqual(result.returncode, -1)


if __name__ == "__main__":
    unittest.main()
