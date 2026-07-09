class MemoryRanker:
    """
    Scores and ranks memory items
    """

    def rank(self, all_memory, target_session, extract_name_fn):
        candidates = []

        for item in all_memory:
            if not isinstance(item, dict):
                continue

            item_text = str(item.get("text") or "").strip()
            if not item_text:
                continue

            name = extract_name_fn(item_text)
            if not name:
                continue

            item_session = str(item.get("session_id") or "").strip()
            item_kind = str(item.get("kind") or "").strip().lower()
            item_source = str(item.get("source") or "").strip().lower()
            item_updated = str(item.get("updated_at") or item.get("created_at") or "")
            weight = float(item.get("weight", 1.0) or 1.0)

            score = 0.0

            # session boost
            if item_session == target_session:
                score += 100.0
            elif not item_session:
                score += 20.0

            # profile boost
            if item_kind == "profile":
                score += 25.0

            # source boost
            if item_source in {"router_auto", "manual", "assistant"}:
                score += 5.0

            # text hints
            text_lower = item_text.lower()

            if text_lower.startswith("user name is"):
                score += 15.0
            elif text_lower.startswith("name:"):
                score += 10.0
            elif text_lower.startswith("my name is"):
                score += 5.0

            score += weight

            candidates.append({
                "score": score,
                "updated_at": item_updated,
                "name": name,
                "item": item,
            })

        if not candidates:
            return None

        candidates.sort(
            key=lambda c: (
                float(c.get("score", 0.0)),
                str(c.get("updated_at") or ""),
            ),
            reverse=True,
        )

        return candidates[0]