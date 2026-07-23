import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryFile


class PythonRunnerService:

    DEFAULT_TIMEOUT = 20
    MAX_TIMEOUT = 30
    MAX_SCRIPT_BYTES = 200_000
    MAX_OUTPUT_BYTES = 20_000

    def __init__(
        self,
        sandbox_dir=None,
    ):
        self.sandbox_dir = Path(
            sandbox_dir
            or r"C:\Users\Owner\nova\nova_backend\sandbox"
        ).resolve()

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
            candidate = (
                self.sandbox_dir / candidate
            )

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
            self.resolve_sandbox_path(
                file_path
            )
            is not None
        )

    def _safe_timeout(self, timeout):
        try:
            timeout = int(timeout)
        except Exception:
            timeout = self.DEFAULT_TIMEOUT

        return max(
            1,
            min(
                timeout,
                self.MAX_TIMEOUT,
            ),
        )

    def _isolated_environment(self):
        environment = {}

        for key in (
            "SYSTEMROOT",
            "WINDIR",
            "TEMP",
            "TMP",
        ):
            value = os.environ.get(key)

            if value:
                environment[key] = value

        environment[
            "PYTHONNOUSERSITE"
        ] = "1"

        environment[
            "PYTHONDONTWRITEBYTECODE"
        ] = "1"

        return environment

    def _read_output(self, stream):
        stream.seek(0)

        raw = stream.read(
            self.MAX_OUTPUT_BYTES + 1
        )

        truncated = (
            len(raw) > self.MAX_OUTPUT_BYTES
        )

        raw = raw[
            : self.MAX_OUTPUT_BYTES
        ]

        text = raw.decode(
            "utf-8",
            errors="replace",
        ).strip()

        return text, truncated

    def _blocked_result(self, error):
        return {
            "ok": False,
            "error": str(error or ""),
            "stdout": "",
            "stderr": "",
            "output_truncated": False,
        }

    def run_file(
        self,
        file_path,
        timeout=DEFAULT_TIMEOUT,
    ):
        file_path = self.resolve_sandbox_path(
            file_path
        )

        if file_path is None:
            return self._blocked_result(
                "Execution blocked: file is outside "
                "Nova's sandbox."
            )

        if file_path.suffix.lower() != ".py":
            return self._blocked_result(
                "Execution blocked: only Python "
                "files may run in this sandbox."
            )

        if not file_path.exists():
            return self._blocked_result(
                f"File not found: {file_path}"
            )

        if not file_path.is_file():
            return self._blocked_result(
                "Execution blocked: target is not "
                "a regular file."
            )

        try:
            script_size = file_path.stat().st_size
        except Exception as exc:
            return self._blocked_result(exc)

        if script_size > self.MAX_SCRIPT_BYTES:
            return self._blocked_result(
                "Execution blocked: Python file "
                "exceeds the sandbox size limit."
            )

        timeout = self._safe_timeout(
            timeout
        )

        creation_flags = 0

        if sys.platform == "win32":
            creation_flags = getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0,
            )

        with TemporaryFile() as stdout_file:
            with TemporaryFile() as stderr_file:
                try:
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-I",
                            "-B",
                            str(file_path),
                        ],
                        cwd=str(file_path.parent),
                        stdin=subprocess.DEVNULL,
                        stdout=stdout_file,
                        stderr=stderr_file,
                        timeout=timeout,
                        env=self._isolated_environment(),
                        creationflags=creation_flags,
                        check=False,
                    )

                    stdout, stdout_truncated = (
                        self._read_output(
                            stdout_file
                        )
                    )

                    stderr, stderr_truncated = (
                        self._read_output(
                            stderr_file
                        )
                    )

                    output_truncated = (
                        stdout_truncated
                        or stderr_truncated
                    )

                    error = ""

                    if result.returncode != 0:
                        error = (
                            stderr
                            or (
                                "Python process exited "
                                f"with code "
                                f"{result.returncode}."
                            )
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
                        "error": error,
                        "output_truncated": (
                            output_truncated
                        ),
                    }

                except subprocess.TimeoutExpired:
                    stdout, stdout_truncated = (
                        self._read_output(
                            stdout_file
                        )
                    )

                    stderr, stderr_truncated = (
                        self._read_output(
                            stderr_file
                        )
                    )

                    return {
                        "ok": False,
                        "error": (
                            "Python execution timed out."
                        ),
                        "stdout": stdout,
                        "stderr": stderr,
                        "output_truncated": (
                            stdout_truncated
                            or stderr_truncated
                        ),
                    }

                except Exception as exc:
                    return self._blocked_result(
                        exc
                    )

    def run_code(
        self,
        code,
        filename="nova_temp_run.py",
        timeout=DEFAULT_TIMEOUT,
    ):
        if not isinstance(code, str):
            return self._blocked_result(
                "Execution blocked: code must be "
                "text."
            )

        encoded_code = code.encode(
            "utf-8"
        )

        if len(encoded_code) > self.MAX_SCRIPT_BYTES:
            return self._blocked_result(
                "Execution blocked: generated code "
                "exceeds the sandbox size limit."
            )

        target = self.resolve_sandbox_path(
            filename
        )

        if target is None:
            return self._blocked_result(
                "Execution blocked: filename escapes "
                "Nova's sandbox."
            )

        if target.suffix.lower() != ".py":
            return self._blocked_result(
                "Execution blocked: generated files "
                "must use the .py extension."
            )

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