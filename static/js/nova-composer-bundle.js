(function () {
  "use strict";

  const CHAT_ENDPOINT = "/api/chat";
  const UPLOAD_ENDPOINT = "/api/upload";

  const els = {
    chatInput: document.getElementById("chatInput"),
    sendBtn: document.getElementById("sendBtn"),
    uploadBtn: document.getElementById("uploadBtn"),
    fileInput: document.getElementById("fileInput"),
    pendingFiles: document.getElementById("novaPendingFiles"),
  };

  const state = {
    sessionId: "default-session",
    pendingFiles: [],
    isSending: false,
    pendingAssistantId: null,
  };

  function log(...args) {
    console.log("nova-composer-bundle loaded", ...args);
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function nowTime() {
    return new Date().toLocaleTimeString([], {
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function getRenderer() {
    return window.NovaRender || null;
  }

  function normalizeMessageText(value) {
    if (value == null) return "";
    if (typeof value === "string") return value;

    if (typeof value === "object") {
      if (typeof value.content === "string") return value.content;
      if (typeof value.text === "string") return value.text;

      if (Array.isArray(value.parts)) {
        return value.parts.map((part) => {
          if (typeof part === "string") return part;
          if (part && typeof part.text === "string") return part.text;
          return "";
        }).join("\n");
      }
    }

    return String(value);
  }

  function extractAssistantText(payload) {
    if (!payload || typeof payload !== "object") return "";

    if (typeof payload.message === "string") return payload.message;
    if (typeof payload.reply === "string") return payload.reply;
    if (typeof payload.response === "string") return payload.response;
    if (typeof payload.output_text === "string") return payload.output_text;

    if (payload.assistant_message) {
      const text =
        normalizeMessageText(payload.assistant_message.content) ||
        normalizeMessageText(payload.assistant_message);
      if (text) return text;
    }

    if (payload.data && typeof payload.data === "object") {
      const nested =
        payload.data.message ||
        payload.data.reply ||
        payload.data.response ||
        normalizeMessageText(payload.data.assistant_message?.content) ||
        normalizeMessageText(payload.data.assistant_message);
      if (nested) return normalizeMessageText(nested);
    }

    return "";
  }

  function extractResponseAttachments(payload) {
    if (!payload || typeof payload !== "object") return [];
    if (Array.isArray(payload.attachments)) return payload.attachments;
    if (Array.isArray(payload.assistant_message?.attachments)) {
      return payload.assistant_message.attachments;
    }
    return [];
  }

  function extractResponseDebug(payload) {
    if (!payload || typeof payload !== "object") return null;
    return payload.debug || payload.meta || payload.assistant_message?.meta || null;
  }

  function setSending(isSending) {
    state.isSending = isSending;

    if (els.sendBtn) {
      els.sendBtn.disabled = isSending;
      els.sendBtn.textContent = isSending ? "..." : "Send";
    }

    if (els.uploadBtn) {
      els.uploadBtn.disabled = isSending;
    }

    if (els.chatInput) {
      els.chatInput.disabled = isSending;
    }
  }

  function autosizeTextarea() {
    if (!els.chatInput) return;
    els.chatInput.style.height = "auto";
    els.chatInput.style.height = `${Math.min(els.chatInput.scrollHeight, 180)}px`;
  }

  function renderPendingFiles() {
    if (!els.pendingFiles) return;

    if (!state.pendingFiles.length) {
      els.pendingFiles.style.display = "none";
      els.pendingFiles.innerHTML = "";
      return;
    }

    els.pendingFiles.style.display = "flex";
    els.pendingFiles.innerHTML = state.pendingFiles.map((file, index) => {
      return `
        <span class="nova-attachment-chip">
          ${escapeHtml(file.name)}
          <button
            type="button"
            class="nova-attachment-chip-remove"
            data-remove-pending-index="${index}"
            aria-label="Remove file"
          >×</button>
        </span>
      `;
    }).join("");

    els.pendingFiles.querySelectorAll("[data-remove-pending-index]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const index = Number(btn.getAttribute("data-remove-pending-index"));
        if (Number.isNaN(index)) return;
        state.pendingFiles.splice(index, 1);
        renderPendingFiles();
      });
    });
  }

  async function parseJsonResponse(response, fallbackPrefix) {
    const rawText = await response.text();
    let data = null;

    try {
      data = rawText ? JSON.parse(rawText) : null;
    } catch (error) {
      throw new Error(rawText || `${fallbackPrefix}: ${response.status}`);
    }

    if (!response.ok) {
      throw new Error(
        data?.error ||
        data?.message ||
        `${fallbackPrefix}: ${response.status}`
      );
    }

    return data;
  }

  async function uploadPendingFiles() {
    if (!state.pendingFiles.length) return [];

    const formData = new FormData();
    state.pendingFiles.forEach((file) => {
      formData.append("files", file);
    });
    formData.append("session_id", state.sessionId);

    const response = await fetch(UPLOAD_ENDPOINT, {
      method: "POST",
      body: formData,
    });

    const data = await parseJsonResponse(response, "Upload failed");

    const uploaded =
      data?.files ||
      data?.attachments ||
      data?.uploaded_files ||
      [];

    return Array.isArray(uploaded) ? uploaded : [];
  }

  function renderUserMessage(content, attachments) {
    const renderer = getRenderer();

    if (renderer && typeof renderer.renderUserMessage === "function") {
      renderer.renderUserMessage(content, {
        time: nowTime(),
        attachments: attachments || [],
      });
      return;
    }

    document.dispatchEvent(new CustomEvent("nova:render:user", {
      detail: {
        content,
        time: nowTime(),
        attachments: attachments || [],
      },
    }));
  }

  function createPendingAssistantBubble() {
    const renderer = getRenderer();
    const pendingId = `pending-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    state.pendingAssistantId = pendingId;

    if (renderer && typeof renderer.setPendingAssistantId === "function") {
      renderer.setPendingAssistantId(pendingId);
    }

    if (renderer && typeof renderer.createPendingAssistantBubble === "function") {
      renderer.createPendingAssistantBubble("...", { pendingId });
      return;
    }

    document.dispatchEvent(new CustomEvent("nova:render:assistant-pending", {
      detail: {
        content: "...",
        pendingId,
      },
    }));
  }

  function replacePendingAssistantBubble(payload) {
    const renderer = getRenderer();

    if (renderer && typeof renderer.setPendingAssistantId === "function") {
      renderer.setPendingAssistantId(state.pendingAssistantId);
    }

    if (renderer && typeof renderer.renderAssistantPayload === "function") {
      renderer.renderAssistantPayload(payload, {
        replacePending: true,
        pendingId: state.pendingAssistantId || "",
        time: nowTime(),
      });
    } else if (renderer && typeof renderer.renderAssistantMessage === "function") {
      renderer.renderAssistantMessage(extractAssistantText(payload) || "(empty response)", {
        replacePending: true,
        pendingId: state.pendingAssistantId || "",
        time: nowTime(),
        debug: extractResponseDebug(payload),
        attachments: extractResponseAttachments(payload),
      });
    } else {
      document.dispatchEvent(new CustomEvent("nova:render:assistant-final", {
        detail: {
          payload,
          replacePending: true,
          pendingId: state.pendingAssistantId || "",
          time: nowTime(),
        },
      }));
    }

    state.pendingAssistantId = null;

    if (renderer && typeof renderer.setPendingAssistantId === "function") {
      renderer.setPendingAssistantId(null);
    }

    if (window.NovaArtifacts && typeof window.NovaArtifacts.refresh === "function") {
      window.dispatchEvent(new CustomEvent("nova:artifacts:refresh"));
    }
  }

  function renderErrorBubble(error) {
    replacePendingAssistantBubble({
      message: `Error: ${error.message}`,
      debug: {
        failed: true,
        error: error.message,
      },
    });
  }

  async function sendMessage() {
    if (state.isSending) return;

    const text = (els.chatInput?.value || "").trim();
    const hasFiles = state.pendingFiles.length > 0;

    if (!text && !hasFiles) return;

    setSending(true);

    try {
      let uploadedAttachments = [];

      if (hasFiles) {
        uploadedAttachments = await uploadPendingFiles();
      }

      const userText = text || "Describe or use the uploaded attachment(s).";

      renderUserMessage(userText, uploadedAttachments);

      if (els.chatInput) {
        els.chatInput.value = "";
        autosizeTextarea();
      }

      state.pendingFiles = [];
      renderPendingFiles();

      createPendingAssistantBubble();

      const payload = {
        content: userText,
        session_id: state.sessionId,
        attachments: uploadedAttachments,
      };

      const response = await fetch(CHAT_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const data = await parseJsonResponse(response, "Chat failed");
      replacePendingAssistantBubble(data);
    } catch (error) {
      renderErrorBubble(error);
    } finally {
      setSending(false);
      if (els.chatInput) {
        els.chatInput.focus();
      }
    }
  }

  function bindComposer() {
    if (els.sendBtn) {
      els.sendBtn.addEventListener("click", sendMessage);
    }

    if (els.uploadBtn && els.fileInput) {
      els.uploadBtn.addEventListener("click", () => {
        els.fileInput.click();
      });
    }

    if (els.fileInput) {
      els.fileInput.addEventListener("change", (event) => {
        const files = Array.from(event.target.files || []);
        if (!files.length) return;

        state.pendingFiles.push(...files);
        renderPendingFiles();
        event.target.value = "";
      });
    }

    if (els.chatInput) {
      els.chatInput.addEventListener("input", autosizeTextarea);

      els.chatInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          sendMessage();
        }
      });

      autosizeTextarea();
    }
  }

  function init() {
    if (!els.chatInput || !els.sendBtn) {
      console.warn("nova-composer-bundle: required DOM missing");
      return;
    }

    bindComposer();
    renderPendingFiles();
    log();
  }

  window.NovaComposer = {
    sendMessage,
    getState() {
      return {
        sessionId: state.sessionId,
        pendingFiles: [...state.pendingFiles],
        isSending: state.isSending,
        pendingAssistantId: state.pendingAssistantId,
      };
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();