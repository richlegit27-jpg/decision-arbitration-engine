from nova_backend.services.runtime_debug_engine import (
    RuntimeDebugEngine,
)
from nova_backend.services.runtime_decision_engine import (
    RuntimeDecisionEngine,
)
from nova_backend.services.runtime_evolution_engine import (
    RuntimeEvolutionEngine,
)
from nova_backend.services.runtime_goal_engine import (
    RuntimeGoalEngine,
)
from nova_backend.services.runtime_healing_engine import (
    RuntimeHealingEngine,
)
from nova_backend.services.runtime_memory_engine import (
    RuntimeMemoryEngine,
)
from nova_backend.services.runtime_planning_engine import (
    RuntimePlanningEngine,
)
from nova_backend.services.runtime_policy_engine import (
    RuntimePolicyEngine,
)
from nova_backend.services.runtime_priority_engine import (
    RuntimePriorityEngine,
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
from nova_backend.services.runtime_self_check_engine import (
    RuntimeSelfCheckEngine,
)
from nova_backend.services.runtime_strategy_engine import (
    RuntimeStrategyEngine,
)
from nova_backend.services.runtime_world_model_engine import (
    RuntimeWorldModelEngine,
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
            RuntimeMemoryEngine(),
            RuntimePolicyEngine(),
            RuntimeEvolutionEngine(),
            RuntimeWorldModelEngine(),
            RuntimeGoalEngine(),
            RuntimeStrategyEngine(),
            RuntimePriorityEngine(),
            RuntimeSelfCheckEngine(),
            RuntimeDecisionEngine(),
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

