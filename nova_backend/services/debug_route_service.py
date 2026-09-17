# NOVA_DEBUG_ROUTE_SERVICE_ATTACHMENT_READY_20260913

class DebugRouteService:

    def install_routes(self, app):

        def debug_routes_enabled():
            try:
                import os

                value = str(
                    os.getenv(
                        "NOVA_DEBUG_ROUTES",
                        "",
                    )
                ).strip().lower()

                return value in {
                    "1",
                    "true",
                    "yes",
                    "on",
                    "enabled",
                }

            except Exception:
                return False

        def debug_routes_disabled_response():
            try:
                from flask import jsonify

                return jsonify(
                    {
                        "ok": False,
                        "error": (
                            "Debug routes are disabled. "
                            "Set NOVA_DEBUG_ROUTES=1 to enable."
                        ),
                    }
                ), 404

            except Exception:
                return {
                    "ok": False,
                    "error": (
                        "Debug routes are disabled. "
                        "Set NOVA_DEBUG_ROUTES=1 to enable."
                    ),
                }, 404

        def json_result(payload, status=200):
            from flask import jsonify

            return jsonify(payload), status

        @app.route(
            "/api/debug/chat-turn-shadow",
            methods=["GET"],
        )
        def api_debug_chat_turn_shadow():
            try:
                if not debug_routes_enabled():
                    return debug_routes_disabled_response()

                from nova_backend.services.chat_service import (
                    ChatService,
                )

                return json_result(
                    ChatService.get_global_chat_turn_shadow_snapshot()
                )

            except Exception as error:
                return json_result(
                    {
                        "ok": False,
                        "error": str(error),
                    },
                    500,
                )

        @app.route(
            "/api/debug/chat-turn-dry-run",
            methods=["POST", "GET"],
        )
        def api_debug_chat_turn_dry_run():
            if not debug_routes_enabled():
                return debug_routes_disabled_response()

            try:
                from flask import request

                payload = request.get_json(
                    silent=True
                ) or {}

                user_text = str(
                    payload.get("user_text")
                    or payload.get("message")
                    or payload.get("text")
                    or ""
                ).strip()

                return json_result(
                    {
                        "ok": True,
                        "dry_run": True,
                        "user_text": user_text,
                        "message": "Chat turn dry run completed.",
                    }
                )

            except Exception as error:
                return json_result(
                    {
                        "ok": False,
                        "error": str(error),
                    },
                    500,
                )

        @app.route(
            "/api/debug/attachment-context-dry-run",
            methods=["POST", "GET"],
        )
        def api_debug_attachment_context_dry_run():
            if not debug_routes_enabled():
                return debug_routes_disabled_response()

            try:
                from flask import request

                payload = request.get_json(
                    silent=True
                ) or {}

                attachments = (
                    payload.get("attachments")
                    or payload.get("files")
                    or []
                )

                if not isinstance(attachments, list):
                    attachments = [attachments]

                return json_result(
                    {
                        "ok": True,
                        "dry_run": True,
                        "attachment_count": len(attachments),
                        "attachments": attachments,
                        "message": (
                            "Attachment context dry run completed."
                        ),
                    }
                )

            except Exception as error:
                return json_result(
                    {
                        "ok": False,
                        "error": str(error),
                    },
                    500,
                )

        @app.route(
            "/api/debug/attachment-web-guard-dry-run",
            methods=["POST", "GET"],
        )
        def api_debug_attachment_web_guard_dry_run():
            if not debug_routes_enabled():
                return debug_routes_disabled_response()

            try:
                from flask import request

                payload = request.get_json(
                    silent=True
                ) or {}

                user_text = str(
                    payload.get("user_text")
                    or payload.get("message")
                    or payload.get("text")
                    or ""
                ).strip()

                return json_result(
                    {
                        "ok": True,
                        "dry_run": True,
                        "web_routing_suppressed": True,
                        "user_text": user_text,
                        "message": (
                            "Attachment web guard dry run completed."
                        ),
                    }
                )

            except Exception as error:
                return json_result(
                    {
                        "ok": False,
                        "error": str(error),
                    },
                    500,
                )

        @app.route(
            "/api/debug/chat-attachment-intent-dry-run",
            methods=["POST", "GET"],
        )
        def api_debug_chat_attachment_intent_dry_run():
            if not debug_routes_enabled():
                return debug_routes_disabled_response()

            try:
                from flask import request

                payload = request.get_json(
                    silent=True
                ) or {}

                user_text = str(
                    payload.get("user_text")
                    or payload.get("message")
                    or payload.get("text")
                    or ""
                ).strip()

                attachments = (
                    payload.get("attachments")
                    or payload.get("files")
                    or []
                )

                if not isinstance(attachments, list):
                    attachments = [attachments]

                return json_result(
                    {
                        "ok": True,
                        "dry_run": True,
                        "user_text": user_text,
                        "attachment_count": len(attachments),
                        "attachment_intent": bool(attachments),
                        "message": (
                            "Chat attachment intent dry run completed."
                        ),
                    }
                )

            except Exception as error:
                return json_result(
                    {
                        "ok": False,
                        "error": str(error),
                    },
                    500,
                )

        @app.route(
            "/api/debug/attachment-readiness",
            methods=["POST", "GET"],
        )
        def api_debug_attachment_readiness():
            if not debug_routes_enabled():
                return debug_routes_disabled_response()

            from nova_backend.services.attachment_pipeline_status import (
                get_attachment_pipeline_status,
            )

            return json_result(
                {
                    "ok": True,
                    "status": get_attachment_pipeline_status(),
                }
            )

        @app.route(
            "/api/attachment/status",
            methods=["GET"],
        )
        def api_attachment_status():
            try:
                from nova_backend.services.attachment_pipeline_status import (
                    get_attachment_pipeline_status,
                )

                payload = get_attachment_pipeline_status()

                return json_result(
                    {
                        "ok": True,
                        "ready": payload.get(
                            "ready",
                            False,
                        ),
                        "attachment_pipeline": payload.get(
                            "attachment_pipeline",
                            {},
                        ),
                        "debug_routes_require_env": payload.get(
                            "debug_routes_require_env",
                            True,
                        ),
                        "debug_env": payload.get(
                            "debug_env",
                            "NOVA_DEBUG_ROUTES=1",
                        ),
                        "details": payload.get(
                            "details",
                            {},
                        ),
                    }
                )

            except Exception as error:
                return json_result(
                    {
                        "ok": False,
                        "ready": False,
                        "error": str(error),
                    },
                    500,
                )
