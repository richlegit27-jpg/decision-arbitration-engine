import subprocess
import sys
from pathlib import Path


class PythonRunnerService:

    def __init__(
        self,
        sandbox_dir=None,
    ):

        self.sandbox_dir = Path(
            sandbox_dir
            or r"C:\Users\Owner\nova\nova_backend\sandbox"
        )

        self.sandbox_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def resolve_sandbox_path(
        self,
        file_path,
    ):
        candidate = Path(file_path)

        if not candidate.is_absolute():
            candidate = self.sandbox_dir / candidate

        sandbox = self.sandbox_dir.resolve()
        candidate = candidate.resolve()

        try:
            candidate.relative_to(sandbox)
        except ValueError:
            return None

        return candidate

    def is_path_allowed(
        self,
        file_path,
    ):
        return (
            self.resolve_sandbox_path(file_path)
            is not None
        )

    def run_file(
        self,
        file_path,
        timeout=20,
    ):

        file_path = self.resolve_sandbox_path(
            file_path
        )

        if file_path is None:
            return {
                "ok": False,
                "error": (
                    "Execution blocked: file is outside "
                    "Nova's sandbox."
                ),
                "stdout": "",
                "stderr": "",
            }

        if file_path.suffix.lower() != ".py":
            return {
                "ok": False,
                "error": (
                    "Execution blocked: only Python "
                    "files may run in this sandbox."
                ),
                "stdout": "",
                "stderr": "",
            }

        if not file_path.exists():

            return {
                "ok": False,
                "error": (
                    f"File not found: "
                    f"{file_path}"
                ),
                "stdout": "",
                "stderr": "",
            }

        try:

            result = subprocess.run(
                [
                    sys.executable,
                    str(file_path),
                ],
                cwd=str(file_path.parent),
                capture_output=True,
                text=True,
                bufsize=1,
                timeout=timeout,
            )

            print(
                "PYTHON RUNNER STDOUT =",
                repr(result.stdout),
            )

            print(
                "PYTHON RUNNER STDERR =",
                repr(result.stderr),
            )

            stdout = (
                result.stdout.strip()
                if result.stdout
                else ""
            )

            stderr = (
                result.stderr.strip()
                if result.stderr
                else ""
            )

            return {
                "ok": (
                    result.returncode == 0
                ),
                "returncode": (
                    result.returncode
                ),
                "stdout": stdout,
                "stderr": stderr,
            }

        except subprocess.TimeoutExpired:

            return {
                "ok": False,
                "error": (
                    "Python execution "
                    "timed out."
                ),
                "stdout": "",
                "stderr": "",
            }

        except Exception as e:

            return {
                "ok": False,
                "error": str(e),
                "stdout": "",
                "stderr": "",
            }

    def run_code(
        self,
        code,
        filename="nova_temp_run.py",
        timeout=20,
    ):

        target = self.resolve_sandbox_path(
            filename
        )

        if target is None:
            return {
                "ok": False,
                "error": (
                    "Execution blocked: filename escapes "
                    "Nova's sandbox."
                ),
                "stdout": "",
                "stderr": "",
            }

        if target.suffix.lower() != ".py":
            return {
                "ok": False,
                "error": (
                    "Execution blocked: generated files "
                    "must use the .py extension."
                ),
                "stdout": "",
                "stderr": "",
            }

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        target.write_text(
            code,
            encoding="utf-8",
        )

        return self.run_file(
            target,
            timeout=timeout,
        )

