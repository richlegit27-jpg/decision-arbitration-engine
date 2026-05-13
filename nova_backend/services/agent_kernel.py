class AgentKernel:

    def __init__(
        self,
        mission_orchestrator=None,
        world_state=None,
        reflection_engine=None,
        strategy_engine=None,
    ):

        self.mission_orchestrator = (
            mission_orchestrator
        )

        self.world_state = (
            world_state
        )

        self.reflection_engine = (
            reflection_engine
        )

        self.strategy_engine = (
            strategy_engine
        )

    def run(
        self,
        execution_state=None,
    ):

        execution_state = (
            execution_state
            if isinstance(
                execution_state,
                dict,
            )
            else {}
        )

        mission_result = (
            self.mission_orchestrator
            .run_mission(
                execution_state=(
                    execution_state
                )
            )
        )

        reflection = (
            self.reflection_engine
            .reflect(
                mission_result=(
                    mission_result
                ),
                world_state=(
                    self.world_state
                    .get_state()
                ),
            )
        )

        mutations = (
            self.strategy_engine
            .mutate_strategy(
                reflection=reflection,
                execution_state=(
                    execution_state
                ),
            )
        )

        self.world_state.append_state(
            "execution_history",
            {
                "mission_result": (
                    mission_result
                ),
                "reflection": (
                    reflection
                ),
                "mutations": (
                    mutations
                ),
            },
        )

        return {
            "ok": mission_result.get(
                "ok",
                False,
            ),
            "mission_result": (
                mission_result
            ),
            "reflection": reflection,
            "mutations": mutations,
            "world_state_summary": (
                self.world_state
                .summarize()
            ),
        }