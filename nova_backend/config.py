from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"
ARTIFACTS_FILE = DATA_DIR / "nova_artifacts.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")
VISION_MODEL = os.getenv("NOVA_VISION_MODEL", "gpt-4.1-mini")
IMAGE_MODEL = os.getenv("NOVA_IMAGE_MODEL", "gpt-image-1.5")

WEB_TIMEOUT = int(os.getenv("NOVA_WEB_TIMEOUT", "12"))
RECON_TIMEOUT = int(os.getenv("NOVA_RECON_TIMEOUT", "10"))

IMAGE_SIZE = os.getenv("NOVA_IMAGE_SIZE", "1024x1024")
IMAGE_QUALITY = os.getenv("NOVA_IMAGE_QUALITY", "medium")

FLASK_HOST = os.getenv("NOVA_HOST", "127.0.0.1")
FLASK_PORT = int(os.getenv("NOVA_PORT", "5001"))
FLASK_DEBUG = str(os.getenv("NOVA_DEBUG", "true")).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

