import re


class AttachmentSummaryService:

    def plain_attachment_text_summary(
        self,
        file_name,
        file_path,
        content,
        user_text="",
    ):
        name = str(file_name or "attachment").strip() or "attachment"
        path = str(file_path or "").strip()
        raw = str(content or "")

        cleaned = raw.replace("\r\n", "\n").replace("\r", "\n")
        cleaned = re.sub(
            r"(?is)\[CURRENT UPLOADED TEXT ATTACHMENTS\]",
            "",
            cleaned,
        )
        cleaned = re.sub(
            r"(?is)\[/CURRENT UPLOADED TEXT ATTACHMENTS\]",
            "",
            cleaned,
        )
        cleaned = re.sub(
            r"(?im)^Attachment file content:\s*.*$",
            "",
            cleaned,
        )
        cleaned = re.sub(
            r"(?im)^Path:\s*.*$",
            "",
            cleaned,
        )
        cleaned = re.sub(
            r"(?im)^Size:\s*.*$",
            "",
            cleaned,
        )
        cleaned = re.sub(
            r"(?im)^Content:\s*$",
            "",
            cleaned,
        )
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

        lines = []

        for line in cleaned.splitlines():
            item = line.strip()

            if not item:
                continue

            if item.lower() in {
                "summarize this file",
                "summarise this file",
                "summarize this",
                "summarise this",
            }:
                continue

            compact = re.sub(r"\s+", "", item)

            if len(compact) <= 2:
                continue

            if re.fullmatch(r"[\W_]+", compact):
                continue

            lines.append(item)

        sample = "\n".join(lines[:120]).strip()
        lower_sample = sample.lower()

        if not sample:
            sample = cleaned[:2000].strip()

        key_points = []

        if (
            "import " in lower_sample
            or "def " in lower_sample
            or "class " in lower_sample
        ):
            key_points.append(
                "This appears to be a source code file."
            )

            if "from __future__ import annotations" in lower_sample:
                key_points.append(
                    "It uses future annotations, so it is likely modern Python code."
                )

            if "def " in lower_sample:
                key_points.append(
                    "It defines functions that likely contain the main behavior."
                )

            if "class " in lower_sample:
                key_points.append(
                    "It defines classes, so part of the file is object-oriented."
                )

            if "flask" in lower_sample or "@app.route" in lower_sample:
                key_points.append(
                    "It appears connected to a Flask/backend route system."
                )

        else:
            key_points.append(
                "The file contains readable text content."
            )

            sentences = re.split(
                r"(?<=[.!?])\s+",
                sample,
            )

            for sentence in sentences:
                sentence = sentence.strip()

                if len(sentence) >= 40:
                    key_points.append(sentence[:220])

                if len(key_points) >= 5:
                    break

        if len(key_points) < 2 and sample:
            for line in lines[:5]:
                key_points.append(line[:220])

                if len(key_points) >= 5:
                    break

        preview = sample[:1200].strip()

        body = []

        body.append(
            f"Summary of {name}:"
        )

        body.append("")

        body.append("Key points:")

        for index, point in enumerate(
            key_points[:6],
            1,
        ):
            body.append(
                f"{index}. {point}"
            )

        body.append("")
        body.append("Preview:")
        body.append(preview)

        if path:
            body.append("")
            body.append(
                f"File path: {path}"
            )

        return "\n".join(body).strip()