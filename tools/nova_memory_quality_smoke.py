from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import threading
import time
import urllib.request

from werkzeug.serving import WSGIRequestHandler, make_server


ROOT = Path(__file__).resolve().parents[1]
SERVER_URL = "http://127.0.0.1:5001"

SMOKES = [
    "nova_project_state_smoke.py",
    "nova_project_compact_context_api_smoke.py",
    "nova_autonomy_task_brain_smoke.py",
    "nova_autonomy_command_api_smoke.py",
]


class _NovaQuietWerkzeugRequestHandler(WSGIRequestHandler):
    def log(self, type, message, *args):
        return


def server_reachable() -> bool:
    try:
        urllib.request.urlopen(f"{SERVER_URL}/api/health", timeout=1)
        return True
    except Exception:
        return False


def wait_for_server(seconds: int = 20) -> bool:
    deadline = time.time() + seconds

    while time.time() < deadline:
        if server_reachable():
            return True

        time.sleep(0.25)

    return False


def start_test_server():
    sys.path.insert(0, str(ROOT))

    from app import app as nova_app

    server = make_server(
        "127.0.0.1",
        5001,
        nova_app,
        threaded=True,
        request_handler=_NovaQuietWerkzeugRequestHandler,
    )

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    return server


def run_smoke(filename: str) -> None:
    smoke_path = ROOT / "tools" / filename

    if not smoke_path.exists():
        raise FileNotFoundError(f"Missing smoke: {smoke_path}")

    print("")
    print(f"=== {filename} ===")
    subprocess.run([sys.executable, str(smoke_path)], cwd=ROOT, check=True)
    print(f"PASS {filename}")


def main():
    server = None

    if server_reachable():
        print(f"PASS Nova server already reachable at {SERVER_URL}")
    else:
        print(f"Starting Nova test server at {SERVER_URL}")
        server = start_test_server()

        if not wait_for_server():
            raise SystemExit(f"FAILED: Nova server not reachable at {SERVER_URL}")

        print(f"PASS Nova test server reachable at {SERVER_URL}")

    try:
        for filename in SMOKES:
            run_smoke(filename)
    finally:
        if server is not None:
            server.shutdown()
            print("PASS Nova test server stopped")

    print("")
    print("NOVA MEMORY QUALITY SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
