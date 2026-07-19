import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

data_dir = BASE_DIR / "data"
sessions_path = data_dir / "nova_sessions.json"


def load_store():
    ...


def save_store(store):
    ...


def parse_powershell_object_string(value):
    ...


def normalize_attachments(value):
    ...


def normalize_message_attachment_shapes():
    ...


class AttachmentShapeNormalizerService:

    def install(self, app):
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
                changed = normalize_message_attachment_shapes()

                if changed:
                    try:
                        app.logger.info(
                            "[Nova Attachment Shape Normalizer] repaired %s message attachment/meta fields",
                            changed,
                        )
                    except Exception:
                        pass

            return response