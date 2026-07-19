from flask import request, jsonify


class CommandRouteService:

    def __init__(self, session_service):
        self.session_service = session_service

    def install_routes(self, app):

        @app.before_request
        def nova_repair_build_command_guard_20260701():
            try:
                if request.path not in ("/api/chat", "/api/chat/stream") or request.method != "POST":
                    return None

                payload = request.get_json(silent=True) or {}

                from nova_backend.services.repair_build_adapter import (
                    build_repair_build_response,
                )

                response_payload = build_repair_build_response(
                    payload,
                    self.session_service,
                )

                if response_payload is None:
                    return None

                return jsonify(response_payload)

            except Exception:
                return None

        @app.before_request
        def nova_workflow_catalog_command_guard_20260701():
            try:
                if request.path not in (
                    "/api/chat",
                    "/api/chat/stream",
                ) or request.method != "POST":
                    return None

                payload = request.get_json(silent=True) or {}

                from nova_backend.services.workflow_catalog_adapter import (
                    build_workflow_catalog_response,
                )

                response_payload = build_workflow_catalog_response(
                    payload,
                    self.session_service,
                )

                if response_payload is None:
                    return None

                return jsonify(response_payload)

            except Exception:
                return None


        @app.before_request
        def nova_autonomy_index_command_guard_20260701():
            try:
                if request.path not in (
                    "/api/chat",
                    "/api/chat/stream",
                ) or request.method != "POST":
                    return None

                payload = request.get_json(silent=True) or {}

                from nova_backend.services.autonomy_index_adapter import (
                    build_autonomy_index_response,
                )

                response_payload = build_autonomy_index_response(
                    payload,
                    self.session_service,
                )

                if response_payload is None:
                    return None

                return jsonify(response_payload)

            except Exception:
                return None


        @app.before_request
        def nova_command_registry_command_guard_20260701():
            try:
                if request.path not in (
                    "/api/chat",
                    "/api/chat/stream",
                ) or request.method != "POST":
                    return None

                payload = request.get_json(silent=True) or {}

                from nova_backend.services.autonomy_command_registry_adapter import (
                    build_command_registry_response,
                )

                response_payload = build_command_registry_response(
                    payload,
                    self.session_service,
                )

                if response_payload is None:
                    return None

                return jsonify(response_payload)

            except Exception:
                return None