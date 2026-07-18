import os
from datetime import datetime, timezone


class AdminLeadService:

    def request_meta(self, request):
        return {
            "ip": request.headers.get("X-Forwarded-For")
            or request.remote_addr
            or "",
            "user_agent": request.headers.get(
                "User-Agent",
                "",
            ),
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }


    def admin_allowed(self, request):
        expected_key = os.environ.get(
            "NOVA_ADMIN_KEY",
            "",
        ).strip()

        if not expected_key:
            return True

        provided_key = (
            request.headers.get(
                "X-NOVA-ADMIN-KEY",
                "",
            )
            or request.args.get(
                "admin_key",
                "",
            )
        ).strip()

        return provided_key == expected_key


    def filter_leads(
        self,
        leads,
        query="",
    ):
        query = str(
            query
            or
            ""
        ).strip().lower()

        if not query:
            return leads

        return [
            lead
            for lead in leads
            if query in str(
                lead.get("name", "")
            ).lower()
            or query in str(
                lead.get("email", "")
            ).lower()
            or query in str(
                lead.get("company", "")
            ).lower()
            or query in str(
                lead.get("interest", "")
            ).lower()
        ]