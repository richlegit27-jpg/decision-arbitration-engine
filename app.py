from __future__ import annotations

import re
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
from services.attachment_service import AttachmentService
from services.chat_service import ChatService
from services.web_service import WebService

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

chat_service = ChatService()
attachment_service = AttachmentService()
web_service = WebService()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/uploads/<path:filename>")
def uploaded_file(filename: str):
    return send_from_directory(str(UPLOAD_DIR), filename)


@app.route("/api/upload", methods=["POST"])
def api_upload():
    if "files" not in request.files:
        return jsonify({"ok": False, "error": "No files part"}), 400

    files = request.files.getlist("files")
    uploaded = []

    for f in files:
        saved = attachment_service.save_file(f)
        if saved.get("ok"):
            saved["url"] = f"/uploads/{saved['id']}"
        uploaded.append(saved)

    ok_files = [x for x in uploaded if x.get("ok")]
    if not ok_files:
        first_error = uploaded[0].get("error", "Upload failed.") if uploaded else "Upload failed."
        return jsonify({"ok": False, "error": first_error, "files": uploaded}), 400

    return jsonify({"ok": True, "files": uploaded})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"ok": False, "error": "No JSON payload"}), 400

    content = (data.get("content") or "").strip()
    session_id = data.get("session_id")
    attachments = data.get("attachments") or []

    if not session_id:
        return jsonify({"ok": False, "error": "Missing session_id"}), 400

    generated_images = []

    if content.lower().startswith("/image "):
        prompt = content[7:].strip()
        result = chat_service.generate_image(prompt)
        if not result.get("ok"):
            return jsonify({"ok": False, "error": result.get("error", "Image generation failed.")}), 400

        generated_images.append(
            {
                "url": result["url"],
                "filename": result.get("filename") or "generated.png",
                "type": result.get("type") or "image/png",
                "prompt": result.get("prompt", ""),
            }
        )

        return jsonify(
            {
                "ok": True,
                "message": f'Generated image for: {prompt}',
                "web": "",
                "attachments_desc": [],
                "attachments": [],
                "generated_images": generated_images,
                "session": session_id,
            }
        )

    web_summary = ""
    urls = re.findall(r"https?://\S+", content)
    if urls:
        try:
            web_summary = web_service.fetch_summary(urls[0]) or ""
        except Exception as e:
            web_summary = f"Web fetch failed: {e}"

    attachment_descs = []
    attachment_items = []

    for attach_id in attachments:
        file_info = attachment_service.get_file_info(attach_id)
        if not file_info:
            continue

        file_url = f"/uploads/{file_info['id']}"
        attachment_items.append(
            {
                "id": file_info["id"],
                "filename": file_info["filename"],
                "type": file_info["type"],
                "url": file_url,
            }
        )

        if (file_info.get("type") or "").startswith("image/"):
            desc = chat_service.describe_image(file_info["path"])
            attachment_descs.append(desc)

    combined_parts = []
    if content:
        combined_parts.append(content)
    if web_summary:
        combined_parts.append(f"Web summary:\n{web_summary}")
    if attachment_descs:
        combined_parts.append("Attachment descriptions:\n" + "\n\n".join(attachment_descs))

    prompt_for_ai = "\n\n".join(part for part in combined_parts if part).strip()

    if prompt_for_ai:
        message = chat_service.send_message(prompt_for_ai, session_id)
    elif attachment_descs:
        message = "\n\n".join(attachment_descs)
    else:
        message = chat_service.send_message(content, session_id)

    return jsonify(
        {
            "ok": True,
            "message": message,
            "web": web_summary,
            "attachments_desc": attachment_descs,
            "attachments": attachment_items,
            "generated_images": generated_images,
            "session": session_id,
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8743, debug=True)