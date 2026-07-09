from nova_backend.services.runtime_engine_base import (
    RuntimeEngineBase,
)


class RuntimeStrategyEngine(
    RuntimeEngineBase
):
    def __init__(
        self,
    ):
        super().__init__(
            name="runtime_strategy_engine",
            tags=[
                "strategy",
                "decision",
                "adaptation",
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

        strategies = []

        if failed_count > 0:
            strategies.append(
                {
                    "strategy": (
                        "stabilize_then_retry"
                    ),
                    "priority": (
                        "critical"
                    ),
                    "reason": (
                        "Failures detected; repair "
                        "must happen before expansion."
                    ),
                }
            )

        if debug_issues:
            strategies.append(
                {
                    "strategy": (
                        "debug_first"
                    ),
                    "priority": (
                        "high"
                    ),
                    "reason": (
                        "Debug signals should guide "
                        "the next runtime move."
                    ),
                    "issues": debug_issues,
                }
            )

        if execution_status in {
            "complete",
            "completed",
        }:
            strategies.append(
                {
                    "strategy": (
                        "promote_success_and_continue"
                    ),
                    "priority": (
                        "medium"
                    ),
                    "reason": (
                        "Completed execution can become "
                        "a reusable strategy pattern."
                    ),
                }
            )

        if not strategies:
            strategies.append(
                {
                    "strategy": (
                        "maintain_observe_mode"
                    ),
                    "priority": (
                        "low"
                    ),
                    "reason": (
                        "No strong strategy shift required."
                    ),
                }
            )

        return {
            "ok": True,
            "action": (
                "runtime_strategy_selected"
            ),
            "strategies": strategies,
            "strategy_count": len(
                strategies
            ),
        }

