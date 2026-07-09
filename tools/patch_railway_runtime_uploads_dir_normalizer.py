from pathlib import Path

path = Path("nova_backend/services/chat_service.py")
text = path.read_text(encoding="utf-8")

marker = "NOVA_RAILWAY_UPLOADS_DIR_RUNTIME_NORMALIZER_20260702"

if marker in text:
    print("runtime uploads dir normalizer already installed")
    raise SystemExit(0)

patch = r'''

# ============================================================
# NOVA_RAILWAY_UPLOADS_DIR_RUNTIME_NORMALIZER_20260702
# Force generated images to save into the real Linux uploads dir on Railway.
# Fixes accidental creation of /app/C:\Users\Owner\nova\uploads.
# ============================================================
def _nova_railway_normalize_uploads_dir_20260702(service):
    try:
        from pathlib import Path as _NovaRailwayPath
        import os as _nova_railway_os

        current = _NovaRailwayPath(getattr(service, "uploads_dir", "uploads"))
        current_text = str(current)

        if _nova_railway_os.name != "nt" and (":" in current_text or "\\" in current_text):
            current = _NovaRailwayPath.cwd() / "uploads"

        current.mkdir(parents=True, exist_ok=True)
        service.uploads_dir = current

        try:
            print("[NOVA_RAILWAY_UPLOADS_DIR_RUNTIME_NORMALIZER_20260702] uploads_dir", str(current))
        except Exception:
            pass

        return current
    except Exception as exc:
        try:
            print("[NOVA_RAILWAY_UPLOADS_DIR_RUNTIME_NORMALIZER_20260702] failed", exc)
        except Exception:
            pass
        return getattr(service, "uploads_dir", None)


try:
    _nova_railway_original_init_20260702 = getattr(ChatService, "__init__", None)

    if callable(_nova_railway_original_init_20260702):
        def _nova_railway_init_wrapper_20260702(self, *args, **kwargs):
            _nova_railway_original_init_20260702(self, *args, **kwargs)
            _nova_railway_normalize_uploads_dir_20260702(self)

        ChatService.__init__ = _nova_railway_init_wrapper_20260702
except Exception as _nova_railway_init_patch_error_20260702:
    try:
        print("[NOVA_RAILWAY_UPLOADS_DIR_RUNTIME_NORMALIZER_20260702] init patch failed", _nova_railway_init_patch_error_20260702)
    except Exception:
        pass


try:
    _nova_railway_original_image_handler_20260702 = getattr(ChatService, "_handle_image_generation", None)

    if callable(_nova_railway_original_image_handler_20260702):
        def _nova_railway_image_handler_wrapper_20260702(self, *args, **kwargs):
            _nova_railway_normalize_uploads_dir_20260702(self)
            return _nova_railway_original_image_handler_20260702(self, *args, **kwargs)

        ChatService._handle_image_generation = _nova_railway_image_handler_wrapper_20260702
except Exception as _nova_railway_image_patch_error_20260702:
    try:
        print("[NOVA_RAILWAY_UPLOADS_DIR_RUNTIME_NORMALIZER_20260702] image patch failed", _nova_railway_image_patch_error_20260702)
    except Exception:
        pass
'''

text = text.rstrip() + "\n" + patch + "\n"
path.write_text(text, encoding="utf-8")
print("patched runtime uploads dir normalizer")
