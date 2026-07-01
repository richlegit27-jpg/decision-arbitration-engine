from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "tools" / "nova_memory_quality_smoke.py"


def main():
    text = TARGET.read_text(encoding="utf-8", errors="replace")
    before = text

    if "class _NovaQuietWerkzeugRequestHandler" not in text:
        anchor = "from werkzeug.serving import make_server"
        replacement = '''from werkzeug.serving import WSGIRequestHandler, make_server


class _NovaQuietWerkzeugRequestHandler(WSGIRequestHandler):
    def log(self, type, message, *args):
        return

'''
        if anchor not in text:
            raise SystemExit("Could not find werkzeug make_server import")

        text = text.replace(anchor, replacement, 1)

    old = 'server = make_server("127.0.0.1", 5001, nova_app, threaded=True)'
    new = '''server = make_server(
        "127.0.0.1",
        5001,
        nova_app,
        threaded=True,
        request_handler=_NovaQuietWerkzeugRequestHandler,
    )'''

    if old not in text and "request_handler=_NovaQuietWerkzeugRequestHandler" not in text:
        raise SystemExit("Could not find make_server call to patch")

    text = text.replace(old, new, 1)

    if text == before:
        raise SystemExit("No Phase 4W changes made")

    TARGET.write_text(text, encoding="utf-8")
    print("NOVA PHASE 4W QUIET WERKZEUG TEST SERVER PATCHED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
