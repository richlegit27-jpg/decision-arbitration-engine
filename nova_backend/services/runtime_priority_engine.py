from nova_backend.services.runtime_engine_base import (
    RuntimeEngineBase,
)


class RuntimePriorityEngine(
    RuntimeEngineBase
):
    def __init__(
        self,
    ):
        super().__init__(
            name="runtime_priority_engine",
            tags=[
                "priority",
                "ranking",
                "decision",
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

        priorities = []

        if failed_count > 0:
            priorities.append(
                {
                    "priority": (
                        "repair"
                    ),
                    "weight": 100,
                    "reason": (
                        "Failure pressure detected."
                    ),
                }
            )

        if debug_issues:
            priorities.append(
                {
                    "priority": (
                        "debug"
                    ),
                    "weight": 90,
                    "reason": (
                        "Debug issues detected."
                    ),
                    "issues": debug_issues,
                }
            )

        if execution_status in {
            "complete",
            "completed",
        }:
            priorities.append(
                {
                    "priority": (
                        "next_goal"
                    ),
                    "weight": 70,
                    "reason": (
                        "Execution completed."
                    ),
                }
            )

        if not priorities:
            priorities.append(
                {
                    "priority": (
                        "observe"
                    ),
                    "weight": 30,
                    "reason": (
                        "No urgent runtime pressure."
                    ),
                }
            )

        priorities.sort(
            key=lambda item: item.get(
                "weight",
                0,
            ),
            reverse=True,
        )

        return {
            "ok": True,
            "action": (
                "runtime_priorities_ranked"
            ),
            "priorities": priorities,
            "top_priority": (
                priorities[0]
                if priorities
                else {}
            ),
            "priority_count": len(
                priorities
            ),
        }

