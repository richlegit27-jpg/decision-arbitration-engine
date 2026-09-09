import app

payload = {
    "user_text": "Inspect the current Nova project and run all steps.",
    "session_id": "http_execution_endgame_test",
}

print("=" * 70)
print("CHAT REQUEST CONTEXT SERVICE TEST")
print("=" * 70)

print()
print("INPUT PAYLOAD:")
print(repr(payload))

print()
print("DIRECT EXTRACTION:")
print(
    repr(
        str(
            payload.get("user_text")
            or payload.get("text")
            or payload.get("message")
            or payload.get("content")
            or ""
        ).strip()
    )
)

print()
print("CONTEXT SERVICE:")

context = app.chat_request_context_service.build_context(
    payload
)

print(repr(context))

print()
print("CONTEXT USER TEXT:")
print(repr(context.get("user_text")))

print()
print("DONE")
print("=" * 70)
