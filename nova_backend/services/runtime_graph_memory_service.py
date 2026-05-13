import time
import uuid

from nova_backend.services.runtime_graph_storage_service import RuntimeGraphStorageService

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