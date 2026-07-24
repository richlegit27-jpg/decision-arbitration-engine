from nova_backend.services.nova_behavior_memory_store import (
    NovaBehaviorMemoryStore,
)


class ProjectBrainDecisionMemory:

    def __init__(self, path=None):
        if path:
            self.store = NovaBehaviorMemoryStore(
                path=path
            )
        else:
            self.store = NovaBehaviorMemoryStore()

    def add_event(self, event):
        return self.store.add_event(event)

    def get_events(self):
        return self.store.get_events()

    def add_outcome(self, data):
        from datetime import datetime, timezone

        event = {
            "event_type": "decision_outcome",
            "recommended_move": data.get("recommended_move", ""),
            "outcome": data.get("outcome", ""),
            "severity": data.get("risk", "medium"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return self.add_event(event)

    def record_outcome(
        self,
        recommended_move,
        outcome,
    ):
        return self.add_outcome(
            {
                "recommended_move": recommended_move,
                "outcome": outcome,
            }
        )


project_brain_decision_memory = ProjectBrainDecisionMemory()