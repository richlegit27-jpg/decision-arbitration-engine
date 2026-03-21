from pathlib import Path
import base64
import hashlib
import hmac
import json
import os
import secrets

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ADMIN_SETTINGS_FILE = DATA_DIR / "admin_settings.json"


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def hash_password(password: str, salt: bytes | None = None, iterations: int = 200_000) -> dict:
    password_bytes = (password or "").encode("utf-8")
    salt = salt or secrets.token_bytes(16)

    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password_bytes,
        salt,
        iterations,
    )

    return {
        "algorithm": "pbkdf2_sha256",
        "iterations": iterations,
        "salt": base64.b64encode(salt).decode("utf-8"),
        "hash": base64.b64encode(derived).decode("utf-8"),
    }


def verify_password(password: str, stored: dict) -> bool:
    if not stored:
        return False

    try:
        algorithm = stored.get("algorithm", "")
        iterations = int(stored.get("iterations", 0))
        salt = base64.b64decode(stored.get("salt", ""))
        expected_hash = base64.b64decode(stored.get("hash", ""))
    except Exception:
        return False

    if algorithm != "pbkdf2_sha256":
        return False
    if iterations <= 0 or not salt or not expected_hash:
        return False

    candidate_hash = hashlib.pbkdf2_hmac(
        "sha256",
        (password or "").encode("utf-8"),
        salt,
        iterations,
    )

    return hmac.compare_digest(candidate_hash, expected_hash)


def load_admin_settings() -> dict:
    data = _read_json(ADMIN_SETTINGS_FILE)
    return data if isinstance(data, dict) else {}


def save_admin_settings(data: dict) -> None:
    _write_json(ADMIN_SETTINGS_FILE, data)


def get_password_record() -> dict:
    data = load_admin_settings()
    password_record = data.get("password_hash")
    if isinstance(password_record, dict) and password_record.get("hash"):
        return password_record
    return {}


def set_password(password: str) -> dict:
    password_record = hash_password(password)
    data = load_admin_settings()
    data["password_hash"] = password_record
    save_admin_settings(data)
    return password_record


def change_password(current_password: str, new_password: str) -> bool:
    current_record = get_password_record()
    if not verify_password(current_password, current_record):
        return False

    set_password(new_password)
    return True


def has_password_configured() -> bool:
    return bool(get_password_record().get("hash"))


def bootstrap_password_from_env() -> bool:
    env_password = (os.getenv("NOVA_APP_PASSWORD") or "").strip()

    if not env_password:
        return False

    if has_password_configured():
        return False

    set_password(env_password)
    return True