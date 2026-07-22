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

from nova_backend.services.hosted_web_search_service import (
    HostedWebSearchService,
)

hosted_service = HostedWebSearchService()

original_client = hosted_service.client
original_extract_sources = (
    hosted_service._extract_sources
)

captured_request = {}


class FakeResponses:

    def create(self, **kwargs):
        captured_request.update(kwargs)

        return type(
            "FakeResponse",
            (),
            {
                "output_text": (
                    "This answer has no cited evidence."
                )
            },
        )()


class FakeClient:
    responses = FakeResponses()


try:
    hosted_service.client = FakeClient()
    hosted_service._extract_sources = (
        lambda response: []
    )

    uncited_result = hosted_service.search(
        "Give me an uncited factual answer."
    )

finally:
    hosted_service.client = original_client
    hosted_service._extract_sources = (
        original_extract_sources
    )


assert_true(
    "uncited_answer_rejected",
    uncited_result.get("ok") is False,
)

assert_true(
    "uncited_answer_has_no_results",
    uncited_result.get("results") == [],
)

assert_true(
    "uncited_answer_reports_evidence_error",
    "no cited evidence"
    in str(uncited_result.get("error") or "").lower(),
)

assert_true(
    "hosted_web_tool_required",
    captured_request.get("tool_choice")
    == "required",
)

fallback_service = WebService()

fallback_service.hosted_web_search_service.search = (
    lambda query, **kwargs: {
        "ok": False,
        "results": [],
        "body": "",
        "summary": "",
        "error": "Hosted provider unavailable.",
    }
)

fallback_service._check_api_key = (
    lambda: "Brave provider unavailable."
)
fallback_service._duckduckgo_search = (
    lambda query, max_results=10: []
)
fallback_service._bing_search = (
    lambda query, max_results=10: []
)
fallback_service._news_rss_search = (
    lambda query, max_results=10: []
)

unavailable = fallback_service.search_web_api(
    "Give me a verified current fact.",
    preferred_mode="general",
)

assert_true(
    "placeholder_fallback_rejected",
    unavailable.get("ok") is False,
)

assert_true(
    "placeholder_has_no_fake_results",
    unavailable.get("results") == [],
)

assert_true(
    "placeholder_reports_web_unavailable",
    unavailable.get("source_type")
    == "web_unavailable",
)

assert_true(
    "placeholder_contains_no_google_search_link",
    "google.com/search"
    not in str(unavailable).lower(),
)

print(
    "\nNOVA HOSTED WEB CONVERSATION SMOKE PASSED"
)
