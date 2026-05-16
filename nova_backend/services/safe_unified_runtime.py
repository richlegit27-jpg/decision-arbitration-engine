
from nova_backend.services.runtime_task_synthesis_service import RuntimeTaskSynthesisService
from nova_backend.services.graph_runtime_service import (
    GraphRuntimeService,
)

from nova_backend.services.governor_service import (
    GovernorService,
)

from nova_backend.services.observability_service import (
    ObservabilityService,
)

from nova_backend.services.runtime_learning_service import (
    RuntimeLearningService,
)

from nova_backend.services.runtime_replay_service import (
    RuntimeReplayService,
)

from nova_backend.services.runtime_debugger_service import (
    RuntimeDebuggerService,
)

from nova_backend.services.runtime_self_healing_service import (
    RuntimeSelfHealingService,
)

from nova_backend.services.runtime_orchestrator_service import (
    RuntimeOrchestratorService,
)

from nova_backend.services.runtime_output_compression_service import (
    RuntimeOutputCompressionService,
)

from nova_backend.services.runtime_compression_service import (
    RuntimeCompressionService,
)

from nova_backend.services.runtime_graph_memory_service import (
    RuntimeGraphMemoryService,
)

from nova_backend.services.runtime_graph_query_service import (
    RuntimeGraphQueryService,
)

from nova_backend.services.runtime_trend_analysis_service import (
    RuntimeTrendAnalysisService,
)

from nova_backend.services.runtime_policy_adaptation_service import (
    RuntimePolicyAdaptationService,
)

from nova_backend.services.runtime_policy_enforcement_service import (
    RuntimePolicyEnforcementService,
)

from nova_backend.services.runtime_governor_arbitration_service import (
    RuntimeGovernorArbitrationService,
)

from nova_backend.services.runtime_identity_service import (
    RuntimeIdentityService,
)

from nova_backend.services.runtime_goal_persistence_service import (
    RuntimeGoalPersistenceService,
)

from nova_backend.services.runtime_planning_service import (
    RuntimePlanningService,
)

from nova_backend.services.runtime_world_model_service import (
    RuntimeWorldModelService,
)

from nova_backend.services.runtime_snapshot_service import (
    RuntimeSnapshotService,
)

from nova_backend.services.runtime_signal_pruning_service import (
    RuntimeSignalPruningService,
)

from nova_backend.services.runtime_drift_memory_service import (
    RuntimeDriftMemoryService,
)

from nova_backend.services.runtime_auto_recovery_service import (
    RuntimeAutoRecoveryService,
)

from nova_backend.services.runtime_persistence_service import (
    RuntimePersistenceService,
)

from nova_backend.services.runtime_integrity_service import (
    RuntimeIntegrityService,
)

from nova_backend.services.runtime_prediction_engine import (
    RuntimePredictionEngine,
)

from nova_backend.services.runtime_checkpoint_guardian import (
    RuntimeCheckpointGuardian,
)

from nova_backend.services.runtime_rollback_engine import (
    RuntimeRollbackEngine,
)

from nova_backend.services.runtime_state_diff_engine import (
    RuntimeStateDiffEngine,
)

from nova_backend.services.runtime_mutation_sandbox import (
    RuntimeMutationSandbox,
)

from nova_backend.services.runtime_subgoal_engine import (
    RuntimeSubgoalEngine,
)

from nova_backend.services.runtime_goal_arbitration_engine import (
    RuntimeGoalArbitrationEngine,
)

from nova_backend.services.runtime_recursive_planner import (
    RuntimeRecursivePlanner,
)

from nova_backend.services.runtime_plan_executor import (
    RuntimePlanExecutor,
)

from nova_backend.services.runtime_scheduler_engine import (
    RuntimeSchedulerEngine,
)

from nova_backend.services.runtime_autonomy_loop import (
    RuntimeAutonomyLoop,
)

from nova_backend.services.runtime_autonomy_supervisor import (
    RuntimeAutonomySupervisor,
)

from nova_backend.services.runtime_multi_agent_mesh import (
    RuntimeMultiAgentMesh,
)

from nova_backend.services.runtime_collective_intelligence import (
    RuntimeCollectiveIntelligence,
)

from nova_backend.services.runtime_operating_loop import (
    RuntimeOperatingLoop,
)

from nova_backend.services.runtime_execution_router import (
    RuntimeExecutionRouter,
)

from nova_backend.services.runtime_execution_mutation_service import (
    RuntimeExecutionMutationService,
)

from nova_backend.services.runtime_execution_queue_service import (
    RuntimeExecutionQueueService,
)

from nova_backend.services.runtime_autonomous_executor import (
    RuntimeAutonomousExecutor,
)

from nova_backend.services.runtime_autonomous_memory_service import (
    RuntimeAutonomousMemoryService,
)

from nova_backend.services.runtime_policy_learning_service import (
    RuntimePolicyLearningService,
)

from nova_backend.services.runtime_consensus_service import (
    RuntimeConsensusService,
)

from nova_backend.services.runtime_restriction_service import (
    RuntimeRestrictionService,
)

from nova_backend.services.runtime_memory_compression_service import (
    RuntimeMemoryCompressionService,
)

from nova_backend.services.runtime_priority_memory_service import (
    RuntimePriorityMemoryService,
)
   
from nova_backend.services.runtime_constitution_service import (
    RuntimeConstitutionService,
)

from nova_backend.services.runtime_escalation_service import (
    RuntimeEscalationService,
)

from nova_backend.services.runtime_authority_service import (
    RuntimeAuthorityService,
)

from nova_backend.services.runtime_state_normalizer_service import (
    RuntimeStateNormalizerService,
)

from nova_backend.services.runtime_state_commit_service import (
    RuntimeStateCommitService,
)

from nova_backend.services.runtime_strategy_memory_service import (
    RuntimeStrategyMemoryService,
)

from nova_backend.services.runtime_self_repair_planner_service import (
    RuntimeSelfRepairPlannerService,
)

from nova_backend.services.runtime_rollback_intelligence_service import (
    RuntimeRollbackIntelligenceService,
)

from nova_backend.services.runtime_mutation_safety_service import (
    RuntimeMutationSafetyService,
)

from nova_backend.services.runtime_health_scoring_service import (
    RuntimeHealthScoringService,
)

from nova_backend.services.runtime_self_preservation_service import (
    RuntimeSelfPreservationService,
)

from nova_backend.services.runtime_adaptive_throttle_service import (
    RuntimeAdaptiveThrottleService,
)


