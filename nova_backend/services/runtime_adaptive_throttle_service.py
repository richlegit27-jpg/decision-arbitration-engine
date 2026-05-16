# C:\Users\Owner\nova\nova_backend\services\runtime_adaptive_throttle_service.py

class RuntimeAdaptiveThrottleService:
    def __init__(
        self,
    ):
        pass

    def throttle(
        self,
        execution_state=None,
        runtime_health=None,
        runtime_self_preservation=None,
    ):
        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        runtime_health = (
            runtime_health
            if isinstance(runtime_health, dict)
            else {}
        )

        runtime_self_preservation = (
            runtime_self_preservation
            if isinstance(runtime_self_preservation, dict)
            else {}
        )

        health_score = int(
            runtime_health.get(
                "health_score",
                100,
            )
            or 100
        )

        preservation_mode = bool(
            runtime_self_preservation.get(
                "preservation_mode",
                False,
            )
        )

        throttle_level = "none"
        allowed_autonomy = "full"
        blocked_actions = []

        if preservation_mode or health_score < 65:
            throttle_level = "medium"
            allowed_autonomy = "supervised"
            blocked_actions.append(
                "high_risk_mutation"
            )

        if health_score < 40:
            throttle_level = "high"
            allowed_autonomy = "restricted"
            blocked_actions.extend(
                [
                    "autonomous_mutation",
                    "recursive_expansion",
                ]
            )

        if health_score < 25:
            throttle_level = "lockdown"
            allowed_autonomy = "manual_only"
            blocked_actions.extend(
                [
                    "autonomous_execution",
                    "self_mutation",
                    "planner_expansion",
                ]
            )

        execution_state[
            "runtime_throttle_level"
        ] = throttle_level

        execution_state[
            "runtime_allowed_autonomy"
        ] = allowed_autonomy

        execution_state[
            "runtime_blocked_actions"
        ] = list(
            dict.fromkeys(blocked_actions)
        )

        return {
            "ok": True,
            "throttle_level": throttle_level,
            "allowed_autonomy": allowed_autonomy,
            "blocked_actions": execution_state.get(
                "runtime_blocked_actions",
                [],
            ),
            "health_score": health_score,
            "preservation_mode": preservation_mode,
            "execution_state": execution_state,
        }