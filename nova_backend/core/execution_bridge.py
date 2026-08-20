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


            if not goal or not steps:

                result["status"] = (
                    "skipped_no_execution_plan"
                )

                return result


            print(
                "[EXECUTION BRIDGE RECEIVED PLAN]",
                plan,
            )

            print(
                "[EXECUTION BRIDGE GOAL]",
                goal,
            )

            print(
                "[EXECUTION BRIDGE STEPS]",
                steps,
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

                execution_state = {
                    "id": session_id,
                    "goal": goal,
                    "steps": steps,
                    "plan": plan,
                    "output": output,
                    "status": "completed",
                    "session_id": session_id,
                    "current_step_index": len(steps),
                    "_execution_processing": False,
                    "lock": False,
                }


                print(
                    "[EXECUTION BRIDGE BEFORE SAVE]",
                    execution_state,
                )


                print(
                    "[EXECUTION BRIDGE SAVE TEST]",
                    session_id,
                )


                saved = (
                    self.execution_state_service
                    .save_execution_state(
                        session_id,
                        execution_state,
                    )
                )


                print(
                    "[EXECUTION BRIDGE SAVE RESULT]",
                    saved,
                )


        except Exception as exc:

            result["status"] = (
                "failed"
            )

            result["error"] = str(exc)


        return result