from flask import Flask, request, jsonify, render_template
from services.chat_service import ChatService
from services.attachment_service import AttachmentService
from services.web_service import WebService
import re

app = Flask(__name__, template_folder="templates", static_folder="static")
chat_service = ChatService()
attachment_service = AttachmentService()
web_service = WebService()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/upload", methods=["POST"])
def api_upload():
    if 'files' not in request.files:
        return jsonify({"ok": False, "error":"No files part"}),400
    files = request.files.getlist('files')
    uploaded = [attachment_service.save_file(f) for f in files]
    return jsonify({"ok": True, "files": uploaded})

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    if not data: return jsonify({"ok": False, "error":"No JSON payload"}),400

    content = data.get("content","")
    session_id = data.get("session_id")
    attachments = data.get("attachments", [])
    if not session_id: return jsonify({"ok": False, "error":"Missing session_id"}),400

    web_summary = ""
    urls = re.findall(r'https?://\S+', content)
    if urls: web_summary = web_service.fetch_summary(urls[0])

    attachment_descs = []
    for attach_id in attachments:
        file_info = attachment_service.get_file_info(attach_id)
        if file_info and file_info.get("type","").startswith("image/"):
            desc = chat_service.describe_image(file_info["path"])
            attachment_descs.append(desc)

    # Combine attachments into chat content
    if attachment_descs:
        content = content + "\n" + "\n".join(attachment_descs)

    message = chat_service.send_message(content, session_id)
    return jsonify({
        "ok": True,
        "message": message,
        "web": web_summary,
        "attachments_desc": attachment_descs,
        "session": session_id
    })

if __name__=="__main__":
    app.run(host="127.0.0.1", port=8743, debug=True)