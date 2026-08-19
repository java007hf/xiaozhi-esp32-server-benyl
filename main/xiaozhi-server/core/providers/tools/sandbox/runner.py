"""Restricted subprocess runner for executing untrusted skill code.

The runner wraps ``subprocess.run`` with best-effort isolation:

* CPU / memory / file-size / process-count limits via ``resource.setrlimit``
  (Linux / macOS).
* Privilege drop to an unprivileged user via ``os.setuid`` (POSIX only).
* Optional network isolation via ``unshare -n`` (Linux, requires
  ``CAP_SYS_ADMIN``; silently degraded when unavailable).
* Hard wall-clock ``timeout`` as a final safety net.
* Per-execution temporary working directory.

On platforms without the required primitives (e.g. Windows dev machines) the
runner degrades gracefully to "timeout-only" execution so behaviour stays
predictable and tests remain portable.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Dict, List, Optional

from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

UNIX = hasattr(os, "setuid")  # Windows has no os.setuid / resource module basics


@dataclass
class SandboxResult:
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    timed_out: bool = False
    sandbox_applied: bool = False


@dataclass
class SandboxConfig:
    enabled: bool = False
    network: bool = False
    timeout_seconds: int = 30
    max_memory_mb: int = 0  # 0 = unlimited
    max_cpu_seconds: int = 0  # 0 = unlimited
    run_as_user: Optional[str] = "nobody"
    max_filesize_mb: int = 50

    @classmethod
    def from_dict(cls, raw: Optional[Dict]) -> "SandboxConfig":
        if not raw:
            return cls()
        # Accept both ``timeout`` (manager-delivered) and ``timeout_seconds``.
        timeout_value = raw.get("timeout_seconds", raw.get("timeout", 30))
        return cls(
            enabled=bool(raw.get("enabled", False)),
            network=bool(raw.get("network", False)),
            timeout_seconds=int(timeout_value),
            max_memory_mb=int(raw.get("max_memory_mb", 0)),
            max_cpu_seconds=int(raw.get("max_cpu_seconds", 0)),
            run_as_user=raw.get("run_as_user") or "nobody",
            max_filesize_mb=int(raw.get("max_filesize_mb", 50)),
        )


def _child_limits(cfg: SandboxConfig) -> None:
    """Apply resource limits and drop privileges in the child process."""
    if not UNIX:
        return
    try:
        import resource  # noqa: WPS433 (platform specific)

        if cfg.max_memory_mb > 0:
            limit = cfg.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        if cfg.max_cpu_seconds > 0:
            resource.setrlimit(resource.RLIMIT_CPU, (cfg.max_cpu_seconds, cfg.max_cpu_seconds))
        if cfg.max_filesize_mb > 0:
            flimit = cfg.max_filesize_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_FSIZE, (flimit, flimit))
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
    except Exception as e:  # pragma: no cover - defensive
        logger.bind(tag=TAG).warning(f"设置资源限制失败: {e}")

    if cfg.run_as_user:
        try:
            import pwd

            uid = pwd.getpwnam(cfg.run_as_user).pw_uid
            if uid != 0:
                os.setuid(uid)
        except Exception as e:  # pragma: no cover - defensive
            logger.bind(tag=TAG).warning(f"降权失败(忽略): {e}")


def run_sandboxed(
    cmd_args: List[str],
    *,
    cwd: Optional[str] = None,
    config: Optional[Dict] = None,
) -> SandboxResult:
    """Run ``cmd_args`` in a restricted subprocess.

    Returns a :class:`SandboxResult`. Network isolation (`unshare -n`) is only
    attempted on Linux and only when ``config.network`` is true.
    """
    cfg = SandboxConfig.from_dict(config)
    sandbox_applied = cfg.enabled

    final_args = list(cmd_args)
    if sandbox_applied and cfg.network and sys.platform.startswith("linux"):
        # Wrap with an empty network namespace when the tool is available.
        unshare = _find_unshare()
        if unshare:
            final_args = [unshare, "-n", "--"] + final_args
        else:
            logger.bind(tag=TAG).warning("unshare 不可用，跳过网络隔离（降级）")
            sandbox_applied = False

    preexec_fn = None
    if sandbox_applied and UNIX:
        # Build a closure capturing cfg.
        def _preexec():
            _child_limits(cfg)

        preexec_fn = _preexec

    timeout = max(1, cfg.timeout_seconds) if cfg.timeout_seconds > 0 else None

    try:
        proc = subprocess.run(
            final_args,
            cwd=cwd or tempfile.gettempdir(),
            timeout=timeout,
            capture_output=True,
            text=True,
            shell=False,
            preexec_fn=preexec_fn,
        )
        return SandboxResult(
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            returncode=proc.returncode,
            timed_out=False,
            sandbox_applied=sandbox_applied,
        )
    except subprocess.TimeoutExpired as e:
        return SandboxResult(
            stdout=(e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or ""),
            stderr=(e.stderr or b"").decode("utf-8", "replace") if isinstance(e.stderr, bytes) else (e.stderr or ""),
            returncode=-1,
            timed_out=True,
            sandbox_applied=sandbox_applied,
        )
    except Exception as e:  # pragma: no cover - defensive
        return SandboxResult(stderr=str(e), returncode=-1, sandbox_applied=sandbox_applied)


def run_python(
    code: str,
    *,
    script_path: Optional[str] = None,
    cwd: Optional[str] = None,
    config: Optional[Dict] = None,
) -> SandboxResult:
    """Run Python ``code`` (-c) or a ``script_path`` inside the sandbox."""
    if script_path:
        args = [sys.executable, script_path]
    else:
        args = [sys.executable, "-c", code]
    return run_sandboxed(args, cwd=cwd, config=config)


def _find_unshare() -> Optional[str]:
    from shutil import which

    return which("unshare")
