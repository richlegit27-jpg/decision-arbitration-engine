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

    def run_file(
        self,
        file_path,
        timeout=20,
    ):

        file_path = Path(file_path)

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

        target = (
            self.sandbox_dir
            / filename
        )

        target.write_text(
            code,
            encoding="utf-8",
        )

        return self.run_file(
            target,
            timeout=timeout,
        )