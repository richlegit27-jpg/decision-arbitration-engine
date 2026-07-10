import json
import sys
import time
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError


API_URL = "http://127.0.0.1:5001/api/chat"


def post_chat(question, case_slug):
    payload = {
        "message": question,
        "session_id": f"answer_quality_freshness_{case_slug}_{int(time.time())}",
        "attachments": [],
    }

    data = json.dumps(payload).encode("utf-8")

    last_error = None
    for attempt in range(1, 4):
        try:
            req = urllib_request.Request(
                API_URL,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib_request.urlopen(req, timeout=20) as response:
                status = response.status
                body = response.read().decode("utf-8", errors="replace")
                parsed = json.loads(body)

            assert_true("api status", status == 200, f"status={status}")
            return parsed

        except (URLError, HTTPError, TimeoutError, ConnectionResetError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(0.8 * attempt)

    raise AssertionError(f"api request failed after retries: {last_error}")


def extract_answer(data):
    assistant = data.get("assistant_message") or {}
    return (
        data.get("text")
        or data.get("content")
        or assistant.get("text")
        or assistant.get("content")
        or ""
    )


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def assert_terms(case_name, answer, required_terms, stale_terms):
    lower = answer.lower()

    missing = [term for term in required_terms if term.lower() not in lower]
    assert_true(
        f"{case_name} includes expected signals",
        not missing,
        f"missing={missing}",
    )

    stale = [term for term in stale_terms if term.lower() in lower]
    assert_true(
        f"{case_name} avoids stale/weak signals",
        not stale,
        f"stale={stale}",
    )


CASES = [
    {
        "name": "current project state",
        "slug": "current_state",
        "question": "what are we working on now",
        "required": [
            "Project Brain",
            "context builder",
            "freshness",
            "answer-quality",
        ],
        "stale": [
            "launch about a month",
            "frontend polish",
            "mobile blocker",
            "heroku",
        ],
    },

{
    "name": "next move judgment freshness",
    "slug": "next_move",
    "question": "what should we do next",
    "required": [
        "Project Brain",
        "cleanup/consolidation",
        "direct recall",
        "broad Project Brain routing",
        "avoiding another app.py guard",
    ],
    "preferred": [
        "Decision Engine v1",
        "Mission Control",
        "Failure Interpreter",
    ],
    "stale": [
        "finish Nova project brain answer quality",
        "make `what's next?` return project context",
        "tools/nova_project_brain_live_answer_sample.py",
        "idle/generic fallback text",
    ],
},

    {
        "name": "current blocker freshness",
        "slug": "current_blocker",
        "question": "what is the current blocker",
        "required": [
            "Project Brain",
            "Decision Engine v1",
            "No active Decision Engine blocker",
            "Mission Control blocker",
            "Failure Interpreter blocker",
            "cleanup/consolidation",
            "move intelligence into services",
        ],
        "stale": [
            "larger Nova answer-quality 95 smoke now passes 20/20",
            "20-case board",
            "measured answer-policy intelligence",
            "Make Nova answer quality smoke retry reload resets",
            "Add Nova answer quality 95 policy",
        ],
    },


    {
        "name": "memory vs execution",
        "slug": "memory_execution",
        "question": "what is the difference between memory and execution in Nova",
        "required": [
            "Memory",
            "Execution",
            "knows",
            "does",
        ],
        "stale": [
            "saved to memory",
            "I can remember that",
            "generic fallback",
        ],
    },

    {
        "name": "safe coding judgment",
        "slug": "safe_coding",
        "question": "what test should we run before touching code",
        "required": [
            "git status",
            "py_compile",
            "focused smoke",
        ],
        "stale": [
            "just code",
            "skip tests",
            "generic fallback",
        ],
    },
]

def post_chat_session(question, session_id):
    payload = {
        "message": question,
        "session_id": session_id,
        "attachments": [],
    }

    data = json.dumps(payload).encode("utf-8")

    req = urllib_request.Request(
        API_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib_request.urlopen(req, timeout=20) as response:
        return json.loads(
            response.read().decode("utf-8", errors="replace")
        )

def run_continuity_test():
    print("")
    print("CASE: conversation continuity")
    print("QUESTION: what were we talking about")

    session_id = f"continuity_test_{int(time.time())}"

    post_chat_session(
        "We are working on Nova Project Brain cleanup and consolidation.",
        session_id,
    )

    data = post_chat_session(
        "what were we talking about",
        session_id,
    )

    answer = extract_answer(data)

    print("ANSWER:", answer[:700])

    assert_terms(
        "conversation continuity",
        answer,
        [
            "Nova",
            "Project Brain",
        ],
        [
            "I don't have context",
            "new conversation",
            "no previous context",
        ],
    )

    assert_answer_depth(
        "conversation continuity",
        answer,
    )

def assert_answer_depth(case_name, answer):
    words = answer.split()

    assert_true(
        f"{case_name} answer exists",
        len(words) > 0,
    )

    assert_true(
        f"{case_name} answer has reasoning depth",
        len(words) >= 40,
        f"word_count={len(words)}",
    )


GLOBAL_STALE = [
    "i don't know",
    "i do not know",
    "generic fallback",
    "it depends",
    "maybe consider",
    "you should probably",
]

def main():
    print("NOVA PROJECT BRAIN INTELLIGENCE SMOKE")
    print("=========================")

    passed = 0

    for case in CASES:
        print("")
        print(f"CASE: {case['name']}")
        print(f"QUESTION: {case['question']}")

        data = post_chat(case["question"], case["slug"])
        answer = extract_answer(data)

        print("ANSWER:", answer[:700])

        assert_terms(
            case["name"],
            answer,
            case["required"],
            case["stale"],
        )

        assert_answer_depth(
            case["name"],
            answer,
        )

        global_stale_hits = [
            term
            for term in GLOBAL_STALE
            if term.lower() in answer.lower()
        ]

        assert_true(
            f"{case['name']} avoids weak reasoning",
            not global_stale_hits,
            f"found={global_stale_hits}",
        )

        passed += 1

    print("")
    print(
    f"NOVA PROJECT BRAIN INTELLIGENCE SCORE: "
    f"{passed}/{len(CASES)} = "
    f"{round((passed / len(CASES)) * 100)}%"
)
    assert_true("answer quality minimum", passed == len(CASES))
    print("")
    print("NOVA ANSWER QUALITY SMOKE PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print("")
        print("NOVA ANSWER QUALITY SMOKE FAILED")
        print(exc)
        raise SystemExit(1)
