import time
import webbrowser
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- Config ---
FRONTEND_FILE = Path(__file__).parent / "templates" / "index.html"
WATCH_PATHS = [
    Path(__file__).parent / "templates",
    Path(__file__).parent / "static" / "css",
    Path(__file__).parent / "static" / "js"
]
THROTTLE_SECONDS = 1  # Minimum delay between reloads

# --- Event Handler ---
class ThrottleReloadHandler(FileSystemEventHandler):
    def __init__(self):
        self._last_reload = 0

    def on_modified(self, event):
        now = time.time()
        if now - self._last_reload > THROTTLE_SECONDS:
            self._last_reload = now
            print(f"[live_reload] Detected change: {event.src_path}")
            try:
                webbrowser.open(FRONTEND_FILE.as_uri(), new=0)
            except Exception as e:
                print(f"[live_reload] Failed to reload: {e}")

# --- Observer Setup ---
observer = Observer()
handler = ThrottleReloadHandler()
for path in WATCH_PATHS:
    observer.schedule(handler, str(path), recursive=True)

print("[live_reload] Watching frontend files with throttle...")
observer.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()