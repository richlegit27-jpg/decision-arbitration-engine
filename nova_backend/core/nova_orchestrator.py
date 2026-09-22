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

from nova_backend.services.project_workspace_service import (
    project_workspace_service,
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
        project_workspace=None,
    ):

        self.state = (
            state
            or NovaState()
        )

        self.context_engine = (
            context_engine
            or ContextFusionEngine(
                memory=memory_service,
                project_workspace=(
                    project_workspace
                    or project_workspace_service
                ),
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

        print(
            "[ORCHESTRATOR SESSION CONTEXT PROJECT DEBUG]",
            {
                "has_session_context": isinstance(
                    session_context,
                    dict,
                ),
                "working_state": (
                    session_context.get("working_state")
                    if isinstance(session_context, dict)
                    else None
                ),
                "project": (
                    session_context.get("working_state", {}).get("project")
                    if isinstance(session_context, dict)
                    and isinstance(
                        session_context.get("working_state"),
                        dict,
                    )
                    else None
                ),
            },
            flush=True,
        )

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

        print(
            "[ORCHESTRATOR FUSED PROJECT DEBUG]",
            state["context"].get("project"),
            flush=True,
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

            project = (
                state["context"].get("project")
                if isinstance(
                    state.get("context"),
                    dict,
                )
                else {}
            )

            if not isinstance(
                project,
                dict,
            ):
                project = {}

            existing_state = (
                project.get("execution")
                or {}
            )

            state["execution"] = (
                existing_state
            )

            tasks = (
                project.get("tasks", [])
            )

            next_step = None

            if isinstance(
                tasks,
                list,
            ):
                for task in tasks:

                    if not isinstance(
                        task,
                        dict,
                    ):
                        continue

                    task_status = str(
                        task.get(
                            "status",
                            "",
                        )
                    ).strip().lower()

                    if task_status in {
                        "completed",
                        "complete",
                        "failed",
                        "blocked",
                    }:
                        continue

                    task_steps = (
                        task.get(
                            "steps",
                            [],
                        )
                    )

                    if isinstance(
                        task_steps,
                        list,
                    ):
                        for step in task_steps:

                            if not isinstance(
                                step,
                                dict,
                            ):
                                continue

                            step_status = str(
                                step.get(
                                    "status",
                                    "",
                                )
                            ).strip().lower()

                            if step_status not in {
                                "completed",
                                "complete",
                            }:
                                next_step = {
                                    "task_id": task.get(
                                        "id"
                                    ),
                                    "task_title": task.get(
                                        "title"
                                    ),
                                    **step,
                                    "project_context": (
                                        step.get(
                                            "project_context"
                                        )
                                        or step.get(
                                            "context"
                                        )
                                        or project.get(
                                            "description"
                                        )
                                        or project.get(
                                            "request"
                                        )
                                        or project.get(
                                            "title"
                                        )
                                        or project.get(
                                            "name"
                                        )
                                        or ""
                                    ),
                                    "goal": (
                                        step.get(
                                            "goal"
                                        )
                                        or project.get(
                                            "description"
                                        )
                                        or project.get(
                                            "request"
                                        )
                                        or project.get(
                                            "title"
                                        )
                                        or project.get(
                                            "name"
                                        )
                                        or ""
                                    ),
                                    "content": (
                                        step.get(
                                            "content"
                                        )
                                        or step.get(
                                            "file_content"
                                        )
                                        or task.get(
                                            "content"
                                        )
                                        or project.get(
                                            "content"
                                        )
                                        or ""
                                    ),
                                }
                                break

                    if next_step is not None:
                        break

            state["next_step"] = (
                next_step
            )

            print(
                "[ORCHESTRATOR NEXT STEP DEBUG]",
                next_step,
                flush=True,
            )

            state["plan"] = {
                "steps": (
                    [next_step]
                    if next_step is not None
                    else []
                ),
                "goal": project.get(
                    "description"
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