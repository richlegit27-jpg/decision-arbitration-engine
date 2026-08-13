"""
Nova Chat Response Module

Owns:

- response formatting
- final chat response shaping
- assistant output handling
"""


class ChatResponseHandler:

    def __init__(self, chat_service):
        self.chat_service = chat_service

    def format_response(self, response):
        return response