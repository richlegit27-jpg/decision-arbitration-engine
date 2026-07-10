"""
NOVA PROJECT BRAIN IMPROVEMENT CONTEXT V1

Provides Project Brain with self-improvement
signals based on behavior history.

Advisory only.
"""


from nova_backend.services.nova_behavior_memory import (
    behavior_memory
)

from nova_backend.services.nova_self_improvement_router import (
    build_self_improvement_signal
)


class NovaProjectBrainImprovementContext:


    def __init__(self):

        self.version = (
            "NOVA_PROJECT_BRAIN_IMPROVEMENT_CONTEXT_V1_20260710"
        )


    def build_context(self):

        report = (
            behavior_memory.export_report()
        )


        signal = (
            build_self_improvement_signal(
                report
            )
        )


        return {

            "engine":
                self.version,

            "behavior_report":
                report,

            "self_improvement_signal":
                signal,

            "recommended_focus":
                report.get(
                    "recommended_focus",
                    {}
                )
        }



project_brain_improvement_context = (
    NovaProjectBrainImprovementContext()
)


def build_project_brain_improvement_context():

    return (
        project_brain_improvement_context
        .build_context()
    )