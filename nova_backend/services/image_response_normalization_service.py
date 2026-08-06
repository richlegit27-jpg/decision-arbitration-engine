def normalize_image_response(result):
    if not isinstance(result, dict):
        return result

    assistant = result.get("assistant_message") or {}

    if not isinstance(assistant, dict):
        return result

    prompt = result.get("prompt") or assistant.get("text") or ""

    if isinstance(prompt, str) and prompt.startswith("generate image "):
        clean_prompt = prompt[len("generate image "):].strip()

        result["prompt"] = clean_prompt
        assistant["text"] = f"Generated image for: {clean_prompt}"
        assistant["content"] = assistant["text"]

        if "image_url" in assistant:
            result["image_url"] = assistant["image_url"]

        result["assistant_message"] = assistant

    return result