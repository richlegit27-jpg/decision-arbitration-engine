import os
import uuid
import shutil
import requests

BASE_URL = "http://127.0.0.1:8743"
DEMO_DIR = os.path.join(os.getcwd(), "static", "demo")
os.makedirs(DEMO_DIR, exist_ok=True)

# -----------------------------
# Step 1: Create placeholder files if missing
# -----------------------------
image_path = os.path.join(DEMO_DIR, "image1.png")
pdf_path = os.path.join(DEMO_DIR, "sample.pdf")
video_path = os.path.join(DEMO_DIR, "video.mp4")

if not os.path.exists(image_path):
    with open(image_path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")  # minimal PNG

if not os.path.exists(pdf_path):
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4\n%Demo PDF\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")  # minimal PDF

if not os.path.exists(video_path):
    with open(video_path, "wb") as f:
        f.write(b"\x00\x00\x00\x18ftypmp42")  # minimal MP4 header

print("[Helper] Demo files ensured in static/demo/")

# -----------------------------
# Step 2: Upload assets via API
# -----------------------------
upload_url = f"{BASE_URL}/api/media/upload"

for filepath in [image_path, pdf_path, video_path]:
    with open(filepath, "rb") as f:
        files = {"file": (os.path.basename(filepath), f)}
        try:
            r = requests.post(upload_url, files=files)
            if r.status_code == 200:
                print(f"[Helper] Uploaded {os.path.basename(filepath)}")
            else:
                print(f"[Helper] Failed to upload {os.path.basename(filepath)}: {r.status_code}")
        except Exception as e:
            print(f"[Helper] Error uploading {os.path.basename(filepath)}: {e}")

# -----------------------------
# Step 3: Pin first artifact
# -----------------------------
pin_url = f"{BASE_URL}/api/artifacts"
try:
    r = requests.get(pin_url)
    artifacts = r.json()
    if artifacts:
        first_id = artifacts[0]["id"]
        toggle_pin_url = f"{BASE_URL}/api/artifacts/toggle-pin/{first_id}"
        requests.post(toggle_pin_url)
        print(f"[Helper] Pinned first artifact {first_id}")
except Exception as e:
    print(f"[Helper] Error pinning artifact: {e}")

print("[Helper] Phase 4 endgame helper finished. Check browser for grid + lightbox + hover effects!")