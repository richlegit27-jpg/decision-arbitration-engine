from nova_backend.services.attachment_action_service import (
    AttachmentActionService,
)


class FakeUploadRouteService:
    def __init__(self):
        self.calls = []

    def handle_upload(
        self,
        file,
        auth_user_id="",
        logger=None,
        secure_filename=None,
    ):
        self.calls.append(
            {
                "file": file,
                "auth_user_id": auth_user_id,
                "logger": logger,
                "secure_filename": secure_filename,
            }
        )

        return {
            "ok": True,
            "filename": "test.txt",
            "url": "/api/uploads/test.txt",
        }


class FakeAttachmentAnalysisService:
    def analyze_binary_attachment_for_prompt(
        self,
        path,
        mime_type,
    ):
        return f"raw text from {path} ({mime_type})"

    def clean_extracted_attachment_text(self, text):
        return str(text or "").replace("raw ", "").strip()

    def local_summary_from_text(self, text):
        return {
            "summary": f"summary: {text}",
        }


def assert_true(name, condition, detail=None):
    if not condition:
        raise AssertionError(
            f"{name} FAILED"
            + (f" {detail}" if detail is not None else "")
        )

    print(f"PASS {name}")


def main():
    upload_service = FakeUploadRouteService()
    analysis_service = FakeAttachmentAnalysisService()

    adapter = AttachmentActionService(
        upload_route_service=upload_service,
        attachment_analysis_service=analysis_service,
        logger="logger",
        secure_filename="secure_filename",
    )

    upload_result = adapter.upload(
        file="fake-file",
        auth_user_id="user_test",
    )

    assert_true(
        "upload_delegates",
        upload_result.get("ok") is True
        and upload_result.get("filename") == "test.txt"
        and len(upload_service.calls) == 1,
        upload_result,
    )

    assert_true(
        "upload_context_forwarded",
        upload_service.calls[0]["auth_user_id"] == "user_test"
        and upload_service.calls[0]["logger"] == "logger"
        and upload_service.calls[0]["secure_filename"]
        == "secure_filename",
        upload_service.calls,
    )

    analyze_result = adapter.analyze(
        file_id="file_test",
        path="C:/uploads/test.txt",
        mime_type="text/plain",
    )

    assert_true(
        "analyze_delegates",
        analyze_result.get("ok") is True
        and analyze_result.get("file_id") == "file_test"
        and analyze_result.get("path") == "C:/uploads/test.txt"
        and "text from" in analyze_result.get("text", ""),
        analyze_result,
    )

    assert_true(
        "summary_returned",
        isinstance(analyze_result.get("summary"), dict)
        and "summary" in analyze_result["summary"],
        analyze_result,
    )

    missing_upload_service = AttachmentActionService().upload(
        file="fake-file",
    )

    assert_true(
        "missing_upload_service_safe",
        missing_upload_service.get("ok") is False
        and "not configured"
        in missing_upload_service.get("error", "").lower(),
        missing_upload_service,
    )

    missing_file = adapter.upload()

    assert_true(
        "missing_file_safe",
        missing_file.get("ok") is False
        and "no file provided"
        in missing_file.get("error", "").lower(),
        missing_file,
    )

    missing_analysis_service = AttachmentActionService().analyze(
        file_id="file_test",
    )

    assert_true(
        "missing_analysis_service_safe",
        missing_analysis_service.get("ok") is False
        and "not configured"
        in missing_analysis_service.get("error", "").lower(),
        missing_analysis_service,
    )

    missing_path = adapter.analyze()

    assert_true(
        "missing_path_safe",
        missing_path.get("ok") is False
        and "missing attachment path"
        in missing_path.get("error", "").lower(),
        missing_path,
    )

    print()
    print("NOVA ATTACHMENT ACTION SERVICE SMOKE PASSED")


if __name__ == "__main__":
    main()