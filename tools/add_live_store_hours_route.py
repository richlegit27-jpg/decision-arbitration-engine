from pathlib import Path
import re

path = Path(r"C:\Users\Owner\nova\nova_backend\services\chat_service.py")
text = path.read_text(encoding="utf-8")

helper = r'''
    def _looks_like_live_store_hours_request(self, user_text: str) -> bool:
        """
        LIVE_STORE_HOURS_ROUTE_V1

        Detect questions that require current business/store-hour lookup.
        These must go through web search instead of normal memory/chat.
        """
        text = (user_text or "").strip().lower()
        if not text:
            return False

        hours_terms = (
            "open now",
            "open right now",
            "are they open",
            "is it open",
            "still open",
            "closed now",
            "closing time",
            "what time do they close",
            "what time does it close",
            "what time are they open",
            "store hours",
            "business hours",
            "hours today",
            "holiday hours",
            "open today",
            "close today",
            "closed today",
        )

        business_terms = (
            "tim hortons",
            "tims",
            "starbucks",
            "mcdonald",
            "wendy",
            "subway",
            "restaurant",
            "coffee shop",
            "cafe",
            "store",
            "shop",
            "pharmacy",
            "clinic",
            "bank",
            "mall",
            "gas station",
            "costco",
            "walmart",
            "superstore",
            "save on foods",
            "safeway",
            "shoppers",
        )

        location_terms = (
            " near me",
            " vancouver",
            " bc",
            " british columbia",
            " keefer",
            " street",
            " st ",
            " ave",
            " avenue",
            " road",
            " rd ",
            " drive",
            " dr ",
            " downtown",
            " chinatown",
            " address",
            " location",
        )

        padded = f" {text} "
        has_hours_intent = (
            any(term in text for term in hours_terms)
            or " hours" in text
            or text.endswith(" hours")
        )
        has_business = any(term in text for term in business_terms)
        has_location = any(term in padded for term in location_terms)

        return has_hours_intent and (has_business or has_location)

    def _rewrite_live_store_hours_query(self, user_text: str, location=None) -> str:
        """
        Rewrite the user's question into a web-search-friendly live hours query.
        """
        query = (user_text or "").strip()

        if location and isinstance(location, dict):
            city = location.get("city") or location.get("name") or ""
            region = location.get("region") or location.get("province") or location.get("state") or ""
            extra = f"{city} {region}".strip()
            if extra and extra.lower() not in query.lower():
                query = f"{query} {extra}".strip()

        return (
            "Current live store hours / open now status for this exact business: "
            f"{query}. Prefer the official store locator or a current business listing. "
            "Answer only if the exact location and today's hours/open status are found. "
            "If not verified, say the live hours could not be verified. "
            "Do not say 'I need live store-hours data for that' to the user."
        )

    def _handle_live_store_hours_request(self, user_text: str, session_id: str = "", attachments=None, location=None):
        """
        Route live business-hours questions through Nova's existing web pipeline.
        """
        web_query = self._rewrite_live_store_hours_query(user_text, location=location)

        decision = {
            "route": "web_search",
            "web_intent": "live_store_hours",
            "reason": "User asked for current business open/closed/store-hours information.",
        }

        try:
            return self._handle_web_request(
                web_query,
                session_id=session_id,
                attachments=attachments,
                decision=decision,
            )
        except TypeError:
            try:
                return self._handle_web_request(
                    web_query,
                    session_id=session_id,
                    attachments=attachments,
                )
            except TypeError:
                return self._handle_web_request(web_query, session_id)
'''

if "LIVE_STORE_HOURS_ROUTE_V1" not in text:
    anchors = [
        "\n    def _run_tool_decision(self,",
        "\n    def _should_use_web(self,",
        "\n    def _build_grounded_business_answer(self,",
        "\n    def handle(self,",
    ]

    inserted = False
    for anchor in anchors:
        idx = text.find(anchor)
        if idx != -1:
            text = text[:idx] + "\n" + helper + text[idx:]
            inserted = True
            break

    if not inserted:
        raise SystemExit("Could not find a safe ChatService method anchor for helper insertion.")
else:
    print("Helpers already installed.")

guard = '''        # LIVE_STORE_HOURS_ROUTE_V1: force current business hours/open-now questions to web.
        if self._looks_like_live_store_hours_request(user_text):
            return self._handle_live_store_hours_request(
                user_text,
                session_id=locals().get("session_id", ""),
                attachments=locals().get("attachments", None),
                location=locals().get("location", None),
            )

'''

handle_match = re.search(r"\n    def handle\(self,[\s\S]*?(?=\n    def )", text)
if not handle_match:
    raise SystemExit("Could not find ChatService.handle block.")

handle_block = handle_match.group(0)

if "force current business hours/open-now questions to web" not in handle_block:
    patterns = [
        r"(        user_text\s*=\s*\(user_text\s+or\s+[\"']{2}\)\.strip\(\)\s*\n)",
        r"(        user_text\s*=\s*user_text\s+or\s+[\"']{2}\s*\n)",
        r"(        text\s*=\s*\(user_text\s+or\s+[\"']{2}\)\.strip\(\)\s*\n)",
    ]

    patched_handle = None
    for pattern in patterns:
        m = re.search(pattern, handle_block)
        if m:
            patched_handle = handle_block[:m.end()] + guard + handle_block[m.end():]
            break

    if patched_handle is None:
        raise SystemExit(
            "Could not find user_text normalization inside handle(). "
            "Add the LIVE_STORE_HOURS_ROUTE_V1 guard manually right after user_text is normalized."
        )

    text = text[:handle_match.start()] + patched_handle + text[handle_match.end():]
else:
    print("Handle guard already installed.")

path.write_text(text, encoding="utf-8")
print("Installed LIVE_STORE_HOURS_ROUTE_V1 in", path)
