import os
import uuid
import webbrowser
from flask import Flask, jsonify, send_from_directory
from threading import Thread

BASE_DIR = os.getcwd()
DEMO_DIR = os.path.join(BASE_DIR, "static", "demo")
os.makedirs(DEMO_DIR, exist_ok=True)

# -----------------------------
# Create placeholder demo files
# -----------------------------
image_path = os.path.join(DEMO_DIR, "image1.png")
pdf_path = os.path.join(DEMO_DIR, "sample.pdf")
video_path = os.path.join(DEMO_DIR, "video.mp4")

if not os.path.exists(image_path):
    with open(image_path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")

if not os.path.exists(pdf_path):
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4\n%Demo PDF\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")

if not os.path.exists(video_path):
    with open(video_path, "wb") as f:
        f.write(b"\x00\x00\x00\x18ftypmp42")

# -----------------------------
# Flask app
# -----------------------------
app = Flask(__name__, static_folder="static", template_folder="templates")

ARTIFACTS = [
    {"id": str(uuid.uuid4()), "title": "Demo Image", "type": "image/png", "url": "/static/demo/image1.png", "pinned": True},
    {"id": str(uuid.uuid4()), "title": "Demo PDF", "type": "application/pdf", "url": "/static/demo/sample.pdf", "pinned": False}
]
MEDIA = [
    {"id": str(uuid.uuid4()), "title": "Demo Video", "type": "video/mp4", "url": "/static/demo/video.mp4", "pinned": False}
]

@app.route("/")
def index():
    return send_from_directory(app.template_folder, "index.html")

@app.route("/api/artifacts")
def get_artifacts(): return jsonify(ARTIFACTS)

@app.route("/api/media")
def get_media(): return jsonify(MEDIA)

@app.route("/api/artifacts/delete/<id>", methods=["POST"])
def delete_artifact(id):
    global ARTIFACTS
    ARTIFACTS = [a for a in ARTIFACTS if a["id"] != id]
    return jsonify({"ok": True})

@app.route("/api/media/delete/<id>", methods=["POST"])
def delete_media(id):
    global MEDIA
    MEDIA = [m for m in MEDIA if m["id"] != id]
    return jsonify({"ok": True})

@app.route("/api/artifacts/toggle-pin/<id>", methods=["POST"])
def toggle_pin(id):
    for a in ARTIFACTS:
        if a["id"] == id:
            a["pinned"] = not a["pinned"]
    for m in MEDIA:
        if m["id"] == id:
            m["pinned"] = not m["pinned"]
    return jsonify({"ok": True})

# -----------------------------
# Open browser automatically
# -----------------------------
def open_browser():
    webbrowser.open("http://127.0.0.1:8743/")

Thread(target=open_browser).start()

# -----------------------------
# Run Flask server
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True, port=8743)