from nova_backend.services.runtime_engine_base import (
    RuntimeEngineBase,
)


class RuntimeDecisionEngine(
    RuntimeEngineBase
):
    def __init__(
        self,
    ):
        super().__init__(
            name="runtime_decision_engine",
            tags=[
                "decision",
                "control",
                "autonomy",
                "runtime",
            ],
        )

    def execute(
        self,
        context=None,
    ):
        context = self._safe_dict(
            context
        )

        failed_count = context.get(
            "failed_count",
            0,
        )

        debug_issues = self._safe_list(
            context.get(
                "debug_issues"
            )
        )

        execution_status = self._safe_str(
            context.get(
                "execution_status"
            )
        ).lower()

        decision = {
            "decision": "observe",
            "priority": "low",
            "reason": "No urgent runtime action required.",
        }

        if failed_count > 0:
            decision = {
                "decision": "repair_first",
                "priority": "critical",
                "reason": (
                    "Execution failure detected; "
                    "repair must happen before expansion."
                ),
            }

        elif debug_issues:
            decision = {
                "decision": "debug_first",
                "priority": "high",
                "reason": (
                    "Debug issues detected; "
                    "inspect runtime before continuing."
                ),
                "issues": debug_issues,
            }

        elif execution_status in {
            "complete",
            "completed",
        }:
            decision = {
                "decision": "plan_next_goal",
                "priority": "medium",
                "reason": (
                    "Execution completed successfully; "
                    "next goal can be prepared."
                ),
            }

        elif execution_status not in {
            "",
            "idle",
            "none",
        }:
            decision = {
                "decision": "continue_execution",
                "priority": "medium",
                "reason": (
                    "Execution is active; "
                    "continue current runtime path."
                ),
            }

        return {
            "ok": True,
            "action": (
                "runtime_decision_selected"
            ),
            "decision": decision,
        }

