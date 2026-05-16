class RuntimeGraphQueryService:

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

    def get_recent_nodes(
        self,
        node_type=None,
        limit=10,
    ):

        graph = (
            self.graph_memory.snapshot()
            if self.graph_memory
            else {}
        )

        nodes = self._safe_dict(
            graph.get("nodes")
        )

        results = []

        for node in nodes.values():

            if not isinstance(node, dict):
                continue

            if (
                node_type
                and node.get("type") != node_type
            ):
                continue

            results.append(node)

        results.sort(
            key=lambda x: x.get(
                "created_at",
                0,
            ),
            reverse=True,
        )

        return results[:limit]

    def get_edges_by_relation(
        self,
        relation=None,
    ):

        graph = (
            self.graph_memory.snapshot()
            if self.graph_memory
            else {}
        )

        edges = self._safe_list(
            graph.get("edges")
        )

        if not relation:
            return edges

        return [
            edge
            for edge in edges
            if isinstance(edge, dict)
            and edge.get("relation") == relation
        ]

    def detect_hot_paths(self):

        graph = (
            self.graph_memory.snapshot()
            if self.graph_memory
            else {}
        )

        edges = self._safe_list(
            graph.get("edges")
        )

        path_counts = {}

        for edge in edges:

            if not isinstance(edge, dict):
                continue

            relation = edge.get(
                "relation",
                "unknown",
            )

            path_counts[relation] = (
                path_counts.get(
                    relation,
                    0,
                ) + 1
            )

        hot_paths = [
            {
                "relation": relation,
                "count": count,
            }
            for relation, count
            in path_counts.items()
            if count >= 3
        ]

        hot_paths.sort(
            key=lambda x: x["count"],
            reverse=True,
        )

        return {
            "ok": True,
            "hot_paths": hot_paths,
            "path_counts": path_counts,
        }

    def summarize_patterns(self):

        hot_path_report = self.detect_hot_paths()

        hot_paths = self._safe_list(
            hot_path_report.get("hot_paths")
        )

        if not hot_paths:

            return {
                "ok": True,
                "summary": "No recurring runtime graph patterns detected yet.",
                "hot_paths": [],
            }

        lines = []

        for item in hot_paths[:5]:

            lines.append(
                f"{item.get('relation')} repeated {item.get('count')} times"
            )

        return {
            "ok": True,
            "summary": "; ".join(lines),
            "hot_paths": hot_paths,
        }

    def recommend_runtime_actions(self):

        pattern_report = self.detect_hot_paths()

        hot_paths = self._safe_list(
            pattern_report.get("hot_paths")
        )

        recommendations = []

        for item in hot_paths:

            relation = str(
                item.get("relation")
                or ""
            ).lower()

            count = int(
                item.get("count")
                or 0
            )

            if (
                relation == "governed"
                and count >= 5
            ):

                recommendations.append(
                    "Governor repeatedly controlling orchestration. Consider stabilization mode."
                )

            if (
                relation == "produced"
                and count >= 10
            ):

                recommendations.append(
                    "High orchestration throughput detected. Increase planner compression."
                )

            if (
                relation == "arbitrated"
                and count >= 5
            ):

                recommendations.append(
                    "Policy arbitration frequency increasing. Review runtime policies."
                )

        if not recommendations:

            recommendations.append(
                "No runtime graph intervention required."
            )

        return {
            "ok": True,
            "recommendations": recommendations,
            "hot_paths": hot_paths,
        }