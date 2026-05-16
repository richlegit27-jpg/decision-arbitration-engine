class ReflectionEngine:

    def reflect(
        self,
        mission_result=None,
        world_state=None,
    ):

        mission_result = (
            mission_result
            if isinstance(
                mission_result,
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

        history = (
            mission_result.get(
                "history"
            )
            or []
        )

        reflection = {
            "success": mission_result.get(
                "ok",
                False,
            ),
            "completed_steps": 0,
            "failed_steps": 0,
            "observations": [],
            "recommended_improvements": [],
        }

        for item in history:

            step = item.get("step")

            if not isinstance(step, dict):
                continue

            status = str(
                step.get("status") or ""
            ).lower()

            if status == "completed":

                reflection[
                    "completed_steps"
                ] += 1

            if status == "failed":

                reflection[
                    "failed_steps"
                ] += 1

        if (
            reflection["failed_steps"]
            == 0
        ):

            reflection[
                "observations"
            ].append(
                "Mission completed successfully."
            )

        else:

            reflection[
                "observations"
            ].append(
                "Mission encountered failures."
            )

            reflection[
                "recommended_improvements"
            ].append(
                "Improve recovery strategy."
            )

        tool_history = (
            world_state.get(
                "tool_history"
            )
            or []
        )

        if len(tool_history) > 25:

            reflection[
                "recommended_improvements"
            ].append(
                "Optimize tool usage efficiency."
            )

        return reflection