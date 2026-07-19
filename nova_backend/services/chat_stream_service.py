import json

from flask import Response


class ChatStreamService:

    def stream(self, api_chat):
        def generate():
            try:
                result = api_chat()

                payload = None

                if isinstance(result, dict):
                    payload = result
                elif hasattr(result, "get_json"):
                    payload = result.get_json(silent=True)

                if not isinstance(payload, dict):
                    payload = {}

                assistant = payload.get("assistant_message") or {}

                text = assistant.get("text", "")

                if not isinstance(text, str):
                    text = ""

            except Exception as e:
                yield "data: " + json.dumps({
                    "type": "error",
                    "content": str(e)
                }) + "\n\n"
                return

            if not text:
                text = "No response generated."

            full = ""

            for chunk in text.split():
                full += chunk + " "

                yield "data: " + json.dumps({
                    "type": "token",
                    "content": chunk + " "
                }) + "\n\n"

            yield "data: " + json.dumps({
                "type": "message",
                "content": full.strip()
            }) + "\n\n"

            yield "data: " + json.dumps({
                "type": "done",
                "done": True
            }) + "\n\n"

        return Response(
            generate(),
            mimetype="text/event-stream",
        )