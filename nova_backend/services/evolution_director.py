class EvolutionDirector:

    def determine_next_evolution(
        self,
        self_model=None,
        reflection=None,
        meta_reasoning=None,
        recursive_improvements=None,
        identity_summary=None,
    ):

        self_model = (
            self_model
            if isinstance(
                self_model,
                dict,
            )
            else {}
        )

        reflection = (
            reflection
            if isinstance(
                reflection,
                dict,
            )
            else {}
        )

        meta_reasoning = (
            meta_reasoning
            if isinstance(
                meta_reasoning,
                dict,
            )
            else {}
        )

        recursive_improvements = (
            recursive_improvements
            if isinstance(
                recursive_improvements,
                dict,
            )
            else {}
        )

        identity_summary = (
            identity_summary
            if isinstance(
                identity_summary,
                dict,
            )
            else {}
        )

        evolution_targets = []

        limitations = (
            self_model.get(
                "limitations",
                []
            )
        )

        failed_steps = int(
            reflection.get(
                "failed_steps",
                0,
            )
        )

        recommendations = (
            meta_reasoning.get(
                "recommendations",
                []
            )
        )

        improvements = (
            recursive_improvements.get(
                "improvements",
                []
            )
        )

        if failed_steps > 5:

            evolution_targets.append({
                "target": (
                    "recovery_architecture"
                ),
                "priority": 1,
            })

        if len(limitations) > 10:

            evolution_targets.append({
                "target": (
                    "capability_expansion"
                ),
                "priority": 2,
            })

        if (
            "Increase autonomous throughput."
            in recommendations
        ):

            evolution_targets.append({
                "target": (
                    "scheduler_optimization"
                ),
                "priority": 3,
            })

        if len(improvements) > 5:

            evolution_targets.append({
                "target": (
                    "recursive_stabilization"
                ),
                "priority": 4,
            })

        if not evolution_targets:

            evolution_targets.append({
                "target": (
                    "maintain_stability"
                ),
                "priority": 99,
            })

        evolution_targets.sort(
            key=lambda x: x.get(
                "priority",
                999,
            )
        )

        return {
            "ok": True,
            "evolution_targets": (
                evolution_targets
            ),
            "identity": (
                identity_summary
            ),
        }

