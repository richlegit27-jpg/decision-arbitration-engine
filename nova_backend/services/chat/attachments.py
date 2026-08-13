"""
Nova Chat Attachment Module

Owns:
- file uploads
- attachment analysis
"""


class ChatAttachmentHandler:

    def __init__(self, chat_service):
        self.chat_service = chat_service