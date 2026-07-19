class ChatResponseCleanupService:

    def clean_image_echo_text(self, value):
        value = str(value or "").strip()
        prefix = "Generated image for:"

        if not value.startswith(prefix):
            return value

        prompt = value[len(prefix):].strip()
        lowered = prompt.lower()

        cleanup_prefixes = [
            "/image",
            "generate an image of ",
            "generate image of ",
            "generate an image ",
            "generate image ",
            "create an image of ",
            "create image of ",
            "create an image ",
            "create image ",
            "make an image of ",
            "make image of ",
            "make an image ",
            "make image ",
            "draw ",
        ]

        if lowered == "/image":
            prompt = "image"
        else:
            for item in cleanup_prefixes:
                if lowered.startswith(item):
                    prompt = prompt[len(item):].strip() or "image"
                    break

        return f"Generated image for: {prompt}"

    def sync_attachment_text(self, result):
        try:
            if not isinstance(result, dict):
                return result

            assistant_message = result.get("assistant_message")

            if isinstance(assistant_message, dict):
                content = str(
                    assistant_message.get("content") or ""
                ).strip()

                if (
                    content.startswith("Attachment analysis:")
                    and "Attachment " in content
                    and " content:" in content
                ):
                    assistant_message["text"] = content
                    assistant_message["content"] = content
                    result["assistant_message"] = assistant_message

        except Exception:
            pass

        return result