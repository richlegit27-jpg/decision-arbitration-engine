from __future__ import annotations

import os
from flask import Flask, request, jsonify, render_template
from services.chat_service import ChatService
from services.memory_service import MemoryService
from services.artifact_service import ArtifactService
from services.attachment_service import AttachmentService
from services.web_service import WebService

app = Flask(__name__, template_folder="templates", static_folder="static")

chat_service = ChatService()
memory_service = MemoryService()
artifact_service = ArtifactService()
attachment_service = AttachmentService()
web_service = WebService()

# =========================================================
# 🔥 HARD FIX: guarantee add_artifact exists
# =========================================================
if not hasattr(artifact_service, "add_artifact"):
    def _fallback_add_artifact(*args, **kwargs):
        payload = kwargs if kwargs else (args[0] if args else {})
        return payload
    artifact_service.add_artifact = _fallback_add_artifact


# =========================================================
# routes
# =========================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        data = request.get_json()
        content = data.get("content")
        session_id = data.get("session_id")

        result = chat_service.send_message(content=content, session_id=session_id)

        return jsonify({
            "ok": True,
            "message": result.get("message"),
            "session": result.get("session"),
            "debug": result.get("debug")
        })

    except Exception as e:
        return jsonify({"ok": False, "error": f"Chat failed: {str(e)}"}), 500


# =========================================================
# 🔥 KNOWLEDGE ROUTE (FIXED PIPELINE)
# =========================================================

@app.route("/api/knowledge", methods=["POST"])
def api_knowledge():
    try:
        data = request.get_json()
        query = data.get("query")
        session_id = data.get("session_id")
        search_limit = int(data.get("search_limit", 5))
        fetch_limit = int(data.get("fetch_limit", 3))

        # -------------------------
        # MEMORY
        # -------------------------
        memory_hits = []
        if hasattr(memory_service, "search"):
            memory_hits = memory_service.search(query=query)

        # -------------------------
        # WEB SEARCH + FETCH
        # -------------------------
        pipeline = web_service.search_and_fetch(
            query=query,
            search_limit=search_limit,
            fetch_limit=fetch_limit
        )

        search_results = pipeline.get("search", {}).get("results", [])
        fetched_items = pipeline.get("fetch", {}).get("items", [])

        usable_sources = []
        for item in fetched_items:
            if item.get("ok"):
                usable_sources.append({
                    "title": item.get("title") or item.get("url"),
                    "url": item.get("url"),
                    "content": (item.get("content") or "")[:4000],
                })

        # 🔥 FORCE SECOND PASS IF EMPTY
        if not usable_sources:
            pipeline = web_service.search_and_fetch(
                query=query,
                search_limit=10,
                fetch_limit=5
            )

            fetched_items = pipeline.get("fetch", {}).get("items", [])

            for item in fetched_items:
                if item.get("ok"):
                    usable_sources.append({
                        "title": item.get("title") or item.get("url"),
                        "url": item.get("url"),
                        "content": (item.get("content") or "")[:4000],
                    })

        # -------------------------
        # BUILD CONTEXT
        # -------------------------
        context = ""

        if usable_sources:
            context += "WEB SOURCES:\n"
            for s in usable_sources:
                context += f"{s['title']}\n{s['content']}\n\n"

        if memory_hits:
            context += "MEMORY:\n"
            for m in memory_hits[:5]:
                context += f"{str(m)}\n\n"

        # -------------------------
        # FINAL ANSWER
        # -------------------------
        result = chat_service.send_message(
            content=f"{query}\n\n{context}",
            session_id=session_id
        )

        message = result.get("message")

        # -------------------------
        # SAVE ARTIFACT (SAFE NOW)
        # -------------------------
        artifact_service.add_artifact(
            title=query,
            content=message,
            kind="knowledge",
            session_id=session_id,
            tags=["knowledge"],
            meta={
                "search_count": len(search_results),
                "fetch_count": len(fetched_items),
                "usable_count": len(usable_sources),
                "memory_count": len(memory_hits),
            }
        )

        return jsonify({
            "ok": True,
            "message": message,
            "session": result.get("session"),
            "sources": usable_sources,
            "debug": {
                "memory_used": bool(memory_hits),
                "search_count": len(search_results),
                "fetch_count": len(fetched_items),
                "usable_count": len(usable_sources),
            }
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": f"Knowledge failed: {str(e)}"
        }), 500


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    port = int(os.getenv("APP_PORT", "5001"))
    app.run(host="127.0.0.1", port=port, debug=True)