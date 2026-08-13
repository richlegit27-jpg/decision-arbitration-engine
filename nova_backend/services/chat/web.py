"""
Nova Chat Web Module

Owns:
- web routing
- freshness
- live data
"""


class ChatWebHandler:

    def __init__(self, chat_service):
        self.chat_service = chat_service