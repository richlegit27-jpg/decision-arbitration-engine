from nova_backend.core.context_fusion import (
    ContextFusionEngine,
)

from nova_backend.core.tool_executor import (
    ToolExecutor,
)

from nova_backend.core.tool_registry import (
    ToolRegistry,
)

from nova_backend.core.model_router import (
    ModelRouter,
)

from nova_backend.core.agent_registry import (
    AgentRegistry,
)

from nova_backend.core.agent_router import (
    AgentRouter,
)

from nova_backend.core.permission_controller import (
    PermissionController,
)

from nova_backend.core.memory_bridge import (
    MemoryBridge,
)

from nova_backend.core.planner_bridge import (
    PlannerBridge,
)

from nova_backend.core.execution_bridge import (
    ExecutionBridge,
)

from nova_backend.core.execution_engine import (
    ExecutionEngine,
)

from nova_backend.services.execution_step_service import (
    ExecutionStepService,
)

from nova_backend.core.evaluation_bridge import (
    EvaluationBridge,
)

from nova_backend.core.quality_gate_bridge import (
    QualityGateBridge,
)

from nova_backend.core.telemetry_bridge import (
    TelemetryBridge,
)

from nova_backend.core.recovery_bridge import (
    RecoveryBridge,
)

from nova_backend.core.learning_loop import (
    LearningLoop,
)

from nova_backend.core.reflection_engine import (
    ReflectionEngine,
)

from nova_backend.core.brain_pipeline import (
    BrainPipeline,
)

from nova_backend.core.project_bridge import (
    ProjectBridge,
)

from nova_backend.core.nova_state import (
    NovaState,
)

from nova_backend.core.execution_plan_normalizer import (
    ExecutionPlanNormalizer,
)


class NovaOrchestrator:


    def __init__(
        self,
        context_engine=None,
        model_router=None,
        agent_router=None,
        tool_executor=None,
        state=None,
        execution_state_service=None,
        memory_service=None,
    ):

        self.state = (
            state
            or NovaState()
        )

        self.context_engine = (
            context_engine
            or ContextFusionEngine(
                memory=memory_service,
            )
        )


        self.model_router = (
            model_router
            or ModelRouter()
        )


        self.agent_registry = (
            AgentRegistry()
        )


        self.agent_router = (
            agent_router
            or AgentRouter(
                self.agent_registry
            )
        )


        self.permission_controller = (
            PermissionController()
        )


        self.tool_registry = (
            ToolRegistry()
        )


        self.tool_executor = (
            tool_executor
            or ToolExecutor(
                self.tool_registry
            )
        )


        self.memory_bridge = (
            MemoryBridge()
        )


        self.execution_step_service = (
            ExecutionStepService(
                tool_executor=self.tool_executor,
            )
        )


        self.execution_engine = (
            ExecutionEngine(
                step_service=self.execution_step_service,
            )
        )


        self.execution_plan_normalizer = (
            ExecutionPlanNormalizer()
        )


        self.execution_bridge = (
            ExecutionBridge(
                execution_engine=self.execution_engine,
                execution_state_service=execution_state_service,
            )
        )


        self.planner_bridge = (
            PlannerBridge()
        )


        self.learning = (
            LearningLoop()
        )


        self.reflection = (
            ReflectionEngine()
        )



    def run(
        self,
        user_text,
        session_context=None,
        session_id="",
        decision=None,
    ):

        if session_id:
            self.state.session_id = (
                session_id
            )

        self.memory_bridge.apply(
            self.state,
            session_id,
        )

        state = {
            "input": user_text,
            "decision": decision or {},
            "context": {},
            "model": {},
            "agent": None,
            "tools": [],
        }

        state["context"] = (
            self.context_engine.build(
                user_text,
                session_context,
            )
        )

        state["model"] = (
            self.model_router.choose(
                user_text,
                state["context"],
            )
        )

        state["agent"] = (
            self.agent_router.choose(
                "general",
            )
        )

        decision_intent = (
            state["decision"].get("intent")
            if isinstance(
                state["decision"],
                dict,
            )
            else None
        )

        print(
            "[ORCHESTRATOR DECISION DEBUG]",
            state["decision"],
            decision_intent,
            flush=True,
        )

        if decision_intent == "mission_control":

            existing_state = {}

            if session_id:
                try:
                    existing_state = (
                        self.execution_bridge
                        .execution_state_service
                        .get_execution_state(
                            session_id
                        )
                        or {}
                    )

                except Exception as exc:
                    print(
                        "[MISSION CONTROL STATE LOAD FAILED]",
                        exc,
                        flush=True,
                    )

            state["execution"] = existing_state

            execution_payload = (
                existing_state.get(
                    "execution_state"
                )
                or existing_state.get(
                    "active_execution"
                )
                or existing_state.get(
                    "execution"
                )
                or existing_state
            )

            steps = execution_payload.get(
                "steps",
                [],
            )

            next_step = None

            if isinstance(
                steps,
                list,
            ):
                for step in steps:
                    if (
                        isinstance(step, dict)
                        and step.get("status")
                        != "complete"
                    ):
                        next_step = step
                        break

            if isinstance(
                steps,
                list,
            ):
                for step in steps:
                    if (
                        isinstance(step, dict)
                        and step.get("status")
                        != "complete"
                    ):
                        next_step = step
                        break

            state["next_step"] = next_step

            state["plan"] = {
                "steps": steps,
                "goal": existing_state.get(
                    "goal"
                ),
                "type": "project_state",
            }

            state["execution"] = (
                existing_state
                or {
                    "status": "waiting_for_project_state",
                }
            )

        else:

            state["plan"] = (
                self.planner_bridge.create_plan(
                    user_text,
                    state["context"],
                )
            )

            state["plan"] = (
                self.execution_plan_normalizer.normalize(
                    state["plan"]
                )
            )

            state["execution"] = (
                self.execution_bridge.execute(
                    state["plan"],
                    session_id,
                )
            )

        self.state.add_decision(
            "model",
            state["model"],
        )

        self.state.add_decision(
            "agent",
            state["agent"],
        )

        state["nova_state"] = (
            self.state.export()
        )

        return state