from __future__ import annotations

from typing import Any

from nova_backend.tools.manager import tool_manager


class ToolDiscoveryService:

    def _get_metadata(
        self,
        tool_name: str,
    ) -> dict[str, Any] | None:

        tool = tool_manager.get_tool(
            tool_name
        )

        if tool is None:
            return None

        if hasattr(tool, "get_metadata"):

            metadata = tool.get_metadata()

        else:

            metadata = {
                "name": tool_name,
                "description": "",
                "category": "general",
                "capabilities": [],
                "risk_level": "low",
                "requires_confirmation": False,
                "class": tool.__class__.__name__,
                "module": tool.__class__.__module__,
            }

        metadata.setdefault(
            "name",
            tool_name,
        )

        metadata.setdefault(
            "description",
            "",
        )

        metadata.setdefault(
            "category",
            "general",
        )

        metadata.setdefault(
            "capabilities",
            [],
        )

        metadata.setdefault(
            "risk_level",
            "low",
        )

        metadata.setdefault(
            "requires_confirmation",
            False,
        )

        metadata.setdefault(
            "class",
            tool.__class__.__name__,
        )

        metadata.setdefault(
            "module",
            tool.__class__.__module__,
        )

        return metadata

    def discover_tools(self) -> dict[str, Any]:

        discovered_tools = []

        for tool_name in tool_manager.list_tools():

            metadata = self._get_metadata(
                tool_name
            )

            if metadata is None:
                continue

            discovered_tools.append(
                metadata
            )

        return {
            "ok": True,
            "count": len(discovered_tools),
            "tools": discovered_tools,
        }

    def get_tool(
        self,
        tool_name: str,
    ) -> dict[str, Any]:

        metadata = self._get_metadata(
            tool_name
        )

        if metadata is None:

            return {
                "ok": False,
                "tool": tool_name,
                "error": "tool_not_found",
            }

        return {
            "ok": True,
            "tool": metadata,
        }

    def has_tool(
        self,
        tool_name: str,
    ) -> bool:

        return tool_manager.has_tool(
            tool_name
        )

    def list_categories(
        self,
    ) -> dict[str, Any]:

        categories = {}

        for tool_name in tool_manager.list_tools():

            metadata = self._get_metadata(
                tool_name
            )

            if metadata is None:
                continue

            category = metadata.get(
                "category",
                "general",
            )

            categories.setdefault(
                category,
                [],
            )

            categories[category].append(
                metadata.get(
                    "name",
                    tool_name,
                )
            )

        return {
            "ok": True,
            "count": len(categories),
            "categories": categories,
        }

    def get_capabilities(
        self,
    ) -> dict[str, Any]:

        capabilities = {}

        for tool_name in tool_manager.list_tools():

            metadata = self._get_metadata(
                tool_name
            )

            if metadata is None:
                continue

            tool_capabilities = metadata.get(
                "capabilities",
                [],
            )

            for capability in tool_capabilities:

                capabilities.setdefault(
                    capability,
                    [],
                )

                capabilities[capability].append(
                    metadata.get(
                        "name",
                        tool_name,
                    )
                )

        return {
            "ok": True,
            "count": len(capabilities),
            "capabilities": capabilities,
        }

    def search_tools(
        self,
        query: str,
    ) -> dict[str, Any]:

        normalized_query = str(
            query or ""
        ).lower().strip()

        if not normalized_query:

            return {
                "ok": True,
                "query": query,
                "count": 0,
                "tools": [],
            }

        matches = []

        for tool_name in tool_manager.list_tools():

            metadata = self._get_metadata(
                tool_name
            )

            if metadata is None:
                continue

            searchable_parts = [

                metadata.get(
                    "name",
                    "",
                ),

                metadata.get(
                    "description",
                    "",
                ),

                metadata.get(
                    "category",
                    "",
                ),

            ]

            searchable_parts.extend(
                metadata.get(
                    "capabilities",
                    [],
                )
            )

            searchable_text = " ".join(
                str(part).lower()
                for part in searchable_parts
            )

            if normalized_query in searchable_text:

                matches.append(
                    metadata
                )

        return {
            "ok": True,
            "query": query,
            "count": len(matches),
            "tools": matches,
        }

    def build_tool_manifest(
        self,
    ) -> dict[str, Any]:

        tools = []

        for tool_name in tool_manager.list_tools():

            metadata = self._get_metadata(
                tool_name
            )

            if metadata is None:
                continue

            tools.append(
                {
                    "name": metadata.get(
                        "name"
                    ),
                    "description": metadata.get(
                        "description"
                    ),
                    "category": metadata.get(
                        "category"
                    ),
                    "capabilities": metadata.get(
                        "capabilities",
                        [],
                    ),
                    "risk_level": metadata.get(
                        "risk_level"
                    ),
                    "requires_confirmation": metadata.get(
                        "requires_confirmation"
                    ),
                }
            )

        return {
            "ok": True,
            "tool_count": len(tools),
            "tools": tools,
        }


tool_discovery_service = ToolDiscoveryService()