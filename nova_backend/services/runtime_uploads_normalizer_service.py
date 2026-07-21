# ============================================================
# NOVA_RAILWAY_UPLOADS_DIR_RUNTIME_NORMALIZER_20260702
# Force generated images to save into the real Linux uploads dir on Railway.
# Fixes accidental creation of /app/C:\Users\Owner\nova\uploads.
# ============================================================

def install_runtime_uploads_normalizer(ChatService):

    def _nova_railway_normalize_uploads_dir_20260702(service):
        try:
            from pathlib import Path as _NovaRailwayPath
            import os as _nova_railway_os

            current = _NovaRailwayPath(
                getattr(service, "uploads_dir", "uploads")
            )

            current_text = str(current)

            if _nova_railway_os.name != "nt" and (
                ":" in current_text or "\\" in current_text
            ):
                current = _NovaRailwayPath.cwd() / "uploads"

            current.mkdir(parents=True, exist_ok=True)
            service.uploads_dir = current

            try:
                print(
                    "[NOVA_RAILWAY_UPLOADS_DIR_RUNTIME_NORMALIZER_20260702] uploads_dir",
                    str(current),
                )
            except Exception:
                pass

            return current

        except Exception as exc:
            try:
                print(
                    "[NOVA_RAILWAY_UPLOADS_DIR_RUNTIME_NORMALIZER_20260702] failed",
                    exc,
                )
            except Exception:
                pass

            return getattr(service, "uploads_dir", None)


    try:
        original_init = getattr(
            ChatService,
            "__init__",
            None,
        )

        if callable(original_init):

            def wrapped_init(self, *args, **kwargs):
                original_init(self, *args, **kwargs)
                _nova_railway_normalize_uploads_dir_20260702(self)

            ChatService.__init__ = wrapped_init

    except Exception as exc:
        try:
            print(
                "[NOVA_RAILWAY_UPLOADS_DIR_RUNTIME_NORMALIZER_20260702] init patch failed",
                exc,
            )
        except Exception:
            pass


    try:
        original_image_handler = getattr(
            ChatService,
            "_handle_image_generation",
            None,
        )

        if callable(original_image_handler):

            def wrapped_image_handler(self, *args, **kwargs):
                _nova_railway_normalize_uploads_dir_20260702(self)

                return original_image_handler(
                    self,
                    *args,
                    **kwargs,
                )

            ChatService._handle_image_generation = wrapped_image_handler

    except Exception as exc:
        try:
            print(
                "[NOVA_RAILWAY_UPLOADS_DIR_RUNTIME_NORMALIZER_20260702] image patch failed",
                exc,
            )
        except Exception:
            pass