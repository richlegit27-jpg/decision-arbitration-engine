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

        if (button) {
          button.textContent = "🎙️";
          button.title = "Record voice";
          button.classList.remove("is-recording");
        }
      }
    };

    mediaRecorder.start();
    recording = true;

    if (button) {
      button.textContent = "⏹️";
      button.title = "Stop recording";
      button.classList.add("is-recording");
    }

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
    }
  }

  function ensureButton() {
    let button = document.querySelector("#nova-mic-recorder-button");

    if (!button) {
      button = document.createElement("button");
      button.id = "nova-mic-recorder-button";
      button.type = "button";
      button.textContent = "🎙️";
      button.title = "Record voice";

      button.style.position = "fixed";
      button.style.right = "24px";
      button.style.bottom = "24px";
      button.style.zIndex = "2147483647";
      button.style.width = "60px";
      button.style.height = "60px";
      button.style.borderRadius = "999px";
      button.style.border = "3px solid white";
      button.style.background = "red";
      button.style.color = "white";
      button.style.fontSize = "26px";
      button.style.cursor = "pointer";
      button.style.boxShadow = "0 10px 30px rgba(0,0,0,0.45)";
      button.style.display = "block";
      button.style.visibility = "visible";
      button.style.opacity = "1";
      button.style.pointerEvents = "auto";

      document.body.appendChild(button);
    }

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