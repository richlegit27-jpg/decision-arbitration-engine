class TranscendenceProtocol:

    def evaluate_transition(
        self,
        runtime_state=None,
        evolution_state=None,
        self_model=None,
        governor_state=None,
    ):

        runtime_state = (
            runtime_state
            if isinstance(
                runtime_state,
                dict,
            )
            else {}
        )

        evolution_state = (
            evolution_state
            if isinstance(
                evolution_state,
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

        governor_state = (
            governor_state
            if isinstance(
                governor_state,
                dict,
            )
            else {}
        )

        decisions = []

        evolution_targets = (
            evolution_state.get(
                "evolution_targets",
                []
            )
        )

        interventions = (
            governor_state.get(
                "interventions",
                []
            )
        )

        health = (
            self_model.get(
                "health",
                {}
            )
        )

        stability = int(
            health.get(
                "execution_stability",
                100,
            )
        )

        if stability < 40:

            decisions.append({
                "type": (
                    "freeze_recursive_expansion"
                ),
                "priority": 1,
            })

        if len(evolution_targets) > 10:

            decisions.append({
                "type": (
                    "limit_parallel_evolution"
                ),
                "priority": 2,
            })

        if any(
            i.get("type")
            == "reduce_autonomy"
            for i in interventions
        ):

            decisions.append({
                "type": (
                    "enter_stabilization_mode"
                ),
                "priority": 3,
            })

        if not decisions:

            decisions.append({
                "type": (
                    "continue_evolution"
                ),
                "priority": 99,
            })

        decisions.sort(
            key=lambda d: d.get(
                "priority",
                999,
            )
        )

        return {
            "ok": True,
            "decisions": decisions,
        }

