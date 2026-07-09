class StrategyMutationEngine:

    def mutate_strategy(
        self,
        reflection=None,
        execution_state=None,
    ):

        reflection = (
            reflection
            if isinstance(
                reflection,
                dict,
            )
            else {}
        )

        execution_state = (
            execution_state
            if isinstance(
                execution_state,
                dict,
            )
            else {}
        )

        mutations = []

        failed_steps = int(
            reflection.get(
                "failed_steps",
                0,
            )
        )

        recommendations = (
            reflection.get(
                "recommended_improvements"
            )
            or []
        )

        if failed_steps > 0:

            mutations.append({
                "type": (
                    "increase_recovery_depth"
                ),
                "value": True,
            })

            mutations.append({
                "type": (
                    "enable_patch_retry"
                ),
                "value": True,
            })

        if (
            "Optimize tool usage efficiency."
            in recommendations
        ):

            mutations.append({
                "type": (
                    "reduce_tool_calls"
                ),
                "value": True,
            })

        if not mutations:

            mutations.append({
                "type": (
                    "maintain_strategy"
                ),
                "value": True,
            })

        return {
            "ok": True,
            "mutations": mutations,
        }

