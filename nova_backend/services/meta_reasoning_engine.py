class MetaReasoningEngine:

    def evaluate_reasoning(
        self,
        reflection=None,
        mutations=None,
        scheduler_state=None,
    ):

        reflection = (
            reflection
            if isinstance(
                reflection,
                dict,
            )
            else {}
        )

        mutations = (
            mutations
            if isinstance(
                mutations,
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

        observations = []
        recommendations = []

        failed_steps = int(
            reflection.get(
                "failed_steps",
                0,
            )
        )

        completed_steps = int(
            reflection.get(
                "completed_steps",
                0,
            )
        )

        mutation_list = (
            mutations.get(
                "mutations",
                []
            )
        )

        if failed_steps > completed_steps:

            observations.append(
                "Failure rate exceeds success rate."
            )

            recommendations.append(
                "Increase recovery depth."
            )

            recommendations.append(
                "Reduce risky execution paths."
            )

        if len(mutation_list) > 5:

            observations.append(
                "Strategy mutation frequency is high."
            )

            recommendations.append(
                "Stabilize execution planning."
            )

        queued = int(
            scheduler_state.get(
                "queued",
                0,
            )
        )

        running = int(
            scheduler_state.get(
                "running",
                0,
            )
        )

        if queued > running * 3:

            observations.append(
                "Task backlog detected."
            )

            recommendations.append(
                "Increase autonomous throughput."
            )

        if not recommendations:

            recommendations.append(
                "Maintain current reasoning strategy."
            )

        return {
            "ok": True,
            "observations": observations,
            "recommendations": (
                recommendations
            ),
        }