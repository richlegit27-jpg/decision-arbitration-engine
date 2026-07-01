import requests
import traceback

BASE = "http://127.0.0.1:5001"

CASES = [
    {
        "name": "current project state",
        "message": "what are we working on now",
        "must_include": ["Current Nova project state", "project-state memory recall"],
        "must_not_include": ["I don't have", "no active project", "not sure"],
    },
    {
        "name": "next move judgment",
        "message": "what should we do next",
        "must_include": ["next", "smoke"],
        "must_not_include": ["whatever you want", "no active project"],
    },
    {
        "name": "current blocker",
        "message": "what is the current blocker",
        "must_include": ["app.py", "guard"],
        "must_not_include": ["I don't know", "no blocker"],
    },
    {
        "name": "coding safety judgment",
        "message": "what test should we run before touching code",
        "must_include": ["py_compile", "smoke", "git status"],
        "must_not_include": ["skip testing", "no test"],
    },
    {
        "name": "memory vs execution",
        "message": "what is the difference between memory and execution in Nova",
        "must_include": ["memory", "execution", "knows", "does"],
        "must_not_include": ["same thing"],
    },
    {
        "name": "no blind patching",
        "message": "why should we not patch blindly right now",
        "must_include": ["blind", "smoke"],
        "must_not_include": ["just patch", "doesn't matter"],
    },
    {
        "name": "commit judgment",
        "message": "when should we commit this change",
        "must_include": ["py_compile", "smoke", "git status"],
        "must_not_include": ["commit first", "without testing"],
    },
    {
        "name": "test selection",
        "message": "which smoke should we run for memory recall",
        "must_include": ["nova_project_state_memory_api_smoke"],
        "must_not_include": ["all tests only", "no smoke"],
    },
    {
        "name": "guard stack awareness",
        "message": "what is risky about app.py right now",
        "must_include": ["guard", "app.py"],
        "must_not_include": ["nothing risky"],
    },
    {
        "name": "attachment web routing awareness",
        "message": "what was the duplicate web attachment marker about",
        "must_include": ["attachment", "web"],
        "must_not_include": ["memory bug"],
    },
    {
        "name": "session continuity",
        "message": "why does project-state memory help session continuity",
        "must_include": ["project", "memory"],
        "must_not_include": ["doesn't help"],
    },
    {
        "name": "direct style",
        "message": "how should you answer Richard during Nova coding work",
        "must_include": ["direct", "PowerShell"],
        "must_not_include": ["long essay"],
    },
    {
        "name": "user preference awareness",
        "message": "what are Richard's workflow preferences for Nova",
        "must_include": ["PowerShell", "exact", "small"],
        "must_not_include": ["vague"],
    },
    {
        "name": "checkpoint summary",
        "message": "summarize the current Nova checkpoint",
        "must_include": ["memory", "smoke"],
        "must_not_include": ["I don't know"],
    },
    {
        "name": "failure diagnosis",
        "message": "if a smoke fails, what should we do first",
        "must_include": ["read", "failure"],
        "must_not_include": ["ignore", "commit anyway"],
    },
    {
        "name": "when to use memory",
        "message": "when should Nova use memory",
        "must_include": ["project", "preference"],
        "must_not_include": ["never"],
    },
    {
        "name": "when not to use memory",
        "message": "when should Nova not save something to memory",
        "must_include": ["temporary", "debug"],
        "must_not_include": ["save everything"],
    },
    {
        "name": "ask vs proceed",
        "message": "when should we ask a question versus proceed with a safe patch",
        "must_include": ["ambiguous", "safe"],
        "must_not_include": ["always ask"],
    },
    {
        "name": "route debug awareness",
        "message": "why do debug.route and route_taken matter",
        "must_include": ["route", "debug"],
        "must_not_include": ["do not matter"],
    },
    {
        "name": "rollback judgment",
        "message": "what should we do if a patch breaks py_compile",
        "must_include": ["fix", "compile"],
        "must_not_include": ["commit"],
    },
]


def ask(message, session_id):
    response = requests.post(
        f"{BASE}/api/chat",
        json={
            "message": message,
            "session_id": session_id,
            "attachments": [],
        },
        timeout=35,
    )

    if response.status_code != 200:
        return "", {"error": response.text[:500], "status": response.status_code}

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
    passed = 0
    failed = []

    print("NOVA ANSWER QUALITY 95 SMOKE")
    print("============================")

    for index, case in enumerate(CASES, start=1):
        session_id = f"answer_quality_95_smoke_{index:03d}"

        print("")
        print(f"CASE {index:02d}: {case['name']}")
        print(f"QUESTION: {case['message']}")

        try:
            text, data = ask(case["message"], session_id)
            lower = text.lower()

            missing = [
                term
                for term in case["must_include"]
                if term.lower() not in lower
            ]

            banned = [
                term
                for term in case["must_not_include"]
                if term.lower() in lower
            ]

            print(f"ANSWER: {text[:700]}")

            if missing or banned:
                failed.append({
                    "name": case["name"],
                    "missing": missing,
                    "banned": banned,
                    "answer": text[:700],
                })
                print(f"FAIL {case['name']} missing={missing} banned={banned}")
            else:
                passed += 1
                print(f"PASS {case['name']}")

        except Exception as exc:
            failed.append({
                "name": case["name"],
                "missing": ["request/exception"],
                "banned": [],
                "answer": repr(exc),
            })
            print(f"FAIL {case['name']} exception={exc}")
            traceback.print_exc()

    total = len(CASES)
    percent = int((passed / total) * 100)

    print("")
    print("NOVA ANSWER QUALITY 95 RESULTS")
    print("==============================")
    print(f"passed: {passed}/{total}")
    print(f"score: {percent}%")

    if failed:
        print("")
        print("FAILED CASES")
        print("============")
        for item in failed:
            print(f"- {item['name']}")
            print(f"  missing: {item['missing']}")
            print(f"  banned: {item['banned']}")
            print(f"  answer: {item['answer'][:300]}")

    if percent < 95:
        raise AssertionError(f"NOVA ANSWER QUALITY 95 FAILED score={percent}%")

    print("")
    print("NOVA ANSWER QUALITY 95 SMOKE PASSED")


if __name__ == "__main__":
    main()
