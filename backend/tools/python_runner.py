from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BASE_DIR
PYTHON_BIN = sys.executable


def run_python(code: str, timeout: int = 12) -> str:
    code = (code or "").strip()

    if not code:
        return "No Python code provided."

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / "nova_tool_run.py"
        temp_path.write_text(code, encoding="utf-8")

        try:
            result = subprocess.run(
                [PYTHON_BIN, str(temp_path)],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            return f"Python execution timed out after {timeout} seconds."
        except Exception as exc:
            return f"Python execution failed: {exc}"

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        parts = [f"Exit code: {result.returncode}"]

        if stdout:
            parts.append("STDOUT:")
            parts.append(stdout)

        if stderr:
            parts.append("STDERR:")
            parts.append(stderr)

        if not stdout and not stderr:
            parts.append("No output.")

        return "\n".join(parts)