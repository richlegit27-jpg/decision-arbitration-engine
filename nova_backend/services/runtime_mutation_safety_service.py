class RuntimeMutationSafetyService:
    def __init__(
        self,
    ):
        pass

    def _safe_dict(
        self,
        value,
    ):
        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def evaluate_mutation(
        self,
        execution_state=None,
        proposed_mutation=None,
    ):
        execution_state = self._safe_dict(
            execution_state
        )

        proposed_mutation = (
            self._safe_dict(
                proposed_mutation
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

        mutation_type = str(
            proposed_mutation.get(
                "mutation_type",
                "unknown",
            )
            or "unknown"
        )

        mutation_risk = 0

        if persistent_risk_score >= 100:
            mutation_risk += 4

        if runtime_health == "unstable":
            mutation_risk += 3

        if retry_ceiling_hit:
            mutation_risk += 2

        if mutation_type in {
            "execution_rewrite",
            "policy_override",
            "autonomous_mutation",
        }:
            mutation_risk += 3

        mutation_allowed = (
            mutation_risk < 6
        )

        rollback_probability = min(
            1.0,
            mutation_risk / 10,
        )

        safety_result = {
            "mutation_allowed": (
                mutation_allowed
            ),
            "mutation_risk": mutation_risk,
            "rollback_probability": (
                rollback_probability
            ),
            "mutation_type": mutation_type,
        }

        execution_state[
            "runtime_mutation_safety"
        ] = safety_result

        execution_state[
            "runtime_mutation_allowed"
        ] = mutation_allowed

        execution_state[
            "runtime_mutation_risk"
        ] = mutation_risk

        execution_state[
            "runtime_rollback_probability"
        ] = rollback_probability

        return {
            "ok": True,
            "execution_state": execution_state,
            "safety_result": safety_result,
        }