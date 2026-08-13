"""
Nova Chat Execution Module

Owns:
- auto-plan execution
- next/continue flows
- execution state handling
- mission lifecycle
"""


class ChatExecutionHandler:

    def __init__(self, chat_service):
        self.chat_service = chat_service

    def auto_advance(self, session_id):
        return self.chat_service._auto_advance_execution(
            session_id
        )