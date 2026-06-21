class RecursiveImprovementEngine:

    def identify_improvements(
        self,
        reflection=None,
        meta_reasoning=None,
        self_model=None,
    ):

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

        self_model = (
            self_model
            if isinstance(
                self_model,
                dict,
            )
            else {}
        )

        improvements = []

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

        limitations = (
            self_model.get(
                "limitations",
                []
            )
        )

        if failed_steps > 3:

            improvements.append({
                "type": (
                    "upgrade_recovery_system"
                ),
                "priority": 1,
            })

        if (
            "Stabilize execution planning."
            in recommendations
        ):

            improvements.append({
                "type": (
                    "refactor_execution_brain"
                ),
                "priority": 2,
            })

        if len(limitations) > 5:

            improvements.append({
                "type": (
                    "improve_capability_coverage"
                ),
                "priority": 3,
            })

        if not improvements:

            improvements.append({
                "type": (
                    "maintain_current_architecture"
                ),
                "priority": 99,
            })

        return {
            "ok": True,
            "improvements": improvements,
        }

