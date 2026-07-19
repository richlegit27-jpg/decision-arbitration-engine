from pathlib import Path
import base64
import mimetypes
import os

from flask import jsonify


class ImageVisionService:

    def handle(self, request):
        try:
            return None

        except Exception as exc:
            print(
                "[NOVA_API_CHAT_IMAGE_VISION_GATE] failed:",
                exc,
            )

            return None