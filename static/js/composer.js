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
            <span>📎 ${file.name}</span>
            <button type="button" data-remove-file="${index}" class="icon-btn" title="Remove file">✕</button>
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

      // 🔹 instant UI add
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

      const payload = {
        content: text,
        model: window.NovaApp.state?.selectedModel || "nova-default",
      };

      const response = await window.NovaApp.apiFetch(`/api/chats/${chat.id}/messages`, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      const serverMessages = Array.isArray(response?.messages)
        ? response.messages
        : Array.isArray(response?.items)
        ? response.items
        : Array.isArray(response)
        ? response
        : [];

      // 🔹 sync state
      window.NovaApp.state.messagesByChatId[chat.id] = serverMessages;

      // 🔥 THIS IS THE FIX
      window.dispatchEvent(new Event("nova:messages-changed"));

      if (Array.isArray(window.NovaApp.state.chats)) {
        const index = window.NovaApp.state.chats.findIndex(
          (item) => Number(item.id) === Number(chat.id)
        );

        if (index >= 0) {
          window.NovaApp.state.chats[index] = {
            ...window.NovaApp.state.chats[index],
            message_count: serverMessages.length,
            updated_at: new Date().toISOString(),
          };
        }
      }

      window.NovaApp.renderChatList?.();
      window.NovaApp.renderActiveChatCard?.();

      input.value = "";
      autosizeInput();

      if (fileInput) {
        fileInput.value = "";
      }
      renderAttachedFiles();
    } catch (error) {
      console.error(error);
      if (window.NovaToast && typeof window.NovaToast.error === "function") {
        window.NovaToast.error(error.message || "Send failed.");
      } else {
        alert(error.message || "Send failed.");
      }
    } finally {
      setSendingState(false);
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