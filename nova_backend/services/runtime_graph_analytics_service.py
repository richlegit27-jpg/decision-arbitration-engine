class RuntimeGraphAnalyticsService:

    def __init__(
        self,
        graph_memory=None,
    ):

        self.graph_memory = (
            graph_memory
        )

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

    def analyze_density(self):

        snapshot = (
            self.graph_memory.snapshot()
            if self.graph_memory
            else {}
        )

        nodes = self._safe_dict(
            snapshot.get("nodes")
        )

        edges = self._safe_list(
            snapshot.get("edges")
        )

        node_count = len(nodes)
        edge_count = len(edges)

        density = (
            edge_count / node_count
            if node_count > 0
            else 0
        )

        return {
            "ok": True,
            "node_count": node_count,
            "edge_count": edge_count,
            "density": density,
        }

    def detect_fragmentation(self):

        snapshot = (
            self.graph_memory.snapshot()
            if self.graph_memory
            else {}
        )

        nodes = self._safe_dict(
            snapshot.get("nodes")
        )

        edges = self._safe_list(
            snapshot.get("edges")
        )

        connected = set()

        for edge in edges:

            if not isinstance(edge, dict):
                continue

            connected.add(
                edge.get("source")
            )

            connected.add(
                edge.get("target")
            )

        isolated = []

        for node_id in nodes:

            if node_id not in connected:
                isolated.append(node_id)

        return {
            "ok": True,
            "isolated_nodes": isolated,
            "isolated_count": len(isolated),
        }