from pathlib import Path
import os


class RuntimeUploadsNormalizerService:

    def normalize(self, service):
        try:
            current = Path(
                getattr(service, "uploads_dir", "uploads")
            )

            current_text = str(current)

            if os.name != "nt" and (
                ":" in current_text or "\\" in current_text
            ):
                current = Path.cwd() / "uploads"

            current.mkdir(
                parents=True,
                exist_ok=True,
            )

            service.uploads_dir = current

            return current

        except Exception:
            return getattr(
                service,
                "uploads_dir",
                None,
            )
