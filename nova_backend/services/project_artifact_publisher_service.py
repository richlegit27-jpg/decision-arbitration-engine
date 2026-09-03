from __future__ import annotations

import mimetypes
import shutil
import uuid
from pathlib import Path

from nova_backend.config import UPLOADS_DIR


class ProjectArtifactPublisherService:

    def __init__(
        self,
        project_workspace_service,
        sandbox_dir=None,
        uploads_dir=None,
    ):
        self.project_workspace_service = (
            project_workspace_service
        )

        self.sandbox_dir = Path(
            sandbox_dir
            or (
                Path(__file__).resolve().parents[1]
                / "sandbox"
            )
        ).resolve()

        self.uploads_dir = Path(
            uploads_dir
            or UPLOADS_DIR
        ).resolve()

        self.uploads_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _resolve_sandbox_file(
        self,
        target_file,
    ):
        target = str(
            target_file or ""
        ).strip()

        if not target:
            return None

        candidate = (
            self.sandbox_dir / target
        ).resolve()

        try:
            candidate.relative_to(
                self.sandbox_dir
            )
        except ValueError:
            return None

        return candidate

    def _safe_artifact_name(
        self,
        value,
    ):
        text = str(
            value or ""
        ).strip()

        if not text:
            return "artifact"

        cleaned = []

        for char in text:
            if char.isalnum() or char in {
                "-",
                "_",
            }:
                cleaned.append(char)
            elif char.isspace():
                cleaned.append("_")

        result = "".join(cleaned).strip(
            "_.-"
        )

        return result or "artifact"

    def _create_text_artifact(
        self,
        project_id,
        task,
        result,
    ):
        output = str(
            result or ""
        ).strip()

        if not output:
            return None

        title = str(
            task.get(
                "title",
                "Project Artifact",
            )
            or "Project Artifact"
        ).strip()

        stem = self._safe_artifact_name(
            title
        )

        original_name = (
            f"{stem}.md"
        )

        destination_name = (
            f"{stem}_{uuid.uuid4().hex}.md"
        )

        destination = (
            self.uploads_dir
            / destination_name
        )

        document = (
            f"# {title}\n\n"
            f"{output.rstrip()}\n"
        )

        destination.write_text(
            document,
            encoding="utf-8",
        )

        size = destination.stat().st_size

        file_record = (
            self.project_workspace_service.add_file(
                project_id,
                original_name,
                str(destination),
                size,
                "text/markdown",
            )
        )

        if not file_record:
            try:
                destination.unlink(
                    missing_ok=True
                )
            except Exception:
                pass

            return None

        file_record["url"] = (
            f"/api/uploads/{destination_name}"
        )

        file_record["download_url"] = (
            f"/api/projects/"
            f"{project_id}/files/"
            f"{file_record.get('id')}/download"
        )

        file_record["generated"] = True
        file_record["source"] = "ai_execution"

        return file_record

    def _publish_existing_file(
        self,
        project_id,
        target_file,
    ):
        source = self._resolve_sandbox_file(
            target_file
        )

        if source is None:
            return None

        if not source.is_file():
            return None

        original_name = (
            Path(target_file).name
            or source.name
            or "artifact"
        )

        suffix = source.suffix

        stem = (
            Path(original_name).stem
            or "artifact"
        )

        destination_name = (
            f"{stem}_{uuid.uuid4().hex}"
            f"{suffix}"
        )

        destination = (
            self.uploads_dir
            / destination_name
        )

        shutil.copy2(
            source,
            destination,
        )

        size = destination.stat().st_size

        mime_type = (
            mimetypes.guess_type(
                original_name
            )[0]
            or "application/octet-stream"
        )

        file_record = (
            self.project_workspace_service.add_file(
                project_id,
                original_name,
                str(destination),
                size,
                mime_type,
            )
        )

        if not file_record:
            try:
                destination.unlink(
                    missing_ok=True
                )
            except Exception:
                pass

            return None

        file_record["url"] = (
            f"/api/uploads/{destination_name}"
        )

        file_record["download_url"] = (
            f"/api/projects/"
            f"{project_id}/files/"
            f"{file_record.get('id')}/download"
        )

        file_record["source_target"] = (
            target_file
        )

        file_record["generated"] = False
        file_record["source"] = "execution_file"

        return file_record

    def publish_task_artifact(
        self,
        project_id,
        task,
        result=None,
    ):
        if not isinstance(
            task,
            dict,
        ):
            return None

        target_file = str(
            task.get(
                "target_file",
                "",
            )
            or ""
        ).strip()

        if target_file:
            file_artifact = (
                self._publish_existing_file(
                    project_id,
                    target_file,
                )
            )

            if file_artifact:
                return file_artifact

        return self._create_text_artifact(
            project_id,
            task,
            result,
        )