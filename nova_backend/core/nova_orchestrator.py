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

        if (
            isinstance(
                session_context,
                dict,
            )
            and isinstance(
                session_context.get(
                    "working_state"
                ),
                dict,
            )
        ):
            state["context"]["working_state"] = (
                session_context.get(
                    "working_state"
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

            context = (
                state.get("context")
                if isinstance(
                    state.get("context"),
                    dict,
                )
                else {}
            )

            working_state = (
                context.get("working_state")
                if isinstance(
                    context.get("working_state"),
                    dict,
                )
                else {}
            )

            print(
                "[MISSION CONTROL WORKING STATE DEBUG]",
                {
                    "working_state_status": (
                        working_state.get(
                            "active_execution",
                            {},
                        ).get("status")
                        if isinstance(
                            working_state.get(
                                "active_execution"
                            ),
                            dict,
                        )
                        else None
                    ),
                    "working_state_index": (
                        working_state.get(
                            "active_execution",
                            {},
                        ).get("current_step_index")
                        if isinstance(
                            working_state.get(
                                "active_execution"
                            ),
                            dict,
                        )
                        else None
                    ),

                    "working_state_step_count": len(
                        working_state.get(
                            "active_execution",
                            {},
                        ).get("steps") or []
                    )
                    if isinstance(
                        working_state.get(
                            "active_execution"
                        ),
                        dict,
                    )
                    else 0,
                },
                flush=True,
            )

            existing_state = (
                working_state.get(
                    "active_execution"
                )
                if isinstance(
                    working_state,
                    dict,
                )
                and isinstance(
                    working_state.get(
                        "active_execution"
                    ),
                    dict,
                )
                else None
            )

            if not existing_state:
                existing_state = (
                    context.get(
                        "execution_state"
                    )
                    if isinstance(
                        context,
                        dict,
                    )
                    and isinstance(
                        context.get(
                            "execution_state"
                        ),
                        dict,
                    )
                    else None
                )

            if not existing_state:
                existing_state = (
                    project.get("execution")
                    if isinstance(
                        project.get("execution"),
                        dict,
                    )
                    else {}
                )

            executed_steps = (
                existing_state.get("steps")
                if isinstance(
                    existing_state,
                    dict,
                )
                else []
            )

            executed_steps = (
                existing_state.get("steps")
                if isinstance(
                    existing_state,
                    dict,
                )
                else []
            )

            completed_execution_step_titles = {
                str(
                    execution_step.get("title")
                    or ""
                ).strip()
                for execution_step in (
                    executed_steps
                    if isinstance(
                        executed_steps,
                        list,
                    )
                    else []
                )
                if isinstance(
                    execution_step,
                    dict,
                )
                and str(
                    execution_step.get("status")
                    or ""
                ).strip().lower()
                in {
                    "completed",
                    "complete",
                }
                and str(
                    execution_step.get("title")
                    or ""
                ).strip()
            }


            state["execution"] = (
                existing_state
            )

            tasks = (
                project.get("tasks", [])
            )

            next_step = None

            print(
                "[ORCHESTRATOR EXECUTION STATE BEFORE SELECTOR]",
                {
                    "status": (
                        existing_state.get("status")
                        if isinstance(
                            existing_state,
                            dict,
                        )
                        else None
                    ),
                    "current_index": (
                        existing_state.get(
                            "current_index"
                        )
                        if isinstance(
                            existing_state,
                            dict,
                        )
                        else None
                    ),
                    "step_count": len(
                        existing_state.get("steps") or []
                    )
                    if isinstance(
                        existing_state,
                        dict,
                    )
                    else 0,
                    "complete": (
                        existing_state.get("complete")
                        if isinstance(
                            existing_state,
                            dict,
                        )
                        else None
                    ),
                },
                flush=True,
            )

            execution_status = str(
                existing_state.get("status")
                or ""
            ).strip().lower()

            execution_steps = (
                existing_state.get("steps")
                if isinstance(
                    existing_state,
                    dict,
                )
                else []
            )

            execution_current_index = (
                existing_state.get(
                    "current_index"
                )
                if isinstance(
                    existing_state,
                    dict,
                )
                else None
            )

            if (
                execution_status
                not in {
                    "complete",
                    "completed",
                }
                and isinstance(
                    execution_steps,
                    list,
                )
            ):

                if (
                    isinstance(
                        execution_current_index,
                        int,
                    )
                    and execution_current_index < len(
                        execution_steps
                    )
                ):
                    execution_step = execution_steps[
                        execution_current_index
                    ]

                    if isinstance(
                        execution_step,
                        dict,
                    ):
                        next_step = dict(
                            execution_step
                        )

            if (
                next_step is None
                and isinstance(
                    tasks,
                    list,
                )
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

                    if not isinstance(
                        task_steps,
                        list,
                    ):
                        continue

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

                        step_title = str(
                            step.get(
                                "title"
                            )
                            or ""
                        ).strip()

                        print(
                            "[ORCHESTRATOR STEP FILTER DEBUG]",
                            {
                                "step_title": step_title,
                                "completed_titles": sorted(
                                    completed_execution_step_titles
                                ),
                                "step_status": step_status,
                            },
                            flush=True,
                        )

                        print(
                            "[ORCHESTRATOR STEP FILTER DEBUG]",
                            {
                                "step_title": step_title,
                                "completed_titles": sorted(
                                    completed_execution_step_titles
                                ),
                                "step_status": step_status,
                            },
                            flush=True,
                        )

                        if (
                            step_title
                            and step_title
                            in completed_execution_step_titles
                        ):
                            continue

                        if step_status in {
                            "completed",
                            "complete",
                            "failed",
                            "blocked",
                        }:
                            continue

                        next_step = {
                            **step,
                            "task_id": (
                                step.get(
                                    "task_id"
                                )
                                or task.get(
                                    "id"
                                )
                                or ""
                            ),
                            "task_title": (
                                task.get(
                                    "title"
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