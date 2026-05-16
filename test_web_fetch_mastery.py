# C:\Users\Owner\nova\test_web_fetch_mastery.py

import json
import re
import sys
import time
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:5001"
CHAT_URL = f"{BASE_URL}/api/chat"


TESTS = [
    {
        "name": "Direct URL fetch",
        "prompt": "summarize https://www.espn.com/nba/",
        "expected_terms": [
            "espn",
        ],
        "blocked_terms": [
            "greg brockman",
            "openai products",
            "anthropic leadership",
        ],
    },
    {
        "name": "Live NBA news search",
        "prompt": "latest NBA news today",
        "expected_terms": [
            "nba",
        ],
        "blocked_terms": [
            "greg brockman",
            "openai products",
            "anthropic leadership",
        ],
    },
    {
        "name": "General live news search",
        "prompt": "latest technology news today",
        "expected_terms": [
            "technology",
            "tech",
            "news",
        ],
        "blocked_terms": [
            "greg brockman",
            "openai products",
            "anthropic leadership",
        ],
    },
    {
        "name": "OpenAI live search sanity",
        "prompt": "latest OpenAI news today",
        "expected_terms": [
            "openai",
        ],
        "blocked_terms": [
            "anthropic leadership scenarios",
            "too many agents",
        ],
    },
]


def post_json(
    url,
    payload,
    timeout=90,
):
    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout,
    ) as response:
        raw_body = response.read().decode(
            "utf-8",
            errors="replace",
        )

        return {
            "status": response.status,
            "body": raw_body,
            "json": safe_json(raw_body),
        }


def safe_json(
    text,
):
    try:
        return json.loads(text)
    except Exception:
        return {}


def flatten_text(
    value,
):
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, (int, float, bool)):
        return str(value)

    if isinstance(value, list):
        return "\n".join(
            flatten_text(item)
            for item in value
        )

    if isinstance(value, dict):
        return "\n".join(
            flatten_text(item)
            for item in value.values()
        )

    return str(value)


def extract_response_text(
    response_json,
):
    candidates = [
        response_json.get("answer"),
        response_json.get("response"),
        response_json.get("text"),
        response_json.get("summary"),
        response_json.get("assistant_response"),
    ]

    assistant_message = response_json.get("assistant_message")

    if isinstance(
        assistant_message,
        dict,
    ):
        candidates.extend(
            [
                assistant_message.get("content"),
                assistant_message.get("text"),
                assistant_message.get("answer"),
            ]
        )

    messages = response_json.get("messages")

    if isinstance(
        messages,
        list,
    ):
        for message in reversed(messages):
            if not isinstance(
                message,
                dict,
            ):
                continue

            if message.get("role") == "assistant":
                candidates.append(
                    message.get("content")
                )
                break

    for candidate in candidates:
        text = flatten_text(candidate).strip()

        if text:
            return text

    return flatten_text(response_json).strip()


def has_any_term(
    text,
    terms,
):
    text_lower = text.lower()

    return any(
        term.lower() in text_lower
        for term in terms
    )


def find_blocked_terms(
    text,
    terms,
):
    text_lower = text.lower()

    return [
        term
        for term in terms
        if term.lower() in text_lower
    ]


def detect_sources(
    text,
):
    source_names = [
        "espn",
        "the new york times",
        "nytimes",
        "cbs sports",
        "nba.com",
        "sports illustrated",
        "bleacher report",
        "the athletic",
        "reuters",
        "associated press",
        "ap news",
        "the verge",
        "techcrunch",
        "wired",
        "bbc",
        "cnn",
    ]

    found = []

    text_lower = text.lower()

    for source in source_names:
        if source in text_lower:
            found.append(source)

    return found


def run_test(
    test,
    index,
):
    print("")
    print("=" * 80)
    print(f"TEST {index}: {test['name']}")
    print("=" * 80)
    print(f"Prompt: {test['prompt']}")

    payload = {
        "user_text": test["prompt"],
        "session_id": "",
        "attachments": [],
    }

    started = time.time()

    try:
        result = post_json(
            CHAT_URL,
            payload,
        )
    except urllib.error.URLError as error:
        print("❌ Request failed")
        print(error)
        return False

    elapsed = round(
        time.time() - started,
        2,
    )

    status = result.get("status")
    response_json = result.get("json") or {}
    response_text = extract_response_text(response_json)

    blocked_hits = find_blocked_terms(
        response_text,
        test.get("blocked_terms", []),
    )

    expected_ok = has_any_term(
        response_text,
        test.get("expected_terms", []),
    )

    sources = detect_sources(response_text)

    print(f"HTTP status: {status}")
    print(f"Elapsed: {elapsed}s")
    print(f"Response chars: {len(response_text)}")
    print(f"Detected sources: {sources}")

    print("")
    print("Preview:")
    print("-" * 80)
    print(response_text[:1200])
    print("-" * 80)

    ok = True

    if status != 200:
        print("❌ HTTP status was not 200")
        ok = False
    else:
        print("✅ response returned 200")

    if not response_text:
        print("❌ response text was empty")
        ok = False
    else:
        print("✅ response text was not empty")

    if not expected_ok:
        print("❌ expected topic terms were missing")
        ok = False
    else:
        print("✅ expected topic terms found")

    if blocked_hits:
        print(f"❌ blocked stale terms found: {blocked_hits}")
        ok = False
    else:
        print("✅ no stale blocked terms found")

    if sources:
        print("✅ source names detected")
    else:
        print("⚠️ no obvious source names detected")

    if ok:
        print(f"✅ PASS: {test['name']}")
    else:
        print(f"❌ FAIL: {test['name']}")

    return ok


def main():
    print("NOVA WEB FETCH MASTERY TEST")
    print(f"Target: {CHAT_URL}")

    passed = 0
    failed = 0

    for index, test in enumerate(
        TESTS,
        start=1,
    ):
        ok = run_test(
            test,
            index,
        )

        if ok:
            passed += 1
        else:
            failed += 1

    print("")
    print("=" * 80)
    print("FINAL RESULT")
    print("=" * 80)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed:
        print("❌ WEB FETCH MASTERY TEST FAILED")
        sys.exit(1)

    print("✅ WEB FETCH MASTERY TEST PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()