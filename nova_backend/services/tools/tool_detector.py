class ToolDetector:
    """
    Detects whether the model output requests tool execution.
    Simple rule-based detector (Phase 2 baseline).
    """

        # -------------------------
        # 6. MULTI-TOOL DETECTION (PRE-CHAT GATE)
        # -------------------------
        # -------------------------
        # 6. MULTI-TOOL DETECTION (PRE-CHAT GATE)
        # -------------------------
        tool_requests = self.tool_detector.detect(enriched_input)

        if tool_requests:
            tool_results = []

            for tool_request in tool_requests:
                tool_name = tool_request["tool"]
                payload = tool_request.get("payload", {})

                if tool_name in getattr(self.tool_executor, "allowed_tools", set()):
                    result = self.tool_executor.run(tool_name, payload)

                    tool_results.append({
                        "tool": tool_name,
                        "result": result
                    })

            return {
                "ok": True,
                "tool_executed": True,
                "tools": tool_results,
                "session_id": session.get("id") if session else session_id
            }