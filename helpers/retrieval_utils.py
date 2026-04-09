from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any


RETRIEVAL_KIND_WEIGHTS: dict[str, float] = {
    "checkpoint": 4.0,
    "project": 3.5,
    "plan": 3.0,
    "debug": 3.0,
    "instruction": 2.5,
    "preference": 2.0,
    "note": 1.5,
    "chat_reply": 1.5,
    "web_result": 2.5,
    "web_fetch": 2.5,
    "image_analysis": 2.0,
    "video_analysis": 2.0,
}


def retrieval_textish(value: Any) -> str:
    return str(value or "").strip()


def retrieval_normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", retrieval_textish(value).lower()).strip()


def retrieval_tokenize(value: Any) -> list[str]:
    text = retrieval_normalize(value)
    if not text:
        return []
    return re.findall(r"[a-z0-9_]{2,}", text)


def retrieval_unique_preserve(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    for item in items:
        key = retrieval_normalize(item)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(str(item).strip())

    return out


def retrieval_query_terms(user_text: str) -> list[str]:
    base = retrieval_tokenize(user_text)
    boosted: list[str] = list(base)

    phrase_hints = [
        "web fetch",
        "video support",
        "video analysis",
        "memory",
        "artifacts",
        "retrieval",
        "checkpoint",
        "session",
        "brain",
        "router",
        "nova",
    ]

    lowered = retrieval_normalize(user_text)
    for phrase in phrase_hints:
        if phrase in lowered:
            boosted.extend(retrieval_tokenize(phrase))

    return retrieval_unique_preserve(boosted)


def retrieval_keyword_overlap_score(query_terms: list[str], text: str) -> float:
    query_set = set(retrieval_tokenize(" ".join(query_terms)))
    text_set = set(retrieval_tokenize(text))
    if not query_set or not text_set:
        return 0.0
    return float(len(query_set.intersection(text_set)))


def retrieval_exact_phrase_bonus(user_text: str, text: str) -> float:
    query = retrieval_normalize(user_text)
    body = retrieval_normalize(text)
    if not query or not body:
        return 0.0

    bonus = 0.0

    if query and query in body:
        bonus += 8.0

    for phrase in re.findall(r'"([^"]+)"', user_text or ""):
        p = retrieval_normalize(phrase)
        if p and p in body:
            bonus += 8.0

    common_phrases = [
        "web fetch",
        "video support",
        "video analysis",
        "memory",
        "artifacts",
        "retrieval",
        "checkpoint",
        "brain",
        "nova",
    ]
    for phrase in common_phrases:
        if phrase in query and phrase in body:
            bonus += 4.0

    return bonus


def retrieval_same_session_bonus(item: dict[str, Any], session_id: str | None) -> float:
    item_session_id = str(item.get("session_id") or "").strip()
    target_session_id = str(session_id or "").strip()
    if item_session_id and target_session_id and item_session_id == target_session_id:
        return 3.0
    return 0.0


def retrieval_kind_bonus(item: dict[str, Any]) -> float:
    kind = retrieval_normalize(item.get("kind") or item.get("source") or "")
    return float(RETRIEVAL_KIND_WEIGHTS.get(kind, 1.0))


def retrieval_recency_bonus(item: dict[str, Any]) -> float:
    stamp = retrieval_textish(
        item.get("updated_at")
        or item.get("created_at")
        or ""
    )
    if not stamp:
        return 0.0

    try:
        dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except Exception:
        return 0.0

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    age_seconds = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds())
    age_days = age_seconds / 86400.0

    if age_days <= 1:
        return 2.5
    if age_days <= 7:
        return 2.0
    if age_days <= 30:
        return 1.5
    if age_days <= 90:
        return 1.0
    return 0.25


def retrieval_text_for_item(item: dict[str, Any]) -> str:
    parts: list[str] = []

    for key in [
        "title",
        "text",
        "body",
        "content",
        "preview",
        "analysis_text",
        "last_message_preview",
    ]:
        value = retrieval_textish(item.get(key))
        if value:
            parts.append(value)

    meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
    for key in ["analysis_text", "source_url"]:
        value = retrieval_textish(meta.get(key))
        if value:
            parts.append(value)

    bullets = meta.get("bullets") if isinstance(meta.get("bullets"), list) else []
    for bullet in bullets:
        value = retrieval_textish(bullet)
        if value:
            parts.append(value)

    return "\n".join(parts).strip()


def retrieval_cosine_score(query_text: str, text: str) -> float:
    q_tokens = retrieval_tokenize(query_text)
    t_tokens = retrieval_tokenize(text)
    if not q_tokens or not t_tokens:
        return 0.0

    q_count = Counter(q_tokens)
    t_count = Counter(t_tokens)

    dot = 0.0
    for token, q_value in q_count.items():
        dot += float(q_value) * float(t_count.get(token, 0))

    q_norm = math.sqrt(sum(float(v * v) for v in q_count.values()))
    t_norm = math.sqrt(sum(float(v * v) for v in t_count.values()))

    if q_norm <= 0.0 or t_norm <= 0.0:
        return 0.0

    return dot / (q_norm * t_norm)


