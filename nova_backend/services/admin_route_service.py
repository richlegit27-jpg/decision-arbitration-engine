from pathlib import Path


class AdminRouteService:

    def __init__(self, admin_lead_service):
        self.admin_lead_service = admin_lead_service

    def install_routes(self, app):

        # NOVA_ADMIN_LEADS_CRM_LITE_20260709
        @app.post("/admin/leads/<lead_id>/update")
        def nova_admin_lead_update_20260709(lead_id):
            import json
            from datetime import datetime, timezone
            from urllib.parse import urlencode

            from flask import abort, redirect, request

            if not self.admin_lead_service.admin_allowed(request):
                abort(403)

            allowed_statuses = (
                "new",
                "reviewed",
                "replied",
                "archived",
            )

            status = str(
                request.form.get("status", "new") or "new"
            ).strip().lower()

            if status not in allowed_statuses:
                status = "new"

            owner_notes = str(
                request.form.get("owner_notes", "") or ""
            ).strip()

            if len(owner_notes) > 4000:
                owner_notes = owner_notes[:4000]

            data_path = (
                Path(__file__).resolve().parents[2]
                / "data"
                / "nova_leads.json"
            )

            try:
                data = json.loads(
                    data_path.read_text(encoding="utf-8")
                )
            except Exception:
                abort(500)

            if not isinstance(data, dict):
                abort(500)

            leads = data.get("leads", [])

            if not isinstance(leads, list):
                abort(500)

            target = None

            for lead in leads:
                if str(lead.get("id", "")) == str(lead_id):
                    target = lead
                    break

            if target is None:
                abort(404)

            now = datetime.now(timezone.utc).isoformat()

            target["status"] = status
            target["owner_notes"] = owner_notes
            target["admin_updated_at"] = now
            data["updated_at"] = now

            tmp_path = data_path.with_suffix(".json.tmp")

            tmp_path.write_text(
                json.dumps(
                    data,
                    indent=2,
                    sort_keys=True,
                ) + "\n",
                encoding="utf-8",
            )

            tmp_path.replace(data_path)

            next_url = str(
                request.form.get("next", "") or ""
            ).strip()

            if next_url.startswith("/admin/leads"):
                return redirect(next_url)

            params = {
                "q": request.form.get("q", ""),
                "kind": request.form.get("kind", "all"),
                "status": request.form.get(
                    "filter_status",
                    "all",
                ),
                "limit": request.form.get(
                    "limit",
                    "100",
                ),
            }

            clean_params = {
                key: value
                for key, value in params.items()
                if value
            }

            suffix = (
                "?"
                + urlencode(clean_params)
                if clean_params
                else ""
            )

            return redirect("/admin/leads" + suffix)

        # NOVA_ADMIN_LEADS_PAGE_HARD_RESTORE_20260709
        @app.get("/admin/leads")
        def nova_admin_leads_page_20260709():
            from flask import abort, render_template, request

            from nova_backend.services.lead_service import list_leads

            if not self.admin_lead_service.admin_allowed(request):
                abort(403)

            raw_limit = request.args.get("limit", 100)

            try:
                selected_limit = int(raw_limit)
            except Exception:
                selected_limit = 100

            selected_limit = max(1, min(selected_limit, 10000))

            data = list_leads(selected_limit)
            all_leads = data.get("leads", [])

            selected_kind = str(
                request.args.get("kind", "all") or "all"
            ).strip().lower()

            if selected_kind not in (
                "all",
                "contact",
                "early_access",
            ):
                selected_kind = "all"

            allowed_statuses = (
                "new",
                "reviewed",
                "replied",
                "archived",
            )

            selected_status = str(
                request.args.get("status", "all") or "all"
            ).strip().lower()

            if selected_status not in (
                ("all",) + allowed_statuses
            ):
                selected_status = "all"

            q = str(
                request.args.get("q", "") or ""
            ).strip()

            q_lower = q.lower()

            leads = list(all_leads)

            if selected_kind != "all":
                leads = [
                    lead
                    for lead in leads
                    if str(
                        lead.get("kind", "")
                    ).lower() == selected_kind
                ]

            if selected_status != "all":
                leads = [
                    lead
                    for lead in leads
                    if str(
                        lead.get("status", "new")
                    ).lower() == selected_status
                ]

            if q_lower:
                leads = [
                    lead
                    for lead in leads
                    if q_lower in " ".join(
                        [
                            str(lead.get("created_at", "")),
                            str(lead.get("kind", "")),
                            str(lead.get("name", "")),
                            str(lead.get("email", "")),
                            str(lead.get("interest", "")),
                            str(lead.get("message", "")),
                            str(lead.get("source", "")),
                            str(lead.get("status", "")),
                            str(lead.get("owner_notes", "")),
                        ]
                    ).lower()
                ]

            contact_count = len([
                lead
                for lead in all_leads
                if str(
                    lead.get("kind", "")
                ).lower() == "contact"
            ])

            early_count = len([
                lead
                for lead in all_leads
                if str(
                    lead.get("kind", "")
                ).lower() == "early_access"
            ])

            return render_template(
                "nova_admin_leads.html",
                leads=leads,
                count=data.get("count", len(all_leads)),
                visible_count=len(leads),
                contact_count=contact_count,
                early_count=early_count,
                path=data.get("path", ""),
                updated_at=data.get("updated_at", ""),
                q=q,
                selected_kind=selected_kind,
                selected_limit=selected_limit,
                selected_status=selected_status,
                allowed_statuses=allowed_statuses,
            )

        @app.get("/admin")
        def nova_admin_home_dashboard_20260709():
            from flask import abort, render_template

            from nova_backend.services.lead_service import list_leads

            if not self.admin_lead_service.admin_allowed(request):
                abort(403)

            data = list_leads(10000)
            leads = data.get("leads", [])

            contact_count = len([
                lead for lead in leads
                if str(lead.get("kind", "")).lower() == "contact"
            ])

            early_count = len([
                lead for lead in leads
                if str(lead.get("kind", "")).lower() == "early_access"
            ])

            return render_template(
                "nova_admin_home.html",
                count=data.get("count", len(leads)),
                contact_count=contact_count,
                early_count=early_count,
                recent_leads=leads[:5],
                path=data.get("path", ""),
                updated_at=data.get("updated_at", ""),
            )

        @app.get("/admin/launch-checklist")
        def nova_admin_launch_checklist_repair_20260709():
            from flask import abort, render_template, request

            if not self.admin_lead_service.admin_allowed(request):
                abort(403)

            return render_template(
                "nova_admin_launch_checklist.html"
            )



