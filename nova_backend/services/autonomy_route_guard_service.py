from __future__ import annotations

from flask import request, jsonify, Response


class AutonomyRouteGuardService:

    def __init__(self, session_service=None):
        self.session_service = session_service

    def install(self, app):
        self._install_autonomy_task_brief(app)
        self._install_autonomy_plan_guard(app)
        self._install_patch_build_guard(app)
        return app

    def _install_autonomy_task_brief(self, app):
        pass


    def _install_autonomy_plan_guard(self, app):

        @app.before_request
        def nova_autonomy_plan_adapter_guard_20260701():
            try:
                if request.method != "POST":
                    return None

                if request.path not in (
                    "/api/chat",
                    "/api/chat/stream",
                ):
                    return None

                payload = request.get_json(silent=True) or {}

                from nova_backend.services.autonomy_plan_adapter import (
                    build_autonomy_plan_response,
                )

                response_json = build_autonomy_plan_response(
                    payload,
                    self.session_service,
                )

                if not response_json:
                    return None

                return jsonify(response_json)

            except Exception as exc:
                print(
                    "[NOVA_AUTONOMY_PLAN_ADAPTER_GUARD] failed:",
                    exc,
                )
                return None

    def _install_patch_build_guard(self, app):

        @app.before_request
        def nova_patch_build_adapter_guard_20260701():
            try:
                if request.method != "POST":
                    return None

                if request.path not in (
                    "/api/chat",
                    "/api/chat/stream",
                ):
                    return None

                payload = request.get_json(silent=True) or {}

                from nova_backend.services.patch_build_adapter import (
                    build_patch_build_response,
                )

                response_json = build_patch_build_response(
                    payload,
                    self.session_service,
                )

                if not response_json:
                    return None

                return jsonify(response_json)

            except Exception as exc:
                print(
                    "[NOVA_PATCH_BUILD_ADAPTER_GUARD] failed:",
                    exc,
                )
                return None