# C:\Users\Owner\nova\nova_backend\services\runtime_self_preservation_service.py

class RuntimeSelfPreservationService:
    def __init__(
        self,
    ):
        pass

    def preserve(
        self,
        execution_state=None,
        runtime_health=None,
        runtime_result=None,
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

        runtime_result = (
            runtime_result
            if isinstance(runtime_result, dict)
            else {}
        )

        health_score = int(
            runtime_health.get(
                "health_score",
                100,
            )
            or 100
        )

        health_state = str(
            runtime_health.get(
                "health_state",
                "healthy",
            )
            or "healthy"
        ).lower()

        preservation_mode = False
        preservation_actions = []

        if health_state in {
            "critical",
            "degraded",
        }:
            preservation_mode = True

            execution_state[
                "runtime_preservation_mode"
            ] = True

            execution_state[
                "runtime_signal"
            ] = (
                "runtime_self_preservation"
            )

            preservation_actions.append(
                "limit_autonomous_mutation"
            )

            preservation_actions.append(
                "increase_checkpoint_frequency"
            )

        if health_score <= 25:

            execution_state[
                "runtime_emergency_lockdown"
            ] = True

            preservation_actions.append(
                "emergency_lockdown"
            )

        return {
            "ok": True,
            "preservation_mode": preservation_mode,
            "preservation_actions": preservation_actions,
            "health_score": health_score,
            "health_state": health_state,
            "execution_state": execution_state,
        }