from nova_backend.services.runtime_engine_base import (
    RuntimeEngineBase,
)


class RuntimeGoalEngine(
    RuntimeEngineBase
):
    def __init__(
        self,
    ):
        super().__init__(
            name="runtime_goal_engine",
            tags=[
                "goal",
                "autonomy",
                "planning",
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

        execution_status = self._safe_str(
            context.get(
                "execution_status"
            )
        ).lower()

        failed_count = context.get(
            "failed_count",
            0,
        )

        debug_issues = self._safe_list(
            context.get(
                "debug_issues"
            )
        )

        goals = []

        if failed_count > 0 or debug_issues:
            goals.append(
                {
                    "goal": (
                        "restore_runtime_stability"
                    ),
                    "priority": (
                        "critical"
                    ),
                    "reason": (
                        "Failures or debug issues "
                        "must be resolved before "
                        "new autonomy."
                    ),
                }
            )

        elif execution_status in {
            "complete",
            "completed",
        }:
            goals.append(
                {
                    "goal": (
                        "generate_next_execution_goal"
                    ),
                    "priority": (
                        "high"
                    ),
                    "reason": (
                        "Previous execution completed "
                        "successfully."
                    ),
                }
            )

        elif execution_status in {
            "",
            "idle",
            "none",
        }:
            goals.append(
                {
                    "goal": (
                        "await_user_or_system_task"
                    ),
                    "priority": (
                        "low"
                    ),
                    "reason": (
                        "Runtime is idle and ready "
                        "for the next task."
                    ),
                }
            )

        else:
            goals.append(
                {
                    "goal": (
                        "continue_active_execution"
                    ),
                    "priority": (
                        "medium"
                    ),
                    "reason": (
                        "Execution is active."
                    ),
                }
            )

        return {
            "ok": True,
            "action": (
                "runtime_goals_selected"
            ),
            "goals": goals,
            "goal_count": len(
                goals
            ),
        }

