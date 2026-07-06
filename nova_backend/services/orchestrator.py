from nova_backend.services.tools.tool_detector import ToolDetector

class NovaOrchestrator:
    """
    Central Brain Controller for Nova (STABLE VERSION)

    Responsibilities:
    - intent detection
    - memory enrichment (safe + optional)
    - attachment context building
    - chat execution
    - runtime update

    DOES NOT:
    - execute tools
    - perform billing
    - mutate system state outside memory/runtime hooks
    """

    def __init__(
        self,
        chat_service,
        session_service,
        memory_service,
        attachment_service,
        intent_router,
        runtime_brain,
        tool_executor
    ):
        self.chat_service = chat_service
        self.session_service = session_service
        self.memory_service = memory_service
        self.attachment_service = attachment_service
        self.intent_router = intent_router
        self.runtime_brain = runtime_brain

        self.tool_executor = tool_executor
        self.tool_detector = ToolDetector()

    # =========================================================
    # MAIN ENTRY
    # =========================================================
    def handle(self, user_text: str, session_id: str = None, attachments=None):
        attachments = attachments or []

        user_text = (user_text or "").strip()

        if not user_text:
            return {"ok": False, "error": "empty_input"}

        # -------------------------
        # 1. INTENT (SAFE)
        # -------------------------
        intent = self._safe_intent(user_text)

        # -------------------------
        # 2. MEMORY (OPTIONAL ENRICHMENT ONLY)
        # -------------------------
        memory_fact = self._extract_and_store_memory(user_text, session_id)

        # -------------------------
        # 3. SESSION
        # -------------------------
        session = self._get_session(session_id)

        # -------------------------
        # 4. ATTACHMENTS
        # -------------------------
        attachment_context = self._process_attachments(attachments)

        # -------------------------
        # 5. BUILD INPUT
        # -------------------------
        enriched_input = self._build_input(
            user_text,
            memory_fact,
            attachment_context
        )

        # -------------------------
        # 6. TOOL DETECTION (PRE-CHAT GATE)
        # -------------------------
        tool_request = self.tool_detector.detect(enriched_input)

        if tool_request:
            tool_name = tool_request["tool"]
            payload = tool_request.get("payload", {})

            allowed = getattr(self.tool_executor, "allowed_tools", None)

            if allowed is None:
                return {
                    "ok": False,
                    "error": "tool_executor_missing_allowed_tools",
                    "tool": tool_name
                }

            if tool_name in allowed:
                tool_result = self.tool_executor.run(tool_name, payload)

                return {
                    "ok": True,
                    "tool_executed": True,
                    "tool": tool_name,
                    "result": tool_result,
                    "session_id": session.get("id") if session else session_id
                }

        # -------------------------
        # 7. CHAT EXECUTION (ONLY IF NO TOOL)
        # -------------------------
        result = self.chat_service.handle(
            user_text=enriched_input,
            session_id=session.get("id") if session else session_id,
            attachments=attachments
        )

        # -------------------------
        # 8. RUNTIME UPDATE (NON-BLOCKING)
        # -------------------------
        self._update_runtime(user_text, intent, session_id)

        return {
            "ok": True,
            "intent": intent,
            "session_id": session.get("id") if session else session_id,
            "result": result
        }

    # =========================================================
    # INTENT (SAFE WRAPPER)
    # =========================================================
    def _safe_intent(self, text):
        try:
            return self.intent_router.route(text)
        except Exception:
            return "unknown"

    # =========================================================
    # SESSION (SAFE WRAPPER)
    # =========================================================
    def _get_session(self, session_id):
        try:
            if session_id:
                return self.session_service.get_session(session_id)
            return self.session_service.get_active()
        except Exception:
            return None

    # =========================================================
    # MEMORY (SAFE + NON-CRITICAL)
    # =========================================================
    def _extract_and_store_memory(self, text, session_id):
        if not text:
            return None

        try:
            extract_memory_fact = getattr(self.memory_service, "extract_memory_fact", None)


        try:
            self.memory_service.add(
                text=fact["text"],
                kind=fact.get("kind", "note"),
                tags=fact.get("tags", []),
                session_id=session_id,
                weight=fact.get("weight", 1.0)
            )
        except Exception:
            pass

        return fact

    # =========================================================
    # ATTACHMENTS
    # =========================================================
    def _process_attachments(self, attachments):
        if not attachments:
            return ""

        try:
            return "\n".join(
                [
                    a.get("summary")
                    or a.get("text")
                    or a.get("filename")
                    or ""
                    for a in attachments
                    if isinstance(a, dict)
                ]
            )
        except Exception:
            return ""

    # =========================================================
    # INPUT BUILDER
    # =========================================================
    def _build_input(self, user_text, memory_fact, attachment_context):
        parts = []

        if memory_fact:
            parts.append(f"[MEMORY]: {memory_fact['text']}")

        if attachment_context:
            parts.append(f"[ATTACHMENTS]: {attachment_context}")

        parts.append(user_text)

        return "\n".join(parts)

    # =========================================================
    # RUNTIME UPDATE (SAFE NON-BLOCKING)
    # =========================================================
    def _update_runtime(self, user_text, intent, session_id):
        try:
            if hasattr(self.runtime_brain, "update"):
                self.runtime_brain.update({
                    "last_user_message": user_text,
                    "intent": intent,
                    "session_id": session_id
                })
        except Exception:
            pass