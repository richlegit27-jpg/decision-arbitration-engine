@app.post("/api/chat")
def api_chat()::
    try:
        data = parse_json_body()
        session_id = (data.get("session_id") or get_active_session_id() or "").strip()
        user_text = (data.get("message") or data.get("text") or data.get("user_text") or "").strip()
        attachments = ensure_list(data.get("attachments"))

        if not user_text and not attachments:
            return jsonify({"ok": False, "error": "Missing message"}), 400

        result = chat_service.handle(
            user_text=user_text,
            session_id=session_id,
            attachments=attachments,
        )

        return jsonify(result)

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
            "trace": traceback.format_exc(),
            "route_build": ROUTE_BUILD,
        }), 500
        # ------------------------------
        # USER MESSAGE
        # ------------------------------
        user_msg = append_message(
            session,
            "user",
            user_text,
            attachments=attachments,
            meta={"route": route_meta},
        )

        # ------------------------------
        # INTENT (FIXED)
        # ------------------------------
        if user_text.lower().startswith("/image"):
            intent = "image"
        else:
            intent = detect_intent(user_text)

        # ------------------------------
        # IMAGE ROUTE
        # ------------------------------
        if intent == "image":
            prompt = user_text.replace("/image", "", 1).strip()

            if not prompt:
                prompt = "a detailed high quality image"

            image_url, image_error = generate_image(prompt)

            if image_error or not image_url:
                assistant_text = f"Image generation failed: {image_error or 'unknown error'}"

                assistant_msg = append_message(
                    session,
                    "assistant",
                    assistant_text,
                    meta={
                        "route": {"intent": "image"},
                        "error": image_error,
                        "prompt": prompt,
                    },
                )

                save_sessions_store(store)

                return jsonify({
                    "ok": True,
                    "session_id": session_id,
                    "assistant_message": assistant_msg,
                    "debug": {
                        "intent": "image",
                        "error": image_error,
                        "prompt": prompt,
                    },
                })

            filename = Path(image_url).name if image_url else "generated.png"

            generated_attachment = {
                "id": new_id("generated"),
                "name": filename,
                "filename": filename,
                "url": image_url,
                "mime_type": "image/png",
                "kind": "image",
                "created_at": utc_now(),
            }

            assistant_text = f"Generated image for: {prompt}"

            assistant_msg = append_message(
                session,
                "assistant",
                assistant_text,
                attachments=[generated_attachment],
                meta={
                    "route": {"intent": "image"},
                    "image_url": image_url,
                    "prompt": prompt,
                },
            )

            artifact = create_artifact(
                session_id=session_id,
                kind="image_generation",
                title="Generated image",
                body=assistant_text,
                preview=truncate(prompt, 180),
                meta={"image_url": image_url, "prompt": prompt},
                viewer={
                    "kind": "image_generation",
                    "title": "Generated image",
                    "body": assistant_text,
                    "image_url": image_url,
                    "bullets": [prompt],
                },
            )

            save_sessions_store(store)

            return jsonify({
                "ok": True,
                "session_id": session_id,
                "assistant_message": assistant_msg,
                "artifact": serialize_artifact(artifact),
                "debug": {
                    "intent": "image",
                    "prompt": prompt,
                    "image_url": image_url,
                },
            })

        # ------------------------------
        # WEB ROUTE
        # ------------------------------
        if intent == "web":
            url = normalize_url(user_text)
            result = fetch_web_page(url)

            assistant_text = result.get("summary") or result.get("title") or url

            assistant_msg = append_message(
                session,
                "assistant",
                assistant_text,
                meta={"route": {"intent": "web"}, "web_result": result},
            )

            artifact = create_artifact(
                session_id=session_id,
                kind="web_result",
                title=result.get("title") or "Web result",
                body=assistant_text,
                preview=truncate(assistant_text, 180),
                meta={"source_url": result.get("url")},
            )

            save_sessions_store(store)

            return jsonify({
                "ok": True,
                "session_id": session_id,
                "assistant_message": assistant_msg,
                "artifact": serialize_artifact(artifact),
                "web_result": result,
                "debug": {"intent": "web"},
            })

        # ------------------------------
        # NORMAL CHAT
        # ------------------------------
        assistant_text = call_chat_model(session, user_text, attachments, route_meta["mode"])

        assistant_msg = append_message(
            session,
            "assistant",
            assistant_text,
            meta={"route": route_meta},
        )

        artifact = create_artifact(
            session_id=session_id,
            kind="chat_reply",
            title="Chat reply",
            body=assistant_text,
            preview=truncate(assistant_text, 180),
            meta={"route": route_meta},
        )

        maybe_store_memory(user_text, session_id)
        save_sessions_store(store)

        return jsonify({
            "ok": True,
            "session_id": session_id,
            "assistant_message": assistant_msg,
            "artifact": serialize_artifact(artifact),
            "debug": {
                "intent": "chat",
                "user_message_id": user_msg.get("id"),
            },
        })

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
            "trace": traceback.format_exc(),
            "route_build": ROUTE_BUILD,
        }), 500

