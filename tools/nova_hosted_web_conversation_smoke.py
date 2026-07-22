from nova_backend.services.web_service import WebService


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(
            f"{name} FAILED {detail}"
        )

    print(f"PASS {name}")


service = WebService()
captured = {}


def fake_hosted_search(
    query,
    *,
    context="",
    max_results=10,
):
    captured["query"] = query
    captured["context"] = context
    captured["max_results"] = max_results

    return {
        "ok": True,
        "query": query,
        "results": [
            {
                "title": "Official result",
                "url": "https://example.com/result",
                "source": "example.com",
            }
        ],
        "body": "Verified contextual answer.",
        "summary": "Verified contextual answer.",
        "source_type": "openai_hosted_web",
    }


service.hosted_web_search_service.search = (
    fake_hosted_search
)

conversation_context = (
    "user: Who won the tournament?\n"
    "assistant: The verified winner was Spain."
)

result = service.search(
    "Who did they beat in the final?",
    context=conversation_context,
    max_results=5,
)

assert_true(
    "hosted_search_primary",
    result.get("source_type")
    == "openai_hosted_web",
)

assert_true(
    "followup_query_preserved",
    captured.get("query")
    == "Who did they beat in the final?",
)

assert_true(
    "conversation_context_forwarded",
    captured.get("context")
    == conversation_context,
)

assert_true(
    "max_results_forwarded",
    captured.get("max_results") == 5,
)

assert_true(
    "verified_sources_returned",
    bool(result.get("results")),
)

print(
    "\nNOVA HOSTED WEB CONVERSATION SMOKE PASSED"
)
