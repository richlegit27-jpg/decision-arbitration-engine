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

    def execute_step_logic(
        self,
        session_id,
        step,
    ):
        try:
            step["status"] = "running"

            step_action = self._safe_str(
                step.get("action")
            ).lower()

            print(
                "STEP ACTION =",
                repr(step_action),
            )

            target_file = self._safe_str(
                step.get("target_file")
            )

            if step_action == "implement" and target_file:
                Path(target_file).parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                Path(target_file).write_text(
                    """
def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


if __name__ == "__main__":
    print("Calculator app created.")
    print("2 + 3 =", add(2, 3))
""".strip() + "\n",
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