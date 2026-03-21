import os
import sys


PROJECT_ROOT = r"C:\Users\Owner\nova"


def bootstrap():
    os.chdir(PROJECT_ROOT)

    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

    runtime_dirs = [
        os.path.join(PROJECT_ROOT, "runtime"),
        os.path.join(PROJECT_ROOT, "runtime", "uploads"),
        os.path.join(PROJECT_ROOT, "runtime", "memory"),
        os.path.join(PROJECT_ROOT, "runtime", "tasks"),
        os.path.join(PROJECT_ROOT, "runtime", "logs"),
        os.path.join(PROJECT_ROOT, "runtime", "backups"),
    ]

    for path in runtime_dirs:
        os.makedirs(path, exist_ok=True)


def main():
    bootstrap()

    from backend.production_server import start
    start()


if __name__ == "__main__":
    main()