from nova_backend.services.governor_service import GovernorService
from nova_backend.services.runtime_output_compression_service import RuntimeOutputCompressionService
from nova_backend.services.runtime_graph_memory_service import RuntimeGraphMemoryService
from nova_backend.services.graph_runtime_service import (
    GraphRuntimeService,
)

from nova_backend.services.governor_service import (
    GovernorService,
)

from nova_backend.services.graph_runtime_service import (
    GraphRuntimeService,
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

        runtime_trend_analysis = self.runtime_trend_analysis.analyze()
        runtime_adaptive_policy = self.runtime_policy_adaptation.adapt_policy()

        adaptive_policy = (
            runtime_adaptive_policy.get("adaptive_policy")
            if isinstance(runtime_adaptive_policy, dict)
            else {}
        )

        runtime_governor = self.runtime_governor.arbitrate(
            repair_action=final_action,
            policy_action=(
                policy_enforcement.get("recommended_action")
                or policy_enforcement.get("enforced_action")
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

        if runtime_governor.get("ok"):
            final_action = runtime_governor.get(
                "selected_action",
                final_action,
            )

        execution_state["runtime_governor"] = runtime_governor

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
                "runtime_signal": (
                    runtime_signal
                ),
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

                "runtime_governor": runtime_governor,
                "control": control,
                "failure_type": failure_type,

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
        result["runtime_persistence"] = (
            self.runtime_persistence.save(
                result
            )
        )
        print(
            "RUNTIME SIGNAL DEBUG =",
            execution_state.get(
                "runtime_signal"
            ),
        )

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