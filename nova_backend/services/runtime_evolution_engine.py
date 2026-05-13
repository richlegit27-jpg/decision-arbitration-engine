from nova_backend.services.runtime_engine_base import (
    RuntimeEngineBase,
)


class RuntimeEvolutionEngine(
    RuntimeEngineBase
):
    def __init__(
        self,
    ):
        super().__init__(
            name="runtime_evolution_engine",
            tags=[
                "evolution",
                "mutation",
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

        evolution_moves = []

        if failed_count > 0:
            evolution_moves.append(
                {
                    "move": (
                        "strengthen_failure_recovery"
                    ),
                    "priority": (
                        "high"
                    ),
                    "reason": (
                        "Runtime failure pressure detected."
                    ),
                }
            )

        if debug_issues:
            evolution_moves.append(
                {
                    "move": (
                        "increase_debug_signal_weight"
                    ),
                    "priority": (
                        "high"
                    ),
                    "reason": (
                        "Debug issues should influence "
                        "future orchestration scoring."
                    ),
                    "issues": debug_issues,
                }
            )

        if execution_status in {
            "complete",
            "completed",
        }:
            evolution_moves.append(
                {
                    "move": (
                        "promote_success_pattern"
                    ),
                    "priority": (
                        "medium"
                    ),
                    "reason": (
                        "Successful cycle can become "
                        "future strategy memory."
                    ),
                }
            )

        if not evolution_moves:
            evolution_moves.append(
                {
                    "move": (
                        "preserve_current_architecture"
                    ),
                    "priority": (
                        "low"
                    ),
                    "reason": (
                        "No evolution pressure detected."
                    ),
                }
            )

        return {
            "ok": True,
            "action": (
                "runtime_evolution_review_completed"
            ),
            "evolution_moves": evolution_moves,
            "evolution_move_count": len(
                evolution_moves
            ),
        }