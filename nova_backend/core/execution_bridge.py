class ExecutionBridge:

    def __init__(
        self,
        execution_engine=None,
        execution_state_service=None,
    ):

        self.execution_engine = (
            execution_engine
        )

        self.execution_state_service = (
            execution_state_service
        )


    def execute(
        self,
        plan,
        session_id="",
    ):

        result = {
            "status": "pending",
            "plan": plan,
            "session_id": session_id,
            "output": None,
        }


        if not self.execution_engine:

            result["status"] = (
                "no_execution_engine"
            )

            return result


        try:

            goal = ""

            steps = plan


            if isinstance(
                plan,
                dict,
            ):

                goal = (
                    plan.get("goal")
                    or ""
                )

                steps = (
                    plan.get("steps")
                    or []
                )


            output = (
                self.execution_engine.run(
                    goal=goal,
                    steps=steps,
                )
            )

            result["output"] = output

            result["status"] = (
                "completed"
            )


            if (
                self.execution_state_service
                and session_id
            ):

                self.execution_state_service.save_execution_state(
                    session_id,
                    output,
                )


        except Exception as exc:

            result["status"] = (
                "failed"
            )

            result["error"] = str(exc)


        return result