def score_retrieval_item(
    *,
    user_text: str,
    query_terms: list[str],
    item: dict[str, Any],
    session_id: str | None,
) -> tuple[float, str]:
    text = retrieval_text_for_item(item)
    if not text:
        return 0.0, ""

    score = 0.0
    score += retrieval_keyword_overlap_score(query_terms, text) * 2.0
    score += retrieval_exact_phrase_bonus(user_text, text)
    score += retrieval_cosine_score(user_text, text) * 6.0
    score += retrieval_same_session_bonus(item, session_id)
    score += retrieval_kind_bonus(item)
    score += retrieval_recency_bonus(item)

    return score, text


def rank_retrieval_items(
    *,
    user_text: str,
    items: list[dict[str, Any]],
    session_id: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    query_terms = retrieval_query_terms(user_text)
    ranked: list[dict[str, Any]] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        score, text = score_retrieval_item(
            user_text=user_text,
            query_terms=query_terms,
            item=item,
            session_id=session_id,
        )
        if score <= 0.0:
            continue

        enriched = dict(item)
        enriched["_retrieval_score"] = round(score, 4)
        enriched["_retrieval_text"] = text
        ranked.append(enriched)

    ranked.sort(
        key=lambda x: (
            float(x.get("_retrieval_score") or 0.0),
            retrieval_textish(x.get("updated_at") or x.get("created_at") or ""),
        ),
        reverse=True,
    )

    return ranked[: max(1, int(limit or 5))]


def build_retrieval_block(
    *,
    user_text: str,
    artifacts: list[dict[str, Any]],
    memory: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
    session_id: str | None = None,
    limit: int = 5,
    max_chars: int = 2200,
) -> tuple[str, list[dict[str, Any]]]:
    pool: list[dict[str, Any]] = []

    for item in artifacts:
        if not isinstance(item, dict):
            continue
        meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
        pool.append(
            {
                "kind": item.get("kind") or "artifact",
                "session_id": item.get("session_id") or "",
                "title": item.get("title") or "",
                "text": item.get("body") or item.get("content") or "",
                "preview": item.get("preview") or "",
                "updated_at": item.get("updated_at") or item.get("created_at") or "",
                "meta": meta,
            }
        )

    for item in memory:
        if not isinstance(item, dict):
            continue
        pool.append(
            {
                "kind": item.get("kind") or "memory",
                "session_id": item.get("session_id") or "",
                "title": "Memory",
                "text": item.get("text") or "",
                "preview": item.get("text") or "",
                "updated_at": item.get("updated_at") or item.get("created_at") or "",
                "meta": {
                    "source": item.get("source") or "memory",
                },
            }
        )

    for item in sessions:
        if not isinstance(item, dict):
            continue
        messages = item.get("messages") if isinstance(item.get("messages"), list) else []
        last_text = ""
        if messages:
            last = messages[-1] if isinstance(messages[-1], dict) else {}
            last_text = retrieval_textish(last.get("text") or "")
        pool.append(
            {
                "kind": "session",
                "session_id": item.get("id") or "",
                "title": item.get("title") or "Session",
                "text": "\n".join(
                    x for x in [
                        retrieval_textish(item.get("title")),
                        retrieval_textish(item.get("last_message_preview")),
                        last_text,
                    ] if x
                ),
                "preview": item.get("last_message_preview") or "",
                "updated_at": item.get("updated_at") or item.get("created_at") or "",
                "meta": {
                    "message_count": int(item.get("message_count") or 0),
                },
            }
        )

    ranked = rank_retrieval_items(
        user_text=user_text,
        items=pool,
        session_id=session_id,
        limit=limit,
    )

    lines: list[str] = []
    used_chars = 0

    for idx, item in enumerate(ranked, start=1):
        kind = retrieval_textish(item.get("kind") or "item")
        title = retrieval_textish(item.get("title") or kind.title())
        text = retrieval_textish(item.get("_retrieval_text") or item.get("text") or "")
        score = float(item.get("_retrieval_score") or 0.0)

        block = (
            f"[retrieval {idx}] kind={kind} score={score:.2f}\n"
            f"title: {title}\n"
            f"text: {text}\n"
        )

        if used_chars + len(block) > max_chars:
            break

        lines.append(block)
        used_chars += len(block)

    return "\n".join(lines).strip(), ranked


def build_retrieval_debug(
    *,
    user_text: str,
    artifacts: list[dict[str, Any]],
    memory: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
    session_id: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    block, ranked = build_retrieval_block(
        user_text=user_text,
        artifacts=artifacts,
        memory=memory,
        sessions=sessions,
        session_id=session_id,
        limit=limit,
    )

    return {
        "query": user_text,
        "selected_count": len(ranked),
        "selected": [
            {
                "kind": item.get("kind") or "",
                "title": item.get("title") or "",
                "session_id": item.get("session_id") or "",
                "score": float(item.get("_retrieval_score") or 0.0),
            }
            for item in ranked
        ],
        "block_preview": block[:600],
    }