(() => {
  "use strict";

  const Nova = (window.Nova = window.Nova || {});
  Nova.composer = Nova.composer || {};

  const state = {
    sessionId: "default-session",
    pendingFiles: [],
    sending: false,
  };

  function $(selector, root = document) {
    return root.querySelector(selector);
  }

  function text(value) {
    if (value == null) return "";
    if (typeof value === "string") return value;
    if (typeof value === "number" || typeof value === "boolean") return String(value);
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }

  function safeMessageText(value) {
    if (value == null) return "";

    if (typeof value === "string") return value;
    if (typeof value === "number" || typeof value === "boolean") return String(value);

    if (Array.isArray(value)) {
      return value.map(safeMessageText).filter(Boolean).join("\n");
    }

    if (typeof value === "object") {
      if (typeof value.content === "string") return value.content;
      if (typeof value.text === "string") return value.text;
      if (typeof value.message === "string") return value.message;
      if (typeof value.output_text === "string") return value.output_text;

      if (value.message && typeof value.message === "object") {
        if (typeof value.message.content === "string") return value.message.content;
        if (typeof value.message.text === "string") return value.message.text;
      }

      if (Array.isArray(value.content)) {
        return value.content.map(safeMessageText).filter(Boolean).join("\n");
      }

      if (Array.isArray(value.output)) {
        return value.output
          .map((entry) => {
            if (!entry) return "";
            if (typeof entry.text === "string") return entry.text;
            if (Array.isArray(entry.content)) {
              return entry.content.map(safeMessageText).filter(Boolean).join("\n");
            }
            return safeMessageText(entry);
          })
          .filter(Boolean)
          .join("\n");
      }

      try {
        return JSON.stringify(value, null, 2);
      } catch {
        return String(value);
      }
    }

    return String(value);
  }

  function setBusy(isBusy) {
    state.sending = Boolean(isBusy);

    const sendBtn = $("#sendBtn");
    const chatInput = $("#chatInput");
    const uploadBtn = $("#uploadBtn");

    if (sendBtn) {
      sendBtn.disabled = state.sending;
      sendBtn.textContent = state.sending ? "Sending..." : "Send";
    }

    if (chatInput) {
      chatInput.disabled = state.sending;
    }

    if (uploadBtn) {
      uploadBtn.disabled = state.sending;
    }
  }

  async function callJson(url, options = {}) {
    const response = await fetch(url, options);
    const raw = await response.text();

    let data = null;
    try {
      data = raw ? JSON.parse(raw) : null;
    } catch {
      data = raw;
    }

    if (!response.ok) {
      const message =
        (data && data.error) ||
        (data && data.message) ||
        raw ||
        `Request failed: ${response.status}`;
      throw new Error(message);
    }

    return data;
  }

  function ensureRender() {
    if (!window.Nova?.render?.appendMessage) {
      throw new Error("Nova.render.appendMessage is missing");
    }
    return window.Nova.render;
  }

  function makeUserMessage(content, attachments = []) {
    return {
      id: `user_${Date.now()}`,
      role: "user",
      content: safeMessageText(content),
      created_at: new Date().toISOString(),
      attachments,
    };
  }

  function makeAssistantMessage(result) {
    const payload =
      result?.message && typeof result.message === "object"
        ? result.message
        : result;

    const content = safeMessageText(
      payload?.content ??
        payload?.text ??
        payload?.message ??
        result?.content ??
        result?.text ??
        result?.message ??
        ""
    );

    return {
      id: payload?.id || `assistant_${Date.now()}`,
      role: payload?.role || "assistant",
      content,
      created_at: payload?.created_at || new Date().toISOString(),
      attachments: Array.isArray(payload?.attachments) ? payload.attachments : [],
      debug: result?.debug || null,
      raw: result,
    };
  }

  function currentPendingFiles() {
    return Array.isArray(state.pendingFiles) ? [...state.pendingFiles] : [];
  }

  function clearPendingFiles() {
    state.pendingFiles = [];
    renderPendingFiles();
    const fileInput = $("#fileInput");
    if (fileInput) fileInput.value = "";
  }

  function renderPendingFiles() {
    const list =
      $("#novaPendingFiles") ||
      $("#pendingFiles") ||
      $('[data-pending-files]');

    if (!list) return;

    const files = currentPendingFiles();

    if (!files.length) {
      list.innerHTML = "";
      list.style.display = "none";
      return;
    }

    list.style.display = "";
    list.innerHTML = files
      .map((file, index) => {
        const name = text(file?.name || file?.filename || `attachment-${index + 1}`);
        const meta = [];
        if (file?.type) meta.push(text(file.type));
        if (file?.extracted_chars) meta.push(`${file.extracted_chars} chars`);

        return `
          <div class="nova-attachment-chip" data-pending-index="${index}" title="${name}">
            <span>${name}${meta.length ? ` • ${meta.join(" • ")}` : ""}</span>
            <button type="button" class="nova-attachment-chip-remove" data-remove-pending="${index}">×</button>
          </div>
        `;
      })
      .join("");
  }

  function installPendingFileEvents() {
    const list =
      $("#novaPendingFiles") ||
      $("#pendingFiles") ||
      $('[data-pending-files]');

    if (!list) return;

    list.addEventListener("click", (event) => {
      const btn = event.target.closest("[data-remove-pending]");
      if (!btn) return;

      const index = Number(btn.getAttribute("data-remove-pending"));
      if (!Number.isFinite(index)) return;

      state.pendingFiles.splice(index, 1);
      renderPendingFiles();
    });
  }

  async function uploadSelectedFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return [];

    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }

    const result = await callJson("/api/upload", {
      method: "POST",
      body: formData,
    });

    const uploaded = Array.isArray(result?.files) ? result.files : [];
    return uploaded.map((file) => ({
      name: file?.name || "",
      filename: file?.name || "",
      url: file?.url || "",
      size: file?.size || 0,
      type: file?.type || guessMimeTypeFromName(file?.name || ""),
      kind: file?.kind || "",
      content: file?.content || "",
      preview: file?.preview || "",
      extracted_chars: file?.extracted_chars || 0,
    }));
  }

  function guessMimeTypeFromName(name) {
    const lower = String(name || "").toLowerCase();
    if (lower.endsWith(".txt") || lower.endsWith(".md") || lower.endsWith(".log")) return "text/plain";
    if (lower.endsWith(".json")) return "application/json";
    if (lower.endsWith(".csv")) return "text/csv";
    if (lower.endsWith(".pdf")) return "application/pdf";
    if (lower.match(/\.(png|jpg|jpeg|gif|webp|bmp)$/)) return "image/*";
    return "";
  }

  async function sendChat() {
    if (state.sending) return;

    const render = ensureRender();
    const chatInput = $("#chatInput");
    if (!chatInput) {
      throw new Error("chatInput not found");
    }

    const userText = String(chatInput.value || "").trim();
    const attachmentsForSend = currentPendingFiles();

    if (!userText && !attachmentsForSend.length) {
      return;
    }

    render.appendMessage(makeUserMessage(userText, attachmentsForSend));

    chatInput.value = "";
    clearPendingFiles();
    setBusy(true);

    try {
      const result = await callJson("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: userText,
          session_id: state.sessionId,
          attachments: attachmentsForSend,
        }),
      });

      console.log("Nova route debug:", result?.debug || null);

      const assistantMessage = makeAssistantMessage(result);
      render.appendMessage(assistantMessage);

      if (window.Nova?.artifacts?.reload) {
        window.Nova.artifacts.reload().catch((err) => {
          console.warn("Artifact reload failed after chat:", err);
        });
      }
    } catch (error) {
      console.error("sendChat failed:", error);
      render.appendMessage({
        id: `assistant_error_${Date.now()}`,
        role: "assistant",
        content: `Error: ${safeMessageText(error?.message || error)}`,
        created_at: new Date().toISOString(),
      });
    } finally {
      setBusy(false);
      chatInput.focus();
    }
  }

  function handleSend() {
    sendChat().catch((err) => {
      console.error("handleSend failed:", err);
    });
  }

  function installComposerEvents() {
    const sendBtn = $("#sendBtn");
    const chatInput = $("#chatInput");
    const uploadBtn = $("#uploadBtn");
    const fileInput = $("#fileInput");

    if (sendBtn) {
      sendBtn.addEventListener("click", handleSend);
    }

    if (chatInput) {
      chatInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          handleSend();
        }
      });
    }

    if (uploadBtn && fileInput) {
      uploadBtn.addEventListener("click", () => {
        fileInput.click();
      });
    }

    if (fileInput) {
      fileInput.addEventListener("change", async (event) => {
        const files = event.target.files;
        if (!files || !files.length) return;

        try {
          setBusy(true);
          const uploaded = await uploadSelectedFiles(files);
          state.pendingFiles.push(...uploaded);
          renderPendingFiles();
        } catch (error) {
          console.error("Upload failed:", error);
          const render = window.Nova?.render;
          if (render?.appendMessage) {
            render.appendMessage({
              id: `upload_error_${Date.now()}`,
              role: "assistant",
              content: `Upload failed: ${safeMessageText(error?.message || error)}`,
              created_at: new Date().toISOString(),
            });
          }
        } finally {
          setBusy(false);
          fileInput.value = "";
        }
      });
    }
  }

  async function loadInitialState() {
    try {
      const result = await callJson(`/api/state?session_id=${encodeURIComponent(state.sessionId)}`);
      const session = result?.session || {};
      const messages = Array.isArray(session?.messages) ? session.messages : [];

      if (window.Nova?.render?.renderMessages) {
        window.Nova.render.renderMessages(messages);
      }

      if (window.Nova?.artifacts?.reload) {
        await window.Nova.artifacts.reload();
      }
    } catch (error) {
      console.warn("Initial state load failed:", error);
    }
  }

  async function bootstrap() {
    installComposerEvents();
    installPendingFileEvents();
    renderPendingFiles();
    await loadInitialState();
  }

  Nova.composer.sendChat = sendChat;
  Nova.composer.safeMessageText = safeMessageText;
  Nova.composer.getPendingFiles = currentPendingFiles;
  Nova.composer.clearPendingFiles = clearPendingFiles;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else {
    bootstrap();
  }

  console.log("nova-composer-bundle loaded");
})();