class ContextFusionEngine:

    def fuse(
        self,
        execution_state=None,
        world_state=None,
        reflection=None,
        meta_reasoning=None,
        evolved_goals=None,
        knowledge_graph=None,
    ):

        execution_state = (
            execution_state
            if isinstance(
                execution_state,
                dict,
            )
            else {}
        )

        world_state = (
            world_state
            if isinstance(
                world_state,
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

        evolved_goals = (
            evolved_goals
            if isinstance(
                evolved_goals,
                dict,
            )
            else {}
        )

        fused = {
            "goal": (
                execution_state.get(
                    "original_user_text"
                )
            ),
            "execution_status": (
                execution_state.get(
                    "status"
                )
            ),
            "active_steps": (
                execution_state.get(
                    "steps",
                    [],
                )
            ),
            "recent_errors": (
                world_state.get(
                    "recent_errors",
                    [],
                )
            ),
            "successful_repairs": (
                world_state.get(
                    "successful_repairs",
                    [],
                )
            ),
            "reflection": reflection,
            "meta_reasoning": (
                meta_reasoning
            ),
            "evolved_goals": (
                evolved_goals.get(
                    "evolved_goals",
                    []
                )
            ),
            "knowledge_summary": (
                knowledge_graph
                .summarize()
                if knowledge_graph
                else {}
            ),
        }

        fused[
            "cognitive_priority"
        ] = self._calculate_priority(
            fused
        )

        return fused

    def _calculate_priority(
        self,
        fused_context=None,
    ):

        fused_context = (
            fused_context
            if isinstance(
                fused_context,
                dict,
            )
            else {}
        )

        errors = len(
            fused_context.get(
                "recent_errors",
                []
            )
        )

        goals = len(
            fused_context.get(
                "evolved_goals",
                []
            )
        )

        if errors > 5:
            return "critical"

        if goals > 3:
            return "high"

        return "normal"