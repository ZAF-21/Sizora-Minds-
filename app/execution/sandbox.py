"""
R2: Sandbox execution — run generated code + tests in an isolated environment.
Separate process, temp directory, timeout, no network.
"""

from __future__ import annotations
import subprocess
import sys
import tempfile
import os
from pathlib import Path
from app.config import SANDBOX_TIMEOUT_SECONDS

# Windows needs these for the child Python to start networking/asyncio. Without SYSTEMROOT, Winsock
# can't load its service providers, and pytest plugins that import asyncio (e.g. anyio) crash with
# "OSError: [WinError 10106] The requested service provider could not be loaded or initialized".
_WINDOWS_REQUIRED_ENV = ("SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "TEMP", "TMP", "PATHEXT", "COMSPEC")


def _sandbox_env(tmpdir: str) -> dict[str, str]:
    """Minimal environment for the sandboxed pytest process: no inherited secrets (API keys etc.),
    HOME pointed at the throwaway temp dir, plus the OS essentials Windows can't run without."""
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": tmpdir,
        "PYTHONPATH": tmpdir,
        "LANG": "en_US.UTF-8",
    }
    if os.name == "nt":
        env.update({k: os.environ[k] for k in _WINDOWS_REQUIRED_ENV if k in os.environ})
        env["USERPROFILE"] = tmpdir
    return env


def run_in_sandbox(code: str, test_code: str, timeout: int = SANDBOX_TIMEOUT_SECONDS) -> dict:
    """
    Execute code + tests in an isolated sandbox.
    Returns dict with: passed (bool), exit_code (int), output (str), error (str)
    """
    with tempfile.TemporaryDirectory(prefix="codeforge_") as tmpdir:
        code_file = Path(tmpdir) / "solution.py"
        test_file = Path(tmpdir) / "test_solution.py"

        code_file.write_text(code)
        test_file.write_text(test_code)

        try:
            result = subprocess.run(
                [sys.executable, "-I", "-m", "pytest", str(test_file), "-v", "--tb=short", "--no-header"],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmpdir,
                env=_sandbox_env(tmpdir),
            )
            return {
                "passed": result.returncode == 0,
                "exit_code": result.returncode,
                "output": result.stdout,
                "error": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "exit_code": -1,
                "output": "",
                "error": f"Execution timed out after {timeout} seconds",
            }
        except Exception as e:
            return {
                "passed": False,
                "exit_code": -2,
                "output": "",
                "error": f"Sandbox error: {str(e)}",
            }
