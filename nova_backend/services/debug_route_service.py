# NOVA_DEBUG_ROUTE_SERVICE_ATTACHMENT_READY_20260827

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


        @app.route(
            "/api/debug/chat-turn-shadow",
            methods=["GET"],
        )
        def api_debug_chat_turn_shadow():

            try:
                if not debug_routes_enabled():
                    return debug_routes_disabled_response()

                from flask import jsonify

                from nova_backend.services.chat_service import (
                    ChatService,
                )

                return jsonify(
                    ChatService.get_global_chat_turn_shadow_snapshot()
                )

            except Exception as error:
                try:
                    from flask import jsonify

                    return jsonify(
                        {
                            "ok": False,
                            "error": str(error),
                        }
                    ), 500

                except Exception:
                    return {
                        "ok": False,
                        "error": str(error),
                    }, 500


        @app.route(
            "/api/debug/attachment-readiness",
            methods=["POST"],
        )
        def api_debug_attachment_readiness():

            if not debug_routes_enabled():
                return debug_routes_disabled_response()

            from flask import jsonify

            from nova_backend.services.attachment_pipeline_status import (
                get_attachment_pipeline_status,
            )

            return jsonify(
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

            from flask import jsonify

            print(
                "[ATTACHMENT STATUS ROUTE HIT]"
            )

            try:
                from nova_backend.services.attachment_pipeline_status import (
                    get_attachment_pipeline_status,
                )

                payload = get_attachment_pipeline_status()

                print(
                    "[ATTACHMENT STATUS RETURN]",
                    payload,
                )

                return jsonify(
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
                print(
                    "[ATTACHMENT STATUS ERROR]",
                    error,
                )

                return jsonify(
                    {
                        "ok": False,
                        "ready": False,
                        "error": str(error),
                    }
                ), 500