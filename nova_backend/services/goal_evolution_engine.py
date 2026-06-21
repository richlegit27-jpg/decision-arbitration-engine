class GoalEvolutionEngine:

    def evolve_goal(
        self,
        execution_state=None,
        reflection=None,
        meta_reasoning=None,
    ):

        execution_state = (
            execution_state
            if isinstance(
                execution_state,
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

        original_goal = str(
            execution_state.get(
                "original_user_text"
            )
            or ""
        )

        evolved_goals = []

        recommendations = (
            meta_reasoning.get(
                "recommendations",
                []
            )
        )

        if (
            "Increase recovery depth."
            in recommendations
        ):

            evolved_goals.append({
                "type": (
                    "improve_recovery_system"
                ),
                "priority": 1,
            })

        if (
            "Stabilize execution planning."
            in recommendations
        ):

            evolved_goals.append({
                "type": (
                    "refactor_execution_planner"
                ),
                "priority": 2,
            })

        if (
            "calculator"
            in original_goal.lower()
        ):

            evolved_goals.append({
                "type": (
                    "add_unit_tests"
                ),
                "priority": 3,
            })

            evolved_goals.append({
                "type": (
                    "improve_input_validation"
                ),
                "priority": 4,
            })

        return {
            "ok": True,
            "original_goal": (
                original_goal
            ),
            "evolved_goals": (
                evolved_goals
            ),
        }

