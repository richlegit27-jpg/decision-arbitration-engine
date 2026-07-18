import json
import re


class AttachmentResponseService:

    def clean_attachment_analysis_response(
        self,
        response,
        request,
    ):
        try:
            if request.path != "/api/chat":
                return response

            content_type = str(
                response.headers.get("Content-Type") or ""
            ).lower()

            if "application/json" not in content_type:
                return response

            data = response.get_json(silent=True)

            if not isinstance(data, dict):
                return response

            assistant_message = data.get(
                "assistant_message"
            )

            if not isinstance(assistant_message, dict):
                return response

            text_value = str(
                assistant_message.get("text") or ""
            )

            if "Attachment analysis:" not in text_value:
                return response

            # move the rest of the existing body here

        except Exception:
            return response