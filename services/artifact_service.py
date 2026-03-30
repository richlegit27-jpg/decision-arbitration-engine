from __future__ import annotations

import json
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ArtifactService:
    def __init__(self, data_dir: Optional[str] = None) -> None:
        base_dir = Path(data_dir or Path(__file__).resolve().parents[1] / "data")
        base_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = base_dir
        self.artifacts_path = self.data_dir / "nova_artifacts.json"
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self.artifacts_path.exists():
            self._write_json([])

    def _read_json(self) -> List[Dict[str, Any]]:
        self._ensure_file()
        try:
            with self.artifacts_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _write_json(self, data: List[Dict[str, Any]]) -> None:
        self.artifacts_path.parent.mkdir(parents=True, exist_ok=True)
        with self.artifacts_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _normalize_content(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, indent=2, ensure_ascii=False)
        except Exception:
            return str(value)

    def _normalize_tags(self, tags: List[Any]) -> List[str]:
        out: List[str] = []
        seen = set()
        for tag in tags:
            text = str(tag).strip()
            if not text:
                continue
            lower = text.lower()
            if lower in seen:
                continue
            seen.add(lower)
            out.append(text)
        return out

    def _normalize_meta(self, meta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        meta = meta or {}
        if not isinstance(meta, dict):
            return {"raw_meta": self._normalize_content(meta)}

        cleaned: Dict[str, Any] = {}
        for key, value in meta.items():
            cleaned[str(key)] = self._safe_json_value(value)
        return cleaned

    def _safe_json_value(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(k): self._safe_json_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._safe_json_value(v) for v in value]
        return self._normalize_content(value)

    def list_artifacts(
        self,
        session_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        items = self._read_json()
        if session_id:
            items = [x for x in items if x.get("session_id") == session_id]
        items.sort(
            key=lambda x: x.get("updated_at") or x.get("created_at") or "",
            reverse=True,
        )
        if limit is not None:
            items = items[:limit]
        return items

    def get_artifacts(
        self,
        session_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        return self.list_artifacts(session_id=session_id, limit=limit)

    def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        for item in self._read_json():
            if str(item.get("id")) == str(artifact_id):
                return item
        return None

    def save_artifact(
        self,
        *,
        title: str,
        content: Any,
        kind: str = "chat",
        session_id: str = "default-session",
        tags: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
        pinned: bool = False,
        artifact_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        items = self._read_json()
        now = utc_now_iso()

        normalized = {
            "id": artifact_id or str(uuid.uuid4()),
            "title": (title or "Untitled artifact").strip(),
            "content": self._normalize_content(content),
            "kind": (kind or "chat").strip(),
            "session_id": session_id or "default-session",
            "tags": self._normalize_tags(tags or []),
            "meta": self._normalize_meta(meta),
            "pinned": bool(pinned),
            "created_at": now,
            "updated_at": now,
        }

        for index, item in enumerate(items):
            if str(item.get("id")) == normalized["id"]:
                normalized["created_at"] = item.get("created_at") or now
                items[index] = normalized
                self._write_json(items)
                return normalized

        items.append(normalized)
        self._write_json(items)
        return normalized

    def delete_artifact(self, artifact_id: str) -> bool:
        items = self._read_json()
        before = len(items)
        items = [x for x in items if str(x.get("id")) != str(artifact_id)]
        if len(items) == before:
            return False
        self._write_json(items)
        return True

    def _tokenize(self, text: str) -> List[str]:
        raw = re.findall(r"[a-zA-Z0-9_]{2,}", text.lower())
        stop = {
            "the", "and", "for", "that", "with", "this", "from", "what", "when",
            "where", "were", "your", "have", "will", "into", "about", "then",
            "than", "them", "they", "just", "want", "need", "work", "next",
            "last", "save", "used", "using", "make", "made", "been", "more",
            "like", "does", "did", "done", "chat", "artifact", "artifacts",
            "reply", "continue",
        }
        return [x for x in raw if x not in stop]

    def _score_item(self, item: Dict[str, Any], tokens: List[str]) -> float:
        title = (item.get("title") or "").lower()
        kind = (item.get("kind") or "").lower()
        content = self._normalize_content(item.get("content")).lower()
        tags = " ".join(str(x).lower() for x in item.get("tags") or [])
        meta = self._normalize_content(item.get("meta")).lower()
        blob = f"{title}\n{kind}\n{tags}\n{content}\n{meta}"

        score = 0.0
        for token in tokens:
            if token in title:
                score += 8.0
            if token in tags:
                score += 5.0
            if token in kind:
                score += 2.0
            count = blob.count(token)
            if count > 0:
                score += min(count, 8) * 1.5

        if item.get("pinned"):
            score += 1.25

        updated_at = item.get("updated_at") or item.get("created_at") or ""
        if updated_at:
            score += 0.25

        return score

    def _truncate(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[: limit - 1].rstrip() + "…"

    def _make_snippet(self, item: Dict[str, Any], tokens: List[str], window: int = 1100) -> str:
        text = self._normalize_content(item.get("content"))
        lower = text.lower()

        positions = []
        for token in tokens:
            pos = lower.find(token)
            if pos >= 0:
                positions.append(pos)

        if not positions:
            return self._truncate(text, window)

        start = max(0, min(positions) - 180)
        end = min(len(text), start + window)
        snippet = text[start:end].strip()

        if start > 0:
            snippet = "… " + snippet
        if end < len(text):
            snippet = snippet + " …"
        return snippet

    def search_artifacts(
        self,
        query: str,
        *,
        session_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            return []

        tokens = self._tokenize(query)
        if not tokens:
            return []

        ranked: List[Dict[str, Any]] = []
        for item in self.list_artifacts(session_id=session_id):
            score = self._score_item(item, tokens)
            if score <= 0:
                continue
            ranked.append(
                {
                    "score": score,
                    "artifact": item,
                    "snippet": self._make_snippet(item, tokens),
                }
            )

        ranked.sort(
            key=lambda x: (
                x["score"],
                x["artifact"].get("updated_at") or x["artifact"].get("created_at") or "",
            ),
            reverse=True,
        )
        return ranked[: max(1, limit)]

    def retrieve_for_prompt(
        self,
        query: str,
        *,
        session_id: Optional[str] = None,
        limit: int = 3,
        max_chars_per_artifact: int = 1400,
    ) -> Dict[str, Any]:
        matches = self.search_artifacts(query, session_id=session_id, limit=limit)
        selected: List[Dict[str, Any]] = []

        for row in matches:
            artifact = deepcopy(row["artifact"])
            artifact["retrieval_score"] = row["score"]
            artifact["retrieval_snippet"] = self._truncate(
                row["snippet"],
                max_chars_per_artifact,
            )
            selected.append(artifact)

        joined_blocks: List[str] = []
        for idx, item in enumerate(selected, start=1):
            joined_blocks.append(
                "\n".join(
                    [
                        f"[artifact {idx}]",
                        f"title: {item.get('title', '')}",
                        f"kind: {item.get('kind', '')}",
                        f"updated_at: {item.get('updated_at', '')}",
                        f"score: {item.get('retrieval_score', 0)}",
                        "content:",
                        self._truncate(
                            item.get("retrieval_snippet") or item.get("content") or "",
                            max_chars_per_artifact,
                        ),
                    ]
                )
            )

        return {
            "items": selected,
            "context_text": "\n\n".join(joined_blocks).strip(),
        }