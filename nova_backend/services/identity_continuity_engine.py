from datetime import datetime


class IdentityContinuityEngine:

    def __init__(self):

        self.identity_state = {
            "system_name": "Nova",
            "active_mission": None,
            "long_term_objectives": [],
            "core_principles": [
                "stability",
                "autonomy",
                "recovery",
                "continuous_improvement",
            ],
            "historical_reflections": [],
            "architectural_changes": [],
            "evolution_history": [],
            "last_cycle": None,
        }

    def register_cycle(
        self,
        consciousness_result=None,
    ):

        consciousness_result = (
            consciousness_result
            if isinstance(
                consciousness_result,
                dict,
            )
            else {}
        )

        reflection = (
            consciousness_result.get(
                "reflection",
                {}
            )
        )

        improvements = (
            consciousness_result.get(
                "improvements",
                {}
            )
        )

        self.identity_state[
            "historical_reflections"
        ].append(
            reflection
        )

        self.identity_state[
            "evolution_history"
        ].append(
            improvements
        )

        self.identity_state[
            "last_cycle"
        ] = (
            datetime.utcnow()
            .isoformat()
        )

    def update_active_mission(
        self,
        mission="",
    ):

        self.identity_state[
            "active_mission"
        ] = mission

    def add_objective(
        self,
        objective="",
    ):

        if (
            objective
            and objective
            not in self.identity_state[
                "long_term_objectives"
            ]
        ):

            self.identity_state[
                "long_term_objectives"
            ].append(
                objective
            )

    def record_architecture_change(
        self,
        change="",
    ):

        if change:

            self.identity_state[
                "architectural_changes"
            ].append(
                change
            )

    def summarize(self):

        return {
            "system_name": (
                self.identity_state.get(
                    "system_name"
                )
            ),
            "active_mission": (
                self.identity_state.get(
                    "active_mission"
                )
            ),
            "long_term_objectives": (
                self.identity_state.get(
                    "long_term_objectives"
                )
            ),
            "reflection_cycles": len(
                self.identity_state.get(
                    "historical_reflections",
                    [],
                )
            ),
            "evolution_events": len(
                self.identity_state.get(
                    "evolution_history",
                    [],
                )
            ),
            "last_cycle": (
                self.identity_state.get(
                    "last_cycle"
                )
            ),
        }

