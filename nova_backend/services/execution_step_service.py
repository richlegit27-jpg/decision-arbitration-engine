from pathlib import Path


class ExecutionStepService:

    def __init__(
        self,
        safe_str=None,
        python_runner=None,
    ):
        self.safe_str = safe_str
        self.python_runner = python_runner

    def _safe_str(self, value):
        if callable(self.safe_str):
            return self.safe_str(value)

        return str(value or "")

    def _implementation_content(self, step):
        for key in (
            "content",
            "file_content",
            "code",
        ):
            value = step.get(key)

            if isinstance(value, str) and value:
                return value

        return ""

    def execute_step_logic(
        self,
        session_id,
        step,
    ):
        try:
            step["status"] = "running"

            step_action = self._safe_str(
                step.get("action")
            ).strip().lower()

            target_file = self._safe_str(
                step.get("target_file")
            ).strip()

            if step_action == "implement" and target_file:
                if (
                    self.python_runner is None
                    or not self.python_runner.is_path_allowed(
                        target_file
                    )
                ):
                    raise PermissionError(
                        "Write blocked: target is outside "
                        "Nova's execution sandbox."
                    )

                content = self._implementation_content(
                    step
                )

                if not content:
                    raise ValueError(
                        "Implement step requires explicit "
                        "file content."
                    )

                target_file = str(
                    self.python_runner.resolve_sandbox_path(
                        target_file
                    )
                )

                step["target_file"] = target_file

                Path(target_file).parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                if not content.endswith("\n"):
                    content += "\n"

                Path(target_file).write_text(
                    content,
                    encoding="utf-8",
                )

                step["result"] = (
                    f"Created file: {target_file}"
                )
                step["error"] = None

            elif (
                step_action
                in {
                    "test",
                    "run",
                    "execute",
                }
                and target_file
                and self.python_runner is not None
            ):
                python_result = (
                    self.python_runner.run_file(
                        target_file
                    )
                )

                result = (
                    f"STDOUT="
                    f"{python_result.get('stdout')} | "
                    f"STDERR="
                    f"{python_result.get('stderr')} | "
                    f"ERROR="
                    f"{python_result.get('error')}"
                )

                step["result"] = result
                step["error"] = (
                    None
                    if python_result.get("ok")
                    else result
                )

            else:
                step["result"] = "step executed"
                step["error"] = None

            step["status"] = "completed"

        except Exception as e:
            step["status"] = "failed"
            step["error"] = str(e)