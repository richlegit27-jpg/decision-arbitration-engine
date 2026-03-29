from __future__ import annotations

import base64
import os
import uuid
from pathlib import Path

from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class ChatService:
    def __init__(self):
        self.sessions = {}

    def send_message(self, content: str, session_id: str) -> str:
        if session_id not in self.sessions:
            self.sessions[session_id] = []

        self.sessions[session_id].append({"role": "user", "content": content})

        if not content.strip():
            return "Hi there! What can I do for you?"

        try:
            response = client.chat.completions.create(
                model="gpt-5.4",
                messages=self.sessions[session_id],
                max_completion_tokens=500,
            )
            assistant_msg = (response.choices[0].message.content or "").strip()
            self.sessions[session_id].append({"role": "assistant", "content": assistant_msg})
            return assistant_msg or "No response."
        except Exception as e:
            return f"AI error: {str(e)}"

    def describe_image(self, image_path: str) -> str:
        if not os.path.exists(image_path):
            return "Image not found."

        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()

            b64 = base64.b64encode(image_bytes).decode("utf-8")
            ext = os.path.splitext(image_path)[1].lower()
            mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else f"image/{ext[1:]}"
            data_url = f"data:{mime};base64,{b64}"

            response = client.responses.create(
                model="gpt-4.1-mini",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": "Describe this image in clear English."},
                            {"type": "input_image", "image_url": data_url},
                        ],
                    }
                ],
            )

            return response.output_text or "No description available."
        except Exception as e:
            return f"Failed to describe image: {str(e)}"

    def generate_image(self, prompt: str) -> dict:
        prompt = (prompt or "").strip()
        if not prompt:
            return {"ok": False, "error": "Missing image prompt."}

        try:
            response = client.images.generate(
                model="gpt-image-1.5",
                prompt=prompt,
                size="1024x1024",
            )

            image_b64 = None
            image_url = None

            if getattr(response, "data", None):
                first = response.data[0]
                image_b64 = getattr(first, "b64_json", None)
                image_url = getattr(first, "url", None)

            if image_b64:
                raw = base64.b64decode(image_b64)
                filename = f"{uuid.uuid4().hex}_generated.png"
                output_path = UPLOAD_DIR / filename
                with open(output_path, "wb") as f:
                    f.write(raw)

                return {
                    "ok": True,
                    "filename": filename,
                    "path": str(output_path),
                    "url": f"/uploads/{filename}",
                    "type": "image/png",
                    "prompt": prompt,
                }

            if image_url:
                return {
                    "ok": True,
                    "filename": "",
                    "path": "",
                    "url": image_url,
                    "type": "image/png",
                    "prompt": prompt,
                }

            return {"ok": False, "error": "Image API returned no image data."}
        except Exception as e:
            return {"ok": False, "error": f"Image generation failed: {str(e)}"}