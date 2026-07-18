import json
import html

from pathlib import Path
from datetime import datetime, timezone
from flask import redirect

class HistoryRouteService:

    def __init__(
        self,
        base_dir,
    ):
        self.base_dir = Path(base_dir)

    def sessions_path(self):
        return (
            self.base_dir
            / "data"
            / "nova_sessions.json"
        )

    def open_session_bridge(
        self,
        session_id,
    ):
        sid = str(session_id or "").strip()

        data_path = self.sessions_path()

        try:
            payload = json.loads(
                data_path.read_text(
                    encoding="utf-8",
                )
            )
        except Exception:
            payload = {
                "sessions": []
            }

        def get_sessions(root):
            if isinstance(root, list):
                return root

            if isinstance(root, dict):
                for key in (
                    "sessions",
                    "items",
                    "data",
                ):
                    value = root.get(key)

                    if isinstance(value, list):
                        return value

            return []

        sessions = get_sessions(payload)

        found = False

        for session in sessions:
            if not isinstance(session, dict):
                continue

            current_id = str(
                session.get("id")
                or session.get("session_id")
                or session.get("sid")
                or session.get("uuid")
                or ""
            ).strip()

            if current_id == sid:
                found = True

                session["id"] = sid
                session["session_id"] = sid

                if not isinstance(
                    session.get("messages"),
                    list,
                ):
                    session["messages"] = []

                break

        if isinstance(payload, dict):
            payload["active_session_id"] = sid

        try:
            data_path.write_text(
                json.dumps(
                    payload,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass

        safe_sid = html.escape(sid)

        if not found:
            return f"""
<!doctype html>
<html>
<body style="background:#0f172a;color:white;font-family:Arial;padding:24px;">
<h1>Session not found</h1>
<p>{safe_sid}</p>
<p><a style="color:#c084fc;" href="/history">Back to history</a></p>
</body>
</html>
"""

        return f"""
<!doctype html>
<html>
<body style="background:#0f172a;color:white;font-family:Arial;padding:24px;">
<p>Opening session...</p>

<script>
const sid = "{safe_sid}";

try {{
    localStorage.setItem(
        "nova_active_session_id",
        sid
    );

    localStorage.setItem(
        "nova_session_id",
        sid
    );

    localStorage.setItem(
        "nova_desktop_active_session_id",
        sid
    );

    localStorage.setItem(
        "nova_current_session_id",
        sid
    );

    localStorage.setItem(
        "active_session_id",
        sid
    );

    localStorage.setItem(
        "session_id",
        sid
    );

    sessionStorage.setItem(
        "nova_active_session_id",
        sid
    );

    sessionStorage.setItem(
        "nova_session_id",
        sid
    );

    sessionStorage.setItem(
        "active_session_id",
        sid
    );

    sessionStorage.setItem(
        "session_id",
        sid
    );
}}
catch (_) {{}}

location.replace(
    "/app?session_id="
    + encodeURIComponent(sid)
    + "&force_session=1&bust="
    + Date.now()
);
</script>

</body>
</html>
"""

    def load_store(
        self,
    ):
        path = self.sessions_path()

        try:
            return json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            return {
                "sessions": []
            }

    def save_store(
        self,
        payload,
    ):
        self.sessions_path().write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def detail_page(
        self,
        session_id,
        history_service,
    ):
        import html

        sessions = history_service.load_sessions()
        session = None

        for s in sessions:
            if history_service.sid(s) == session_id:
                session = s
                break

        if not session:
            return f"""
<!doctype html>
<html>
<body style="font-family:Arial;background:#0f172a;color:white;padding:24px;">
  <h1>Session not found</h1>
  <p>{html.escape(session_id)}</p>
  <p><a style="color:#c084fc;" href="/history">Back to history</a></p>
</body>
</html>
"""
        title = history_service.title(session)
        sid = history_service.sid(session)
        messages = history_service.messages(session)

        rows = []

        for m in messages:
            role = history_service.msg_role(m)
            text = history_service.msg_text(m)

            rows.append(
                f"""
<div class="msg {html.escape(role.lower())}">
<div class="role">{html.escape(role)}</div>
<pre>{html.escape(text)}</pre>
</div>
"""
            )

        if not rows:
            rows.append(
                """
<div class="empty">
This is a new empty session. No messages yet.
</div>
"""
            )

        return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
</head>
<body>
<div class="wrap">
<h1>{html.escape(title)}</h1>
<div>{html.escape(sid)}</div>
<div>
{''.join(rows)}
</div>
</div>
</body>
</html>
"""

    def create_new_session(self):
        import uuid
        from datetime import datetime, timezone

        data_path = (
            self.base_dir
            / "data"
            / "nova_sessions.json"
        )

        try:
            payload = json.loads(
                data_path.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            payload = {
                "sessions": []
            }

        if isinstance(payload, list):
            root = {
                "sessions": payload
            }
            sessions = payload

        elif isinstance(payload, dict):
            root = payload
            sessions = None

            for key in (
                "sessions",
                "items",
                "data",
            ):
                if isinstance(
                    root.get(key),
                    list,
                ):
                    sessions = root[key]
                    break

            if sessions is None:
                sessions = []
                root["sessions"] = sessions

        else:
            root = {
                "sessions": []
            }
            sessions = root["sessions"]

        now = datetime.now(
            timezone.utc
        ).isoformat()

        sid = (
            "session_"
            + uuid.uuid4().hex
        )

        session = {
            "id": sid,
            "title": "New Chat",
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
            "messages": [],
            "meta": {},
            "pinned": False,
            "working_state": {
                "active_task": "",
                "checkpoint": "",
                "current_bug": "",
                "current_file": "",
                "last_success": "",
                "next_move": "",
                "updated_at": "",
            },
        }

        sessions.insert(
            0,
            session,
        )

        root["active_session_id"] = sid
        root["sessions"] = sessions

        data_path.write_text(
            json.dumps(
                root,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return f"""
<!doctype html>
<html>
<body>
<script>
localStorage.setItem("nova_active_session_id", "{sid}");
localStorage.setItem("nova_session_id", "{sid}");
localStorage.setItem("nova_desktop_active_session_id", "{sid}");
localStorage.setItem("nova_current_session_id", "{sid}");
location.href = "/app?session_id={sid}&bust=" + Date.now();
</script>
New session created.
</body>
</html>
"""

    def direct_send(
        self,
        session_id,
        request,
    ):
        import json
        from datetime import datetime, timezone

        sid = str(session_id or "").strip()
        text = str(
            request.form.get("text") or ""
        ).strip()

        if not sid or not text:
            return redirect(
                "/history/" + sid
            )

        data_path = (
            self.base_dir
            / "data"
            / "nova_sessions.json"
        )

        try:
            payload = json.loads(
                data_path.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            payload = {
                "sessions": []
            }

        def get_sessions(root):
            if isinstance(root, list):
                return root

            if isinstance(root, dict):
                for key in (
                    "sessions",
                    "items",
                    "data",
                ):
                    value = root.get(key)
                    if isinstance(value, list):
                        return value

            return []

        def get_sid(session):
            if not isinstance(session, dict):
                return ""

            return str(
                session.get("id")
                or session.get("session_id")
                or session.get("sid")
                or session.get("uuid")
                or ""
            ).strip()

        sessions = get_sessions(payload)
        target = None

        for session in sessions:
            if get_sid(session) == sid:
                target = session
                break

        if target is None:
            now = datetime.now(
                timezone.utc
            ).isoformat()

            target = {
                "id": sid,
                "session_id": sid,
                "title": "New Chat",
                "created_at": now,
                "updated_at": now,
                "message_count": 0,
                "messages": [],
                "meta": {},
                "pinned": False,
            }

            if isinstance(payload, dict):
                if not isinstance(
                    payload.get("sessions"),
                    list,
                ):
                    payload["sessions"] = []

                payload["sessions"].insert(
                    0,
                    target,
                )

            else:
                payload = {
                    "sessions": [target]
                }

        messages = target.get("messages")

        if not isinstance(messages, list):
            messages = []
            target["messages"] = messages

        now = datetime.now(
            timezone.utc
        ).isoformat()

        messages.append(
            {
                "role": "user",
                "content": text,
                "created_at": now,
            }
        )

        target["id"] = sid
        target["session_id"] = sid
        target["message_count"] = len(messages)
        target["updated_at"] = now

        if str(
            target.get("title") or ""
        ).strip().lower() in (
            "",
            "new chat",
            "untitled session",
        ):
            words = (
                text
                .replace("\n", " ")
                .split()
            )

            title = " ".join(
                words[:6]
            ).strip()

            target["title"] = (
                title[:60]
                if title
                else "New Chat"
            )

        if isinstance(payload, dict):
            payload["active_session_id"] = sid

        data_path.write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return redirect(
            "/history/" + sid
        )