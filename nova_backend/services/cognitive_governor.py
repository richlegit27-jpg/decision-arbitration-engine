class CognitiveGovernor:

    def evaluate(
        self,
        fused_context=None,
        self_model=None,
        scheduler_state=None,
    ):

        fused_context = (
            fused_context
            if isinstance(
                fused_context,
                dict,
            )
            else {}
        )

        self_model = (
            self_model
            if isinstance(
                self_model,
                dict,
            )
            else {}
        )

        scheduler_state = (
            scheduler_state
            if isinstance(
                scheduler_state,
                dict,
            )
            else {}
        )

        interventions = []

        health = (
            self_model.get(
                "health",
                {}
            )
        )

        execution_stability = int(
            health.get(
                "execution_stability",
                100,
            )
        )

        cognitive_load = int(
            health.get(
                "cognitive_load",
                0,
            )
        )

        queued = int(
            scheduler_state.get(
                "queued",
                0,
            )
        )

        priority = str(
            fused_context.get(
                "cognitive_priority"
            )
            or ""
        ).lower()

        if execution_stability < 50:

            interventions.append({
                "type": (
                    "reduce_autonomy"
                ),
                "reason": (
                    "execution instability"
                ),
            })

        if cognitive_load > 80:

            interventions.append({
                "type": (
                    "pause_noncritical_tasks"
                ),
                "reason": (
                    "high cognitive load"
                ),
            })

        if queued > 25:

            interventions.append({
                "type": (
                    "throttle_scheduler"
                ),
                "reason": (
                    "task overload"
                ),
            })

        if priority == "critical":

            interventions.append({
                "type": (
                    "prioritize_recovery"
                ),
                "reason": (
                    "critical context state"
                ),
            })

        if not interventions:

            interventions.append({
                "type": (
                    "maintain_operation"
                ),
                "reason": (
                    "system stable"
                ),
            })

        return {
            "ok": True,
            "interventions": (
                interventions
            ),
        }