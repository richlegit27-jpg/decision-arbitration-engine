from pathlib import Path
import base64
import mimetypes
import os

from nova_backend.services.model_gateway_service import (
    chat_completions_create,
)


class ImageVisionService:

    def handle(
        self,
        image_item,
        user_text,
    ):
        try:
            text = ""
            vision_used = False

            raw_url = str(
                image_item.get("url")
                or image_item.get("file_url")
                or ""
            ).strip()

            raw_name = str(
                image_item.get("filename")
                or image_item.get("original_filename")
                or image_item.get("name")
                or ""
            ).strip()

            filename = ""

            if "/api/uploads/" in raw_url:
                filename = (
                    raw_url.split("/api/uploads/", 1)[1]
                    .split("?", 1)[0]
                    .split("#", 1)[0]
                )
            elif raw_url:
                filename = Path(raw_url).name

            if not filename and raw_name:
                filename = Path(raw_name).name

            filename = filename.replace("\\", "/").split("/")[-1].strip()

            candidates = [
                Path.cwd() / "uploads" / filename,
                Path.cwd() / "static" / "uploads" / filename,
                Path(__file__).resolve().parents[2] / "uploads" / filename,
                Path(__file__).resolve().parents[2] / "static" / "uploads" / filename,
            ]

            image_path = None

            for candidate in candidates:
                try:
                    if candidate.exists() and candidate.is_file():
                        image_path = candidate
                        break
                except Exception:
                    continue

            if image_path is None:
                text = (
                    "VISION_DEBUG: image file not found. "
                    + "filename=" + str(filename)
                    + " candidates=" + " | ".join(str(c) for c in candidates)
                )
                vision_used = False

            else:
                try:
                    mime_type = mimetypes.guess_type(
                        str(image_path)
                    )[0] or "image/jpeg"

                    with open(image_path, "rb") as image_file:
                        encoded = base64.b64encode(
                            image_file.read()
                        ).decode("utf-8")

                    data_url = (
                        "data:"
                        + mime_type
                        + ";base64,"
                        + encoded
                    )

                    response = chat_completions_create(
                        model=os.getenv(
                            "NOVA_VISION_MODEL",
                            "gpt-4o-mini",
                        ),
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "You are Nova's image analysis module. "
                                    "Describe the attached image directly. "
                                    "Do not use web search. "
                                    "Do not mention unrelated news. "
                                    "If something cannot be identified, "
                                    "describe what is visible."
                                ),
                            },
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": user_text or "What is this image?",
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": data_url,
                                        },
                                    },
                                ],
                            },
                        ],
                        temperature=0.2,
                        max_tokens=500,
                    )

                    text = str(
                        response.choices[0].message.content or ""
                    ).strip()

                    if text:
                        vision_used = True
                    else:
                        text = (
                            "VISION_DEBUG: OpenAI vision returned empty text."
                        )

                except Exception as exc:
                    text = (
                        "VISION_DEBUG: OpenAI vision failed: "
                        + str(exc)
                    )
                    vision_used = False
            return {
                "text": text,
                "vision_used": vision_used,
            }

        except Exception as exc:
            print(
                "[NOVA_API_CHAT_IMAGE_VISION_GATE] failed:",
                exc,
            )

            return {
                "text": "VISION_DEBUG: vision failed.",
                "vision_used": False,
            }