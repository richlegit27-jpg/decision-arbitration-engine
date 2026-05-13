from nova_backend.services.runtime_engine_base import (
    RuntimeEngineBase,
)


class RuntimeMemoryEngine(
    RuntimeEngineBase
):
    def __init__(
        self,
    ):
        super().__init__(
            name="runtime_memory_engine",
            tags=[
                "memory",
                "continuity",
                "learning",
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

        runtime_status = context.get(
            "runtime_status"
        )

        execution_status = self._safe_str(
            context.get(
                "execution_status"
            )
        ).lower()

        debug_issues = (
            self._safe_list(
                context.get(
                    "debug_issues"
                )
            )
        )

        healing_applied = (
            self._safe_list(
                context.get(
                    "healing_applied"
                )
            )
        )

        memory_updates = []

        memory_updates.append(
            {
                "type": (
                    "runtime_cycle"
                ),
                "value": {
                    "runtime_status": (
                        runtime_status
                    ),
                    "execution_status": (
                        execution_status
                    ),
                },
            }
        )

        if debug_issues:
            memory_updates.append(
                {
                    "type": (
                        "debug_history"
                    ),
                    "value": (
                        debug_issues
                    ),
                }
            )

        if healing_applied:
            memory_updates.append(
                {
                    "type": (
                        "healing_history"
                    ),
                    "value": (
                        healing_applied
                    ),
                }
            )

        if execution_status in {
            "failed",
            "error",
        }:
            memory_updates.append(
                {
                    "type": (
                        "failure_memory"
                    ),
                    "value": (
                        "Execution failure "
                        "occurred during "
                        "runtime cycle."
                    ),
                }
            )

        if execution_status in {
            "complete",
            "completed",
        }:
            memory_updates.append(
                {
                    "type": (
                        "success_memory"
                    ),
                    "value": (
                        "Execution completed "
                        "successfully."
                    ),
                }
            )

        return {
            "ok": True,
            "action": (
                "runtime_memory_updated"
            ),
            "memory_updates": (
                memory_updates
            ),
            "memory_update_count": len(
                memory_updates
            ),
        }