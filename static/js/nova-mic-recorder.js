(function () {
  "use strict";

  let micStream = null;
  let mediaRecorder = null;
  let chunks = [];
  let recording = false;
  let busy = false;
  let wired = false;
  let lastToggleAt = 0;

  function getActiveSessionId() {
    return (
      window.activeSessionId ||
      window.state?.activeSessionId ||
      localStorage.getItem("nova_active_session_id") ||
      ""
    );
  }

  function findThread() {
    return (
      document.querySelector("[data-chat-thread]") ||
      document.querySelector(".nova-thread") ||
      document.querySelector("#chat-thread") ||
      document.querySelector(".chat-thread")
    );
  }

  function appendMessage(role, text) {
    const thread = findThread();

    if (!thread) {
      console.log("[NovaMicRecorder]", role, text);
      return;
    }

    const row = document.createElement("div");
    row.className = "nova-message nova-message-" + role;
    row.innerHTML = `
      <div class="nova-message-role">${role}</div>
      <div class="nova-message-text">${String(text || "").replace(/\n/g, "<br>")}</div>
    `;

    thread.appendChild(row);
    thread.scrollTop = thread.scrollHeight;
  }

  function getVoiceButton() {
    return document.querySelector('[data-action="voice"]');
  }

  function setButtonState(state) {
    const button = getVoiceButton();

    if (!button) {
      return;
    }

    button.classList.remove("is-recording", "is-busy");

    if (state === "recording") {
      button.textContent = "⏹️";
      button.title = "Stop recording";
      button.setAttribute("aria-label", "Stop recording");
      button.classList.add("is-recording");
      return;
    }

    if (state === "busy") {
      button.textContent = "⏳";
      button.title = "Transcribing";
      button.setAttribute("aria-label", "Transcribing");
      button.classList.add("is-busy");
      return;
    }

    button.textContent = "🎤";
    button.title = "Voice";
    button.setAttribute("aria-label", "Voice");
  }

  async function uploadBlob(blob) {
    const file = new File(
      [blob],
      "nova_mic_recording.webm",
      { type: "audio/webm" }
    );

    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch("/api/upload", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.error || "Upload failed.");
    }

    const uploaded = data.attachment || data.file || data.upload || data;

    return {
      id: uploaded.id || "mic_" + Date.now(),
      name: uploaded.name || file.name,
      filename: uploaded.filename || file.name,
      original_name: uploaded.original_name || file.name,
      stored_name: uploaded.stored_name || uploaded.filename || file.name,
      url: uploaded.url || uploaded.file_url || "",
      mime_type: uploaded.mime_type || file.type || "audio/webm",
      size: uploaded.size || file.size,
      status: "uploaded",
    };
  }

  async function sendToChat(attachment) {
    const payload = {
      user_text: "voice_input",
      session_id: getActiveSessionId(),
      attachments: [attachment],
      meta: {
        voice_conversation: true,
      },
    };

    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.error || "Chat request failed.");
    }

    const text =
      data.assistant_message?.text ||
      data.message ||
      "No response text returned.";

    appendMessage("assistant", text);
    console.log("[NovaMicRecorder] chat response", data);

    return data;
  }

  async function startRecording() {
    if (recording || busy) {
      return;
    }

    chunks = [];

    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(micStream);

    mediaRecorder.ondataavailable = function (event) {
      if (event.data && event.data.size > 0) {
        chunks.push(event.data);
      }
    };

    mediaRecorder.onstop = async function () {
      try {
        busy = true;
        setButtonState("busy");

        const blob = new Blob(chunks, { type: "audio/webm" });

        appendMessage("user", "🎙️ Voice recording sent for transcription...");

        const attachment = await uploadBlob(blob);
        await sendToChat(attachment);
      } catch (error) {
        console.error("[NovaMicRecorder] failed", error);
        appendMessage("assistant", "Mic transcription failed: " + error.message);
      } finally {
        if (micStream) {
          micStream.getTracks().forEach(function (track) {
            track.stop();
          });
        }

        micStream = null;
        mediaRecorder = null;
        chunks = [];
        recording = false;
        busy = false;

        setButtonState("idle");
      }
    };

    mediaRecorder.start();
    recording = true;

    setButtonState("recording");

    console.log("[NovaMicRecorder] recording started");
  }

  function stopRecording() {
    if (mediaRecorder && recording) {
      mediaRecorder.stop();
      console.log("[NovaMicRecorder] recording stopped");
    }
  }

  async function toggleRecorder(event) {
    const voiceButton = event.target.closest('[data-action="voice"]');

    if (!voiceButton) {
      return;
    }

    const now = Date.now();

    if (now - lastToggleAt < 700) {
      return;
    }

    lastToggleAt = now;

    event.preventDefault();
    event.stopPropagation();

    if (typeof event.stopImmediatePropagation === "function") {
      event.stopImmediatePropagation();
    }

    try {
      if (recording) {
        stopRecording();
        return;
      }

      await startRecording();
    } catch (error) {
      console.error("[NovaMicRecorder] mic failed", error);
      appendMessage("assistant", "Mic failed: " + error.message);
      recording = false;
      busy = false;
      setButtonState("idle");
    }
  }

  function wireComposerMic() {
    const button = getVoiceButton();

    if (!button) {
      console.warn("[NovaMicRecorder] composer voice button not found");
      return;
    }

    button.setAttribute("data-nova-mic-bound", "true");
    button.style.pointerEvents = "auto";
    button.style.cursor = "pointer";

    if (!wired) {
      document.addEventListener("click", toggleRecorder, true);
      wired = true;
    }

    setButtonState("idle");

    console.log("[NovaMicRecorder] composer voice button wired", button);
  }

  function boot() {
    wireComposerMic();

    setTimeout(wireComposerMic, 500);
    setTimeout(wireComposerMic, 1500);
    setTimeout(wireComposerMic, 3000);
    setTimeout(wireComposerMic, 5000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.NovaMicRecorder = {
    start: startRecording,
    stop: stopRecording,
    wire: wireComposerMic,
  };
})();