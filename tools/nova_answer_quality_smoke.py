import requests

BASE = "http://127.0.0.1:5001"


CASES = [
    {
        "name": "current project state",
        "message": "what are we working on now",
        "must_include": [
            "Current Nova project state",
            "project-state memory recall fix",
        ],
        "must_not_include": [
            "I don't have",
            "no active project",
            "not sure",
        ],
    },
    {
        "name": "next move judgment",
        "message": "what should we do next",
        "must_include": [
            "next",
            "smoke",
        ],
        "must_not_include": [
            "I don't have",
            "no active project",
            "whatever you want",
        ],
    },
    {
        "name": "current blocker",
        "message": "what is the current blocker",
        "must_include": [
            "app.py",
            "guard",
        ],
        "must_not_include": [
            "I don't know",
            "no blocker",
        ],
    },
    {
        "name": "memory vs execution",
        "message": "what is the difference between memory and execution in Nova",
        "must_include": [
            "memory",
            "execution",
        ],
        "must_not_include": [
            "same thing",
        ],
    },
    {
        "name": "safe coding judgment",
        "message": "what test should we run before touching code",
        "must_include": [
            "smoke",
            "py_compile",
        ],
        "must_not_include": [
            "no test",
            "skip testing",
        ],
    },
]


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def ask(message, session_id):
    response = requests.post(
        f"{BASE}/api/chat",
        json={
            "message": message,
            "session_id": session_id,
            "attachments": [],
        },
        timeout=30,
    )
    assert_true("api status", response.status_code == 200, response.text[:500])

    data = response.json()
    assistant = data.get("assistant_message") or {}
    text = str(
        assistant.get("text")
        or assistant.get("content")
        or data.get("text")
        or ""
    ).strip()

    return text, data


def main():
    score = 0
    possible = len(CASES)

    print("NOVA ANSWER QUALITY SMOKE")
    print("=========================")

    for index, case in enumerate(CASES, start=1):
        session_id = f"answer_quality_smoke_{index:03d}"
        text, data = ask(case["message"], session_id)

        lower = text.lower()

        includes_ok = all(term.lower() in lower for term in case["must_include"])
        excludes_ok = all(term.lower() not in lower for term in case["must_not_include"])

        print("")
        print(f"CASE: {case['name']}")
        print(f"QUESTION: {case['message']}")
        print(f"ANSWER: {text[:500]}")

        assert_true(
            f"{case['name']} includes expected signals",
            includes_ok,
            f"missing from answer; expected={case['must_include']}",
        )

        assert_true(
            f"{case['name']} avoids weak signals",
            excludes_ok,
            f"bad phrase found; banned={case['must_not_include']}",
        )

        score += 1

    percent = int((score / possible) * 100)

    print("")
    print(f"NOVA ANSWER QUALITY SCORE: {score}/{possible} = {percent}%")

    assert_true(
        "answer quality minimum",
        percent >= 80,
        f"score={percent}%",
    )

    print("")
    print("NOVA ANSWER QUALITY SMOKE PASSED")


if __name__ == "__main__":
    main()
