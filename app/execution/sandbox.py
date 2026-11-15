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
                env={
                    "PATH": os.environ.get("PATH", ""),
                    "HOME": tmpdir,
                    "PYTHONPATH": tmpdir,
                    "LANG": "en_US.UTF-8",
                },
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
