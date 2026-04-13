from __future__ import annotations

import base64
from pathlib import Path
from typing import List
from urllib.parse import urlparse, unquote

from openai import OpenAI

from nova_backend.config import UPLOADS_DIR
from nova_backend.models.session import new_message
from nova_backend.services.agent_service import AgentService
from nova_backend.services.artifact_service import ArtifactService
from nova_backend.services.autonomy_service import AutonomyService
from nova_backend.services.memory_ranker_service import MemoryRankerService
from nova_backend.services.memory_service import MemoryService
from nova_backend.services.recon_service import ReconService
from nova_backend.services.session_service import SessionService
from nova_backend.services.web_service import WebService


class ChatService:
    def __init__(
        self,
        session_service: SessionService,
        memory_service: MemoryService,
        artifact_service: ArtifactService,
        web_service: WebService,
        recon_service: ReconService,
    ):
        self.sessions = session_service
        self.memory = memory_service
        self.artifacts = artifact_service
        self.web = web_service
        self.recon = recon_service

        self.client = OpenAI()

        self.agent = AgentService()
        self.memory_ranker = MemoryRankerService()

        self.autonomy = AutonomyService(
            web_service=self.web,
            recon_service=self.recon,
            memory_service=self.memory,
            artifact_service=self.artifacts,
            max_steps=5,
            max_deep_js=5,
            max_follow_links=5,
        )

    def _is_image_generation_request(self, user_text: str) -> bool:
        text = str(user_text or "").strip().lower()
        if not text:
            return False

        triggers = (
            "/image",
            "generate an image",
            "generate image",
            "make an image",
            "create an image",
            "draw ",
            "draw me ",
        )
        return any(text.startswith(trigger) for trigger in triggers)

    def _image_prompt_from_text(self, user_text: str) -> str:
        text = str(user_text or "").strip()
        lowered = text.lower()

        if lowered.startswith("/image"):
            prompt = text[6:].strip()
            return prompt or "Generate an image."

        prefixes = (
            "generate an image of ",
            "generate an image ",
            "generate image of ",
            "generate image ",
            "make an image of ",
            "make an image ",
            "create an image of ",
            "create an image ",
            "draw me ",
            "draw ",
        )

        for prefix in prefixes:
            if lowered.startswith(prefix):
                prompt = text[len(prefix):].strip()
                return prompt or text

        return text

    def _generate_image_attachment(self, prompt: str) -> dict:
        response = self.client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024",
        )

        image_b64 = ""
        data_items = getattr(response, "data", None) or []
        if data_items:
            first = data_items[0]
            image_b64 = str(getattr(first, "b64_json", "") or "").strip()
            if not image_b64 and isinstance(first, dict):
                image_b64 = str(first.get("b64_json") or "").strip()

        if not image_b64:
            raise ValueError("Image generation returned no image data.")

        filename = f"generated_{__import__('uuid').uuid4().hex}.png"
        save_path = Path(UPLOADS_DIR) / filename
        save_path.write_bytes(base64.b64decode(image_b64))

        return {
            "id": f"att_{filename}",
            "filename": filename,
            "name": filename,
            "stored_name": filename,
            "file_url": f"/api/uploads/{filename}",
            "url": f"/api/uploads/{filename}",
            "mime_type": "image/png",
            "size": save_path.stat().st_size if save_path.exists() else 0,
            "status": "uploaded",
            "upload_error": "",
        }

    def _image_attachment_to_data_url(self, attachment: dict) -> str:
        mime_type = str(attachment.get("mime_type") or "image/jpeg").strip() or "image/jpeg"

        candidates: list[str] = []

        for key in ("stored_name", "filename", "name", "original_filename"):
            value = str(attachment.get(key) or "").strip()
            if value:
                candidates.append(value)

        for key in ("url", "file_url"):
            value = str(attachment.get(key) or "").strip()
            if not value:
                continue

            parsed = urlparse(value)
            path = parsed.path or value
            if "/api/uploads/" in path:
                candidates.append(path.split("/api/uploads/", 1)[1])
            elif "/uploads/" in path:
                candidates.append(path.split("/uploads/", 1)[1])
            else:
                candidates.append(Path(path).name)

        seen: set[str] = set()
        for raw_name in candidates:
            name = unquote(Path(raw_name).name)
            if not name or name in seen:
                continue
            seen.add(name)

            file_path = Path(UPLOADS_DIR) / name
            if file_path.exists() and file_path.is_file():
                encoded = base64.b64encode(file_path.read_bytes()).decode("utf-8")
                return f"data:{mime_type};base64,{encoded}"

        raise FileNotFoundError(
            "Could not locate uploaded image on disk for attachment keys: "
            + ", ".join(sorted(attachment.keys()))
        )

    def handle(
        self,
        user_text: str,
        session_id: str,
        attachments: List[dict] | None = None,
    ) -> dict:
        attachments = attachments or []

        session = self.sessions.get_by_id(session_id)
        if not session:
            session = self.sessions.create("New Chat")
            session_id = session["id"]

        if self._is_image_generation_request(user_text):
            prompt = self._image_prompt_from_text(user_text)
            generated_attachment = self._generate_image_attachment(prompt)

            user_msg = new_message("user", user_text, attachments=attachments)
            self.sessions.append_message(session_id, user_msg)

            assistant_text = f"Generated image for: {prompt}"
            assistant_msg = new_message(
                "assistant",
                assistant_text,
                attachments=[generated_attachment],
            )
            self.sessions.append_message(session_id, assistant_msg)

            refreshed_session = self.sessions.get_by_id(session_id) or session

            return {
                "ok": True,
                "session_id": session_id,
                "session": refreshed_session,
                "assistant_message": assistant_msg,
                "debug": {
                    "mode": "image_generation",
                    "prompt": prompt,
                    "generated_filename": generated_attachment.get("stored_name", ""),
                },
            }

        memory_context = self.memory.memory_context(
            query=user_text,
            mode="chat",
            session_id=session_id,
            limit=6,
        )

        ranked_memory_items = self.memory_ranker.rank_memories(
            user_text=user_text,
            memory_items=memory_context.get("items", []),
            max_items=6,
        )

        if ranked_memory_items:
            memory_context = {
                **memory_context,
                "items": ranked_memory_items,
            }

        decision = self.agent.decide(
            user_text=user_text,
            attachments=attachments,
            memory_context=memory_context,
        )

        if decision.get("use_memory"):
            memory_context = self.memory.memory_context(
                query=user_text,
                mode=str(decision.get("mode") or "chat"),
                session_id=session_id,
                limit=6,
            )

            ranked_memory_items = self.memory_ranker.rank_memories(
                user_text=user_text,
                memory_items=memory_context.get("items", []),
                max_items=6,
            )

            if ranked_memory_items:
                memory_context = {
                    **memory_context,
                    "items": ranked_memory_items,
                }

            decision = self.agent.decide(
                user_text=user_text,
                attachments=attachments,
                memory_context=memory_context,
            )

        decision["_memory_context"] = memory_context
        decision["_session"] = session
        decision["_attachments"] = attachments

        user_msg = new_message("user", user_text, attachments=attachments)
        self.sessions.append_message(session_id, user_msg)

        autonomy_result = self.autonomy.execute(
            user_text=user_text,
            decision=decision,
            session_id=session_id,
        )

        assistant_text = str(autonomy_result.get("response_text") or "").strip()

        image_attachments = [
            a for a in attachments
            if isinstance(a, dict) and str(a.get("mime_type") or "").startswith("image/")
        ]

        if image_attachments:
            try:
                content = [
                    {
                        "type": "input_text",
                        "text": user_text or "Describe this image.",
                    }
                ]

                used_images = 0
                for img in image_attachments:
                    data_url = self._image_attachment_to_data_url(img)
                    content.append(
                        {
                            "type": "input_image",
                            "image_url": data_url,
                        }
                    )
                    used_images += 1

                if used_images > 0:
                    response = self.client.responses.create(
                        model="gpt-4.1-mini",
                        input=[
                            {
                                "role": "user",
                                "content": content,
                            }
                        ],
                    )

                    vision_text = str(getattr(response, "output_text", "") or "").strip()
                    if vision_text:
                        assistant_text = vision_text
            except Exception as e:
                assistant_text = f"[Vision error] {e}"

        if not assistant_text:
            assistant_text = "Nova completed the task, but no response text was produced."

        assistant_msg = new_message("assistant", assistant_text)
        self.sessions.append_message(session_id, assistant_msg)

        refreshed_session = self.sessions.get_by_id(session_id)
        if refreshed_session:
            session = refreshed_session

        return {
            "ok": True,
            "session_id": session_id,
            "session": session,
            "assistant_message": assistant_msg,
            "debug": {
                "decision": decision,
                "memory_items_used": len(memory_context.get("items", [])),
                "attachments_count": len(attachments),
                "image_attachments_count": len(image_attachments),
                "used_vision": bool(image_attachments),
            },
        }