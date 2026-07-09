from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8", errors="replace")

marker = "NOVA_RICHARD_LEGACY_SESSION_OWNER_BRIDGE_20260703"

if marker in text:
    print("legacy owner bridge already installed")
    raise SystemExit(0)

needle = '''        if request.path != "/api/sessions" or request.method != "GET":
            return None

'''

insert = '''        if request.path != "/api/sessions" or request.method != "GET":
            return None

        # NOVA_RICHARD_LEGACY_SESSION_OWNER_BRIDGE_20260703
        # Production/local-auth migration bridge:
        # richard is the current real owner, but older sessions were saved as joe
        # or with no owner. Build /api/sessions from the raw store before the
        # older slim route can collapse visibility to one empty auth session.
        try:
            import json as _nova_legacy_json
            from pathlib import Path as _NovaLegacyPath
            from flask import session as _nova_legacy_flask_session

            base_dir = _NovaLegacyPath(__file__).resolve().parent
            sessions_path = base_dir / "data" / "nova_sessions.json"
            users_path = base_dir / "data" / "nova_auth_users.json"

            current_uid = str(_nova_legacy_flask_session.get("nova_user_id") or "").strip()
            current_username = ""

            if current_uid and users_path.exists():
                users_data = _nova_legacy_json.loads(users_path.read_text(encoding="utf-8"))
                for user_item in users_data.get("users", []):
                    if isinstance(user_item, dict) and str(user_item.get("id") or "") == current_uid:
                        current_username = str(user_item.get("username") or "").strip().lower()
                        break

            if current_username == "richard" and sessions_path.exists():
                store = _nova_legacy_json.loads(sessions_path.read_text(encoding="utf-8"))

                if isinstance(store, dict):
                    raw_store_sessions = store.get("sessions")
                    if not isinstance(raw_store_sessions, list):
                        raw_store_sessions = store.get("items")
                    if not isinstance(raw_store_sessions, list):
                        raw_store_sessions = []
                elif isinstance(store, list):
                    raw_store_sessions = store
                    store = {"active_session_id": "", "sessions": raw_store_sessions}
                else:
                    raw_store_sessions = []
                    store = {"active_session_id": "", "sessions": []}

                changed = False
                visible_sessions = []

                for item in raw_store_sessions:
                    if not isinstance(item, dict):
                        continue

                    item_user_id = str(item.get("user_id") or "").strip()
                    item_username = str(item.get("username") or "").strip().lower()

                    is_current = bool(current_uid and item_user_id == current_uid)
                    is_same_name = bool(item_username and item_username == current_username)
                    is_legacy_joe = item_username == "joe"
                    is_unowned = not item_user_id and not item_username

                    if not (is_current or is_same_name or is_legacy_joe or is_unowned):
                        continue

                    if is_legacy_joe or is_unowned:
                        meta = item.get("meta")
                        if not isinstance(meta, dict):
                            meta = {}
                            item["meta"] = meta

                        if not meta.get("previous_owner_user_id") and item_user_id:
                            meta["previous_owner_user_id"] = item_user_id
                        if not meta.get("previous_owner_username") and item_username:
                            meta["previous_owner_username"] = item_username

                        if current_uid and item.get("user_id") != current_uid:
                            item["user_id"] = current_uid
                            changed = True

                        if item.get("username") != current_username:
                            item["username"] = current_username
                            changed = True

                        if meta.get("owner_source") != "local_auth_legacy_adoption_20260703":
                            meta["owner_source"] = "local_auth_legacy_adoption_20260703"
                            changed = True

                    visible_sessions.append(item)

                if changed:
                    if isinstance(store, dict):
                        store["sessions"] = raw_store_sessions
                    sessions_path.write_text(
                        _nova_legacy_json.dumps(store, ensure_ascii=False, indent=2),
                        encoding="utf-8"
                    )

                def _message_count(item):
                    messages = item.get("messages")
                    return len(messages) if isinstance(messages, list) else int(item.get("message_count") or 0)

                def _slim(item):
                    return {
                        "id": item.get("id") or item.get("session_id") or "",
                        "title": item.get("title") or "New Chat",
                        "created_at": item.get("created_at") or "",
                        "updated_at": item.get("updated_at") or "",
                        "pinned": bool(item.get("pinned")),
                        "message_count": _message_count(item),
                        "user_id": item.get("user_id") or "",
                        "username": item.get("username") or "",
                        "meta": item.get("meta") if isinstance(item.get("meta"), dict) else {},
                        "working_state": item.get("working_state") if isinstance(item.get("working_state"), dict) else {},
                        "active_execution": item.get("active_execution") if isinstance(item.get("active_execution"), dict) else {},
                    }

                visible_sessions.sort(
                    key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""),
                    reverse=True
                )

                returned_sessions = [_slim(item) for item in visible_sessions]
                active_session_id = str(store.get("active_session_id") or "").strip()
                if not active_session_id and returned_sessions:
                    active_session_id = returned_sessions[0].get("id") or ""

                active_session = None
                for item in visible_sessions:
                    if str(item.get("id") or item.get("session_id") or "") == active_session_id:
                        active_session = _slim(item)
                        break

                slim_response = jsonify({
                    "ok": True,
                    "active_session_id": active_session_id,
                    "session": active_session,
                    "sessions": returned_sessions,
                    "items": returned_sessions,
                    "artifacts": [],
                    "slim_sessions_payload": True,
                    "debug": {
                        "route": "richard_legacy_session_owner_bridge",
                        "route_taken": "legacy_owner_bridge_slim_sessions_payload",
                        "raw_session_count": len(raw_store_sessions),
                        "returned_session_count": len(returned_sessions),
                        "legacy_owner_bridge": True,
                        "current_user_id": current_uid,
                        "current_username": current_username,
                        "adopted_legacy_sessions": changed,
                    },
                })
                slim_response.headers["X-Nova-Slim-Sessions"] = "1"
                return slim_response

        except Exception as legacy_exc:
            try:
                app.logger.warning("[Nova Legacy Session Owner Bridge] failed: %s", legacy_exc)
            except Exception:
                pass

'''

if needle not in text:
    raise SystemExit("Could not find /api/sessions before_request insertion point")

text = text.replace(needle, insert, 1)
path.write_text(text.rstrip() + "\n", encoding="utf-8")
print("patched:", path)
