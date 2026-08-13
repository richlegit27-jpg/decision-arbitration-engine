from pathlib import Path
import json


def force_mobile_image_session_result(
    result,
    data,
    session_id,
    session_service,
    uploads_dir,
    sessions_file,
):
    try:
        if not isinstance(result, dict):
            return result

        request_payload_for_image = (
            data
            if isinstance(data, dict)
            else {}
        )

        target_session_id = str(
            request_payload_for_image.get("session_id")
            or request_payload_for_image.get("sessionId")
            or request_payload_for_image.get("active_session_id")
            or result.get("active_session_id")
            or result.get("session_id")
            or session_id
            or ""
        ).strip()

        assistant = result.get("assistant_message")

        if not isinstance(assistant, dict):
            assistant = {
                "role": "assistant",
                "text": str(result.get("text") or "").strip(),
            }

        image_url = str(
            result.get("image_url")
            or result.get("imageUrl")
            or assistant.get("image_url")
            or assistant.get("imageUrl")
            or ""
        ).strip()

        result_text = str(
            result.get("text")
            or assistant.get("text")
            or assistant.get("content")
            or ""
        ).strip()

        if (
            not image_url
            and result_text.startswith("Generated image for:")
        ):
            try:
                generated_files = sorted(
                    Path(uploads_dir).glob("generated_*.png"),
                    key=lambda item: item.stat().st_mtime,
                    reverse=True,
                )

                if generated_files:
                    image_url = f"/api/uploads/{generated_files[0].name}"

            except Exception:
                pass

        if image_url:
            image_filename = (
                image_url
                .split("/api/uploads/", 1)[-1]
                .split("?", 1)[0]
                .strip("/\\")
            )

            image_attachment = {
                "id": image_filename,
                "filename": image_filename,
                "stored_name": image_filename,
                "url": image_url,
                "file_url": image_url,
                "mime_type": "image/png",
                "type": "image/png",
            }

            assistant["role"] = "assistant"
            assistant["text"] = (
                result_text
                or "Generated image"
            )
            assistant["content"] = assistant["text"]
            assistant["image_url"] = image_url
            assistant["attachments"] = [
                image_attachment
            ]

            meta = assistant.get("meta")

            if not isinstance(meta, dict):
                meta = {}

            meta["source"] = "image_generation"
            meta["image_url"] = image_url
            meta["active_session_forced"] = True
            meta["forced_target_session_id"] = target_session_id

            assistant["meta"] = meta

            result["assistant_message"] = assistant
            result["text"] = assistant["text"]
            result["content"] = assistant["text"]
            result["image_url"] = image_url
            result["active_session_id"] = target_session_id
            result["session_id"] = target_session_id

            try:
                current_session = (
                    session_service.get_session(target_session_id)
                    or {}
                )

                messages = current_session.get("messages")

                if isinstance(messages, list):
                    for message in reversed(messages):
                        if (
                            isinstance(message, dict)
                            and str(
                                message.get("role") or ""
                            ).lower()
                            == "assistant"
                            and str(
                                message.get("text") or ""
                            ).startswith("Generated image for:")
                        ):
                            message["image_url"] = image_url
                            message["attachments"] = [
                                image_attachment
                            ]
                            message["meta"] = dict(meta)
                            break

                    current_session["messages"] = messages

            except Exception:
                pass

        return result

    except Exception:
        return result