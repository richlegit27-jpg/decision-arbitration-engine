"""
NOVA SELF IMPROVEMENT RECOMMENDER V1

Converts behavior learning signals into
engineering improvement recommendations.

Advisory only.
Project Brain decides execution.
"""


from datetime import datetime, timezone


class NovaSelfImprovementRecommender:


    def __init__(self):

        self.version = (
            "NOVA_SELF_IMPROVEMENT_RECOMMENDER_V1_20260710"
        )


    def recommend(self, behavior_priority):

        if not behavior_priority:

            return self._empty()


        focus = behavior_priority.get(
            "focus",
            "unknown"
        )

        priority = behavior_priority.get(
            "priority",
            "low"
        )

        reason = behavior_priority.get(
            "reason",
            ""
        )


        recommendation = self._map_focus(
            focus
        )


        return {

            "engine":
                self.version,

            "generated_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "problem":
                focus,

            "priority":
                priority,

            "reason":
                reason,

            "recommended_upgrade":
                recommendation["upgrade"],

            "target_system":
                recommendation["target"],

            "confidence":
                self._confidence(
                    priority
                ),
        }



    def _map_focus(self, focus):

        mappings = {

            "continuity": {

                "upgrade":
                    "Improve conversation recall and session continuity",

                "target":
                    "conversation memory system",
            },


            "attachments": {

                "upgrade":
                    "Improve attachment understanding pipeline",

                "target":
                    "attachment analysis system",
            },


            "answer_quality": {

                "upgrade":
                    "Improve response quality evaluation",

                "target":
                    "chat response pipeline",
            },

        }


        return mappings.get(
            focus,
            {

                "upgrade":
                    f"Investigate {focus} behavior",

                "target":
                    "general intelligence layer",
            }
        )



    def _confidence(self, priority):

        if priority == "critical":
            return "high"

        if priority == "high":
            return "medium-high"

        if priority == "medium":
            return "medium"

        return "low"



    def _empty(self):

        return {

            "engine":
                self.version,

            "problem":
                "none",

            "recommended_upgrade":
                "collect more behavior data",

            "confidence":
                "low",
        }



self_improvement_recommender = (
    NovaSelfImprovementRecommender()
)


def create_self_improvement_recommendation(
    behavior_priority
):

    return (
        self_improvement_recommender.recommend(
            behavior_priority
        )
    )