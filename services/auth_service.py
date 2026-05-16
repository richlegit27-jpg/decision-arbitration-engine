import hashlib
import hmac

from db import get_connection, init_db


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def normalize_username(username: str) -> str:
    return (username or "").strip().lower()


def validate_username(username: str) -> str | None:
    username = normalize_username(username)

    if len(username) < 3:
        return "Username must be at least 3 characters."

    if len(username) > 32:
        return "Username must be 32 characters or less."

    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_-")
    if any(character not in allowed for character in username):
        return "Username can only use letters, numbers, underscore, or dash."

    return None


def validate_password(password: str) -> str | None:
    password = (password or "").strip()

    if len(password) < 6:
        return "Password must be at least 6 characters."

    if len(password) > 128:
        return "Password is too long."

    return None


def create_user(username: str, password: str) -> tuple[bool, str]:
    init_db()

    username = normalize_username(username)
    username_error = validate_username(username)
    if username_error:
        return False, username_error

    password_error = validate_password(password)
    if password_error:
        return False, password_error

    password_hash = hash_password(password)

    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO users (username, password_hash)
                VALUES (?, ?)
                """,
                (username, password_hash),
            )
            connection.commit()
    except Exception:
        return False, "That username already exists."

    return True, "Account created."


def authenticate_user(username: str, password: str) -> bool:
    init_db()

    username = normalize_username(username)
    password_hash = hash_password(password)

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT password_hash
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

    if not row:
        return False

    stored_hash = row["password_hash"]
    return hmac.compare_digest(stored_hash, password_hash)


def user_exists(username: str) -> bool:
    init_db()

    username = normalize_username(username)

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

    return row is not None


def get_user_by_username(username: str):
    init_db()

    username = normalize_username(username)

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, username, created_at
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

    return row