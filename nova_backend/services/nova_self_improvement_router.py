"""
NOVA SELF IMPROVEMENT ROUTER V1

Determines when Project Brain should
request a self-improvement analysis.

Advisory routing only.
"""


class NovaSelfImprovementRouter:


    def __init__(self):

        self.version = (
            "NOVA_SELF_IMPROVEMENT_ROUTER_V1_20260710"
        )


    def should_analyze(
        self,
        behavior_report
    ):

        if not behavior_report:

            return False


        focus = behavior_report.get(
            "recommended_focus",
            {}
        )


        priority = focus.get(
            "priority",
            "low"
        )


        if priority in (
            "medium",
            "high",
            "critical"
        ):

            return True


        return False



    def build_signal(
        self,
        behavior_report
    ):

        return {

            "engine":
                self.version,

            "analyze":
                self.should_analyze(
                    behavior_report
                ),

            "reason":
                (
                    behavior_report
                    .get(
                        "recommended_focus",
                        {}
                    )
                    .get(
                        "reason",
                        ""
                    )
                )
        }



self_improvement_router = (
    NovaSelfImprovementRouter()
)


def build_self_improvement_signal(
    behavior_report
):

    return (
        self_improvement_router
        .build_signal(
            behavior_report
        )
    )