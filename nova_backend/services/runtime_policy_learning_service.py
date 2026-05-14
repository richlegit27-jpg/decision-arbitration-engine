class RuntimePolicyLearningService:

    name = "runtime_policy_learning_service"

    tags = [
        "runtime",
        "policy",
        "learning",
        "adaptation",
    ]

    def evolve_policy(
        self,
        runtime_autonomous_memory=None,
    ):

        runtime_autonomous_memory = (
            runtime_autonomous_memory
            if isinstance(
                runtime_autonomous_memory,
                list,
            )
            else []
        )

        action_stats = {}

        for memory in runtime_autonomous_memory:

            if not isinstance(memory, dict):
                continue

            action = str(
                memory.get(
                    "action",
                    "",
                )
            ).lower()

            if not action:
                continue

            stats = action_stats.setdefault(
                action,
                {
                    "count": 0,
                    "confidence": 0.50,
                },
            )

            stats["count"] += 1

        for action, stats in action_stats.items():

            count = stats["count"]

            confidence = min(
                0.95,
                0.50 + (count * 0.03),
            )

            stats["confidence"] = round(
                confidence,
                2,
            )

        recommended_action = None

        if action_stats:

            recommended_action = max(
                action_stats.items(),
                key=lambda item: (
                    item[1]["confidence"]
                ),
            )[0]

        return {
            "ok": True,
            "recommended_action": (
                recommended_action
            ),
            "action_stats": action_stats,
        }