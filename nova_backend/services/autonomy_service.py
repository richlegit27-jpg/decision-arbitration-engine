from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from nova_backend.services.model_gateway_service import (
    responses_create,
)

from nova_backend.services.prompt_builder_service import PromptBuilderService


class AutonomyService:
    def __init__(
        self,
        web_service=None,
        recon_service=None,
        memory_service=None,
        artifact_service=None,
        max_steps: int = 5,
        max_deep_js: int = 5,
        max_follow_links: int = 5,
    ):
        self.web = web_service
        self.recon = recon_service
        self.memory = memory_service
        self.artifacts = artifact_service
        self.max_steps = int(max_steps or 5)
        self.max_deep_js = int(max_deep_js or 5)
        self.max_follow_links = int(max_follow_links or 5)
        self.prompt_builder = PromptBuilderService()

        self.model = os.getenv("OPENAI_MODEL", "gpt-5.4")
        

    def _text(self, value: Any) -> str:
        return str(value or "").strip()

    def _tool_plan(self, decision: dict) -> List[str]:
        mode = self._text((decision or {}).get("mode")) or "chat"

        if mode == "web":
            return [
                "Inspect URL or web intent",
                "Fetch target page through web service",
                "Summarize important findings",
            ]
        if mode == "recon":
            return [
                "Inspect target and recon intent",
                "Run recon workflow",
                "Summarize findings and next moves",
            ]
        if mode == "coding":
            return [
                "Read the user's goal carefully",
                "Use relevant memory and project context",
                "Return concrete implementation guidance",
            ]
        if mode == "planning":
            return [
                "Use project context and constraints",
                "Produce a clean sequence of next moves",
                "Keep the plan actionable",
            ]

        return [
            "Use the selected route",
            "Apply relevant memory and preferences",
            "Return the strongest direct answer",
        ]

    def _extract_response_text(self, response: Any) -> str:
        text = self._text(getattr(response, "output_text", ""))
        if text:
            return text

        chunks: List[str] = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                if hasattr(content, "text") and self._text(content.text):
                    chunks.append(self._text(content.text))
                    continue

                text_value = getattr(content, "text", None)
                if isinstance(text_value, dict):
                    maybe = self._text(text_value.get("value"))
                    if maybe:
                        chunks.append(maybe)

        return "\n".join(chunk for chunk in chunks if chunk).strip()

    def _call_model(self, *, system_prompt: str, user_prompt: str) -> str:
        try:
            response = responses_create(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            text = self._extract_response_text(response)
            if text:
                return text
            return ""
        except Exception as exc:
            return f"[MODEL ERROR] {exc}"

    def _maybe_save_artifact(
        self,
        *,
        decision: dict,
        response_text: str,
        session_id: str,
        meta: Optional[dict] = None,
    ) -> Any:
        if not self.artifacts or not decision.get("save_artifact"):
            return None

        text = self._text(response_text)

        if not text or len(text) < 40:
            return None

        if text.lower() in {"ok", "done", "hello", "hi"}:
            return None

        if "current model response path is still being tuned" in text:
            return None

        try:
            mode = self._text(decision.get("mode")) or "chat"

            title_map = {
                "coding": "Implementation",
                "planning": "Plan",
                "analysis": "Analysis",
                "web": "Web Result",
                "recon": "Recon Result",
                "image": "Image Result",
            }

            title = title_map.get(mode, f"{mode.title()} Result")

            return self.artifacts.add(
                session_id=session_id,
                kind=mode,
                title=title,
                body=text,
                meta={
                    **(meta or {}),
                    "auto_saved": True,
                    "mode": mode,
                },
            )
        except Exception:
            return None

    def execute(
        self,
        user_text: str,
        decision: Dict[str, Any],
        session_id: str = "",
    ) -> dict:
        decision = decision or {}
        mode = self._text(decision.get("mode")) or "chat"
        response_style = self._text(decision.get("response_style")) or "direct"

        memory_context = (
            decision.get("_memory_context")
            if isinstance(decision.get("_memory_context"), dict)
            else {}
        )

        session = (
            decision.get("_session")
            if isinstance(decision.get("_session"), dict)
            else {}
        )

        attachments = (
            decision.get("_attachments")
            if isinstance(decision.get("_attachments"), list)
            else []
        )

        plan = self._tool_plan(decision)

        memory_items = memory_context.get("items", [])
        session_messages = session.get("messages", [])

        prompt_packet = self.prompt_builder.build_prompt(
            user_text=user_text,
            messages=session_messages,
            memory_items=memory_items,
            mode=mode,
            response_style=response_style,
        )

        response_text = self._call_model(
            system_prompt=prompt_packet.get("system_prompt", ""),
            user_prompt=prompt_packet.get("user_prompt", ""),
        )

        clean_user = self._text(user_text)
        if not response_text or self._text(response_text).lower() == clean_user.lower():
            response_text = (
                "I got your message. The current model response path is still being tuned, "
                "but chat transport is now working."
            )

        saved_artifact = self._maybe_save_artifact(
            decision=decision,
            response_text=response_text,
            session_id=session_id,
            meta={
                "mode": mode,
                "response_style": response_style,
                "memory_used": prompt_packet.get("memory_used"),
                "memory_items_used": prompt_packet.get("memory_items_used"),
                "locked_memory_used": prompt_packet.get("locked_memory_used", 0),
            },
        )

        return {
            "response_text": response_text,
            "plan": plan,
            "transcript": [
                {
                    "step": "prompt_build",
                    "mode": mode,
                    "response_style": response_style,
                    "memory_used": bool(prompt_packet.get("memory_used")),
                    "memory_items_used": int(prompt_packet.get("memory_items_used", 0)),
                    "locked_memory_used": int(prompt_packet.get("locked_memory_used", 0)),
                },
                {
                    "step": "model_response",
                    "model": self.model,
                },
            ],
            "expanded_js": [],
            "followed_links": [],
            "saved_artifact": saved_artifact,
            "prompt_packet": prompt_packet,
        }

