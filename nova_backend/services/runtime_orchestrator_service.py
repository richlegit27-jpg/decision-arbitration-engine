import time
import uuid

from nova_backend.services.runtime_engine_factory import RuntimeEngineFactory

class RuntimeOrchestratorService:

    def __init__(self):
        self.engine_registry = {}
        self.engine_states = {}
        self.orchestration_history = []
        self.last_plan = {}
        self.engine_factory = RuntimeEngineFactory()

        self.register_default_engines()

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
        return value if isinstance(value, dict) else {}

    def _safe_list(self, value):
        return value if isinstance(value, list) else []

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

        cooldown_until = state.get("cooldown_until", 0)

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
        }

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

        for name, config in self.engine_registry.items():
            if not self.engine_available(name):
                continue

            tags = self._safe_list(
                config.get("tags")
            )

            priority = config.get(
                "priority",
                50,
            )

            score = priority

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

            selected.append(
                {
                    "name": name,
                    "score": score,
                    "priority": priority,
                    "tags": tags,
                }
            )

        selected.sort(
            key=lambda item: item.get("score", 0),
            reverse=True,
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
                state["cooldown_until"] = (
                    self._now() + 60
                )
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

        report = {
            "ok": True,
            "plan_id": plan.get("plan_id"),
            "results": results,
            "steps": steps,
            "engine_states": self.get_engine_states(),
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

    def get_orchestration_history(
        self,
        limit=25,
    ):
        return self.orchestration_history[-limit:]