import json
import traceback
import re

from flask import Response, stream_with_context


class ChatStreamService:

    def _extract_payload(self, result):

        if isinstance(result, dict):
            return result

        if isinstance(result, tuple):

            for item in result:
                payload = self._extract_payload(item)

                if isinstance(payload, dict) and payload:
                    return payload

            return {}

        if hasattr(result, "get_json"):

            try:
                payload = result.get_json(
                    silent=True
                )

                if isinstance(payload, dict):
                    return payload

            except Exception:
                pass

        if hasattr(result, "response"):

            try:
                response = result.response

                payload = self._extract_payload(
                    response
                )

                if isinstance(payload, dict):
                    return payload

            except Exception:
                pass

        return {}

    def _extract_text(self, payload):

        if not isinstance(payload, dict):
            return ""

        assistant = payload.get("assistant_message")

        if isinstance(assistant, dict):

            for key in (
                "text",
                "content",
                "message",
                "response",
            ):

                value = assistant.get(key)

                if isinstance(value, str) and value.strip():
                    return value.strip()

        for key in (
            "text",
            "content",
            "response",
            "message",
            "answer",
        ):

            value = payload.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

        return ""

    def _event(self, payload):

        return (
            "data: "
            + json.dumps(
                payload,
                ensure_ascii=False,
            )
            + "\n\n"
        )

    def _extract_status(self, result):
        if isinstance(result, tuple):
            for item in result:
                if isinstance(item, int):
                    return item
            for item in result:
                status = self._extract_status(item)
                if status is not None:
                    return status

        status = getattr(result, "status_code", None)
        return status if isinstance(status, int) else None

    def _completion_metadata(self, payload):
        metadata = {}
        assistant = payload.get("assistant_message")
        if isinstance(assistant, dict):
            for key in ("attachments", "image_url"):
                if assistant.get(key):
                    metadata[key] = assistant[key]
        for key in ("attachments", "image_url"):
            if payload.get(key) and key not in metadata:
                metadata[key] = payload[key]
        return metadata

    def stream(self, api_chat):

        @stream_with_context
        def generate():
            try:
                result = api_chat()
                payload = self._extract_payload(
                    result
                )

                status = self._extract_status(result)
                failed = (
                    (status is not None and status >= 400)
                    or payload.get("ok") is False
                    or bool(payload.get("error"))
                )

                if failed:
                    message = str(
                        payload.get("error")
                        or payload.get("message")
                        or "Nova could not complete this request."
                    )
                    yield self._event({
                        "type": "error",
                        "content": message,
                    })
                    yield self._event({"type": "done", "done": True})
                    return

                text = self._extract_text(
                    payload
                )

                if not text:
                    yield self._event({
                        "type": "error",
                        "content": "Nova returned an empty response.",
                    })
                    yield self._event({"type": "done", "done": True})
                    return

                for chunk in re.findall(r"\S+\s*|\s+", text):
                    yield self._event({
                        "type": "token",
                        "content": chunk,
                    })

                yield self._event({
                    "type": "message",
                    "content": text,
                })

                done_payload = {
                    "type": "done",
                    "done": True,
                }
                done_payload.update(self._completion_metadata(payload))
                yield self._event(done_payload)

            except Exception as error:
                traceback.print_exc()
                yield self._event({
                    "type": "error",
                    "content": str(error),
                })

                yield self._event({
                    "type": "done",
                    "done": True,
                })

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
