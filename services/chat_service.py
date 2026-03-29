import os
import base64
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ChatService:
    def __init__(self):
        # Session chat history
        self.sessions = {}

    def send_message(self, content: str, session_id: str) -> str:
        """
        Sends a message through GPT, maintains session history.
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = []

        self.sessions[session_id].append({"role": "user", "content": content})

        if not content.strip():
            return "Hi there! What can I do for you?"

        try:
            response = client.chat.completions.create(
                model="gpt-5.4",
                messages=self.sessions[session_id],
                max_completion_tokens=500
            )
            assistant_msg = response.choices[0].message.content.strip()
            self.sessions[session_id].append({"role": "assistant", "content": assistant_msg})
            return assistant_msg
        except Exception as e:
            return f"AI error: {str(e)}"

    def describe_image(self, image_path: str) -> str:
        """
        Describes an uploaded image using a vision-capable model.
        Uses a data URL (base64) for proper JSON serialization.
        """
        if not os.path.exists(image_path):
            return "Image not found."

        try:
            # Read local file and encode as base64
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            b64 = base64.b64encode(image_bytes).decode("utf-8")

            # Determine MIME type
            ext = os.path.splitext(image_path)[1].lower()
            mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else f"image/{ext[1:]}"
            data_url = f"data:{mime};base64,{b64}"

            # Send to vision-capable model using image_url
            response = client.responses.create(
                model="gpt-4.1-mini",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": "Describe this image in clear English."},
                            {"type": "input_image", "image_url": data_url}  # Correct
                        ]
                    }
                ]
            )

            return response.output_text or "No description available."

        except Exception as e:
            return f"Failed to describe image: {str(e)}"