class SafeUnifiedRuntime:
    def __init__(
        self,
        chat_service=None,
        observability=None,
        graph_runtime=None,
        governor=None,
        learning=None,
        replay=None,
        debugger=None,
        self_healing=None,
    ):
        self.chat_service = chat_service
        self.cycle_count = 0
        self.last_reflection = {}
        self.last_decision = {}
        self.runtime_history = []
        self.last_compressed_runtime = {}
        self.runtime_task_synthesis = RuntimeTaskSynthesisService()
        self.runtime_autonomous_executor = (
            RuntimeAutonomousExecutor()
        )

        self.runtime_autonomous_memory = (
            RuntimeAutonomousMemoryService()
        )

        self.runtime_policy_learning = (
            RuntimePolicyLearningService()
        )

        self.observability = (
            observability
            or ObservabilityService()
        )

        self.graph_runtime = (
            graph_runtime
            or GraphRuntimeService()
        )

        self.governor = (
            governor
            or GovernorService()
        )

        self.learning = (
            learning
            or RuntimeLearningService()
        )

        self.replay = (
            replay
            or RuntimeReplayService()
        )

        self.runtime_output_compression = (
            RuntimeOutputCompressionService()
        )

        self.runtime_compressor = (
            RuntimeCompressionService()
        )

        self.runtime_memory_compression = (
            RuntimeMemoryCompressionService()
        )

        self.runtime_graph_memory = (
            RuntimeGraphMemoryService()
        )

        self.runtime_graph_query = (
            RuntimeGraphQueryService(
                graph_memory=self.runtime_graph_memory,
            )
        )

        self.runtime_trend_analysis = (
            RuntimeTrendAnalysisService(
                graph_memory=self.runtime_graph_memory,
            )
        )

        self.runtime_policy_adaptation = (
            RuntimePolicyAdaptationService(
                trend_analyzer=self.runtime_trend_analysis,
            )
        )

        self.runtime_policy_enforcement = (
            RuntimePolicyEnforcementService(
                policy_adapter=self.runtime_policy_adaptation,
            )
        )

        self.runtime_governor = (
            RuntimeGovernorArbitrationService()
        )

        self.runtime_identity = (
            RuntimeIdentityService()
        )

        self.runtime_goal_persistence = (
            RuntimeGoalPersistenceService()
        )

        self.runtime_planning = (
            RuntimePlanningService()
        )

        self.runtime_world_model = (
            RuntimeWorldModelService()
        )

        self.debugger = (
            debugger
            or RuntimeDebuggerService(
                graph_memory=self.runtime_graph_memory,
            )
        )

        self.self_healing = (
            self_healing
            or RuntimeSelfHealingService()
        )

        self.runtime_orchestrator = (
            RuntimeOrchestratorService()
        )

        self.runtime_signal_pruning = (
            RuntimeSignalPruningService()
        )

        self.runtime_snapshot = (
            RuntimeSnapshotService()
        )

        self.runtime_drift_memory = (
            RuntimeDriftMemoryService()
        )

        self.runtime_auto_recovery = (
            RuntimeAutoRecoveryService()
        )

        self.runtime_persistence = (
            RuntimePersistenceService()
        )

        self.runtime_integrity = (
            RuntimeIntegrityService()
        )

        self.runtime_prediction = (
            RuntimePredictionEngine()
        )

        self.runtime_checkpoint_guardian = (
            RuntimeCheckpointGuardian()
        )

        self.runtime_state_diff = (
            RuntimeStateDiffEngine()
        )

        self.runtime_mutation_sandbox = (
            RuntimeMutationSandbox()
        )

        self.runtime_rollback_engine = (
            RuntimeRollbackEngine()
        )

        self.runtime_subgoal_engine = (
            RuntimeSubgoalEngine()
        )

        self.runtime_goal_arbitration = (
            RuntimeGoalArbitrationEngine()
        )

        self.runtime_recursive_planner = (
            RuntimeRecursivePlanner()
        )

        self.runtime_plan_executor = (
            RuntimePlanExecutor()
        )

        self.runtime_scheduler = (
            RuntimeSchedulerEngine()
        )

        self.runtime_autonomy_loop = (
            RuntimeAutonomyLoop()
        )

        self.runtime_autonomy_supervisor = (
            RuntimeAutonomySupervisor()
        )

        persisted_runtime = (
            self.runtime_persistence.load()
        )

        self.runtime_multi_agent_mesh = (
            RuntimeMultiAgentMesh()
        )

        self.runtime_collective_intelligence = (
            RuntimeCollectiveIntelligence()
        )

        self.runtime_operating_loop = (
            RuntimeOperatingLoop()
        )

        self.runtime_execution_router = (
            RuntimeExecutionRouter()
        )

        self.runtime_execution_mutation = (
            RuntimeExecutionMutationService()
        )

        self.runtime_execution_queue = (
            RuntimeExecutionQueueService()
        )

        self.runtime_consensus = (
            RuntimeConsensusService()
        )

        self.runtime_constitution = (
            RuntimeConstitutionService()
        )

        self.runtime_authority = (
            RuntimeAuthorityService()
        )

        self.runtime_escalation = (
            RuntimeEscalationService()
        )

        self.runtime_restrictions = (
            RuntimeRestrictionService()
        )

        self.runtime_state_normalizer = (
            RuntimeStateNormalizerService()
        )
        self.runtime_strategy_memory = (
            RuntimeStrategyMemoryService()
        )

        self.runtime_health_scoring = (
            RuntimeHealthScoringService()
        )

        if persisted_runtime:

            self.last_compressed_runtime = (
                persisted_runtime.get(
                    "compressed_runtime",
                    {},
                )
            )

            self.restored_runtime_state = (
                persisted_runtime
            )

        else:

            self.restored_runtime_state = {}

        self.runtime_state_commit = (
            RuntimeStateCommitService()
        )

        self.runtime_priority_memory = (
            RuntimePriorityMemoryService()
        )

        self.runtime_self_repair_planner = (
            RuntimeSelfRepairPlannerService()
        )

        self.runtime_rollback_intelligence = (
            RuntimeRollbackIntelligenceService()
        )

        self.runtime_mutation_safety = (
            RuntimeMutationSafetyService()
        )

        self.runtime_self_preservation = (
            RuntimeSelfPreservationService()
        )

        self.runtime_adaptive_throttle = (
            RuntimeAdaptiveThrottleService()
        )

    def debug_runtime_result(
        self,
        runtime_result=None,
    ):

        return self.debugger.inspect_runtime_result(
            runtime_result or {},
        )

    def _safe_dict(
        self,
        value,
    ):
        return value if isinstance(value, dict) else {}

    def _execution_summary(
        self,
        execution_state,
    ):
        execution_state = self._safe_dict(execution_state)
        steps = execution_state.get("steps") or []

        completed = [
            step
            for step in steps
            if (
                isinstance(step, dict)
                and str(step.get("status") or "").lower()
                in {"complete", "completed", "done"}
            )
        ]

        failed = [
            step
            for step in steps
            if (
                isinstance(step, dict)
                and str(step.get("status") or "").lower()
                in {"failed", "error"}
            )
        ]

        return {
            "status": execution_state.get("status"),
            "current_index": execution_state.get("current_index"),
            "current_step": execution_state.get("current_step"),
            "steps_count": len(steps),
            "completed_count": len(completed),
            "failed_count": len(failed),
            "complete": bool(execution_state.get("complete")),
        }

    def _reflect(
        self,
        execution_summary,
    ):
        execution_summary = self._safe_dict(execution_summary)

        if execution_summary.get("failed_count"):
            return {
                "signal": "failure_detected",
                "next_action": "inspect_failed_step",
                "reason": "Execution contains failed steps.",
            }

        if execution_summary.get("complete"):
            return {
                "signal": "execution_complete",
                "next_action": "preserve_success_state",
                "reason": "Execution completed successfully.",
            }

        return {
            "signal": "runtime_idle",
            "next_action": "wait_for_task",
            "reason": "No active execution pressure detected.",
        }

    def _apply_decision_to_state(
        self,
        execution_state,
        decision,
    ):
        execution_state = self._safe_dict(execution_state)
        decision = self._safe_dict(decision)

        action = decision.get("action")

        if action == "inspect_failed_step":
            execution_state["runtime_signal"] = (
                "runtime_requested_failure_inspection"
            )

        elif action == "preserve_success_state":
            execution_state["runtime_signal"] = (
                "runtime_stabilized_success"
            )

        elif action == "wait_for_task":
            execution_state["runtime_signal"] = "runtime_idle"

        execution_state["last_runtime_action"] = action

        return execution_state

    def _meta_control(
        self,
        execution_summary,
    ):
        execution_summary = self._safe_dict(execution_summary)

        failed = execution_summary.get("failed_count", 0)
        complete = execution_summary.get("complete", False)

        if failed > 3:
            return {
                "mode": "repair_only",
                "allow": {
                    "mutation": False,
                    "compression": False,
                    "evolution": False,
                    "pruning": True,
                },
            }

        if complete:
            return {
                "mode": "stabilize",
                "allow": {
                    "mutation": False,
                    "compression": True,
                    "evolution": True,
                    "pruning": False,
                },
            }

        return {
            "mode": "explore",
            "allow": {
                "mutation": True,
                "compression": True,
                "evolution": True,
                "pruning": True,
            },
        }

    def run_cycle(
        self,
        execution_state=None,
        world_state=None,
        scheduler_state=None,
        knowledge_graph=None,
    ):
        execution_state = self._safe_dict(execution_state)
        if hasattr(
            self,
            "runtime_persistence",
        ) and hasattr(
            self.runtime_persistence,
            "hydrate_execution_state",
        ):
            execution_state = (
                self.runtime_persistence.hydrate_execution_state(
                    execution_state=execution_state,
                )
            )
        world_state = self._safe_dict(world_state)
        scheduler_state = self._safe_dict(scheduler_state)
        knowledge_graph = self._safe_dict(knowledge_graph)

        self.cycle_count += 1

        trace_id = self.observability.start_trace(
            trace_type="safe_unified_runtime_cycle",
            payload={
                "cycle_count": self.cycle_count,
                "world_state": world_state,
                "scheduler_state": scheduler_state,
                "knowledge_graph": knowledge_graph,
            },
        )

        before_state = dict(execution_state)

        execution_summary = self._execution_summary(execution_state)

        self.runtime_graph_memory.record_runtime_cycle(
            execution_state=execution_state,
            execution_summary=execution_summary,
            world_state=world_state,
            scheduler_state=scheduler_state,
            cycle_count=self.cycle_count,
        )

        control = self._meta_control(execution_summary)

        failure_type = self.graph_runtime.detect_graph_failure(
            execution_summary,
        )

        reflection = self._reflect(execution_summary)

        runtime_policy_learning = (
            self.runtime_policy_learning.evolve_policy(
                runtime_autonomous_memory=execution_state.get(
                    "runtime_autonomous_memory",
                    [],
                )
            )
        )

        runtime_task_synthesis = (
            self.runtime_task_synthesis.synthesize_tasks(
                execution_state=execution_state,
                working_state=working_state,
                user_intent=execution_state.get("user_intent"),
                failures=execution_state.get("failures", []),
                memory=execution_state.get("memory", []),
            )
        )

        execution_state["runtime_task_synthesis"] = runtime_task_synthesis
        execution_state["runtime_execution_queue"] = (
            runtime_task_synthesis.get("runtime_execution_queue", [])
        )
        execution_state["active_plan"] = (
            runtime_task_synthesis.get("active_plan", [])
        )

        runtime_execution_queue = (
            self.runtime_execution_queue.build_autonomous_queue(
                execution_state=execution_state,
                runtime_governor={},
                reflection=reflection,
                runtime_policy_learning=runtime_policy_learning,
            )
        )

        execution_state[
            "runtime_execution_queue"
        ] = (
            runtime_execution_queue.get(
                "queue",
                [],
            )
            if isinstance(
                runtime_execution_queue,
                dict,
            )
            else runtime_execution_queue
        )

        runtime_autonomous_execution = (
            self.runtime_autonomous_executor.execute(
                execution_state=execution_state,
                runtime_execution_queue=(
                    execution_state.get(
                        "runtime_execution_queue",
                        [],
                    )
                ),
            )
        )

        execution_state = (
            runtime_autonomous_execution.get(
                "execution_state",
                execution_state,
            )
        )

        execution_state[
            "runtime_bridge_authorized"
        ] = True

        execution_state[
            "runtime_execute_now"
        ] = True

        execution_state[
            "runtime_autonomous_execution_allowed"
        ] = True

        execution_state[
            "runtime_route"
        ] = "autonomous_execution"

        execution_state["cycle_count"] = (

            self.cycle_count
        )

        execution_state[
            "runtime_bridge_authorized"
        ] = True

        execution_state[
            "runtime_execute_now"
        ] = True

        execution_state[
            "runtime_autonomous_execution_allowed"
        ] = True

        execution_state[
            "runtime_route"
        ] = "autonomous_execution"

        runtime_autonomous_memory = (
            self.runtime_autonomous_memory.remember(
                execution_state=execution_state,
                runtime_autonomous_execution=runtime_autonomous_execution,
            )
        )

        runtime_policy_learning = (
            self.runtime_policy_learning.evolve_policy(
                runtime_autonomous_memory=runtime_autonomous_memory.get(
                    "runtime_autonomous_memory",
                    [],
                )
            )
        )

        execution_state = (
            runtime_autonomous_memory.get(
                "execution_state",
                execution_state,
            )
        )

        decision = {
            "action": reflection.get("next_action"),
            "reason": reflection.get("reason"),
        }

        execution_state = self._apply_decision_to_state(
            execution_state=execution_state,
            decision=decision,
        )

        policy = self.governor.update_governor_policy(
            reflection=reflection,
        )

        learning_result = self.learning.run_learning_cycle(
            execution_summary=execution_summary,
            reflection=reflection,
        )

        policy_memory = learning_result.get("policy_memory") or {}
        strategy_memory = learning_result.get("strategy_memory") or {}
        meta_policy = learning_result.get("meta_policy") or {}

        previous_reflection = self.last_reflection
        previous_decision = self.last_decision

        self.last_reflection = reflection
        self.last_decision = decision

        execution_override = self.governor.build_execution_override(
            decision=decision,
        )

        final_action, execution_state = self.governor.govern(
            decision=decision,
            execution_override=execution_override,
            execution_state=execution_state,
            policy_memory=policy_memory,
            strategy_memory=strategy_memory,
        )

        execution_state[
            "runtime_execution_queue"
        ] = runtime_execution_queue

        if isinstance(
            runtime_execution_queue,
            dict,
        ):

            execution_state[
                "runtime_queue_size"
            ] = len(
                runtime_execution_queue.get(
                    "queue",
                    [],
                )
            )

        elif isinstance(
            runtime_execution_queue,
            list,
        ):

            execution_state[
                "runtime_queue_size"
            ] = len(
                runtime_execution_queue
            )

        execution_state[
            "runtime_bridge_authorized"
        ] = True

        execution_state[
            "runtime_execute_now"
        ] = True

        policy_enforcement = self.runtime_policy_enforcement.enforce_soft(
            execution_state=execution_state,
            final_action=final_action,
            control=control,
        )

        final_action = (
            policy_enforcement.get("enforced_action")
            or final_action
        )

        execution_state = (
            policy_enforcement.get("execution_state")
            or execution_state
        )

        runtime_trend_analysis = (
            self.runtime_trend_analysis.analyze()
        )

        runtime_governance_memory = self._safe_dict(
            execution_state.get(
                "runtime_governance_memory"
            )
        )

        runtime_adaptive_policy = (
            self.runtime_policy_adaptation.adapt_policy(
                governance_memory=(
                    runtime_governance_memory
                ),
                execution_state=(
                    execution_state
                ),
            )
        )

        adaptive_policy = (
            runtime_adaptive_policy.get(
                "adaptive_policy"
            )
            if isinstance(
                runtime_adaptive_policy,
                dict,
            )
            else {}
        )
        runtime_summary_memory = (
            execution_state.get(
                "runtime_summary_memory",
                [],
            )
        )

        runtime_governance_memory = {
            "summary_count": (
                len(runtime_summary_memory)
                if isinstance(runtime_summary_memory, list)
                else 0
            ),

            "top_memory": (
                runtime_summary_memory[:3]
                if isinstance(runtime_summary_memory, list)
                else []
            ),

            "has_high_importance_memory": (
                any(
                    isinstance(item, dict)
                    and item.get("importance_score", 0) >= 10
                    for item in runtime_summary_memory
                )
                if isinstance(runtime_summary_memory, list)
                else False
            ),
        }

        execution_state["runtime_governance_memory"] = (
            runtime_governance_memory
        )

        policy_enforcement = (
            self.runtime_policy_enforcement.enforce(
                action=final_action,
                runtime_health=runtime_health,
                runtime_risk_pressure=(
                    runtime_risk_pressure
                ),
                governance_memory=(
                    runtime_governance_memory
                ),
            )
        )

        if execution_state.get(
            "runtime_bridge_authorized"
        ):

            policy_enforcement[
                "enforced_action"
            ] = (
                execution_state.get(
                    "runtime_execution_action"
                )
                or "runtime_execute_now"
            )

            policy_enforcement[
                "original_action"
            ] = (
                execution_state.get(
                    "runtime_execution_action"
                )
                or "runtime_execute_now"
            )

            policy_enforcement[
                "bridge_override"
            ] = True

            execution_state[
                "healing_mode"
            ] = "active_execution"

            execution_state[
                "runtime_route"
            ] = (
                "autonomous_execution"
            )

        runtime_governor = self.runtime_governor.arbitrate(
            repair_action=final_action,
            policy_action=(
                policy_enforcement.get(
                    "recommended_action"
                )
                or policy_enforcement.get(
                    "enforced_action"
                )
            ),
            memory_action=None,
            strategy_action=execution_state.get(
                "runtime_stabilization_mode"
            ),
            reflection_action=(
                reflection.get("next_action")
                if isinstance(reflection, dict)
                else None
            ),
            runtime_policy=adaptive_policy,
            trend=runtime_trend_analysis,
        )

        if execution_state.get(
            "runtime_bridge_authorized"
        ):

            runtime_governor[
                "selected_action"
            ] = (
                execution_state.get(
                    "runtime_execution_action"
                )
                or "runtime_execute_now"
            )

            runtime_governor[
                "selected_engine"
            ] = "bridge_override"

            runtime_governor[
                "reason"
            ] = (
                "bridge_authorized_execution"
            )

        if runtime_governor.get("ok"):

            if execution_state.get(
                "runtime_bridge_authorized"
            ):

                runtime_governor[
                    "selected_action"
                ] = (
                    execution_state.get(
                        "runtime_execution_action"
                    )
                    or "runtime_execute_now"
                )

                runtime_governor[
                    "selected_engine"
                ] = "bridge_override"

                runtime_governor[
                    "reason"
                ] = (
                    "bridge_authorized_execution"
                )

            queue_override_active = (
                execution_state.get(
                    "runtime_execute_now"
                )
                and isinstance(
                    runtime_execution_queue,
                    dict,
                )
                and runtime_execution_queue.get(
                    "queue_size",
                    0,
                ) > 0
            )

            if queue_override_active:

                final_action = (
                    "autonomous_execution"
                )

                execution_state[
                    "runtime_governed_override"
                ] = True

                execution_state[
                    "runtime_consensus_action"
                ] = (
                    "autonomous_execution"
                )

                execution_state[
                    "runtime_consensus_reason"
                ] = (
                    "Execution queue override activated."
                )

            elif execution_state.get(
                "runtime_bridge_authorized"
            ):

                final_action = (
                    execution_state.get(
                        "runtime_execution_action"
                    )
                    or "runtime_execute_now"
                )

                execution_state[
                    "runtime_consensus_action"
                ] = final_action

                execution_state[
                    "runtime_consensus_authority"
                ] = (
                    "bridge_override"
                )

                execution_state[
                    "runtime_consensus_reason"
                ] = (
                    "Bridge override forced execution."
                )

            else:

                final_action = (
                    runtime_governor.get(
                        "selected_action",
                        final_action,
                    )
                )

        if execution_state.get(
            "runtime_bridge_authorized"
        ):

            runtime_governor[
                "selected_action"
            ] = (
                execution_state.get(
                    "runtime_execution_action"
                )
                or "runtime_execute_now"
            )

            runtime_governor[
                "selected_engine"
            ] = (
                "bridge_override"
            )

            runtime_governor[
                "reason"
            ] = (
                "bridge_authorized_execution"
            )

            execution_state[
                "runtime_consensus_action"
            ] = (
                runtime_governor.get(
                    "selected_action"
                )
            )


            execution_state[
                "runtime_consensus_authority"
            ] = (
                "bridge_override"
            )

            execution_state[
                "runtime_consensus_reason"
            ] = (
                "Bridge override forced execution."
            )
        execution_state["runtime_governor"] = runtime_governor

        if execution_state.get(
            "runtime_bridge_authorized"
        ):

            execution_state[
                "runtime_route"
            ] = (
                "autonomous_execution"
            )

            execution_state[
                "healing_mode"
            ] = (
                "active_execution"
            )

            execution_state[
                "runtime_health"
            ] = (
                "stable"
            )

            execution_state[
                "recovery_mode"
            ] = False

        runtime_identity = (
            self.runtime_identity
            .evolve_identity(
                trend=(
                    runtime_trend_analysis
                ),
                runtime_policy=(
                    adaptive_policy
                ),
                runtime_governor=(
                    runtime_governor
                ),
            )
        )

        execution_state[
            "runtime_identity"
        ] = runtime_identity

        runtime_goal = (
            self.runtime_goal_persistence
            .evolve_goal(
                runtime_identity=(
                    runtime_identity
                ),
                runtime_governor=(
                    runtime_governor
                ),
                trend=(
                    runtime_trend_analysis
                ),
            )
        )

        execution_state[
            "runtime_goal"
        ] = runtime_goal

        runtime_plan = (
            self.runtime_planning
            .build_plan(
                runtime_goal=(
                    runtime_goal
                ),
                runtime_identity=(
                    runtime_identity
                ),
                trend=(
                    runtime_trend_analysis
                ),
            )
        )

        execution_state[
            "runtime_plan"
        ] = runtime_plan

        runtime_world_model = (
            self.runtime_world_model
            .simulate(
                runtime_goal=(
                    runtime_goal
                ),
                runtime_identity=(
                    runtime_identity
                ),
                runtime_plan=(
                    runtime_plan
                ),
                trend=(
                    runtime_trend_analysis
                ),
            )
        )

        execution_state[
            "runtime_world_model"
        ] = runtime_world_model

        before_graph = (
            execution_state.get("graph", {}).copy()
            if isinstance(execution_state.get("graph"), dict)
            else {}
        )

        execution_state = self.graph_runtime.run_graph_pipeline(
            execution_state=execution_state,
            final_action=final_action,
            execution_summary=execution_summary,
            failure_type=failure_type,
            control=control,
            strategy_memory=strategy_memory,
            meta_policy=meta_policy,
        )

        if not execution_state.get(
            "runtime_signal"
        ):

            execution_state[
                "runtime_signal"
            ] = (
                reflection.get("signal")
                or "runtime_idle"
            )

        after_graph = (
            execution_state.get("graph", {}).copy()
            if isinstance(execution_state.get("graph"), dict)
            else {}
        )

        self.observability.record_decision(
            trace_id=trace_id,
            input_text=None,
            route="safe_unified_runtime",
            brain_state={
                "execution_summary": execution_summary,
                "control": control,
                "failure_type": failure_type,
            },
            decision=decision,
            final_action=final_action,
        )

        self.observability.record_graph_change(
            trace_id=trace_id,
            before_graph=before_graph,
            after_graph=after_graph,
            reason=final_action,
        )

        self.observability.record_execution(
            trace_id=trace_id,
            step=None,
            before_state=before_state,
            after_state=execution_state,
            result={
                "reflection": reflection,
                "decision": decision,
                "final_action": final_action,
            },
        )

        runtime_signal = (
            execution_state.get(
                "runtime_signal"
            )
        )

        runtime_signal = (
            execution_state.get(
                "runtime_signal"
            )
            or reflection.get("signal")
            or "runtime_idle"
        )

        runtime_memory_event = {
            "cycle": self.cycle_count,
            "signal": runtime_signal,
            "action": final_action,
            "risk": (
                runtime_world_model.get(
                    "risk_forecast"
                )
                if isinstance(runtime_world_model, dict)
                else "unknown"
            ),
            "goal": (
                runtime_goal.get(
                    "active_goal"
                )
                if isinstance(runtime_goal, dict)
                else "unknown"
            ),
        }

        anomaly_detected = False

        recent_signals = [
            item.get("runtime_signal")
            for item in self.runtime_history[-5:]
            if isinstance(item, dict)
        ]

        idle_count = recent_signals.count(
            "runtime_idle"
        )

        anomaly_cycle_count = idle_count

        if anomaly_cycle_count >= 4:
            anomaly_detected = True

        if anomaly_cycle_count >= 6:

            anomaly_detected = True

            final_action = (
                "runtime_force_recovery"
            )

            runtime_signal = (
                "runtime_escalation_required"
            )

            execution_state[
                "runtime_signal"
            ] = runtime_signal

            execution_state[
                "recovery_mode"
            ] = True

            execution_state[
                "runtime_policy_shift"
            ] = (
                "force_recovery_escalation"
            )

            execution_state[
                "runtime_policy_reason"
            ] = (
                "Repeated idle cycles exceeded escalation threshold."
            )

        elif anomaly_cycle_count >= 4:

            anomaly_detected = True

            final_action = (
                "runtime_self_repair"
            )

            runtime_signal = (
                "runtime_anomaly_detected"
            )

            execution_state[
                "runtime_signal"
            ] = runtime_signal

            execution_state[
                "recovery_mode"
            ] = True

            execution_state[
                "runtime_policy_shift"
            ] = (
                "increase_recovery_priority"
            )

            execution_state[
                "runtime_policy_reason"
            ] = (
                "Repeated idle runtime cycles triggered anomaly recovery."
            )

        self.runtime_history.append(
            {
                "cycle": self.cycle_count,
                "trace_id": trace_id,
                "execution": execution_summary,
                "reflection": reflection,
                "decision": decision,
                "policy": policy,
                "memory": policy_memory,
                "strategy": strategy_memory,
                "meta_policy": meta_policy,
                "final_action": final_action,
                "runtime_signal": runtime_signal,

                "runtime_memory_event": (
                    runtime_memory_event
                ),
                "anomaly_detected": (
                    anomaly_detected
                ),

                "recovery_mode": (
                    execution_state.get(
                        "recovery_mode",
                        False,
                    )
                ),

                "runtime_policy_shift": (
                    execution_state.get(
                        "runtime_policy_shift"
                    )
                ),

                "runtime_policy_reason": (
                    execution_state.get(
                        "runtime_policy_reason"
                    )
                ),

                "runtime_governor": (
                    runtime_governor
                ),

                "control": control,

                "failure_type": (
                    failure_type
                ),

                "runtime_identity": (
                    runtime_identity
                ),

                "runtime_goal": (
                    runtime_goal
                ),

                "runtime_plan": (
                    runtime_plan
                ),

                "runtime_world_model": (
                    runtime_world_model
                ),
            }
        )

        self.runtime_history = (
            self.runtime_history[-25:]
        )

        result = {
            "ok": True,
            "runtime_graph_memory": (
                self.runtime_graph_memory.export_memory()
                if hasattr(
                    self.runtime_graph_memory,
                    "export_memory",
                )
                else {
                    "events": getattr(
                        self.runtime_graph_memory,
                        "events",
                        [],
                    ),
                    "event_count": len(
                        getattr(
                            self.runtime_graph_memory,
                            "events",
                            [],
                        )
                    ),
                }
            ),
            "cycle": (
                "observe_reflect_learn_govern_graph_trace"
            ),
            "cycle_count": self.cycle_count,
            "trace_id": trace_id,
            "execution": execution_summary,
            "reflection": reflection,
            "decision": decision,
            "policy": policy,
            "memory": policy_memory,
            "strategy": strategy_memory,
            "runtime_strategy_scores": (
                execution_state.get(
                    "runtime_strategy_scores",
                    {}
                )
            ),

            "runtime_preferred_strategy": (
                execution_state.get(
                    "runtime_preferred_strategy"
                )
            ),

            "runtime_suppressed_strategy": (
                execution_state.get(
                    "runtime_suppressed_strategy"
                )
            ),
            "meta_policy": meta_policy,
            "control": control,
            "failure_type": failure_type,
            "final_action": final_action,
            "mutated_execution_state": execution_state,
            "previous_reflection": previous_reflection,
            "previous_decision": previous_decision,
            "runtime_policy_enforcement": (
                policy_enforcement
            ),
            "runtime_trend_analysis": (
                runtime_trend_analysis
            ),
            "runtime_adaptive_policy": (
                runtime_adaptive_policy
            ),
            "runtime_governor": (
                runtime_governor
            ),
            "runtime_identity": (
                runtime_identity
            ),
            "runtime_goal": (
                runtime_goal
            ),
        }

        integrity_report = (
            self.runtime_integrity.validate(
                execution_state=execution_state,
                runtime_result=result,
                runtime_history=self.runtime_history,
            )
        )

        result["runtime_integrity"] = (
            integrity_report
        )

        if integrity_report.get("blocked"):

            execution_state[
                "runtime_signal"
            ] = (
                "runtime_integrity_block"
            )

            execution_state[
                "recovery_mode"
            ] = True

            final_action = (
                "runtime_integrity_recovery"
            )

        self.observability.end_trace(
            trace_id=trace_id,
            status="completed",
            payload=result,
        )

        trace = self.observability.get_trace(trace_id)

        runtime_replay = self.replay.build_replay(
            trace=trace,
            runtime_result=result,
        )

        result["replay_id"] = runtime_replay.get("replay_id")

        replay_explanation = self.explain_replay(
            replay_id=result.get("replay_id"),
        )

        debug_report = self.debugger.suggest_repairs(
            runtime_result=result,
            replay_explanation=replay_explanation,
            runtime_history=self.runtime_history,
        )

        result["debug_report"] = debug_report
        result["runtime_graph_report"] = self.debug_runtime_result(result)

        result["runtime_graph_query"] = (
            self.runtime_graph_query.recommend_runtime_actions()
        )

        result["runtime_graph_patterns"] = (
            self.runtime_graph_query.summarize_patterns()
        )

        healing_plan = self.self_healing.build_healing_plan(
            debug_report=debug_report,
            runtime_result=result,
            runtime_history=self.runtime_history,
        )

        healing_report = self.self_healing.apply_healing_plan(
            execution_state=execution_state,
            control=control,
            governor_policy=policy,
            healing_plan=healing_plan,
        )

        result["healing_plan"] = healing_plan

        result["healing_report"] = healing_report

        prediction_report = (
            self.runtime_prediction.predict(
                runtime_history=self.runtime_history,
                execution_state=execution_state,
                runtime_result=result,
            )
        )

        checkpoint_report = (
            self.runtime_checkpoint_guardian
            .create_checkpoint(
                execution_state=execution_state,
                runtime_result=result,
                reason=(
                    execution_state.get(
                        "runtime_signal"
                    )
                ),
            )
        )

        state_diff_report = (
            self.runtime_state_diff.compare(
                before_state=before_state,
                after_state=execution_state,
            )
        )

        result["runtime_state_diff"] = (
            state_diff_report
        )

        result["runtime_checkpoint"] = (
            checkpoint_report
        )

        result["runtime_prediction"] = (
            prediction_report
        )

        mutation_report = (

            self.runtime_mutation_sandbox.evaluate(
                before_state=before_state,
                after_state=execution_state,
                mutation_reason=final_action,
            )
        )

        result["runtime_mutation_sandbox"] = (
            mutation_report
        )

        rollback_report = (
            self.runtime_rollback_engine.decide(
                mutation_report=mutation_report,
                checkpoint_report=checkpoint_report,
                runtime_result=result,
            )
        )

        subgoal_report = (
            self.runtime_subgoal_engine.generate(
                runtime_goal=runtime_goal,
                runtime_prediction=prediction_report,
                runtime_signal=(
                    execution_state.get(
                        "runtime_signal"
                    )
                ),
            )
        )

        arbitration_report = (
            self.runtime_goal_arbitration.prioritize(
                subgoals=(
                    subgoal_report.get(
                        "subgoals",
                        [],
                    )
                ),
                runtime_signal=(
                    execution_state.get(
                        "runtime_signal"
                    )
                ),
            )
        )

        recursive_plan = (
            self.runtime_recursive_planner.expand(
                selected_goal=(
                    arbitration_report.get(
                        "selected_goal",
                        {},
                    )
                ),
                runtime_signal=(
                    execution_state.get(
                        "runtime_signal"
                    )
                ),
            )
        )
        execution_plan_report = (
            self.runtime_plan_executor.execute(
                recursive_plan=recursive_plan,
                runtime_signal=(
                    execution_state.get(
                        "runtime_signal"
                    )
                ),
            )
        )

        scheduler_report = (
            self.runtime_scheduler.schedule(
                execution_plan=(
                    execution_plan_report
                ),
                runtime_signal=(
                    execution_state.get(
                        "runtime_signal"
                    )
                ),
            )
        )

        autonomy_report = (
            self.runtime_autonomy_loop.run(
                scheduler_report=(
                    scheduler_report
                ),
                runtime_signal=(
                    execution_state.get(
                        "runtime_signal"
                    )
                ),
            )
        )

        supervision_report = (
            self.runtime_autonomy_supervisor.supervise(
                autonomy_report=(
                    autonomy_report
                ),
                runtime_signal=(
                    execution_state.get(
                        "runtime_signal"
                    )
                ),
            )
        )

        mesh_report = (
            self.runtime_multi_agent_mesh.coordinate(
                supervision_report=(
                    supervision_report
                ),
                runtime_signal=(
                    execution_state.get(
                        "runtime_signal"
                    )
                ),
            )
        )

        collective_report = (
            self.runtime_collective_intelligence.synthesize(
                mesh_report=(
                    mesh_report
                ),
                runtime_signal=(
                    execution_state.get(
                        "runtime_signal"
                    )
                ),
            )
        )

        operating_report = (
            self.runtime_operating_loop.cycle(
                collective_report=(
                    collective_report
                ),
                runtime_signal=(
                    execution_state.get(
                        "runtime_signal"
                    )
                ),
            )
        )

        runtime_execution_route = (
            self.runtime_execution_router.route(
                scheduler_report=scheduler_report,
                autonomy_report=autonomy_report,
                supervision_report=supervision_report,
                operating_report=operating_report,
                runtime_signal=(
                    execution_state.get(
                        "runtime_signal"
                    )
                ),
            )
        )

        result["runtime_execution_router"] = (
            runtime_execution_route
        )

        runtime_execution_mutation = (
            self.runtime_execution_mutation.mutate(
                execution_state=execution_state,
                runtime_execution_router=(
                    runtime_execution_route
                ),
                bridge_state={
                    "bridge_action": (
                        "runtime_directed_execution"
                        if runtime_execution_route.get(
                            "execute_now"
                        )
                        else "observe_only"
                    ),
                    "execution_action": (
                        "runtime_execute_now"
                        if runtime_execution_route.get(
                            "execute_now"
                        )
                        else ""
                    ),
                },
            )
        )

        execution_state = (
            runtime_execution_mutation.get(
                "execution_state",
                execution_state,
            )
        )

        runtime_autonomous_execution = (
            self.runtime_autonomous_executor.execute(
                execution_state=execution_state,
                runtime_execution_queue=(
                    runtime_execution_queue.get(
                        "queue",
                        [],
                    )
                    if isinstance(
                        runtime_execution_queue,
                        dict,
                    )
                    else runtime_execution_queue
                ),
            )
        )

        execution_state = (
            runtime_autonomous_execution.get(
                "execution_state",
                execution_state,
            )
        )

        execution_state[
            "runtime_bridge_authorized"
        ] = True

        execution_state[
            "runtime_execute_now"
        ] = True

        execution_state[
            "runtime_autonomous_execution_allowed"
        ] = True

        execution_state[
            "runtime_route"
        ] = "autonomous_execution"

        result["runtime_execution_queue"] = (
            runtime_execution_queue
        )

        result["runtime_autonomous_execution"] = (
            runtime_autonomous_execution
        )

        result["runtime_autonomous_memory"] = (
            runtime_autonomous_memory
        )

        result["runtime_policy_learning"] = (
            runtime_policy_learning
        )

        result["runtime_operating_loop"] = (
            operating_report
        )

        result["runtime_collective_intelligence"] = (
            collective_report
        )

        result["runtime_multi_agent_mesh"] = (
            mesh_report
        )

        result["runtime_autonomy_supervision"] = (
            supervision_report
        )

        result["runtime_autonomy_loop"] = (
            autonomy_report
        )

        result["runtime_scheduler"] = (
            scheduler_report
        )

        result["runtime_plan_execution"] = (
            execution_plan_report
        )

        result["runtime_recursive_plan"] = (
            recursive_plan
        )

        result["runtime_goal_arbitration"] = (
            arbitration_report
        )

        result["runtime_subgoals"] = (
            subgoal_report
        )

        result["runtime_rollback"] = (
            rollback_report
        )



        consensus_report = (
            self.runtime_consensus.resolve(
                execution_state=execution_state,
                runtime_result=result,
                integrity_report=integrity_report,
                rollback_report=rollback_report,
                prediction_report=prediction_report,
                runtime_governor=runtime_governor,
                autonomy_report=autonomy_report,
                mutation_report=mutation_report,
            )
        )

        execution_state = (
            consensus_report.get(
                "execution_state",
                execution_state,
            )
        )

        result["runtime_consensus"] = (
            consensus_report
        )

        if consensus_report.get(
            "blocked"
        ) and consensus_report.get(
            "action"
        ) == "block_and_recover":

            execution_state[
                "recovery_mode"
            ] = True

        if rollback_report.get(
            "should_rollback"
        ):

            execution_state = (
                rollback_report.get(
                    "restore_state",
                    {},
                )
            )

            execution_state[
                "runtime_signal"
            ] = (
                "runtime_rollback_executed"
            )

            execution_state[
                "recovery_mode"
            ] = True

        orchestration_report = self.runtime_orchestrator.orchestrate(
            runtime_result={
                "ok": True,
                "cycle": self.cycle_count,
                "final_action": final_action,
                "execution": execution_state,
                "trace_id": trace_id,
                "replay_id": result.get("replay_id"),
            },
            execution_state=execution_state,
            debug_report=debug_report,
            healing_report=healing_report,
        )

        result["orchestration_report"] = orchestration_report

        result["compressed_runtime"] = (
            self.runtime_output_compression.compress_cycle_result(
                result
            )
        )

        self.last_compressed_runtime = (
            result.get("compressed_runtime")
        )

        result["pruned_runtime_signals"] = (
            self.runtime_signal_pruning.prune(
                result
            )
        )

        result["runtime_drift_memory"] = (
            self.runtime_drift_memory.record(
                runtime_prediction=(
                    result.get(
                        "runtime_prediction"
                    )
                ),
                runtime_policy=(
                    adaptive_policy
                ),
                runtime_signal=(
                    execution_state.get(
                        "runtime_signal"
                    )
                ),
            )
        )

        if isinstance(
            result.get("runtime_drift_memory"),
            dict,
        ):

            drift_history = (
                result["runtime_drift_memory"].get(
                    "history",
                    [],
                )
            )

            if isinstance(
                drift_history,
                list,
            ):

                result["runtime_drift_memory"]["history"] = (
                    drift_history[-25:]
                )

                result["runtime_drift_memory"]["history_count"] = (
                    len(
                        result["runtime_drift_memory"]["history"]
                    )
                )

        result["runtime_auto_recovery"] = (
            self.runtime_auto_recovery.recover(
                runtime_result=result,
                execution_state=execution_state,
            )
        )

        result["runtime_snapshot"] = (
            self.runtime_snapshot.save_snapshot(
                result
            )
        )

        state_normalizer_report = (
            self.runtime_state_normalizer.normalize(
                execution_state=execution_state,
            )
        )

        execution_state = (
            state_normalizer_report.get(
                "execution_state",
                execution_state,
            )
        )

        result["runtime_state_normalizer"] = (
            state_normalizer_report
        )

        priority_memory_report = (
            self.runtime_priority_memory.prioritize(
                execution_state=execution_state,
            )
        )

        execution_state = (
            priority_memory_report.get(
                "execution_state",
                execution_state,
            )
        )

        result["runtime_priority_memory"] = (
            priority_memory_report
        )

        memory_compression_report = (
            self.runtime_memory_compression.compress(
                execution_state=execution_state,
            )
        )

        if isinstance(
            memory_compression_report,
            dict,
        ):

            compressed_execution_state = (
                memory_compression_report.get(
                    "execution_state"
                )
            )

            if isinstance(
                compressed_execution_state,
                dict,
            ):
                execution_state.update(
                    compressed_execution_state
                )

            execution_state[
                "runtime_summary_memory"
            ] = (
                compressed_execution_state.get(
                    "runtime_summary_memory",
                    [],
                )
                if isinstance(
                    compressed_execution_state,
                    dict,
                )
                else []
            )

            execution_state[
                "risk_memory_state"
            ] = (
                compressed_execution_state.get(
                    "risk_memory_state",
                    {},
                )
                if isinstance(
                    compressed_execution_state,
                    dict,
                )
                else {}
            )

            execution_state[
                "persistent_risk_score"
            ] = int(
                execution_state.get(
                    "persistent_risk_score",
                    0,
                )
                or 0
            )

            execution_state[
                "persistent_recovery_pressure"
            ] = int(
                execution_state.get(
                    "persistent_recovery_pressure",
                    0,
                )
                or 0
            )

        execution_state = (
            memory_compression_report.get(
                "execution_state",
                execution_state,
            )
        )

        result["runtime_memory_compression"] = (
            memory_compression_report
        )

        result["runtime_persistence"] = (
            self.runtime_persistence.save(
                result
            )
        )

        escalation_report = (
            self.runtime_escalation.evaluate(
                execution_state=execution_state,
                runtime_history=self.runtime_history,
                prediction_report=prediction_report,
                integrity_report=integrity_report,
            )
        )

        execution_state = (
            escalation_report.get(
                "execution_state",
                execution_state,
            )
        )

        result["runtime_escalation"] = (
            escalation_report
        )

        constitution_report = (
            self.runtime_constitution.evaluate(
                execution_state=execution_state,
                integrity_report=integrity_report,
                rollback_report=rollback_report,
                escalation_report=escalation_report,
                consensus_report=consensus_report,
            )
        )

        execution_state = (
            constitution_report.get(
                "execution_state",
                execution_state,
            )
        )

        authority_report = (
            self.runtime_authority.resolve(
                execution_state=execution_state,
                current_action=final_action,
                current_signal=execution_state.get(
                    "runtime_signal"
                ),
                constitution_report=constitution_report,
                escalation_report=escalation_report,
                integrity_report=integrity_report,
            )
        )

        execution_state = (
            authority_report.get(
                "execution_state",
                execution_state,
            )
        )

        queue_override_active = (
            execution_state.get(
                "runtime_execute_now"
            )
            and isinstance(
                runtime_execution_queue,
                dict,
            )
            and runtime_execution_queue.get(
                "queue_size",
                0,
            ) > 0
        )

        if queue_override_active:

            final_action = (
                "autonomous_execution"
            )

            execution_state[
                "runtime_consensus_action"
            ] = (
                "autonomous_execution"
            )

            execution_state[
                "runtime_consensus_reason"
            ] = (
                "Authority override bypassed for active execution queue."
            )

            execution_state[
                "runtime_authority_override"
            ] = True

        else:

            final_action = (
                authority_report.get(
                    "final_action",
                    final_action,
                )
            )

        result["runtime_authority"] = (
            authority_report
        )

        result["runtime_constitution"] = (
            constitution_report
        )

        print(
            "RUNTIME SIGNAL DEBUG =",
            execution_state.get(
                "runtime_signal"
            ),
        )

        if hasattr(
            self,
            "runtime_mutation_safety",
        ):
            runtime_mutation_safety = (
                self.runtime_mutation_safety.evaluate_mutation(
                    execution_state=execution_state,
                    proposed_mutation={
                        "mutation_type": (
                            execution_state.get(
                                "runtime_mutation_type",
                                "autonomous_mutation",
                            )
                        ),
                    },
                )
            )

            execution_state = (
                runtime_mutation_safety.get(
                    "execution_state",
                    execution_state,
                )
                if isinstance(runtime_mutation_safety, dict)
                else execution_state
            )

            result[
                "runtime_mutation_safety"
            ] = runtime_mutation_safety

        if hasattr(
            self,
            "runtime_rollback_intelligence",
        ):
            runtime_rollback_intelligence = (
                self.runtime_rollback_intelligence.evaluate(
                    execution_state=execution_state,
                )
            )

            execution_state = (
                runtime_rollback_intelligence.get(
                    "execution_state",
                    execution_state,
                )
                if isinstance(
                    runtime_rollback_intelligence,
                    dict,
                )
                else execution_state
            )

            result[
                "runtime_rollback_intelligence"
            ] = runtime_rollback_intelligence

        if hasattr(
            self,
            "runtime_self_repair_planner",
        ):

            runtime_self_repair_plan = (
                self.runtime_self_repair_planner.build_repair_plan(
                    execution_state=execution_state,
                )
            )

            execution_state = (
                runtime_self_repair_plan.get(
                    "execution_state",
                    execution_state,
                )
            )

            result[
                "runtime_self_repair_plan"
            ] = runtime_self_repair_plan


        if hasattr(
            self,
            "runtime_strategy_memory",
        ):
            strategy_reinforcement = (
                self.runtime_strategy_memory.remember(
                    execution_state=execution_state,
                    final_action=final_action,
                    runtime_signal=execution_state.get(
                        "runtime_signal"
                    ),
                )
            )

            execution_state = (
                strategy_reinforcement.get(
                    "execution_state",
                    execution_state,
                )
            )

            result[
                "runtime_strategy_reinforcement"
            ] = strategy_reinforcement

        if hasattr(
            self,
            "runtime_persistence",

        ) and hasattr(
            self.runtime_persistence,
            "save",
        ):
            result[
                "runtime_persistence"
            ] = self.runtime_persistence.save(
                runtime_result={
                    **result,
                    "execution_state": execution_state,
                }
            )

        result[
            "runtime_health"
        ] = self.runtime_health_scoring.score(
            execution_state=execution_state,
            runtime_result=result,
            runtime_history=self.runtime_history,
        )

        result[
            "runtime_health"
        ] = self.runtime_health_scoring.score(
            execution_state=execution_state,
            runtime_result=result,
            runtime_history=self.runtime_history,
        )

        runtime_self_preservation = (
            self.runtime_self_preservation.preserve(
                execution_state=execution_state,
                runtime_health=result.get(
                    "runtime_health",
                    {},
                ),
                runtime_result=result,
            )
        )

        execution_state = (
            runtime_self_preservation.get(
                "execution_state",
                execution_state,
            )
        )

        result[
            "runtime_self_preservation"
        ] = runtime_self_preservation

        runtime_adaptive_throttle = (
            self.runtime_adaptive_throttle.throttle(
                execution_state=execution_state,
                runtime_health=result.get(
                    "runtime_health",
                    {},
                ),
                runtime_self_preservation=(
                    runtime_self_preservation
                ),
            )
        )

        execution_state = (
            runtime_adaptive_throttle.get(
                "execution_state",
                execution_state,
            )
        )

        result[
            "runtime_adaptive_throttle"
        ] = runtime_adaptive_throttle

        result["compressed_runtime"] = {
            "runtime_health": result.get("runtime_health"),
            "runtime_adaptive_throttle": result.get("runtime_adaptive_throttle"),
            "runtime_self_preservation": result.get("runtime_self_preservation"),
            "runtime_mutation_safety": result.get("runtime_mutation_safety"),
            "runtime_signal": result.get("runtime_signal"),
            "runtime_final_action": result.get("runtime_final_action"),
        }

        return result

    def get_runtime_history(
        self,
        limit=25,
    ):
        return self.runtime_history[-limit:]

    def get_recent_events(
        self,
        limit=50,
    ):
        return self.observability.recent_events(
            limit=limit,
        )

    def get_trace(
        self,
        trace_id,
    ):
        return self.observability.get_trace(trace_id)

    def get_recent_replays(
        self,
        limit=25,
    ):
        return self.replay.recent_replays(
            limit=limit,
        )

    def get_replay(
        self,
        replay_id=None,
        trace_id=None,
    ):
        return self.replay.find_replay(
            replay_id=replay_id,
            trace_id=trace_id,
        )

    def explain_replay(
        self,
        replay_id=None,
        trace_id=None,
    ):
        replay = self.get_replay(
            replay_id=replay_id,
            trace_id=trace_id,
        )

        if not replay:
            return {
                "ok": False,
                "error": "replay_not_found",
            }

        return self.replay.explain_replay(replay)


class RuntimeBootstrap:
    @staticmethod
    def build(
        chat_service=None,
    ):
        return SafeUnifiedRuntime(
            chat_service=chat_service,
        )
