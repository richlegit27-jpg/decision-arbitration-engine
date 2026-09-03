from pathlib import Path

from nova_backend.services.execution_approval_service import (
    ExecutionApprovalService,
)

from nova_backend.services.ai_execution_service import (
    AIExecutionService,
)

class ExecutionStepService:

    def __init__(
        self,
        safe_str=None,
        python_runner=None,
        approval_service=None,
        ai_execution_service=None,
    ):
        self.safe_str = safe_str
        self.python_runner = python_runner
        self.approval_service = (
            approval_service
            or ExecutionApprovalService()
        )
        self.ai_execution_service = (
            ai_execution_service
            or AIExecutionService(
                safe_str=self._safe_str,
            )
        )

    def _safe_str(
        self,
        value,
    ):
        if callable(self.safe_str):
            return self.safe_str(value)

        return str(value or "")

    def _implementation_content(
        self,
        step,
    ):
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

        print(
            "DEBUG EXECUTOR RECEIVED STEP =",
            step,
            flush=True,
        )

        print(
            "DEBUG EXECUTOR ACTION =",
            step.get("action"),
            flush=True,
        )

        try:
            approval = (
                self.approval_service.evaluate(
                    step
                )
            )

            if approval.get("waiting"):
                step["status"] = "waiting_approval"
                step["result"] = ""
                step["error"] = (
                    approval.get("reason")
                    or "Approval required before execution."
                )
                return None
            step["status"] = "running"

            step_action = self._safe_str(
                step.get("action")
            ).strip().lower()

            # Natural-language mission steps do not always have
            # an explicit execution action. Treat those as AI
            # reasoning tasks instead of failing immediately.
            if not step_action:
                step_action = "design"

                print(
                    "DEBUG EXECUTOR: missing action, "
                    "defaulting to AI execution",
                    flush=True,
                )

            ACTION_ALIASES = {
                "analysis": "design",
                "analyze": "design",
                "research": "design",
                "review": "design",
                "planning": "design",
                "plan": "design",
                "architecture": "design",
                "integration": "design",
                "optimization": "design",
                "delivery": "design",
                "implementation": "implement",
                "implementing": "implement",
                "coding": "implement",
                "testing": "test",
                "validation": "test",
            }

            step_action = ACTION_ALIASES.get(
                step_action,
                step_action,
            )

            print(
                "DEBUG EXECUTOR RECEIVED STEP =",
                step,
                flush=True,
            )

            print(
                "DEBUG EXECUTOR ACTION =",
                step_action,
                flush=True,
            )

            target_file = self._safe_str(
                step.get("target_file")
            ).strip()

            if step_action in {
                "design",
                "build",
                "verify",
            }:

                ai_result = (
                    self.ai_execution_service.execute_step(
                        session_id=session_id,
                        step=step,
                        context={
                            "project_context": self._safe_str(
                                step.get("project_context")
                                or step.get("context")
                                or ""
                            ),
                        },
                    )
                )

                if not ai_result.get("ok"):
                    raise RuntimeError(
                        self._safe_str(
                            ai_result.get("error")
                            or "AI execution failed."
                        )
                    )

                result = self._safe_str(
                    ai_result.get("output")
                ).strip()

                if not result:
                    raise RuntimeError(
                        "AI execution returned an empty result."
                    )

                step["result"] = result
                step["error"] = None
            elif step_action == "implement" and target_file:

                if (
                    self.python_runner is None
                    or not self.python_runner.is_path_allowed(
                        target_file
                    )
                ):
                    raise PermissionError(
                        "Write blocked: target is outside Nova's execution sandbox."
                    )

                content = self._implementation_content(
                    step
                )

                if not content:
                    raise ValueError(
                        "Implement step requires explicit file content."
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
                    f"STDOUT={python_result.get('stdout')} | "
                    f"STDERR={python_result.get('stderr')} | "
                    f"ERROR={python_result.get('error')}"
                )

                step["result"] = result

                step["error"] = (
                    None
                    if python_result.get("ok")
                    else result
                )

            else:

                action_label = (
                    step_action
                    or "missing"
                )

                raise ValueError(
                    "Unsupported execution action: "
                    f"{action_label}"
                )

            step["status"] = "completed"

        except Exception as e:
            step["status"] = "failed"
            step["error"] = str(e)

        return step

