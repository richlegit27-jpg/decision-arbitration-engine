from __future__ import annotations


class RuntimeAutoRecoveryService:
    def recover(
        self,
        runtime_result=None,
        execution_state=None,
    ):
        runtime_result = runtime_result or {}
        execution_state = execution_state or {}

        prediction = (
            runtime_result.get(
                "runtime_prediction",
                {}
            )
        )

        policy = (
            runtime_result.get(
                "runtime_adaptive_policy",
                {}
            )
            .get(
                "adaptive_policy",
                {}
            )
        )

        health = policy.get(
            "runtime_health"
        )

        predicted_state = prediction.get(
            "predicted_state"
        )

        recovery_actions = []

        if health == "unstable":
            recovery_actions.append(
                "enable_repair_mode"
            )

        if predicted_state == "unstable":
            recovery_actions.append(
                "increase_debug_priority"
            )

        if execution_state.get("status") == "failed":
            recovery_actions.append(
                "retry_failed_execution"
            )

        recovery_mode = "observe"

        if recovery_actions:
            recovery_mode = "recover"

        return {
            "ok": True,
            "recovery_mode": recovery_mode,
            "recovery_actions": recovery_actions,
            "action_count": len(
                recovery_actions
            ),
        }

