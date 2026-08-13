"""
Nova Chat Image Module

Owns:
- image generation routing
- image artifact handling
"""


class ChatImageHandler:

    def __init__(self, chat_service):
        self.chat_service = chat_service