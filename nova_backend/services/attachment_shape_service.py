# NOVA_ATTACHMENT_SHAPE_NORMALIZER_20260610
# Keeps saved session message attachments as JSON-safe lists of objects.

def _nova_install_attachment_shape_normalizer_20260610():

    from flask import request

    @app.after_request
    def nova_attachment_shape_normalizer_after_request_20260610(response):
        path = str(request.path or "")

        if (
            path.startswith("/api/sessions")
            or path.startswith("/api/chat")
            or path.startswith("/api/chat/stream")
            or path == "/mobile"
        ):
            changed = attachment_shape_service.normalize_message_attachment_shapes()

            if changed:
                try:
                    app.logger.info(
                        "[Nova Attachment Shape Normalizer] repaired %s message attachment/meta fields",
                        changed,
                    )
                except Exception:
                    pass

        return response


