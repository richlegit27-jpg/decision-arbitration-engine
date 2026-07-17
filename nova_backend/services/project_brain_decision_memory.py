from nova_backend.services.nova_behavior_memory_store import (
    NovaBehaviorMemoryStore,
)


class ProjectBrainDecisionMemory:

    def __init__(self):
        self.store = NovaBehaviorMemoryStore()

    def add_event(self, event):
        return self.store.add_event(event)

    def get_events(self):
        return self.store.get_events()

    def record_outcome(
        self,
        recommended_move,
        outcome,
    ):
        return self.add_event(
            {
                "decision": {
                    "recommended_move": recommended_move,
                },
                "outcome": outcome,
                "severity": "medium",
            }
        )


project_brain_decision_memory = (
    ProjectBrainDecisionMemory()
)