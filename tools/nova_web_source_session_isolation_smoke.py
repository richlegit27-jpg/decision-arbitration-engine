from pathlib import Path
import time

import requests


ROOT = Path(r"C:\Users\Owner\nova")

CHAT_SERVICE = (
    ROOT
    / "nova_backend"
    / "services"
    / "chat_service.py"
)

URL = "http://127.0.0.1:5001/api/chat"


def require(condition, message, evidence=None):
    if not condition:
        raise AssertionError(
            message
            + (
                "\nEVIDENCE: "
                + repr(evidence)
                if evidence is not None
                else ""
            )
        )

    print("PASS", message)


def post(session_id, message):
    response = requests.post(
        URL,
        json={
            "session_id": session_id,
            "message": message,
        },
        timeout=120,
    )

    response.raise_for_status()
    data = response.json()

    assistant = (
        data.get("assistant_message")
        if isinstance(data.get("assistant_message"), dict)
        else {}
    )

    meta = (
        assistant.get("meta")
        if isinstance(assistant.get("meta"), dict)
        else {}
    )

    answer = str(
        data.get("text")
        or data.get("content")
        or assistant.get("text")
        or assistant.get("content")
        or ""
    )

    return data, meta, answer


print("=" * 100)
print("NOVA WEB SOURCE SESSION ISOLATION SMOKE")
print("=" * 100)


source = CHAT_SERVICE.read_text(
    encoding="utf-8-sig",
    errors="replace",
)

require(
    source.count(
        "NOVA_WEB_SOURCE_SESSION_ISOLATION_LOCK_20260712"
    ) == 1,
    "session-isolation owner exists exactly once",
)

require(
    "_nova_has_reference_pair_20260712"
    in source,
    "two-option reference setup guard exists",
)

require(
    'getattr(self, "_last_web_source_urls", None)'
    not in source,
    "global source fallback remains removed",
)

require(
    "WEB_FOLLOWUP_DURABLE_SOURCE_CACHE_READ_FAILED"
    not in source,
    "durable cross-session source fallback remains removed",
)


session_id = (
    "web_source_isolation_smoke_"
    + str(int(time.time()))
)

setup = (
    "We are comparing two possible upgrades. "
    "The first option is improving voice controls. "
    "The second option is adding session search. "
    "Do not choose yet; just keep both options straight."
)

data, meta, answer = post(
    session_id,
    setup,
)

route = str(
    meta.get("route")
    or data.get("route")
    or ""
).lower()

sources = meta.get("sources") or []
source_urls = meta.get("source_urls") or []

require(
    route != "web",
    "reference setup does not route to web",
    route,
)

require(
    not sources,
    "reference setup receives no web sources",
    sources,
)

require(
    not source_urls,
    "reference setup receives no source URLs",
    source_urls,
)

forbidden = (
    "web results",
    "new york times",
    "meta removed",
    "labor concerns",
)

leaked = [
    marker
    for marker in forbidden
    if marker in answer.lower()
]

require(
    not leaked,
    "reference setup receives no stale web content",
    leaked,
)

require(
    "voice controls" in answer.lower()
    and "session search" in answer.lower(),
    "reference setup preserves both options",
    answer,
)


_, followup_meta, followup_answer = post(
    session_id,
    "Which was the second option?",
)

require(
    not (
        followup_meta.get("sources")
        or followup_meta.get("source_urls")
    ),
    "ordinal follow-up remains free of web sources",
    followup_meta,
)

require(
    "session search" in followup_answer.lower(),
    "ordinal follow-up resolves conversational option",
    followup_answer,
)


print()
print("=" * 100)
print("WEB SOURCE SESSION ISOLATION: REAL PASS")
print("FALSE WEB ROUTING: BLOCKED")
print("CROSS-SESSION SOURCE LEAKAGE: BLOCKED")
print("=" * 100)
