import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import webbrowser
import subprocess

NOVA_DIR = r"C:\Users\Owner\nova"
SERVER_SCRIPT = os.path.join(NOVA_DIR, "nova_app.py")
BROWSER_URL = "http://127.0.0.1:8743/"

class HMRHandler(FileSystemEventHandler):
    def __init__(self, process):
        self.process = process

    def on_modified(self, event):
        if event.src_path.endswith((".js", ".css", ".html")):
            print(f"[HMR] Detected change in {event.src_path}, reloading...")
            self.process.terminate()
            time.sleep(0.5)
            self.process = subprocess.Popen(["python", SERVER_SCRIPT], cwd=NOVA_DIR)

if __name__ == "__main__":
    # Open browser
    webbrowser.open(BROWSER_URL)

    # Start backend
    process = subprocess.Popen(["python", SERVER_SCRIPT], cwd=NOVA_DIR)

    # Watch for file changes
    event_handler = HMRHandler(process)
    observer = Observer()
    observer.schedule(event_handler, path=NOVA_DIR, recursive=True)
    observer.start()

    print("HMR running... Ctrl+C to stop")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        process.terminate()
    observer.join()