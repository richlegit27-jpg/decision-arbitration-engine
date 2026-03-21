from __future__ import annotations

import os
from pathlib import Path

CONFIG_FILE = Path(__file__).resolve()
CORE_DIR = CONFIG_FILE.parent
BACKEND_DIR = CORE_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent

STATIC_DIR = BACKEND_DIR / "static"
if not STATIC_DIR.exists():
    STATIC_DIR = PROJECT_DIR / "static"

TEMPLATES_DIR = BACKEND_DIR / "templates"
if not TEMPLATES_DIR.exists():
    TEMPLATES_DIR = PROJECT_DIR / "templates"

UPLOADS_DIR = BACKEND_DIR / "uploads"
if not UPLOADS_DIR.exists():
    UPLOADS_DIR = PROJECT_DIR / "uploads"

DATA_DIR = BACKEND_DIR / "data"
if not DATA_DIR.exists():
    DATA_DIR = PROJECT_DIR / "data"

MEMORY_DIR = DATA_DIR / "memory"
CHATS_DIR = DATA_DIR / "chats"
FILES_DIR = DATA_DIR / "files"

APP_TITLE = "Nova"
APP_VERSION = "1.0"
API_PREFIX = "/api"

ALLOW_ORIGINS = ["*"]
ALLOW_METHODS = ["*"]
ALLOW_HEADERS = ["*"]

DEFAULT_MODEL = os.getenv("NOVA_DEFAULT_MODEL", "gpt-4o-mini")

AVAILABLE_MODELS = [
    "gpt-4o-mini",
    "gpt-4.1-mini",
    "gpt-4.1",
]

SYSTEM_PROMPT = "You are Nova, a helpful assistant. Be direct, clear, and useful."

MAX_UPLOAD_SIZE_MB = int(os.getenv("NOVA_MAX_UPLOAD_SIZE_MB", "25"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

ALLOWED_TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".json",
    ".csv",
    ".py",
    ".js",
    ".html",
    ".css",
    ".xml",
    ".yaml",
    ".yml",
    ".log",
}

ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".docx",
}

ALLOWED_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
}

ALLOWED_UPLOAD_EXTENSIONS = (
    ALLOWED_TEXT_EXTENSIONS
    | ALLOWED_DOCUMENT_EXTENSIONS
    | ALLOWED_IMAGE_EXTENSIONS
)

def ensure_runtime_dirs() -> None:
    for path in (
        STATIC_DIR,
        TEMPLATES_DIR,
        UPLOADS_DIR,
        DATA_DIR,
        MEMORY_DIR,
        CHATS_DIR,
        FILES_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)