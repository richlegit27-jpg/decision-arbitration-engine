from __future__ import annotations

import os
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from nova_backend.services.model_gateway_service import (
    responses_create,
)


class HostedWebSearchService:
    """Evidence-backed web research through OpenAI hosted search."""

    def __init__(self, client=None, model: str = ""):
        self.client = client
        self.model = (
            str(model or "").strip()
            or os.getenv("NOVA_WEB_SEARCH_MODEL", "").strip()
            or os.getenv("OPENAI_MODEL", "").strip()
            or "gpt-5.4"
        )

    def _clean_url(self, url: str) -> str:
        value = str(url or "").strip()

        if not value:
            return ""

        try:
            parts = urlsplit(value)
            query = [
                (key, item)
                for key, item in parse_qsl(
                    parts.query,
                    keep_blank_values=True,
                )
                if not key.lower().startswith("utm_")
            ]

            return urlunsplit(
                (
                    parts.scheme,
                    parts.netloc,
                    parts.path,
                    urlencode(query),
                    parts.fragment,
                )
            )
        except Exception:
            return value

    def _extract_sources(self, response) -> list[dict]:
        sources = []
        seen_urls = set()

        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                for annotation in (
                    getattr(content, "annotations", []) or []
                ):
                    url = self._clean_url(
                        getattr(annotation, "url", "") or ""
                    )
                    title = str(
                        getattr(annotation, "title", "") or ""
                    ).strip()

                    if not url or url in seen_urls:
                        continue

                    seen_urls.add(url)

                    domain = ""
                    try:
                        domain = urlsplit(url).netloc.lower()
                        if domain.startswith("www."):
                            domain = domain[4:]
                    except Exception:
                        domain = ""

                    sources.append(
                        {
                            "title": title or domain or url,
                            "url": url,
                            "source": domain or url,
                            "domain": domain,
                            "snippet": "",
                        }
                    )

        return sources

    def search(
        self,
        query: str,
        *,
        context: str = "",
        max_results: int = 10,
    ) -> dict:
        question = str(query or "").strip()

        if not question:
            return {
                "ok": False,
                "query": question,
                "results": [],
                "body": "",
                "summary": "",
                "source_type": "openai_hosted_web",
                "error": "Empty search query.",
            }

        today = datetime.now(timezone.utc).date().isoformat()

        prompt = (
            "Answer the user's factual question using live web search.\n"
            f"Current date: {today}.\n"
            "Prefer primary and authoritative sources.\n"
            "Verify dates, names, numbers, scores, titles, versions, "
            "prices, schedules, and other changing facts.\n"
            "Use conversation context to resolve pronouns, omitted "
            "subjects, and follow-up references before searching.\n"
            "Treat the latest relevant exchange as authoritative context.\n"
            "Do not substitute an unrelated person, team, event, product, "
            "or topic when resolving a follow-up.\n"
            "Convert contextual follow-ups into a standalone research question "
            "with the resolved subject before searching.\n"
            "Always execute web search, even when conversation context appears "
            "to contain the answer.\n"
            "Do not rely on model memory when web evidence is needed.\n"
            "If reliable evidence is unavailable, say that the current "
            "answer could not be verified.\n"
            "Answer directly and retain inline citations.\n\n"
            f"Conversation context:\n{str(context or '').strip()}\n\n"
            f"Question:\n{question}"
        )

        try:
            response = responses_create(
                model=self.model,
                tools=[
                    {
                        "type": "web_search",
                    }
                ],
                tool_choice="required",
                input=prompt,
            )

            answer = str(
                getattr(response, "output_text", "") or ""
            ).strip()
            sources = self._extract_sources(response)
            sources = sources[:max(1, int(max_results or 10))]

            return {
                "ok": bool(answer and sources),
                "query": question,
                "results": sources,
                "body": answer,
                "summary": answer,
                "source_type": "openai_hosted_web",
                "model": self.model,
                "error": (
                    ""
                    if answer and sources
                    else "Hosted search returned no cited evidence."
                ),
            }

        except Exception as exc:
            return {
                "ok": False,
                "query": question,
                "results": [],
                "body": "",
                "summary": "",
                "source_type": "openai_hosted_web",
                "model": self.model,
                "error": str(exc),
            }
