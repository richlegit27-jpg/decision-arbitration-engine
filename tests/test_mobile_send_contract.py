from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _send_now_source():
    source = (ROOT / "static/js/nova-mobile-app.js").read_text(encoding="utf-8")
    start = source.index("async function sendNow(event) {")
    end = source.index("\nfunction wireSend()", start)
    return source[start:end]


def test_mobile_send_keeps_failed_message_and_attachments_recoverable():
    send_now = _send_now_source()

    assert send_now.index("const attachments = currentAttachmentsForSend()") < send_now.index(
        "const res = await fetch(\"/api/chat\""
    )
    assert "if (!res.ok || data?.ok === false)" in send_now
    assert send_now.index("if (!res.ok || data?.ok === false)") < send_now.index(
        "clearAttachmentsAfterSend();"
    )
    assert "if (!String(input.value || \"\").trim())" in send_now
    assert "input.value = text;" in send_now


def test_mobile_send_passes_abort_signal_for_stop_control():
    send_now = _send_now_source()

    assert "const abortController = new AbortController();" in send_now
    assert "signal: abortController.signal" in send_now
    assert "window.NovaMobileAbortController = abortController;" in send_now
    assert "window.NovaMobileAbortController = null;" in send_now


def test_mobile_model_picker_uses_available_models_and_sends_selection():
    source = (ROOT / "static/js/nova-mobile-app.js").read_text(encoding="utf-8")

    assert 'fetch("/api/models"' in source
    assert 'fetch("/api/models/select"' in source
    assert 'if (modelSelector && (modelSelector.disabled || !selectedModel))' in source
    assert 'model: selectedModel' in source
    assert 'new Option("No model provider available", "")' in source
