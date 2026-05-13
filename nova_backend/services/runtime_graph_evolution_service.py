class RuntimeGraphEvolutionService:

from nova_backend.services.runtime_graph_evolution_service import RuntimeGraphEvolutionService

    def __init__(
        self,
        graph_memory=None,
    ):

        self.graph_memory = (
            graph_memory
        )

        self.runtime_graph_query = RuntimeGraphQueryService(
            self.runtime_graph_memory
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

    def analyze_success_patterns(self):

        snapshot = (
            self.graph_memory.snapshot()
            if self.graph_memory
            else {}
        )

        nodes = self._safe_dict(
            snapshot.get("nodes")
        )

        success_count = 0
        failure_count = 0

        for node in nodes.values():

            if not isinstance(node, dict):
                continue

            payload = self._safe_dict(
                node.get("payload")
            )

            if payload.get("ok") is True:
                success_count += 1

            if payload.get("ok") is False:
                failure_count += 1

        total = (
            success_count
            + failure_count
        )

        success_rate = (
            success_count / total
            if total > 0
            else 0
        )

        return {
            "ok": True,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": success_rate,
        }

    def recommend_evolution(self):

        report = (
            self.analyze_success_patterns()
        )

        success_rate = float(
            report.get(
                "success_rate",
                0,
            )
        )

        recommendations = []

        if success_rate < 0.40:

            recommendations.append(
                "System instability detected. Increase repair and debugging priority."
            )

        elif success_rate < 0.70:

            recommendations.append(
                "Moderate runtime stability. Continue adaptive orchestration."
            )

        else:

            recommendations.append(
                "High runtime stability detected. Allow more autonomous orchestration."
            )

        return {
            "ok": True,
            "recommendations": recommendations,
            "success_rate": success_rate,
            "report": report,
        }