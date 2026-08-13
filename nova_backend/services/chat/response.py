"""
Nova Chat Response Module

Owns:
- response formatting
- final answer shaping
- fallback responses
"""


class ChatResponseHandler:

    def __init__(self, chat_service):
        self.chat_service = chat_service