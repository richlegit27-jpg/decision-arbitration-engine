document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("messageInput");
  const sendBtn = document.getElementById("sendBtn");
  const stopBtn = document.getElementById("stopBtn");
  const attachBtn = document.getElementById("attachBtn");
  const fileInput = document.getElementById("fileInput");
  const attachedFilesBar = document.getElementById("attachedFilesBar");

  if (!input || !sendBtn) return;

  let isSending = false;

  function autosizeInput() {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 220)}px`;
  }

  function renderAttachedFiles() {
    if (!attachedFilesBar || !fileInput) return;

    const files = Array.from(fileInput.files || []);
    if (!files.length) {
      attachedFilesBar.innerHTML = "";
      attachedFilesBar.style.display = "none";
      return;
    }

    attachedFilesBar.style.display = "flex";
    attachedFilesBar.innerHTML = files
      .map(
        (file, index) => `
          <div class="mini-chip">
            <span>ðŸ“Ž ${file.name}</span>
            <button type="button" data-remove-file="${index}" class="icon-btn" title="Remove file">âœ•</button>
          </div>
        `
      )
      .join("");
  }

  function setSendingState(next) {
    isSending = Boolean(next);

    sendBtn.disabled = isSending;
    if (attachBtn) attachBtn.disabled = isSending;
    if (input) input.disabled = isSending;

    if (stopBtn) {
      stopBtn.classList.toggle("hidden", !isSending);
    }
  }

  async function sendMessage() {
    if (isSending) return;

    const text = input.value.trim();
    const hasFiles = fileInput && fileInput.files && fileInput.files.length > 0;

    if (!text && !hasFiles) return;
    if (!window.NovaApp || typeof window.NovaApp.ensureActiveChat !== "function") {
      console.error("NovaApp is not ready.");
      return;
    }

    try {
      setSendingState(true);

      const chat = await window.NovaApp.ensureActiveChat();
      if (!chat || !chat.id) {
        throw new Error("No active chat available.");
      }

      // ðŸ”¹ instant UI add
      if (text) {
        window.dispatchEvent(
          new CustomEvent("nova:message-added", {
            detail: {
              chatId: chat.id,
              message: {
                role: "user",
                content: text,
                created_at: new Date().toISOString(),
              },
            },
          })
        );
      }

      const response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        credentials: "same-origin",
        body: JSON.stringify({
          chat_id: chat.id,
          message: text,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `HTTP ${response.status}${errorText ? ` - ${errorText}` : ""}`
        );
      }

      if (!response.body) {
        throw new Error("Streaming response body is unavailable.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let buffer = "";
      let assistantText = "";
      let imageUrl = "";
      let attachments = [];

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const eventBlock of events) {
          const dataLine = eventBlock
            .split("\n")
            .find((line) => line.startsWith("data:"));

          if (!dataLine) continue;

          const rawData = dataLine.slice(5).trim();
          if (!rawData) continue;

          let payload;

          try {
            payload = JSON.parse(rawData);
          } catch {
            continue;
          }

          if (payload.assistant_message) {
            assistantText =
              payload.assistant_message.text ||
              assistantText;

            imageUrl =
              payload.assistant_message.image_url ||
              imageUrl;

            attachments =
              Array.isArray(payload.assistant_message.attachments)
                ? payload.assistant_message.attachments
                : attachments;
          }

          if (payload.image_url) {
            imageUrl = payload.image_url;
          }

          if (Array.isArray(payload.attachments)) {
            attachments = payload.attachments;
          }

          if (payload.type === "message" && payload.content) {
            assistantText = payload.content;
          }

          if (payload.type === "error") {
            throw new Error(
              payload.content || "Chat stream failed."
            );
          }
        }
      }

      const finalMessage = {
        role: "assistant",
        content: assistantText || "Generated image",
        created_at: new Date().toISOString(),
      };

      if (imageUrl) {
        finalMessage.image_url = imageUrl;
      }

      if (attachments.length) {
        finalMessage.attachments = attachments;
      }

      window.NovaApp.state.messagesByChatId[chat.id] = [
        ...(window.NovaApp.state.messagesByChatId[chat.id] || []),
        finalMessage,
      ];

      window.dispatchEvent(
        new Event("nova:messages-changed")
      );

      window.NovaApp.renderChatList?.();
      window.NovaApp.renderActiveChatCard?.();

      input.value = "";

    } catch (error) {
      console.error(error);
      if (window.NovaToast && typeof window.NovaToast.error === "function") {
        window.NovaToast.error(error.message || "Send failed.");
      } else {
        alert(error.message || "Send failed.");
      }

    } finally {
      setSendingState(false);

      if (window.NovaApp?.state) {
        window.NovaApp.state.attachedFiles = [];
      }
      if (fileInput) {
        fileInput.value = "";
      }
      if (window.NovaApp?.renderAttachedFiles) {
        window.NovaApp.renderAttachedFiles();
      } else {
        renderAttachedFiles();
      }
      input.focus();
    }
  }

  if (attachBtn && fileInput) {
    attachBtn.addEventListener("click", () => {
      if (isSending) return;
      fileInput.click();
    });

    fileInput.addEventListener("change", () => {
      renderAttachedFiles();
    });
  }

  if (attachedFilesBar && fileInput) {
    attachedFilesBar.addEventListener("click", (event) => {
      const btn = event.target.closest("[data-remove-file]");
      if (!btn) return;

      const removeIndex = Number(btn.getAttribute("data-remove-file"));
      if (!Number.isFinite(removeIndex)) return;

      const existing = Array.from(fileInput.files || []);
      const dt = new DataTransfer();

      existing.forEach((file, index) => {
        if (index !== removeIndex) dt.items.add(file);
      });

      fileInput.files = dt.files;
      renderAttachedFiles();
    });
  }

  sendBtn.addEventListener("click", sendMessage);

  input.addEventListener("input", autosizeInput);

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });

  if (stopBtn) {
    stopBtn.addEventListener("click", () => {
      input.value = "";
      autosizeInput();
      setSendingState(false);
    });
  }

  autosizeInput();
  renderAttachedFiles();
});

