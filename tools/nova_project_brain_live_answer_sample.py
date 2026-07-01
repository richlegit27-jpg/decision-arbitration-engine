import json
import time
import urllib.request


URL = "http://127.0.0.1:5001/api/chat"


def post_chat(session_id, message):
    data = json.dumps({
        "session_id": session_id,
        "message": message,
        "attachments": [],
    }).encode("utf-8")

    request = urllib.request.Request(
        URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def get_text(result):
    assistant = result.get("assistant_message") or {}
    return str(
        assistant.get("text")
        or assistant.get("content")
        or result.get("response")
        or result.get("message")
        or ""
    ).strip()


def get_route(result):
    debug = result.get("debug") or {}
    assistant = result.get("assistant_message") or {}
    meta = assistant.get("meta") or result.get("meta") or {}

    return (
        debug.get("route_taken")
        or debug.get("route")
        or meta.get("route")
        or meta.get("strategy")
        or result.get("route_taken")
        or result.get("route")
        or ""
    )


def main():
    print("NOVA PROJECT BRAIN LIVE ANSWER SAMPLE")
    print("")

    stamp = str(int(time.time()))
    session_id = f"project_brain_answer_quality_{stamp}"

    setup_messages = [
        "current task is improve Nova project brain answer quality",
        "next move is create a focused project brain behavior smoke",
        "checkpoint is intelligence behavior smoke passed",
    ]

    questions = [
        "what are we working on?",
        "what's next?",
        "continue",
    ]

    for message in setup_messages:
        result = post_chat(session_id, message)
        print(f"SETUP: {message}")
        print(f"ROUTE: {get_route(result)}")
        print(f"TEXT: {get_text(result)[:300]}")
        print("")

    for question in questions:
        result = post_chat(session_id, question)
        print(f"QUESTION: {question}")
        print(f"ROUTE: {get_route(result)}")
        print(f"TEXT:")
        print(get_text(result))
        print("-" * 70)

    print("")
    print("NOVA PROJECT BRAIN LIVE ANSWER SAMPLE DONE")


if __name__ == "__main__":
    main()
