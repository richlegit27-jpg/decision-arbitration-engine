class LeadRouteService:

    def __init__(self, admin_lead_service):
        self.admin_lead_service = admin_lead_service

    def install_routes(self, app):

        @app.post("/api/contact")
        def nova_api_contact_submit_20260709():
            from flask import jsonify, request
            from nova_backend.services.lead_service import save_lead

            payload = request.get_json(silent=True) or request.form.to_dict(flat=True)

            try:
                lead = save_lead(
                    "contact",
                    payload,
                    self.admin_lead_service.request_meta(request),
                )
            except ValueError as error:
                return jsonify({
                    "ok": False,
                    "error": str(error),
                }), 400

            return jsonify({
                "ok": True,
                "lead_id": lead["id"],
                "dry_run": bool(lead.get("dry_run")),
                "message": "Thanks, your message was received.",
            })


        @app.post("/api/early-access")
        def nova_api_early_access_submit_20260709():
            from flask import jsonify, request
            from nova_backend.services.lead_service import save_lead

            payload = request.get_json(silent=True) or request.form.to_dict(flat=True)

            try:
                lead = save_lead(
                    "early_access",
                    payload,
                    self.admin_lead_service.request_meta(request),
                )
            except ValueError as error:
                return jsonify({
                    "ok": False,
                    "error": str(error),
                }), 400

            return jsonify({
                "ok": True,
                "lead_id": lead["id"],
                "dry_run": bool(lead.get("dry_run")),
                "message": "You are on the Nova early access list.",
            })


        @app.get("/api/leads")
        def nova_api_leads_admin_20260709():
            from flask import jsonify, request
            from nova_backend.services.lead_service import list_leads

            if not self.admin_lead_service.admin_allowed(request):
                return jsonify({
                    "ok": False,
                    "error": "Forbidden",
                }), 403

            return jsonify(
                list_leads(request.args.get("limit", 100))
            )