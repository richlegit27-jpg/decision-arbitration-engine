



def _nova_runtime_handle_image_generation(
    self,
    prompt: str,
    session_id: str = "",
    parent_artifact_id: str = "",
    source_type: str = "generated",
) -> dict:
    # IMAGE_GENERATION_PROMPT_ATTACHMENT_GUARD_LOCK
    try:
        _nova_image_prompt_text = str(prompt or "").lower()
    except Exception:
        _nova_image_prompt_text = ""

    if (
        "attachment " in _nova_image_prompt_text
        or "attachment images_" in _nova_image_prompt_text
        or "binary attachment skipped" in _nova_image_prompt_text
        or "session attachment memory" in _nova_image_prompt_text
        or "/api/uploads/" in _nova_image_prompt_text
    ):
        return {
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "text": "I received the attachment, but I should analyze it instead of generating an image from it.",
            },
            "skip_cleanup": True,
            "skip_post_processing": True,
            "skip_rewrite": True,
        }

    # RUNTIME_IMAGE_HIT_DIRECT_ATTACHMENT_GUARD_LOCK
    _nova_prompt_guard_text = str(prompt or "").lower()

    if (
        "attachment " in _nova_prompt_guard_text
        or "binary attachment skipped" in _nova_prompt_guard_text
        or "session attachment memory" in _nova_prompt_guard_text
        or "/api/uploads/" in _nova_prompt_guard_text
    ):
        return {
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "text": "I received the attachment. I should analyze the uploaded file instead of generating an image from it.",
            },
            "skip_cleanup": True,
            "skip_post_processing": True,
            "skip_rewrite": True,
        }


    saved_artifact = None

    regen_commands = {
        "regen",
        "regenerate",
        "redo image",
        "make another",
        "another image",
    }

    try:
        from nova_backend.services.model_gateway_service import (
            images_generate_create,
        )

        result = images_generate_create(
            model=self.image_model,
            prompt=prompt,
            size=self.image_size,
        )

        first = result.data[0] if getattr(result, "data", None) else None
        image_b64 = getattr(first, "b64_json", None) if first else None
        remote_image_url = getattr(first, "url", None) if first else None

        # NOVA_RAILWAY_IMAGE_SAVE_BYTES_20260702
        # Always turn OpenAI image output into a real local uploads file before returning /api/uploads/...
        # Railway was receiving valid image metadata but no verified PNG existed at /app/uploads.
        from pathlib import Path as _NovaImagePath
        import urllib.request as _nova_urllib_request

        image_bytes = b""

        if image_b64:
            image_bytes = base64.b64decode(image_b64)
        elif remote_image_url:
            request = _nova_urllib_request.Request(
                remote_image_url,
                headers={"User-Agent": "Nova/1.0"},
            )
            with _nova_urllib_request.urlopen(request, timeout=45) as response:
                image_bytes = response.read()
        else:
            raise ValueError("Image API returned no image data")

        if not image_bytes:
            raise ValueError("Image API returned empty image bytes")

        filename = f"generated_{uuid.uuid4().hex}.png"
        uploads_dir = _NovaImagePath(self.uploads_dir)

        # NOVA_RAILWAY_UPLOAD_DIR_FIX_20260702
        # Railway/Linux must not use the old Windows dev path C:\Users\Owner\nova\uploads.
        uploads_dir_text = str(uploads_dir)
        if ":" in uploads_dir_text or "\\" in uploads_dir_text:
            uploads_dir = _NovaImagePath.cwd() / "uploads"

        uploads_dir.mkdir(parents=True, exist_ok=True)
        filepath = uploads_dir / filename

        filepath.write_bytes(image_bytes)

        print("[NOVA_RAILWAY_UPLOAD_DIR_FIX_20260702] uploads_dir", str(uploads_dir))

        if not filepath.exists() or filepath.stat().st_size <= 0:
            raise ValueError(f"Generated image file was not saved: {filepath}")

        try:
            owner_id = get_current_user_id()
            if owner_id:
                UploadOwnershipService().register_upload(
                    filename,
                    owner_id,
                )
        except Exception:
            pass

        print(
            "[NOVA_RAILWAY_IMAGE_SAVE_BYTES_20260702] saved",
            str(filepath),
            filepath.stat().st_size,
        )

        image_url = f"/api/uploads/{filename}"

        if self._safe_str(prompt).strip().lower() not in regen_commands:
            self._set_session_meta(
                session_id,
                "last_image_prompt",
                prompt,
            )

        self._set_session_meta(
            session_id,
            "last_image_url",
            image_url,
        )

        try:
            saved_artifact = self.artifacts.save_artifact(
                {
                    "kind": "image_generation",
                    "type": "image_generation",
                    "title": "Generated image",
                    "body": prompt,
                    "summary": f"Generated image: {prompt}",
                    "preview": image_url,
                    "session_id": session_id,
                    "source": source_type,
                    "image_url": image_url,
                    "prompt": prompt,
                    "revised_prompt": "",
                    "parent_id": parent_artifact_id or None,
                    "meta": {
                        "image_url": image_url,
                        "prompt": prompt,
                        "generation_mode": "text_to_image",
                        "source_type": source_type,
                    },
                }
            )

            exec_debug("IMAGE ARTIFACT RESULT:", saved_artifact)

        except Exception as e:
            exec_debug("IMAGE ARTIFACT SAVE FAILED:", e)
            exec_debug("IMAGE ARTIFACT RESULT:", saved_artifact)

        return {
            "ok": True,
            "skip_rewrite": True,
            "skip_cleanup": True,
            "skip_post_processing": True,
            "assistant_message": {
                "role": "assistant",
                "text": f"Generated image: {prompt}",
                "content": f"Generated image: {prompt}",
                "image_url": image_url,
            },
            "image_url": image_url,
            "prompt": prompt,
            "revised_prompt": "",
            "saved_artifact": saved_artifact,
            "session": self._get_session_payload(session_id),
        }

    except Exception as e:
        exec_debug("IMAGE GENERATION FAILED:", e)

        return {
            "ok": False,
            "skip_rewrite": True,
            "skip_cleanup": True,
            "skip_post_processing": True,
            "assistant_message": {
                "role": "assistant",
                "text": f"Image generation failed: {e}",
            },
            "error": str(e),
            "image_url": "",
            "prompt": prompt,
            "revised_prompt": "",
            "saved_artifact": saved_artifact,
            "session": self._get_session_payload(session_id),
        }


def install_image_generation_runtime(ChatService):
    ChatService._handle_image_generation = (
        _nova_runtime_handle_image_generation
    )