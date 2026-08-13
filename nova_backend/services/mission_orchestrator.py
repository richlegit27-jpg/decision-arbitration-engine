class MissionOrchestrator:

    def __init__(
        self,
        execution_brain=None,
        code_generator=None,
        tool_registry=None,
        retest_loop=None,
    ):
        self.execution_brain = (
            execution_brain
        )

        self.code_generator = (
            code_generator
        )

        self.tool_registry = (
            tool_registry
        )

        self.retest_loop = (
            retest_loop
        )


    def run_mission(
        self,
        execution_state=None,
    ):

        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        steps = (
            execution_state.get("steps")
            or []
        )

        history = []

        for step in steps:

            if not isinstance(step, dict):
                step = {
                    "title": str(step),
                    "status": "pending",
                }

            decision = (
                self.execution_brain
                .decide_next_action(
                    execution_state=execution_state,
                    current_step=step,
                )
                if self.execution_brain
                else {
                    "type": "complete_step"
                }
            )

            history.append(
                {
                    "step": step,
                    "decision": decision,
                }
            )

            decision_type = str(
                decision.get("type") or ""
            ).lower()


            if decision_type == "complete_step":

                step["status"] = (
                    "completed"
                )

                continue


            if decision_type == "generate_code":

                if not self.code_generator:

                    return {
                        "ok": False,
                        "error": "code_generator_missing",
                        "history": history,
                    }

                generation = (
                    self.code_generator
                    .generate_code(
                        step=step,
                        execution_state=(
                            execution_state
                        ),
                    )
                )

                history.append(
                    {
                        "generation": generation,
                    }
                )

                if not generation.get("ok"):

                    step["status"] = (
                        "failed"
                    )

                    return {
                        "ok": False,
                        "history": history,
                        "project_brain_decisions": history,
                        "failed_step": step,
                    }


                if self.tool_registry:

                    write_result = (
                        self.tool_registry.execute(
                            "write_file",
                            path=generation.get(
                                "target_file"
                            ),
                            content=generation.get(
                                "code"
                            ),
                        )
                    )

                    history.append(
                        {
                            "write_result": write_result,
                        }
                    )


                step["status"] = (
                    "completed"
                )

                continue


            if decision_type == "run_python_file":

                if not self.retest_loop:

                    return {
                        "ok": False,
                        "error": "retest_loop_missing",
                        "history": history,
                    }

                test_result = (
                    self.retest_loop
                    .attempt_recovery(
                        target_file=step.get(
                            "target_file"
                        ),
                    )
                )

                history.append(
                    {
                        "test_result": test_result,
                    }
                )

                if not test_result.get("ok"):

                    step["status"] = (
                        "failed"
                    )

                    return {
                        "ok": False,
                        "history": history,
                        "failed_step": step,
                    }


                step["status"] = (
                    "completed"
                )


        return {
            "ok": True,
            "history": history,
            "project_brain_decisions": history,
            "execution_state": execution_state,
        }