from nova_backend.core.memory_intelligence import MemoryIntelligence


class BrainPipeline:

    def __init__(
        self,
        orchestrator=None,
        planner_bridge=None,
        execution_bridge=None,
        evaluation_bridge=None,
        quality_gate=None,
        telemetry_bridge=None,
        recovery_bridge=None,
    ):

        self.orchestrator = orchestrator
        self.planner_bridge = planner_bridge
        self.execution_bridge = execution_bridge
        self.evaluation_bridge = evaluation_bridge
        self.quality_gate = quality_gate
        self.telemetry_bridge = telemetry_bridge
        self.recovery_bridge = recovery_bridge

        self.memory_intelligence = MemoryIntelligence()


    def run(
        self,
        user_text,
        session_id="",
        context=None,
    ):

        pipeline_state = {

            "input": user_text,

            "plan": None,

            "execution": None,

            "evaluation": None,

            "quality": None,

            "response": None,

        }


        try:

            if self.telemetry_bridge:

                self.telemetry_bridge.record(
                    "pipeline_start",
                    {
                        "session_id": session_id,
                    },
                )


            memory_candidate = self.memory_intelligence.extract_memory(
                user_text
            )

            if memory_candidate:

                pipeline_state["memory"] = memory_candidate

                pipeline_state["response"] = (
                    "Memory saved: "
                    + memory_candidate["content"]
                )

                return pipeline_state


            if self.orchestrator:

                brain_state = (
                    self.orchestrator.run(
                        user_text=user_text,
                        session_context=context,
                        session_id=session_id,
                    )
                )

                pipeline_state["brain"] = brain_state


            if self.planner_bridge:

                pipeline_state["plan"] = (
                    self.planner_bridge.create_plan(
                        user_text,
                        context,
                    )
                )


            if self.execution_bridge:

                pipeline_state["execution"] = (
                    self.execution_bridge.execute(
                        pipeline_state["plan"],
                        session_id,
                    )
                )


            if self.evaluation_bridge:

                pipeline_state["evaluation"] = (
                    self.evaluation_bridge.evaluate(
                        user_text,
                        pipeline_state["execution"],
                    )
                )


            return pipeline_state


        except Exception as exc:

            if self.recovery_bridge:

                return {
                    "error":
                        self.recovery_bridge.handle(
                            exc,
                            pipeline_state,
                        )
                }


            return {
                "error": str(exc)
            }