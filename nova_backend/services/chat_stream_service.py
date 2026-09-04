import json
import traceback

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

    def stream(self, api_chat):

        @stream_with_context
        def generate():

            try:

                yield self._event({
                    "type": "meta",
                    "stream": True,
                    "status": "started",
                })
                result = api_chat()

                print(
                    "[CHAT STREAM RAW RESULT]",
                    type(result),
                    repr(result)[:2000],
                    flush=True,
                )

                yield self._event({
                    "type": "debug",
                    "result_type": str(type(result)),
                    "result_repr": repr(result)[:3000],
                })

                payload = self._extract_payload(
                    result
                )

                print(
                    "[CHAT STREAM PAYLOAD]",
                    repr(payload)[:3000],
                    flush=True,
                )

                yield self._event({
                    "type": "debug",
                    "payload": payload,
                })

                print(
                    "[CHAT STREAM PAYLOAD]",
                    repr(payload)[:3000],
                    flush=True,
                )

                text = self._extract_text(
                    payload
                )

                if not text:

                    error_message = (
                        payload.get("error")
                        or payload.get("message")
                        or "No response generated."
                    )

                    yield self._event({
                        "type": "error",
                        "content": str(error_message),
                    })

                    yield self._event({
                        "type": "done",
                        "done": True,
                    })

                    return

                full = ""

                for word in text.split():

                    chunk = word + " "

                    full += chunk

                    yield self._event({
                        "type": "token",
                        "content": chunk,
                    })

                yield self._event({
                    "type": "message",
                    "content": full.strip(),
                })

                yield self._event({
                    "type": "done",
                    "done": True,
                })

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