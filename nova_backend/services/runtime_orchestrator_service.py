import time
import uuid

from nova_backend.services.runtime_governor_service import RuntimeGovernorService
from nova_backend.services.runtime_engine_suppression_service import RuntimeEngineSuppressionService
from nova_backend.services.runtime_failure_intelligence_service import RuntimeFailureIntelligenceService
from nova_backend.services.runtime_brain_store_service import RuntimeBrainStoreService
from nova_backend.services.runtime_engine_factory import RuntimeEngineFactory
from nova_backend.services.runtime_engine_fusion_service import (
    RuntimeEngineFusionService,
)


class RuntimeOrchestratorService:
    def __init__(self):
        self.engine_registry = {}
        self.engine_states = {}
        self.orchestration_history = []
        self.last_plan = {}
        self.last_fusion = {}
        self.engine_factory = RuntimeEngineFactory()
        self.fusion = RuntimeEngineFusionService()
        self.register_default_engines()
        self.runtime_brain_store = RuntimeBrainStoreService()
        self.runtime_failure_intelligence = (
            RuntimeFailureIntelligenceService()
        )
        self.runtime_engine_suppression = (
            RuntimeEngineSuppressionService()
        )
        self.runtime_governor = (
            RuntimeGovernorService()
        )

    def register_default_engines(self):
        engines = self.engine_factory.build_default_engines()

        for engine in engines:
            self.register_engine(
                name=engine.name,
                engine=engine,
                priority=50,
                enabled=True,
                tags=engine.tags,
            )

        return {
            "ok": True,
            "registered_count": len(engines),
            "engines": [
                engine.name
                for engine in engines
            ],
        }

    def _safe_dict(self, value):
        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def _safe_list(self, value):
        return (
            value
            if isinstance(value, list)
            else []
        )

    def _now(self):
        return time.time()

    def register_engine(
        self,
        name,
        engine=None,
        priority=50,
        enabled=True,
        tags=None,
    ):
        if not name:
            return {
                "ok": False,
                "error": "missing_engine_name",
            }

        self.engine_registry[name] = {
            "name": name,
            "engine": engine,
            "priority": priority,
            "enabled": enabled,
            "tags": tags or [],
            "registered_at": self._now(),
        }

        self.engine_states[name] = {
            "status": "registered",
            "last_run": None,
            "last_result": None,
            "failure_count": 0,
            "success_count": 0,
            "cooldown_until": 0,
        }

        return {
            "ok": True,
            "engine": name,
        }

    def disable_engine(
        self,
        name,
        reason="",
    ):
        if name not in self.engine_registry:
            return {
                "ok": False,
                "error": "engine_not_found",
                "engine": name,
            }

        self.engine_registry[name]["enabled"] = False
        self.engine_states[name]["status"] = "disabled"
        self.engine_states[name]["disabled_reason"] = reason

        return {
            "ok": True,
            "engine": name,
            "enabled": False,
            "reason": reason,
        }




    def enable_engine(
        self,
        name,
    ):
        if name not in self.engine_registry:
            return {
                "ok": False,
                "error": "engine_not_found",
                "engine": name,
            }

        self.engine_registry[name]["enabled"] = True
        self.engine_states[name]["status"] = "enabled"

        return {
            "ok": True,
            "engine": name,
            "enabled": True,
        }

    def engine_available(
        self,
        name,
    ):
        registry = self.engine_registry.get(name)
        state = self.engine_states.get(name, {})

        if not registry:
            return False

        if not registry.get("enabled"):
            return False

        cooldown_until = state.get(
            "cooldown_until",
            0,
        )

        if cooldown_until and cooldown_until > self._now():
            return False

        return True

    def build_orchestration_context(
        self,
        runtime_result=None,
        execution_state=None,
        debug_report=None,
        healing_report=None,
    ):
        runtime_result = self._safe_dict(runtime_result)
        execution_state = self._safe_dict(execution_state)
        debug_report = self._safe_dict(debug_report)
        healing_report = self._safe_dict(healing_report)

        return {
            "runtime_status": runtime_result.get("ok"),
            "runtime_cycle": runtime_result.get("cycle"),
            "final_action": runtime_result.get("final_action"),
            "execution_status": (
                self._safe_dict(
                    runtime_result.get("execution")
                ).get("status")
                or execution_state.get("status")
            ),
            "failed_count": (
                self._safe_dict(
                    runtime_result.get("execution")
                ).get("failed_count", 0)
            ),
            "debug_ok": debug_report.get("ok"),
            "debug_issues": debug_report.get("issues", []),
            "healing_applied": healing_report.get("applied", []),
            "trace_id": runtime_result.get("trace_id"),
            "replay_id": runtime_result.get("replay_id"),
            "last_fusion": (
                self._safe_dict(
                    self.last_fusion
                )
            ),
        }

    def _apply_preventive_runtime_actions(
        self,
        engine_scores,
        runtime_failure_intelligence,
    ):

        engine_scores = self._safe_dict(
            engine_scores
        )

        runtime_failure_intelligence = (
            self._safe_dict(
                runtime_failure_intelligence
            )
        )

        preventive_actions = (
            runtime_failure_intelligence.get(
                "preventive_actions"
            )
            or []
        )

        if not isinstance(
            preventive_actions,
            list,
        ):

            preventive_actions = []

        for action in preventive_actions:

            action = str(
                action or ""
            ).strip().lower()

            for engine_name in engine_scores:

                if (
                    action
                    == "increase_repair_bias"
                    and "repair"
                    in engine_name
                ):

                    engine_scores[
                        engine_name
                    ] += 5

                if (
                    action
                    == "increase_debug_bias"
                    and "debug"
                    in engine_name
                ):

                    engine_scores[
                        engine_name
                    ] += 5

                if (
                    action
                    == "reduce_parallelism"
                    and "scheduler"
                    in engine_name
                ):

                    engine_scores[
                        engine_name
                    ] -= 2

                if (
                    action
                    == "stabilize_context"
                    and "memory"
                    in engine_name
                ):

                    engine_scores[
                        engine_name
                    ] += 4

        return engine_scores

    def _calculate_runtime_confidence(
        self,
        engine_name,
        engine_state,
    ):

        engine_name = str(
            engine_name or ""
        ).strip()

        engine_state = self._safe_dict(
            engine_state
        )

        success_count = int(
            engine_state.get(
                "success_count"
            )
            or 0
        )

        failure_count = int(
            engine_state.get(
                "failure_count"
            )
            or 0
        )

        total = (
            success_count
            + failure_count
        )

        if total <= 0:

            return 0.50

        confidence = (
            success_count / total
        )

        if failure_count >= 3:

            confidence *= 0.75

        if failure_count >= 5:

            confidence *= 0.50

        if "repair" in engine_name:

            confidence += 0.10

        return max(
            0.05,
            min(
                1.0,
                confidence,
            ),
        )

    def _apply_self_healing_orchestration_mode(
        self,
        selected,
        runtime_governor,
    ):

        selected = (
            selected
            if isinstance(
                selected,
                list,
            )
            else []
        )

        runtime_governor = self._safe_dict(
            runtime_governor
        )

        if runtime_governor.get("mode") != "stabilization":

            return selected

        for item in selected:

            if not isinstance(
                item,
                dict,
            ):
                continue

            name = str(
                item.get("name")
                or ""
            ).lower()

            tags = self._safe_list(
                item.get("tags")
            )

            if (
                "repair" in name
                or "repair" in tags
            ):

                item["score"] = (
                    item.get("score", 0)
                    + 50
                )

                item["self_healing_boost"] = True

            if (
                "debug" in name
                or "debug" in tags
            ):

                item["score"] = (
                    item.get("score", 0)
                    + 35
                )

                item["self_healing_boost"] = True

            if (
                "healing" in name
                or "healing" in tags
            ):

                item["score"] = (
                    item.get("score", 0)
                    + 40
                )

                item["self_healing_boost"] = True

        selected.sort(
            key=lambda item: item.get("score", 0),
            reverse=True,
        )

        return selected

    def choose_engines(
        self,
        context=None,
    ):

        context = self._safe_dict(context)

        selected = []

        debug_issues = self._safe_list(
            context.get("debug_issues")
        )

        failed_count = context.get(
            "failed_count",
            0,
        )

        execution_status = context.get(
            "execution_status",
        )

        last_fusion = self._safe_dict(
            context.get("last_fusion")
        )

        priority_weights = self._safe_dict(
            last_fusion.get("priority_weights")
        )

        runtime_brain = (
            self.runtime_brain_store.snapshot()
        )

        runtime_failure_intelligence = (
            self.runtime_failure_intelligence.analyze(
                runtime_brain
            )
        )
        suppression_report = {}

        for name, config in self.engine_registry.items():
            if not self.engine_available(name):
                continue

            suppression = (
                self.runtime_engine_suppression.evaluate(
                    name,
                    self.engine_states.get(
                        name,
                        {},
                    ),
                    runtime_failure_intelligence,
                )
            )

            suppression_report[
                name
            ] = suppression

            if suppression.get(
                "suppressed"
            ):
                continue

            tags = self._safe_list(
                config.get("tags")
            )

            priority = config.get(
                "priority",
                50,
            )

            engine_state = (
                self.engine_states.get(
                    name,
                    {},
                )
            )

            runtime_confidence = (
                self._calculate_runtime_confidence(
                    name,
                    engine_state,
                )
            )

            score = (
                priority
                * runtime_confidence
            )

            if "debug" in tags and debug_issues:
                score += 30

            if "repair" in tags and failed_count > 0:
                score += 35

            if "healing" in tags and debug_issues:
                score += 25

            if "planning" in tags and execution_status in {
                "idle",
                "complete",
                "completed",
                None,
            }:
                score += 10

            for tag in tags:
                if tag in priority_weights:
                    score += (
                        priority_weights.get(
                            tag,
                            0,
                        )
                        * 10
                    )

            score_map = {
                name: score
            }

            score_map = (
                self._apply_preventive_runtime_actions(
                    score_map,
                    runtime_failure_intelligence,
                )
            )

            score = score_map.get(
                name,
                score,
            )

            selected.append(
                {
                    "name": name,
                    "score": score,
                    "runtime_confidence": runtime_confidence,
                    "priority": priority,
                    "tags": tags,
                }
            )

        selected.sort(
            key=lambda item: item.get("score", 0),
            reverse=True,
        )

        runtime_governor = (
            self.runtime_governor.govern(
                runtime_failure_intelligence,
                selected,
                runtime_brain,
            )
        )

        selected = (
            self._apply_self_healing_orchestration_mode(
                selected,
                runtime_governor,
            )
        )

        self.last_runtime_governor = (
            runtime_governor
        )

        self.last_suppression_report = (
            suppression_report
        )

        return selected


    def build_plan(
        self,
        context=None,
    ):
        context = self._safe_dict(context)

        selected = self.choose_engines(
            context=context,
        )

        plan_id = str(uuid.uuid4())

        plan = {
            "ok": True,
            "plan_id": plan_id,
            "created_at": self._now(),
            "context": context,
            "selected_engines": selected,
            "steps": [],
        }

        for item in selected:
            plan["steps"].append(
                {
                    "engine": item.get("name"),
                    "score": item.get("score"),
                    "action": "run_engine",
                    "status": "pending",
                }
            )

        self.last_plan = plan

        return plan

    def _calculate_adaptive_cooldown(
        self,
        engine_name,
        engine_state,
        runtime_brain=None,
    ):

        engine_name = str(
            engine_name or ""
        ).strip()

        engine_state = self._safe_dict(
            engine_state
        )

        runtime_brain = self._safe_dict(
            runtime_brain
        )

        failures = int(
            engine_state.get(
                "failure_count"
            )
            or 0
        )

        recurring_failures = (
            self._safe_dict(
                runtime_brain.get(
                    "recurring_failures"
                )
            )
        )

        cooldown = 60

        if failures >= 5:

            cooldown += 120

        elif failures >= 3:

            cooldown += 60

        if recurring_failures:

            cooldown += min(
                120,
                len(
                    recurring_failures
                ) * 5,
            )

        if "repair" in engine_name:

            cooldown = max(
                30,
                cooldown - 30,
            )

        if "scheduler" in engine_name:

            cooldown += 45

        return cooldown



    def run_engine(
        self,
        name,
        context=None,
    ):
        context = self._safe_dict(context)

        config = self.engine_registry.get(name)
        state = self.engine_states.get(name)

        if not config or not state:
            return {
                "ok": False,
                "error": "engine_not_found",
                "engine": name,
            }

        if not self.engine_available(name):
            return {
                "ok": False,
                "error": "engine_unavailable",
                "engine": name,
            }

        engine = config.get("engine")

        if engine is None:
            result = {
                "ok": True,
                "engine": name,
                "mode": "registered_placeholder",
                "message": "Engine registered without callable instance.",
            }

        elif hasattr(engine, "run"):
            result = engine.run(
                context=context,
            )

        elif callable(engine):
            result = engine(
                context,
            )

        else:
            result = {
                "ok": False,
                "engine": name,
                "error": "engine_not_callable",
            }

        state["last_run"] = self._now()
        state["last_result"] = result

        if isinstance(result, dict) and result.get("ok"):
            state["success_count"] += 1
            state["status"] = "healthy"

        else:
            state["failure_count"] += 1
            state["status"] = "failed"

            if state["failure_count"] >= 3:

                runtime_brain = (
                    self.runtime_brain_store.snapshot()
                )

                adaptive_cooldown = (
                    self._calculate_adaptive_cooldown(
                        name,
                        state,
                        runtime_brain,
                    )
                )

                state[
                    "cooldown_until"
                ] = (
                    self._now()
                    + adaptive_cooldown
                )

                state[
                    "adaptive_cooldown"
                ] = adaptive_cooldown

                state["status"] = "cooldown"

        self.engine_states[name] = state

        return result

    def run_plan(
        self,
        plan=None,
    ):
        plan = self._safe_dict(
            plan or self.last_plan
        )

        context = self._safe_dict(
            plan.get("context")
        )

        steps = self._safe_list(
            plan.get("steps")
        )

        results = []

        for step in steps:
            if not isinstance(step, dict):
                continue

            engine_name = step.get("engine")

            result = self.run_engine(
                name=engine_name,
                context=context,
            )

            step["status"] = (
                "completed"
                if isinstance(result, dict)
                and result.get("ok")
                else "failed"
            )

            step["result"] = result

            results.append(
                {
                    "engine": engine_name,
                    "result": result,
                }
            )

        fused_result = self.fusion.fuse_results(
            results=results,
        )

        plan["fusion"] = fused_result
        self.last_fusion = fused_result

        report = {
            "ok": True,
            "plan_id": plan.get("plan_id"),
            "results": results,
            "steps": steps,
            "engine_states": self.get_engine_states(),
            "fusion": fused_result,
        }

        self.orchestration_history.append(report)
        self.orchestration_history = (
            self.orchestration_history[-100:]
        )

        return report

    def orchestrate(
        self,
        runtime_result=None,
        execution_state=None,
        debug_report=None,
        healing_report=None,
    ):
        context = self.build_orchestration_context(
            runtime_result=runtime_result,
            execution_state=execution_state,
            debug_report=debug_report,
            healing_report=healing_report,
        )

        plan = self.build_plan(
            context=context,
        )

        report = self.run_plan(
            plan=plan,
        )

        return {
            "ok": True,
            "context": context,
            "plan": plan,
            "report": report,
            "fusion": report.get("fusion"),
        }

    def get_engine_registry(self):
        safe_registry = {}

        for name, config in self.engine_registry.items():
            safe_registry[name] = {
                "name": config.get("name"),
                "priority": config.get("priority"),
                "enabled": config.get("enabled"),
                "tags": config.get("tags"),
                "registered_at": config.get("registered_at"),
                "has_engine": config.get("engine") is not None,
            }

        return safe_registry

    def get_engine_states(self):
        return self.engine_states

    def get_last_plan(self):
        return self.last_plan

    def get_last_fusion(self):
        return self.last_fusion

    def get_orchestration_history(
        self,
        limit=25,
    ):
        return self.orchestration_history[-limit:]