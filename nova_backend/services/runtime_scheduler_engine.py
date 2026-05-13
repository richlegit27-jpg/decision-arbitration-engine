from nova_backend.services.runtime_engine_base import RuntimeEngineBase


class RuntimeSchedulerEngine(RuntimeEngineBase):
    def __init__(self):
        super().__init__(
            name="runtime_scheduler_engine",
            tags=[
                "scheduler",
                "planning",
                "future",
                "runtime",
            ],
        )

    def execute(
        self,
        context=None,
    ):
        context = self._safe_dict(context)

        execution_status = self._safe_str(
            context.get("execution_status")
        ).lower()

        failed_count = context.get(
            "failed_count",
            0,
        )

        future_tasks = []

        if failed_count > 0:
            future_tasks.append(
                {
                    "task": "retry_failed_execution",
                    "priority": "high",
                    "reason": "Execution failures detected.",
                }
            )

        if execution_status in {
            "complete",
            "completed",
        }:
            future_tasks.append(
                {
                    "task": "prepare_next_goal",
                    "priority": "medium",
                    "reason": "Execution completed successfully.",
                }
            )

        if execution_status in {
            "",
            "idle",
            None,
        }:
            future_tasks.append(
                {
                    "task": "await_new_work",
                    "priority": "low",
                    "reason": "Runtime is idle.",
                }
            )

        return {
            "ok": True,
            "action": "runtime_schedule_generated",
            "future_tasks": future_tasks,
            "future_task_count": len(
                future_tasks
            ),
        }