# === ADD THESE IMPORTS AT TOP (under existing imports) ===
from web_search import search_web
from web_fetch import fetch_page

# === ADD THESE CONSTANTS (under config) ===
MAX_WEB_RESULTS = 5
MAX_WEB_PAGES = 3
MAX_WEB_TEXT_CHARS = 5000


# === REPLACE route_message WITH THIS ===
def route_message(user_text: str, memory_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    started = now_ms()
    text = normalize_text(user_text)
    lowered = text.lower()

    mode = "general"
    intent = "conversation"
    reason = "Defaulted to general conversation."
    memory_used: List[str] = []

    coding_terms = ["code","bug","fix","app.py","javascript","python","flask","html","css","smff","file","router","panel"]
    planning_terms = ["plan","roadmap","next","steps","phase","version","launch","strategy"]
    writing_terms = ["write","rewrite","email","book","blog","post","story"]
    analysis_terms = ["analyze","compare","why","breakdown","review"]
    web_terms = ["latest","today","current","news","recent","docs","documentation","search","online","web","live"]

    use_web = any(term in lowered for term in web_terms)

    if use_web:
        mode = "research"
        intent = "web_research"
        reason = "Detected freshness/web query"
    elif any(term in lowered for term in coding_terms):
        mode = "coding"
        intent = "build_or_fix_code"
        reason = "Detected coding"
    elif any(term in lowered for term in planning_terms):
        mode = "planning"
        intent = "project_planning"
    elif any(term in lowered for term in writing_terms):
        mode = "writing"
        intent = "draft_or_rewrite"
    elif any(term in lowered for term in analysis_terms):
        mode = "analysis"
        intent = "inspect_or_explain"

    return {
        "mode": mode,
        "intent": intent,
        "reason": reason,
        "use_web": use_web,
        "memory_hits": 0,
        "memory_used": [],
        "route_time_ms": max(1, now_ms() - started),
        "timestamp": now_ms(),
        "model": OPENAI_MODEL,
    }


# === ADD THESE FUNCTIONS ===
def build_web_context(user_text, router_meta):
    if not router_meta.get("use_web"):
        return "", []

    try:
        results = search_web(user_text, max_results=MAX_WEB_RESULTS)
    except:
        return "", []

    sources = []
    blocks = []

    for r in results[:MAX_WEB_PAGES]:
        url = r.get("url")
        if not url:
            continue

        try:
            page = fetch_page(url)
        except:
            continue

        text = (page.get("text") or "")[:MAX_WEB_TEXT_CHARS]
        if not text:
            continue

        sources.append({
            "title": r.get("title", url),
            "url": url,
            "snippet": r.get("snippet","")
        })

        blocks.append(text)

    return "\n\n".join(blocks), sources


# === MODIFY /api/chat ===
# FIND THIS SECTION AND REPLACE THE MODEL CALL PART ONLY

    web_context, sources = build_web_context(user_message, router_meta)

    model_messages = [
        {"role": "system", "content": build_system_prompt(router_meta, memory_items) + "\n\n" + web_context},
        *[
            {"role": m["role"], "content": m["content"]}
            for m in session["messages"][-16:]
            if m.get("role") in {"user", "assistant"}
        ],
    ]

    assistant_text = chat_with_model(model_messages[1:], router_meta, memory_items)

# ADD sources TO RESPONSE
    assistant_entry["sources"] = sources


# === MODIFY STREAM ===
# inside generate()

        web_context, sources = build_web_context(user_message, router_meta)

        yield sse({
            "type": "meta",
            "router_meta": router_meta,
            "sources": sources,
            "session_id": session["id"]
        })

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            stream=True,
            messages=[
                {"role": "system", "content": build_system_prompt(router_meta, memory_items) + "\n\n" + web_context},
                *model_messages,
            ],
        )

# FINAL DONE EVENT
        yield sse({
            "type": "done",
            "response": full_text,
            "router_meta": router_meta,
            "sources": sources,
            "session_id": session["id"],
        })