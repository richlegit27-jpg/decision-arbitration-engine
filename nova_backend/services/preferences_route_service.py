import json
import os
import tempfile
from pathlib import Path

from flask import jsonify, render_template, request
from filelock import FileLock

from nova_backend.services.auth_context import get_current_user_id


class PreferencesRouteService:
    """Small account-scoped store for the preferences Nova currently supports."""

    DEFAULTS = {"theme": "dark", "enter_to_send": True}
    ALLOWED = {"theme", "enter_to_send"}

    def __init__(self, data_dir):
        self.path = Path(data_dir) / "user_preferences.json"

    def _read(self):
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise RuntimeError("User preferences store has an invalid shape.")
            return payload
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as exc:
            raise RuntimeError("User preferences could not be read safely.") from exc

    def _write(self, payload):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix="preferences-", suffix=".json", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as output:
                json.dump(payload, output, ensure_ascii=False, indent=2)
                output.write("\n")
                output.flush()
                os.fsync(output.fileno())
            os.replace(temp_name, self.path)
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass

    def install_routes(self, app):
        @app.get("/settings")
        def nova_settings_page():
            if not get_current_user_id():
                from flask import redirect
                return redirect("/login")
            return render_template("settings.html")

        @app.route("/api/settings", methods=["GET", "PATCH"])
        def nova_user_preferences_api():
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({"ok": False, "error": "Authentication required."}), 401
            lock = FileLock(str(self.path) + ".lock", timeout=5)
            try:
                with lock:
                    return self._handle_preferences(user_id)
            except RuntimeError:
                return jsonify({"ok": False, "error": "Preferences are temporarily unavailable."}), 500

        def _handle_preferences(user_id):
            payload = self._read()
            users = payload.get("users", {})
            if not isinstance(users, dict):
                raise RuntimeError("User preferences store has an invalid users map.")
            preferences = dict(self.DEFAULTS)
            saved = users.get(user_id)
            if isinstance(saved, dict):
                preferences.update({k: v for k, v in saved.items() if k in self.ALLOWED})
            if request.method == "PATCH":
                changes = request.get_json(silent=True)
                if not isinstance(changes, dict) or not changes:
                    return jsonify({"ok": False, "error": "Provide at least one preference."}), 400
                for key, value in changes.items():
                    if key not in self.ALLOWED:
                        return jsonify({"ok": False, "error": "Unsupported preference."}), 400
                    if key == "theme" and value not in {"dark", "light", "system"}:
                        return jsonify({"ok": False, "error": "Theme must be dark, light, or system."}), 400
                    if key == "enter_to_send" and not isinstance(value, bool):
                        return jsonify({"ok": False, "error": "Enter-to-send must be true or false."}), 400
                    preferences[key] = value
                users[user_id] = preferences
                payload["users"] = users
                self._write(payload)
            return jsonify({"ok": True, "preferences": preferences})
