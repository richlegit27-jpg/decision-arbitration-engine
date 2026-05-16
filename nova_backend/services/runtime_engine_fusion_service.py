class RuntimeEngineFusionService:
    def _safe_dict(self, value):
        return value if isinstance(value, dict) else {}

    def _safe_list(self, value):
        return value if isinstance(value, list) else []

    def fuse_results(self, results=None):
        results = self._safe_list(results)

        fused = {
            "ok": True,
            "signals": [],
            "priority_weights": {},
            "recommended_action": "observe",
            "confidence": 0.5,
        }

        for item in results:
            result = self._safe_dict(
                self._safe_dict(item).get("result")
            )

            action = result.get("action")
            if action:
                fused["signals"].append(action)

            for key in [
                "repair",
                "debug",
                "planning",
                "healing",
                "memory",
                "policy",
                "evolution",
                "goal",
                "strategy",
                "priority",
                "decision",
            ]:
                if key in str(result).lower():
                    fused["priority_weights"][key] = (
                        fused["priority_weights"].get(key, 0) + 1
                    )

        if fused["priority_weights"]:
            fused["recommended_action"] = max(
                fused["priority_weights"],
                key=fused["priority_weights"].get,
            )
            fused["confidence"] = min(
                0.95,
                0.5 + (
                    fused["priority_weights"][fused["recommended_action"]]
                    * 0.05
                ),
            )

        return fused