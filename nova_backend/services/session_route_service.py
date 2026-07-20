from flask import jsonify


class SessionRouteService:

    def handle_slim_sessions(
        self,
        request,
        session,
        session_service,
        app,
        jsonify,
    ):
        try:

            if request.path != "/api/sessions" or request.method != "GET":
                return None

            if not session.get("nova_user_id"):
                return None

            raw_sessions = []

            for method_name in (
                "list_sessions",
                "get_sessions",
                "all_sessions",
                "load_sessions",
                "all",
            ):
                try:
                    method = getattr(session_service, method_name, None)

                    if callable(method):
                        candidate = method(
                            user_id=str(
                                session.get("nova_user_id") or ""
                            ).strip()
                        )

                        if isinstance(candidate, list):
                            raw_sessions = candidate
                            break

                        if isinstance(candidate, dict):
                            if isinstance(candidate.get("sessions"), list):
                                raw_sessions = candidate.get("sessions") or []
                                break

                            if (
                                isinstance(candidate.get("data"), dict)
                                and isinstance(candidate["data"].get("sessions"), list)
                            ):
                                raw_sessions = candidate["data"]["sessions"] or []
                                break

                except Exception:
                    pass

            current_user_id = str(
                session.get("nova_user_id") or ""
            ).strip()

            raw_sessions = [
                item
                for item in raw_sessions
                if (
                    isinstance(item, dict)
                    and str(item.get("user_id") or "").strip()
                    == current_user_id
                )
            ]

            slim_sessions = []

            for item in raw_sessions:
                if not isinstance(item, dict):
                    continue

                messages = item.get("messages")

                message_count = (
                    len(messages)
                    if isinstance(messages, list)
                    else int(item.get("message_count") or 0)
                )

                slim_sessions.append({
                    "id": item.get("id") or item.get("session_id") or "",
                    "title": item.get("title") or "New Chat",
                    "created_at": item.get("created_at") or "",
                    "updated_at": item.get("updated_at") or "",
                    "pinned": bool(item.get("pinned")),
                    "message_count": message_count,
                    "user_id": item.get("user_id") or "",
                    "username": item.get("username") or "",
                    "meta": item.get("meta")
                    if isinstance(item.get("meta"), dict)
                    else {},
                    "working_state": item.get("working_state")
                    if isinstance(item.get("working_state"), dict)
                    else {},
                    "active_execution": item.get("active_execution")
                    if isinstance(item.get("active_execution"), dict)
                    else {},
                })

            slim_sessions.sort(
                key=lambda item: str(
                    item.get("updated_at")
                    or item.get("created_at")
                    or ""
                ),
                reverse=True,
            )

            active_session_id = ""

            try:
                active_session_id = str(
                    request.cookies.get("nova_active_session_id")
                    or request.cookies.get("active_session_id")
                    or request.cookies.get("session_id")
                    or ""
                ).strip()

            except Exception:
                active_session_id = ""

            if not active_session_id and slim_sessions:
                for candidate in slim_sessions:
                    if int(candidate.get("message_count") or 0) > 0:
                        active_session_id = str(candidate.get("id") or "")
                        break

                if not active_session_id:
                    active_session_id = str(
                        slim_sessions[0].get("id") or ""
                    )

            returned_sessions = slim_sessions[:50]

            response = jsonify({
                "ok": True,
                "active_session_id": active_session_id,
                "sessions": returned_sessions,
                "items": returned_sessions,
                "artifacts": [],
                "slim_sessions_payload": True,
            })

            response.headers["X-Nova-Slim-Sessions"] = "1"

            return response

        except Exception as exc:
            print("[SESSION_ROUTE_SERVICE_ERROR]", repr(exc))
            raise

    def handle_sessions_new(
        self,
        request_json,
        session,
        session_service,
        DATA_DIR,
        load_json,
        app,
        json_ok,
    ):
        # NOVA_SESSION_NEW_FORCE_DURABLE_OWNER_WRITE_20260703
        # Create a real durable session, stamp current local-auth owner fields,
        # force-write it into the canonical session store, then return only the
        # saved/readable version. This prevents ghost active_session_id values.

        data = request_json()
        title = str(data.get("title") or "New Chat").strip() or "New Chat"

        auth_user_id = ""
        auth_username = ""

        try:
            auth_user_id = str(
                session.get("nova_user_id") or ""
            ).strip()

        except Exception:
            auth_user_id = ""

        if hasattr(session_service, "create_session"):
            created = session_service.create_session(
                title,
                user_id=auth_user_id,
            )

        elif hasattr(session_service, "new_session"):
            created = session_service.new_session(
                title,
                user_id=auth_user_id,
            )

        else:
            raise AttributeError(
                "SessionService has no create_session/new_session method"
            )

        session_id = ""

        if isinstance(created, dict):
            session_id = str(created.get("id") or "").strip()

        if not session_id:
            session_id = str(
                getattr(session_service, "active_session_id", "") or ""
            ).strip()

        try:
            users_path = DATA_DIR / "nova_auth_users.json"
            users_data = load_json(users_path, {"users": []})
            users = (
                users_data.get("users", [])
                if isinstance(users_data, dict)
                else []
            )

            for user in users:
                if not isinstance(user, dict):
                    continue

                if str(user.get("id") or "") == auth_user_id:
                    auth_username = str(
                        user.get("username")
                        or user.get("email")
                        or ""
                    ).strip()
                    break

        except Exception:
            auth_username = ""

        if (
            auth_user_id == "user_richard_stable_local_login"
            and not auth_username
        ):
            auth_username = "richard"

        if isinstance(created, dict):
            if auth_user_id:
                created["user_id"] = auth_user_id

            if auth_username:
                created["username"] = auth_username

            meta = created.get("meta")

            if not isinstance(meta, dict):
                meta = {}

            if auth_user_id or auth_username:
                meta["owner_source"] = "local_auth"

            created["meta"] = meta

        if session_id and isinstance(created, dict):
            try:
                store = session_service._read_store()

                if not isinstance(store, dict):
                    store = {
                        "active_session_id": "",
                        "sessions": [],
                    }

                sessions = store.get("sessions")

                if not isinstance(sessions, list):
                    sessions = []

                found = False

                for index, item in enumerate(sessions):
                    if (
                        isinstance(item, dict)
                        and str(item.get("id") or "") == session_id
                    ):
                        merged = dict(item)
                        merged.update(created)
                        sessions[index] = merged
                        created = merged
                        found = True
                        break

                if not found:
                    sessions.insert(0, created)

                store["sessions"] = sessions
                store["active_session_id"] = session_id

                session_service._write_store(store)

            except Exception as exc:
                try:
                    app.logger.warning(
                        "[NOVA_SESSION_NEW_FORCE_DURABLE_OWNER_WRITE_20260703] force write failed: %s",
                        exc,
                    )
                except Exception:
                    pass

        saved = (
            session_service.get_session(
                session_id,
                user_id=auth_user_id,
            )
            if session_id
            else None
        )

        if isinstance(saved, dict):
            created = saved

        sessions = session_service.get_all(
            user_id=auth_user_id,
        )

        if session_id and isinstance(created, dict):
            found_in_response = False

            for item in sessions:
                if (
                    isinstance(item, dict)
                    and str(item.get("id") or "") == session_id
                ):
                    found_in_response = True
                    break

            if not found_in_response:
                sessions = [
                    created
                ] + [
                    item
                    for item in sessions
                    if isinstance(item, dict)
                ]

        return json_ok(
            session=created if isinstance(created, dict) else None,
            sessions=sessions,
            active_session_id=(
                session_id
                or getattr(session_service, "active_session_id", "")
            ),
            session_id=session_id,
            skip_session_auth_scope_filter=True,
            durable_session_write=True,
        )

    def install_routes(
        self,
        app,
        session_service,
        artifact_service,
        memory_service,
    ):
        from flask import request, session

        @app.get("/api/sessions")
        def api_sessions():
            slim_response = self.handle_slim_sessions(
                request,
                session,
                session_service,
                app,
                jsonify,
            )

            if slim_response is not None:
                return slim_response

            sessions = session_service.list_sessions(
                user_id=str(
                    session.get("nova_user_id") or ""
                ).strip()
            )

            return jsonify({
                "ok": True,
                "sessions": sessions,
                "items": sessions,
                "artifacts": (
                    artifact_service.all()
                    if hasattr(artifact_service, "all")
                    else []
                ),
            })


        @app.post("/api/sessions/new")
        def api_sessions_new():
            return self.handle_sessions_new(
                request_json,
                session,
                session_service,
                DATA_DIR,
                load_json,
                app,
                json_ok,
            )

    def handle_sessions_switch(
        self,
        payload,
        session_service,
        flask_session,
        json_error,
        json_ok,
    ):
        data = payload or {}

        session_id = str(data.get("session_id") or "").strip()

        if not session_id:
            return json_error("Missing session_id", 400)

        auth_user_id = ""

        try:
            auth_user_id = str(
                flask_session.get("nova_user_id")
                or flask_session.get("user_id")
                or ""
            ).strip()

        except Exception:
            auth_user_id = ""

        session = session_service.set_active(
            session_id,
            user_id=auth_user_id,
        )

        if not session:
            return json_error("Session not found", 404)

        return json_ok(
            session=session_service.get_session(session_id),
            sessions=session_service.get_all(),
            active_session_id=session_service.active_session_id,
        )


    def api_sessions_switch(self):
        return self.handle_sessions_switch(
            request_json(),
            self.session_service,
            session,
            json_error,
            json_ok,
        )

    def handle_sessions_pin(
        self,
        payload,
        session_service,
        flask_session,
        json_error,
        json_ok,
    ):
        data = payload or {}

        session_id = str(data.get("session_id") or "").strip()
        pinned = bool(data.get("pinned"))

        if not session_id:
            return json_error("Missing session_id", 400)

        auth_user_id = ""

        try:
            auth_user_id = str(
                flask_session.get("nova_user_id")
                or flask_session.get("user_id")
                or ""
            ).strip()

        except Exception:
            auth_user_id = ""

        session = session_service.pin(
            session_id,
            pinned,
            user_id=auth_user_id,
        )

        if not session:
            return json_error("Session not found", 404)

        return json_ok(
            session=session_service.get_session(session_id),
            sessions=session_service.get_all(),
            active_session_id=session_service.active_session_id,
        )


    def handle_sessions_delete(
        self,
        payload,
        session_service,
        flask_session,
        json_error,
        json_ok,
    ):
        data = payload or {}

        session_id = str(data.get("session_id") or "").strip()

        if not session_id:
            return json_error("Missing session_id", 400)

        auth_user_id = ""

        try:
            auth_user_id = str(
                flask_session.get("nova_user_id")
                or flask_session.get("user_id")
                or ""
            ).strip()

        except Exception:
            auth_user_id = ""

        if not session_service.delete(
            session_id,
            user_id=auth_user_id,
        ):
            return json_error("Session not found", 404)

        active_id = session_service.active_session_id
        active_session = session_service.get_active()

        return json_ok(
            session=active_session,
            sessions=session_service.get_all(),
            active_session_id=active_id,
        )

    def api_sessions_pin(self):
        return self.handle_sessions_pin(
            request_json(),
            self.session_service,
            session,
            json_error,
            json_ok,
        )


    def api_sessions_delete(self):
        return self.handle_sessions_delete(
            request_json(),
            self.session_service,
            session,
            json_error,
            json_ok,
        )

    def handle_sessions_rename(
        self,
        payload,
        session_service,
        flask_session,
        json_error,
        json_ok,
    ):
        data = payload or {}

        session_id = str(data.get("session_id") or "").strip()
        title = str(data.get("title") or "").strip()

        if not session_id:
            return json_error("Missing session_id", 400)

        auth_user_id = ""

        try:
            auth_user_id = str(
                flask_session.get("nova_user_id")
                or flask_session.get("user_id")
                or ""
            ).strip()

        except Exception:
            auth_user_id = ""

        session = session_service.rename(
            session_id,
            title or "New Chat",
            user_id=auth_user_id,
        )

        if not session:
            return json_error("Session not found", 404)

        return json_ok(
            session=session_service.get_session(session_id),
            sessions=session_service.get_all(),
            active_session_id=session_service.active_session_id,
        )

    def api_sessions_rename(self):
        return self.handle_sessions_rename(
            request_json(),
            self.session_service,
            session,
            json_error,
            json_ok,
        )


