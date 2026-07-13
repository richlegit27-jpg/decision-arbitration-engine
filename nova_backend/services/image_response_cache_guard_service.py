import re
import json


_re = re.compile


def clean_prompt(value):
    raw = str(value or "").strip()

    raw = _re(
        r"^\s*Generated\s+image\s*(for)?\s*:",
        re.I,
    ).sub(
        "",
        raw,
    )

    raw = _re(
        r"^\s*Image\s*:",
        re.I,
    ).sub(
        "",
        raw,
    )

    raw = _re(
        r"^\s*(please\s+)?(generate|create|make|draw|render|produce)\s+(an?\s+)?(image|picture|photo|illustration|art|drawing)\s*",
        re.I,
    ).sub(
        "",
        raw,
    )

    raw = _re(
        r"^\s*(of|for)\s+",
        re.I,
    ).sub(
        "",
        raw,
    )

    raw = raw.strip(" .")

    return raw or "your image"


def is_image_response(data):
    if not isinstance(data, dict):
        return False

    assistant_message = data.get("assistant_message")
    saved_artifact = data.get("saved_artifact")

    if isinstance(assistant_message, dict):
        meta = assistant_message.get("meta")

        if assistant_message.get("image_url"):
            return True

        if isinstance(meta, dict):
            if meta.get("source") == "image_generation":
                return True

        attachments = assistant_message.get("attachments")

        if isinstance(attachments, list):
            for item in attachments:
                if not isinstance(item, dict):
                    continue

                if (
                    item.get("image_url")
                    or item.get("url")
                    or item.get("file_url")
                ):
                    mime = str(
                        item.get("mime_type")
                        or item.get("type")
                        or ""
                    ).lower()

                    filename = str(
                        item.get("filename")
                        or ""
                    ).lower()

                    if (
                        mime.startswith("image/")
                        or filename.endswith(
                            (
                                ".png",
                                ".jpg",
                                ".jpeg",
                                ".webp",
                                ".gif",
                            )
                        )
                    ):
                        return True

    if isinstance(saved_artifact, dict):

        if saved_artifact.get("image_url"):
            return True

        if str(
            saved_artifact.get("kind")
            or ""
        ).lower() == "image":
            return True

        if str(
            saved_artifact.get("type")
            or ""
        ).lower() == "image_generation":
            return True

    return False


def pick_prompt(data):
    assistant_message = (
        data.get("assistant_message")
        if isinstance(data, dict)
        else {}
    )

    saved_artifact = (
        data.get("saved_artifact")
        if isinstance(data, dict)
        else {}
    )

    session = (
        data.get("session")
        if isinstance(data, dict)
        else {}
    )

    candidates = []

    if isinstance(saved_artifact, dict):
        candidates.extend(
            [
                saved_artifact.get("summary"),
                saved_artifact.get("prompt"),
                saved_artifact.get("body"),
            ]
        )

        meta = saved_artifact.get("meta")

        if isinstance(meta, dict):
            candidates.append(
                meta.get("prompt")
            )

    if isinstance(session, dict):
        candidates.append(
            session.get("title")
        )

    if isinstance(assistant_message, dict):
        candidates.extend(
            [
                assistant_message.get("text"),
                assistant_message.get("content"),
            ]
        )

    for candidate in candidates:
        clean = clean_prompt(candidate)

        if clean and clean != "your image":
            return clean

    return "your image"


def fix_image_response(data):
    if not is_image_response(data):
        return data

    prompt = pick_prompt(data)

    clean_text = (
        "Generated image: "
        + prompt
    )

    assistant_message = data.get("assistant_message")

    if isinstance(assistant_message, dict):
        assistant_message["text"] = clean_text
        assistant_message["content"] = clean_text

        data["assistant_message"] = assistant_message

    saved_artifact = data.get("saved_artifact")

    if isinstance(saved_artifact, dict):
        saved_artifact["summary"] = clean_text

        viewer = saved_artifact.get("viewer")

        if isinstance(viewer, dict):
            viewer["summary"] = clean_text
            saved_artifact["viewer"] = viewer

        data["saved_artifact"] = saved_artifact

    session = data.get("session")

    if isinstance(session, dict):

        working_state = session.get("working_state")

        if isinstance(working_state, dict):
            working_state["last_assistant_message"] = clean_text
            session["working_state"] = working_state

        messages = session.get("messages")

        if isinstance(messages, list):

            for message in messages:

                if not isinstance(message, dict):
                    continue

                if str(
                    message.get("role")
                    or ""
                ).lower() == "assistant":

                    message_text = str(
                        message.get("text")
                        or message.get("content")
                        or ""
                    )

                    if "Generated image" in message_text:
                        message["text"] = clean_text
                        message["content"] = clean_text

        data["session"] = session

    return data