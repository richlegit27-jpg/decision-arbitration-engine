class RuntimeRollbackIntelligenceService:
    def __init__(
        self,
        max_snapshots=10,
    ):
        self.max_snapshots = max_snapshots

    def _safe_dict(
        self,
        value,
    ):
        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def _safe_list(
        self,
        value,
    ):
        return (
            value
            if isinstance(value, list)
            else []
        )

    def evaluate(
        self,
        execution_state=None,
    ):
        execution_state = self._safe_dict(
            execution_state
        )

        rollback_history = self._safe_list(
            execution_state.get(
                "runtime_rollback_history"
            )
        )

        persistent_risk_score = int(
            execution_state.get(
                "persistent_risk_score",
                0,
            )
            or 0
        )

        runtime_health = str(
            execution_state.get(
                "runtime_health",
                ""
            )
            or ""
        ).lower()

        retry_ceiling_hit = bool(
            execution_state.get(
                "runtime_retry_ceiling_hit"
            )
        )

        dangerous_runtime = bool(
            persistent_risk_score >= 80
            or runtime_health == "unstable"
            or retry_ceiling_hit
        )

        snapshot = {
            "cycle_count": execution_state.get(
                "cycle_count"
            ),
            "persistent_risk_score": (
                persistent_risk_score
            ),
            "runtime_health": runtime_health,
            "runtime_final_action": (
                execution_state.get(
                    "runtime_final_action"
                )
            ),
            "runtime_strategy_scores": (
                execution_state.get(
                    "runtime_strategy_scores",
                    {},
                )
            ),
        }

        rollback_history.append(snapshot)
        rollback_history = rollback_history[
            -self.max_snapshots:
        ]

        rollback_required = False
        rollback_reason = None

        if dangerous_runtime:
            rollback_required = True
            rollback_reason = (
                "dangerous_runtime_detected"
            )

        rollback_target = None

        if rollback_required:
            stable_candidates = [
                item
                for item in rollback_history
                if (
                    int(
                        item.get(
                            "persistent_risk_score",
                            999,
                        )
                    )
                    < 50
                )
            ]

            if stable_candidates:
                rollback_target = stable_candidates[0]

        execution_state[
            "runtime_rollback_history"
        ] = rollback_history

        execution_state[
            "runtime_rollback_required"
        ] = rollback_required

        execution_state[
            "runtime_rollback_reason"
        ] = rollback_reason

        execution_state[
            "runtime_rollback_target"
        ] = rollback_target

        return {
            "ok": True,
            "execution_state": execution_state,
            "rollback_required": rollback_required,
            "rollback_reason": rollback_reason,
            "rollback_target": rollback_target,
            "rollback_history": rollback_history,
        }