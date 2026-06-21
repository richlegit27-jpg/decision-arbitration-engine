import time
import uuid

from nova_backend.services.runtime_graph_storage_service import RuntimeGraphStorageService
from nova_backend.services.runtime_graph_store_service import (
    RuntimeGraphStoreService,
)

class RuntimeGraphMemoryService:

    def __init__(
        self,
        storage_path=None,
    ):

        self.storage = RuntimeGraphStorageService(
            storage_path=storage_path
        )

        snapshot = self.storage.load_snapshot()

        self.nodes = self._safe_dict(
            snapshot.get("nodes")
        )

        self.edges = self._safe_list(
            snapshot.get("edges")
        )
        self.store = (
            RuntimeGraphStoreService()
        )

        loaded = self.store.load()

        self.events = (
            loaded.get("events")
            if isinstance(
                loaded.get("events"),
                list,
            )
            else []
        )


    def _now(self):

        return time.time()

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

    def add_node(
        self,
        node_type,
        payload=None,
    ):

        node_id = str(
            uuid.uuid4()
        )

        self.nodes[node_id] = {
            "id": node_id,
            "type": str(
                node_type or "unknown"
            ),
            "payload": self._safe_dict(
                payload
            ),
            "created_at": self._now(),
        }

        return node_id

    def add_edge(
        self,
        source_id,
        target_id,
        relation,
        payload=None,
    ):

        if not source_id or not target_id:

            return None

        edge = {
            "source": source_id,
            "target": target_id,
            "relation": str(
                relation or "related_to"
            ),
            "payload": self._safe_dict(
                payload
            ),
            "created_at": self._now(),
        }

        self.edges.append(edge)
        self.edges = self.edges[-500:]

        return edge

    def record_orchestration(
        self,
        plan=None,
        report=None,
        runtime_governor=None,
        runtime_policy=None,
    ):

        plan = self._safe_dict(plan)
        report = self._safe_dict(report)
        runtime_governor = self._safe_dict(runtime_governor)
        runtime_policy = self._safe_dict(runtime_policy)

        plan_node = self.add_node(
            "plan",
            plan,
        )

        report_node = self.add_node(
            "report",
            report,
        )

        governor_node = self.add_node(
            "governor",
            runtime_governor,
        )

        policy_node = self.add_node(
            "policy",
            runtime_policy,
        )

        self.add_edge(
            plan_node,
            report_node,
            "produced",
        )

        self.add_edge(
            governor_node,
            plan_node,
            "governed",
        )

        self.add_edge(
            policy_node,
            plan_node,
            "arbitrated",
        )

        self.storage.save_snapshot(
            self.snapshot()
        )

        return {
            "ok": True,
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "last_nodes": {
                "plan": plan_node,
                "report": report_node,
                "governor": governor_node,
                "policy": policy_node,
            },
        }

    def snapshot(self):

        return {
            "nodes": self.nodes,
            "edges": self.edges,
        }

    def record_event(
        self,
        event=None,
    ):

        event = self._safe_dict(event)

        if not event:
            return {
                "ok": False,
                "reason": "empty_event",
            }

        if hasattr(
            self,
            "add_event",
        ):

            return self.add_event(event)

        if hasattr(
            self,
            "remember",
        ):

            return self.remember(event)

        if not hasattr(
            self,
            "events",
        ):

            self.events = []

        self.events.append(event)

        self.events = self.events[-250:]

        self.store.save(
            {
                "events": self.events,
            }
        )

        return {
            "ok": True,
            "event": event,
            "event_count": len(self.events),
        }

    def record_runtime_cycle(
        self,
        execution_state=None,
        execution_summary=None,
        world_state=None,
        scheduler_state=None,
        cycle_count=0,
    ):

        event = {
            "type": "runtime_cycle",
            "cycle_count": cycle_count,
            "execution_state": self._safe_dict(execution_state),
            "execution_summary": self._safe_dict(execution_summary),
            "world_state": self._safe_dict(world_state),
            "scheduler_state": self._safe_dict(scheduler_state),
        }

        return self.record_event(event)

    def record_runtime_outcome(
        self,
        execution_state=None,
        control=None,
        world_state=None,
        scheduler_state=None,
    ):

        event = {
            "type": "runtime_outcome",
            "execution_state": self._safe_dict(execution_state),
            "control": self._safe_dict(control),
            "world_state": self._safe_dict(world_state),
            "scheduler_state": self._safe_dict(scheduler_state),
        }

        return self.record_event(event)

