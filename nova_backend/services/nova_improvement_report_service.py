"""
NOVA IMPROVEMENT REPORT SERVICE V1

Creates human-readable reports from
self-improvement pipeline outputs.

Reporting only.
No decisions.
No execution.
"""


from datetime import datetime, timezone


class NovaImprovementReportService:


    def __init__(self):

        self.version = (
            "NOVA_IMPROVEMENT_REPORT_SERVICE_V1_20260710"
        )


    def create_report(
        self,
        recommendation=None,
        decision=None,
        proposal=None,
        mission_proposal=None,
    ):

        return {

            "type":
                "improvement_report",

            "engine":
                self.version,

            "created_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "detected_problem":
                (recommendation or {}).get(
                    "problem",
                    "",
                ),

            "evidence":
                (recommendation or {}).get(
                    "reason",
                    "",
                ),

            "recommended_upgrade":
                (recommendation or {}).get(
                    "recommended_upgrade",
                    "",
                ),

            "target_system":
                (recommendation or {}).get(
                    "target_system",
                    "",
                ),

            "decision":
                (decision or {}).get(
                    "decision",
                    "",
                ),

            "risk":
                (proposal or {}).get(
                    "risk",
                    "",
                ),

            "mission_status":
                (mission_proposal or {}).get(
                    "status",
                    "",
                ),

            "approval_required":
                (mission_proposal or {}).get(
                    "approval_required",
                    True,
                ),

        }


report_service = NovaImprovementReportService()


def create_improvement_report(
    recommendation=None,
    decision=None,
    proposal=None,
    mission_proposal=None,
):

    return report_service.create_report(
        recommendation,
        decision,
        proposal,
        mission_proposal,
    )