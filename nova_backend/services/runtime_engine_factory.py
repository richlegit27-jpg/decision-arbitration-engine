from nova_backend.services.runtime_debug_engine import (
    RuntimeDebugEngine,
)
from nova_backend.services.runtime_healing_engine import (
    RuntimeHealingEngine,
)
from nova_backend.services.runtime_planning_engine import (
    RuntimePlanningEngine,
)
from nova_backend.services.runtime_reflection_engine import (
    RuntimeReflectionEngine,
)
from nova_backend.services.runtime_repair_engine import (
    RuntimeRepairEngine,
)
from nova_backend.services.runtime_scheduler_engine import (
    RuntimeSchedulerEngine,
)


class RuntimeEngineFactory:
    def build_default_engines(
        self,
    ):
        return [
            RuntimeDebugEngine(),
            RuntimeRepairEngine(),
            RuntimePlanningEngine(),
            RuntimeHealingEngine(),
            RuntimeReflectionEngine(),
            RuntimeSchedulerEngine(),
        ]

    def build_engine_map(
        self,
    ):
        engines = (
            self.build_default_engines()
        )

        return {
            engine.name: engine
            for engine in engines
        }