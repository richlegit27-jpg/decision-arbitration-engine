from nova_backend.utils.api_response import ok_response, error_response
from nova_backend.utils.request_utils import get_json_body, get_str
from nova_backend.utils.route_guard import guarded_json_route
from nova_backend.utils.time_utils import iso_now

from flask import request

class MemoryRouteService:

    def __init__(self, memory_service):
        self.memory_service = memory_service

    def install_routes(self, app):

        @app.get("/api/memory")
        @guarded_json_route
        def api_memory():
            memory = self.memory_service.all()

            return ok_response(
                data={
                    "memory": memory,
                    "count": len(memory),
                },
                message="Memory loaded.",
            )

        @app.post("/api/memory/add")
        @guarded_json_route
        def api_memory_add():
            data = get_json_body(request)

            text = get_str(data, "text")
            kind = get_str(data, "kind", "note") or "note"
            source = get_str(data, "source", "manual") or "manual"
            session_id = get_str(data, "session_id")

            if not text:
                return error_response(
                    error="text is required.",
                    code="missing_text",
                ), 400

            item = self.memory_service.add_memory({
                "text": text,
                "kind": kind,
                "source": source,
                "session_id": session_id,
            })

            memory = self.memory_service.all()

            return ok_response(
                data={
                    "item": item,
                    "memory": memory,
                    "count": len(memory),
                },
                message="Memory added.",
            )

        @app.post("/api/memory/pin")
        @guarded_json_route
        def api_memory_pin():
            data = get_json_body(request)
            memory_id = get_str(data, "id") or get_str(data, "memory_id")
            pinned = bool(data.get("pinned", True))

            if not memory_id:
                return error_response(
                    error="id is required.",
                    code="missing_id",
                ), 400

            item = self.memory_service.pin_memory(
                memory_id,
                pinned=pinned,
            )

            memory = self.memory_service.all()

            return ok_response(
                data={
                    "item": item,
                    "memory": memory,
                    "count": len(memory),
                },
                message="Memory pinned." if pinned else "Memory unpinned.",
            )


        @app.post("/api/memory/delete")
        @guarded_json_route
        def api_memory_delete():
            data = get_json_body(request)
            memory_id = get_str(data, "id") or get_str(data, "memory_id")

            if not memory_id:
                return error_response(
                    error="id is required.",
                    code="missing_id",
                ), 400

            deleted = self.memory_service.delete_memory(memory_id)
            memory = self.memory_service.all()

            return ok_response(
                data={
                    "deleted": deleted,
                    "memory": memory,
                    "count": len(memory),
                },
                message="Memory deleted." if deleted else "Memory not found.",
            )

        @app.post("/api/memory/update")
        @guarded_json_route
        def api_memory_update():
            data = get_json_body(request)

            memory_id = str(data.get("id") or "").strip()
            text = str(data.get("text") or "").strip()
            kind = str(data.get("kind") or "note").strip()

            if not memory_id:
                return error_response(
                    "Missing memory id",
                    code="missing_id",
                ), 400

            if not text:
                return error_response(
                    "Missing memory text",
                    code="missing_text",
                ), 400

            items = self.memory_service.all()

            updated = None

            for item in items:
                if str(item.get("id")) == memory_id:
                    item["text"] = text
                    item["kind"] = kind
                    item["updated_at"] = iso_now()
                    updated = item
                    break

            if not updated:
                return error_response(
                    "Memory not found",
                    code="not_found",
                ), 404

            self.memory_service._write_store(
                {"memory": items}
            )

            return ok_response(
                item=updated,
                message="Memory updated.",
            )

        @app.post("/api/memory/cleanup")
        @guarded_json_route
        def api_memory_cleanup():
            result = self.memory_service.cleanup_memories()
            memory = self.memory_service.all()

            return ok_response(
                data={
                    "result": result,
                    "memory": memory,
                    "count": len(memory),
                },
                message="Memory cleanup complete.",
            )


        @app.post("/api/memory/promote")
        @guarded_json_route
        def api_memory_promote():
            result = self.memory_service.promote_memories()
            memory = self.memory_service.all()

            return ok_response(
                data={
                    "result": result,
                    "memory": memory,
                    "count": len(memory),
                },
                message="Memory promotion complete.",
            )


        @app.post("/api/memory/cleanup-promote")
        @guarded_json_route
        def api_memory_cleanup_promote():
            result = self.memory_service.cleanup_and_promote_memories()
            memory = self.memory_service.all()

            return ok_response(
                data={
                    "result": result,
                    "memory": memory,
                    "count": len(memory),
                },
                message="Memory cleanup and promotion complete.",
            )