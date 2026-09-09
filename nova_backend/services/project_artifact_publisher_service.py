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

        self.sandbox_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

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

        result = "".join(
            cleaned
        ).strip(
            "_.-"
        )

        return result or "artifact"

    def _extract_result_text(
        self,
        result,
    ):
        if result is None:
            return ""

        if isinstance(
            result,
            str,
        ):
            return result.strip()

        if isinstance(
            result,
            dict,
        ):
            for key in (
                "result",
                "output",
                "content",
                "message",
                "text",
            ):
                value = result.get(key)

                if isinstance(
                    value,
                    str,
                ) and value.strip():
                    return value.strip()

            return ""

        return str(
            result
        ).strip()

    def _write_result_to_target(
        self,
        target_file,
        result,
    ):
        target = self._resolve_sandbox_file(
            target_file
        )

        if target is None:
            return None

        output = self._extract_result_text(
            result
        )

        if not output:
            return None

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            target.write_text(
                output.rstrip() + "\n",
                encoding="utf-8",
            )
        except Exception as exc:
            print(
                "[PROJECT ARTIFACT WRITE FAILED]",
                target_file,
                str(exc),
                flush=True,
            )

            return None

        print(
            "[PROJECT ARTIFACT RESULT WRITTEN]",
            {
                "target_file": target_file,
                "path": str(target),
                "size": target.stat().st_size,
            },
            flush=True,
        )

        return target

    def _create_text_artifact(
        self,
        project_id,
        task,
        result,
    ):
        output = self._extract_result_text(
            result
        )

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

        if size <= 0:
            try:
                destination.unlink(
                    missing_ok=True
                )
            except Exception:
                pass

            return None

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

        try:
            source_size = source.stat().st_size
        except Exception:
            return None

        if source_size <= 0:
            print(
                "[PROJECT ARTIFACT SKIPPING EMPTY FILE]",
                {
                    "target_file": target_file,
                    "path": str(source),
                },
                flush=True,
            )

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

        if size <= 0:
            try:
                destination.unlink(
                    missing_ok=True
                )
            except Exception:
                pass

            return None

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

        print(
            "[PROJECT ARTIFACT PUBLISHED]",
            {
                "project_id": project_id,
                "filename": original_name,
                "size": size,
            },
            flush=True,
        )

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

        if not target_file:
            print(
                "[PROJECT ARTIFACT SKIPPED - NO TARGET FILE]",
                {
                    "project_id": project_id,
                    "task_title": task.get("title"),
                    "task_id": task.get("id"),
                },
                flush=True,
            )

            return None

        source = self._resolve_sandbox_file(
            target_file
        )

        source_has_content = False

        if (
            source is not None
            and source.is_file()
        ):
            try:
                source_has_content = (
                    source.stat().st_size > 0
                )
            except Exception:
                source_has_content = False

        if not source_has_content:
            written_target = (
                self._write_result_to_target(
                    target_file,
                    result,
                )
            )

            if written_target is None:
                print(
                    "[PROJECT ARTIFACT WRITE FAILED]",
                    {
                        "project_id": project_id,
                        "target_file": target_file,
                        "task_title": task.get("title"),
                    },
                    flush=True,
                )

                return None

        file_artifact = (
            self._publish_existing_file(
                project_id,
                target_file,
            )
        )

        if file_artifact:
            return file_artifact

        print(
            "[PROJECT ARTIFACT PUBLISH FAILED]",
            {
                "project_id": project_id,
                "target_file": target_file,
                "task_title": task.get("title"),
            },
            flush=True,
        )

        return None