from __future__ import annotations

from typing import Any


class ToolRegistry:
    """
    Unified Nova tool registry.

    Combines:

    - Internal Nova application actions
    - Real Nova executable tools
    - Planned external integrations

    Tool execution remains the responsibility of ToolExecutor.
    """

    INTERNAL_TOOLS = {
        "chat.send": {
            "name": "chat.send",
            "category": "internal",
            "requires_confirmation": False,
            "aliases": ["chat"],
            "implemented": True,
        },
        "session.rename": {
            "name": "session.rename",
            "category": "internal",
            "requires_confirmation": False,
            "aliases": ["rename"],
            "implemented": True,
        },
        "session.pin": {
            "name": "session.pin",
            "category": "internal",
            "requires_confirmation": False,
            "aliases": ["pin"],
            "implemented": True,
        },
        "session.delete": {
            "name": "session.delete",
            "category": "internal",
            "requires_confirmation": False,
            "aliases": ["delete"],
            "implemented": True,
        },
        "attachment.upload": {
            "name": "attachment.upload",
            "category": "internal",
            "requires_confirmation": False,
            "aliases": ["upload"],
            "implemented": True,
        },
        "attachment.analyze": {
            "name": "attachment.analyze",
            "category": "internal",
            "requires_confirmation": False,
            "aliases": ["analyze"],
            "implemented": True,
        },
    }

    EXTERNAL_TOOLS = {
        "email.send": {
            "name": "email.send",
            "category": "external",
            "requires_confirmation": True,
            "aliases": ["email"],
            "implemented": False,
        },
        "calendar.create": {
            "name": "calendar.create",
            "category": "external",
            "requires_confirmation": True,
            "aliases": ["calendar"],
            "implemented": False,
        },
    }

    def __init__(
        self,
        tool_executor=None,
        chat_service=None,
        nova_tool_registry=None,
    ):
        self.tool_executor = tool_executor
        self.chat_service = chat_service
        self.nova_tool_registry = nova_tool_registry

        self._tools = {}

        self._register_internal_tools()
        self._register_real_nova_tools()
        self._register_external_tools()

    # =========================================================
    # REGISTRATION
    # =========================================================

    def _register_internal_tools(self):
        for name, metadata in self.INTERNAL_TOOLS.items():
            item = dict(metadata)
            from nova_backend.tools.risk_policy import tool_risk_metadata
            risk = tool_risk_metadata(name)
            item["requires_confirmation"] = risk["requires_approval"]
            item["risk_class"] = risk["risk_class"]
            schemas = {
                "chat.send": {"message": {"type": "string"}},
                "session.rename": {"session_id": {"type": "string"}, "title": {"type": "string"}},
                "session.pin": {"session_id": {"type": "string"}, "pinned": {"type": "boolean"}},
                "session.delete": {"session_id": {"type": "string"}},
                "attachment.upload": {"session_id": {"type": "string"}, "filename": {"type": "string"}},
                "attachment.analyze": {"attachment_id": {"type": "string"}, "question": {"type": "string"}},
            }
            item["parameter_schema"] = {
                "type": "object", "properties": schemas.get(name, {}), "additionalProperties": False,
            }
            self._tools[name] = item

    def _register_external_tools(self):
        for name, metadata in self.EXTERNAL_TOOLS.items():
            self._tools[name] = dict(metadata)

    def _register_real_nova_tools(self):

        if self.nova_tool_registry is None:
            return

        try:
            tool_names = (
                self.nova_tool_registry.list_tools()
            )

        except Exception:
            return

        for tool_name in tool_names:

            tool = self.nova_tool_registry.get(
                tool_name
            )

            if tool is None:
                continue

            aliases = getattr(
                tool,
                "aliases",
                [],
            )

            if not isinstance(aliases, list):
                aliases = []

            requires_confirmation = bool(
                getattr(
                    tool,
                    "requires_confirmation",
                    False,
                )
            )
            from nova_backend.tools.risk_policy import tool_risk_metadata
            metadata = tool.get_metadata() if callable(getattr(tool, "get_metadata", None)) else {}
            risk = tool_risk_metadata(tool_name, tool)

            category = getattr(
                tool,
                "category",
                "nova",
            )

            parameter_schema = metadata.get("parameter_schema")
            if not self._is_valid_object_schema(parameter_schema):
                # A registered implementation without a usable contract must
                # never be advertised to a model as executable.
                continue

            self._tools[tool_name] = {
                "name": tool_name,
                "description": str(metadata.get("description") or "").strip(),
                "category": category,
                "requires_confirmation": risk["requires_approval"] or requires_confirmation,
                "requires_approval": risk["requires_approval"] or requires_confirmation,
                "risk_class": risk["risk_class"],
                "parameter_schema": parameter_schema,
                "aliases": list(aliases),
                "implemented": bool(metadata.get("implemented", True)),
                "available": tool_name not in {"shell_command", "terminal_execute", "python_run", "process_start"},
                "source": "nova",
            }

    @staticmethod
    def _is_valid_object_schema(schema):
        if not isinstance(schema, dict) or schema.get("type") != "object":
            return False
        properties = schema.get("properties")
        required = schema.get("required", [])
        if schema.get("additionalProperties") is not False:
            return False
        if not isinstance(properties, dict) or not isinstance(required, list):
            return False
        if any(not isinstance(key, str) or key not in properties for key in required):
            return False
        allowed_types = {"string", "integer", "number", "boolean", "array", "object"}
        for key, definition in properties.items():
            if not isinstance(key, str) or not isinstance(definition, dict):
                return False
            if definition.get("type") not in allowed_types:
                return False
        return True

    # =========================================================
    # DISCOVERY
    # =========================================================

    def get_available_tools(
        self,
    ) -> dict[str, dict[str, Any]]:

        return {
            name: dict(metadata)
            for name, metadata
            in self._tools.items()
            if metadata.get("implemented", True) is True
            and metadata.get("available", True) is True
        }

    def get_model_tool_definitions(self, surface="chat"):
        """Return model contracts only for executable canonical Nova tools."""
        if surface not in {"chat", "project", "super_ai"} or self.tool_executor is None:
            return []
        definitions = []
        for name, metadata in sorted(self.get_available_tools().items()):
            if metadata.get("source") != "nova":
                continue
            schema = metadata.get("parameter_schema")
            if not self._is_valid_object_schema(schema):
                continue
            description = str(metadata.get("description") or "").strip()
            if not description:
                continue
            definitions.append({
                "name": name,
                "description": description,
                "parameters": schema,
                "risk_level": metadata.get("risk_class", "WRITE"),
                "requires_approval": bool(metadata.get("requires_approval")),
                "implemented": True,
                "available": True,
            })
        return definitions


    def list_tool_names(self) -> list[str]:

        return sorted(
            name for name, metadata in self._tools.items()
            if metadata.get("implemented", True) is True
            and metadata.get("available", True) is True
        )

    def get_tool_count(self) -> int:

        return len(self.list_tool_names())

    def get_tool(
        self,
        tool_name: str,
    ) -> dict[str, Any] | None:

        normalized = self.resolve_tool_name(
            tool_name
        )

        if not normalized:
            return None

        tool = self._tools.get(normalized)

        if not tool or tool.get("implemented", True) is not True or tool.get("available", True) is not True:
            return None

        return dict(tool)

    # =========================================================
    # RESOLUTION
    # =========================================================

    def resolve_tool_name(
        self,
        tool_name: str,
    ) -> str:

        normalized = str(
            tool_name or ""
        ).lower().strip()

        if not normalized:
            return ""

        if normalized in self._tools:
            return normalized

        for name, metadata in self._tools.items():

            if metadata.get("implemented", True) is not True:
                continue

            aliases = (
                metadata.get("aliases")
                or []
            )

            normalized_aliases = [
                str(alias).lower().strip()
                for alias in aliases
            ]

            if normalized in normalized_aliases:
                return name

        return ""

    # =========================================================
    # METADATA
    # =========================================================

    def requires_confirmation(
        self,
        tool_name: str,
    ) -> bool:

        tool = self.get_tool(tool_name)

        if not tool:
            return False

        return bool(
            tool.get(
                "requires_confirmation"
            )
        )

    # =========================================================
    # EXECUTION
    # =========================================================

    def execute(
        self,
        tool_name: str,
        payload: dict | None = None,
        confirm: bool = False,
    ) -> dict:

        return self.execute_tool(
            tool_name,
            payload=payload,
            confirm=confirm,
        )

    def execute_tool(
        self,
        tool_name: str,
        payload: dict | None = None,
        confirm: bool = False,
    ) -> dict:

        resolved_name = self.resolve_tool_name(
            tool_name
        )

        if not resolved_name:
            return {
                "ok": False,
                "tool": tool_name,
                "tool_name": tool_name,
                "status": "failed",
                "error": (
                    f"Tool not registered: "
                    f"{tool_name}"
                ),
            }

        if self.tool_executor is None:
            return {
                "ok": False,
                "tool": resolved_name,
                "tool_name": resolved_name,
                "status": "failed",
                "error": (
                    "Tool executor is not configured."
                ),
            }

        result = self.tool_executor.run(
            resolved_name,
            payload or {},
            confirm=confirm,
        )

        if not isinstance(
            result,
            dict,
        ):
            return {
                "ok": True,
                "tool": resolved_name,
                "tool_name": resolved_name,
                "status": "executed",
                "result": result,
            }

        normalized_result = dict(result)

        normalized_result.setdefault(
            "tool",
            resolved_name,
        )

        normalized_result.setdefault(
            "tool_name",
            resolved_name,
        )

        if (
            normalized_result.get(
                "requires_confirmation"
            )
            is True
        ):
            normalized_result.setdefault(
                "status",
                "awaiting_confirmation",
            )

        elif normalized_result.get("ok") is True:
            normalized_result.setdefault(
                "status",
                "executed",
            )

        elif normalized_result.get("ok") is False:
            normalized_result.setdefault(
                "status",
                "failed",
            )

        return normalized_result
