(function () {
  "use strict";

  let micStream = null;
  let mediaRecorder = null;
  let chunks = [];
  let recording = false;
  let clickWired = false;

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

  function injectStyles() {
    if (document.querySelector("#nova-mic-recorder-style")) {
      return;
    }

    const style = document.createElement("style");
    style.id = "nova-mic-recorder-style";
    style.textContent = `
      #nova-mic-recorder-button {
        position: fixed;
        right: 24px;
        bottom: 24px;
        z-index: 2147483647;
        width: 56px;
        height: 56px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.18);
        background: linear-gradient(135deg, #111827, #1f2937);
        color: white;
        font-size: 24px;
        cursor: pointer;
        box-shadow: 0 14px 40px rgba(0,0,0,0.38);
        display: flex;
        align-items: center;
        justify-content: center;
        visibility: visible;
        opacity: 1;
        pointer-events: auto;
        transition:
          transform 140ms ease,
          box-shadow 140ms ease,
          background 140ms ease,
          border-color 140ms ease;
      }

      #nova-mic-recorder-button:hover {
        transform: translateY(-2px) scale(1.04);
        box-shadow: 0 18px 50px rgba(0,0,0,0.46);
        border-color: rgba(255,255,255,0.34);
      }

      #nova-mic-recorder-button.is-recording {
        background: linear-gradient(135deg, #7f1d1d, #dc2626);
        animation: novaMicPulse 1.05s infinite;
      }

      #nova-mic-recorder-button.is-busy {
        opacity: 0.75;
        cursor: wait;
      }

      #nova-mic-recorder-label {
        position: fixed;
        right: 88px;
        bottom: 35px;
        z-index: 2147483647;
        padding: 7px 10px;
        border-radius: 999px;
        background: rgba(17,24,39,0.92);
        color: white;
        font-size: 12px;
        line-height: 1;
        border: 1px solid rgba(255,255,255,0.16);
        box-shadow: 0 10px 28px rgba(0,0,0,0.25);
        opacity: 0;
        transform: translateX(8px);
        pointer-events: none;
        transition:
          opacity 140ms ease,
          transform 140ms ease;
      }

      #nova-mic-recorder-label.is-visible {
        opacity: 1;
        transform: translateX(0);
      }

      @keyframes novaMicPulse {
        0% {
          box-shadow: 0 0 0 0 rgba(239,68,68,0.48), 0 14px 40px rgba(0,0,0,0.38);
        }
        70% {
          box-shadow: 0 0 0 14px rgba(239,68,68,0), 0 14px 40px rgba(0,0,0,0.38);
        }
        100% {
          box-shadow: 0 0 0 0 rgba(239,68,68,0), 0 14px 40px rgba(0,0,0,0.38);
        }
      }
    `;

    document.head.appendChild(style);
  }

  function setLabel(text, visible) {
    let label = document.querySelector("#nova-mic-recorder-label");

    if (!label) {
      label = document.createElement("div");
      label.id = "nova-mic-recorder-label";
      document.body.appendChild(label);
    }

    label.textContent = text || "";

    if (visible) {
      label.classList.add("is-visible");
    } else {
      label.classList.remove("is-visible");
    }
  }

  function setButtonState(button, state) {
    if (!button) {
      return;
    }

    button.classList.remove("is-recording", "is-busy");

    if (state === "recording") {
      button.textContent = "⏹️";
      button.title = "Stop recording";
      button.classList.add("is-recording");
      setLabel("Recording… click to stop", true);
      return;
    }

    if (state === "busy") {
      button.textContent = "⏳";
      button.title = "Transcribing...";
      button.classList.add("is-busy");
      setLabel("Transcribing…", true);
      return;
    }

    button.textContent = "🎙️";
    button.title = "Record voice";
    setLabel("", false);
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
      user_text: "what is in this audio?",
      session_id: getActiveSessionId(),
      attachments: [attachment],
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

  async function start(button) {
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
        setButtonState(button, "busy");

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

        setButtonState(button, "idle");
      }
    };

    mediaRecorder.start();
    recording = true;

    setButtonState(button, "recording");

    console.log("[NovaMicRecorder] recording started");
  }

  function stop() {
    if (mediaRecorder && recording) {
      mediaRecorder.stop();
      console.log("[NovaMicRecorder] recording stopped");
    }
  }

  async function handleMicClick(event) {
    const clickedButton = event.target.closest("#nova-mic-recorder-button");

    if (!clickedButton) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();

    try {
      if (recording) {
        stop();
        return;
      }

      await start(clickedButton);
    } catch (error) {
      console.error("[NovaMicRecorder] mic failed", error);
      appendMessage("assistant", "Mic failed: " + error.message);
      setButtonState(clickedButton, "idle");
    }
  }

  function ensureButton() {
    injectStyles();

    let button = document.querySelector("#nova-mic-recorder-button");

    if (!button) {
      button = document.createElement("button");
      button.id = "nova-mic-recorder-button";
      button.type = "button";
      document.body.appendChild(button);
    }

    setButtonState(button, "idle");

    button.onclick = handleMicClick;

    if (!clickWired) {
      document.addEventListener("click", handleMicClick, true);
      clickWired = true;
    }

    console.log("[NovaMicRecorder] button ready", button);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ensureButton);
  } else {
    ensureButton();
  }

  window.NovaMicRecorder = {
    start: function () {
      const button = document.querySelector("#nova-mic-recorder-button");
      return start(button);
    },
    stop: stop,
    ensureButton: ensureButton,
  };
})();