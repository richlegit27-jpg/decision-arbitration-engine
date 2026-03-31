(() => {
  "use strict";

  const BUNDLE_VERSION = "session-restore-2026-03-31-001";
  const MAX_HISTORY_MESSAGES = 12;

  const state = {
    isSending: false,
    stagedAttachments: [],
    sessionId: loadSessionId(),
    restored: false,
  };

  function log(...args) {
    console.log("nova-composer-bundle loaded", ...args);
  }

  function loadSessionId() {
    try {
      const saved = localStorage.getItem("nova_session_id");
      if (saved && String(saved).trim()) {
        return String(saved).trim();
      }
    } catch (_err) {}
    return crypto && crypto.randomUUID ? crypto.randomUUID() : `session-${Date.now()}`;
  }

  function saveSessionId(sessionId) {
    if (!sessionId || !String(sessionId).trim()) return;
    state.sessionId = String(sessionId).trim();
    try {
      localStorage.setItem("nova_session_id", state.sessionId);
    } catch (_err) {}
  }

  function qs(selector, root = document) {
    return root.querySelector(selector);
  }

  function qsa(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
  }

  function normalizeText(value) {
    if (value == null) return "";
    return String(value).replace(/\r\n/g, "\n").trim();
  }

  function getEls() {
    return {
      input: qs("#chatInput"),
      sendBtn: qs("#sendBtn"),
      uploadBtn: qs("#uploadBtn"),
      fileInput: qs("#fileInput"),
      messages: qs("#messages"),
      emptyState: qs("#novaEmptyState"),
      composer: qs(".nova-composer") || qs(".nova-composer-shell") || document.body,
      attachmentsTray:
        qs("#composerAttachments") ||
        qs("#stagedAttachments") ||
        qs("#novaPendingFiles") ||
        qs(".nova-composer-attachments") ||
        qs(".nova-pending-files"),
    };
  }

  function ensureTray() {
    const els = getEls();
    if (els.attachmentsTray) return els.attachmentsTray;

    const tray = document.createElement("div");
    tray.id = "composerAttachments";
    tray.className = "nova-composer-attachments";
    tray.style.display = "flex";
    tray.style.flexWrap = "wrap";
    tray.style.gap = "8px";
    tray.style.marginTop = "10px";

    if (els.input && els.input.parentElement) {
      els.input.parentElement.appendChild(tray);
    } else if (els.composer) {
      els.composer.appendChild(tray);
    } else {
      document.body.appendChild(tray);
    }

    return tray;
  }

  function setBusy(isBusy) {
    state.isSending = !!isBusy;
    const { sendBtn, input, uploadBtn } = getEls();

    if (sendBtn) {
      sendBtn.disabled = state.isSending;
      sendBtn.dataset.busy = state.isSending ? "true" : "false";
    }

    if (input) {
      input.disabled = state.isSending;
      input.dataset.busy = state.isSending ? "true" : "false";
    }

    if (uploadBtn) {
      uploadBtn.disabled = state.isSending;
      uploadBtn.dataset.busy = state.isSending ? "true" : "false";
    }
  }

  function hideEmptyState() {
    const { emptyState } = getEls();
    if (emptyState) {
      emptyState.style.display = "none";
    }
  }

  function scrollMessagesToBottom() {
    const { messages } = getEls();
    if (!messages) return;
    messages.scrollTop = messages.scrollHeight;
  }

  function getRoleFromText(value) {
    const text = normalizeText(value).toLowerCase();
    if (text === "you" || text === "user") return "user";
    if (text === "nova" || text === "assistant") return "assistant";
    return "";
  }

  function getMessageRoleFromNode(node) {
    if (!node) return "";

    const dataRole =
      normalizeText(node.getAttribute?.("data-role")).toLowerCase() ||
      normalizeText(node.dataset?.role).toLowerCase();

    if (dataRole === "user" || dataRole === "assistant") {
      return dataRole;
    }

    const cls = String(node.className || "");
    if (/nova-message-user/i.test(cls)) return "user";
    if (/nova-message-assistant/i.test(cls)) return "assistant";

    const author =
      qs(".nova-message-author", node) ||
      qs(".nova-message-role", node) ||
      qs(".message-role", node) ||
      qs(".role", node);

    return getRoleFromText(author ? author.textContent : "");
  }

  function getMessageContentFromNode(node) {
    if (!node) return "";

    const explicit = normalizeText(node.getAttribute?.("data-message-text"));
    if (explicit) return explicit;

    const innerExplicit = normalizeText(qs(".nova-message", node)?.getAttribute?.("data-message-text"));
    if (innerExplicit) return innerExplicit;

    const candidates = [
      ".nova-message-markdown",
      ".nova-message-text",
      ".message-content",
      ".nova-message-body",
      ".content",
    ];

    for (const selector of candidates) {
      const el = qs(selector, node);
      const text = normalizeText(el ? el.getAttribute?.("data-message-content") || el.textContent : "");
      if (text) return text;
    }

    const inner = qs(".nova-message-inner", node);
    if (inner) {
      const clone = inner.cloneNode(true);
      qsa(
        ".nova-message-topline, .nova-message-head, .nova-message-badges, .nova-message-attachments, .nova-message-time, .nova-message-author, .nova-message-role",
        clone
      ).forEach((el) => el.remove());
      const text = normalizeText(clone.textContent);
      if (text) return text;
    }

    return normalizeText(node.textContent);
  }

  function dedupeSequentialHistory(items) {
    const deduped = [];
    for (const item of items) {
      const last = deduped[deduped.length - 1];
      if (
        last &&
        last.role === item.role &&
        normalizeText(last.content) === normalizeText(item.content)
      ) {
        continue;
      }
      deduped.push(item);
    }
    return deduped;
  }

  function collectHistoryFromDom() {
    const { messages } = getEls();
    if (!messages) return [];

    const nodes = qsa(".nova-message-wrap, .nova-message, [data-role]", messages);
    const items = [];

    for (const node of nodes) {
      let target = node;
      if (!String(node.className || "").includes("nova-message")) {
        const nested = qs(".nova-message", node);
        if (nested) target = nested;
      }

      const role = getMessageRoleFromNode(target) || getMessageRoleFromNode(node);
      if (role !== "user" && role !== "assistant") continue;

      const content = getMessageContentFromNode(target) || getMessageContentFromNode(node);
      if (!content) continue;

      items.push({ role, content });
    }

    const out = dedupeSequentialHistory(items).slice(-MAX_HISTORY_MESSAGES);
    window.NovaLastCollectedHistory = out;
    return out;
  }

  function collectHistory() {
    return collectHistoryFromDom();
  }

  function renderAttachmentTray() {
    const tray = ensureTray();
    tray.innerHTML = "";

    if (!state.stagedAttachments.length) {
      tray.style.display = "none";
      return;
    }

    tray.style.display = "flex";

    state.stagedAttachments.forEach((file, index) => {
      const chip = document.createElement("div");
      chip.className = "nova-attachment-chip";
      chip.style.display = "inline-flex";
      chip.style.alignItems = "center";
      chip.style.gap = "8px";

      const label = document.createElement("span");
      label.className = "nova-attachment-chip-label";
      label.textContent = file.name || `file-${index + 1}`;
      label.style.whiteSpace = "nowrap";
      label.style.overflow = "hidden";
      label.style.textOverflow = "ellipsis";
      label.style.maxWidth = "280px";

      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "nova-attachment-chip-remove";
      removeBtn.textContent = "×";
      removeBtn.addEventListener("click", () => {
        state.stagedAttachments.splice(index, 1);
        renderAttachmentTray();
      });

      chip.appendChild(label);
      chip.appendChild(removeBtn);
      tray.appendChild(chip);
    });
  }

  function renderUserMessage(content) {
    if (window.NovaRender && typeof window.NovaRender.appendUserMessage === "function") {
      window.NovaRender.appendUserMessage(content, new Date().toISOString());
      scrollMessagesToBottom();
      return;
    }

    if (window.NovaRender && typeof window.NovaRender.appendMessage === "function") {
      window.NovaRender.appendMessage({
        role: "user",
        content,
        created_at: new Date().toISOString(),
        attachments: [],
        meta: {},
      });
      scrollMessagesToBottom();
    }
  }

  function renderAssistantMessage(responsePayload) {
    if (window.NovaRender && typeof window.NovaRender.appendAssistantResponse === "function") {
      window.NovaRender.appendAssistantResponse(responsePayload);
      scrollMessagesToBottom();
      return;
    }

    const content = normalizeText(
      responsePayload?.assistant_message?.content ||
      responsePayload?.message ||
      ""
    );

    if (window.NovaRender && typeof window.NovaRender.appendMessage === "function") {
      window.NovaRender.appendMessage(
        {
          role: "assistant",
          content,
          created_at: new Date().toISOString(),
          attachments: responsePayload?.assistant_message?.attachments || [],
          meta: responsePayload?.assistant_message?.meta || {},
        },
        {
          debug: responsePayload?.debug || {},
        }
      );
      scrollMessagesToBottom();
    }
  }

  async function uploadFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;

    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));

    setBusy(true);

    try {
      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok || !data?.ok) {
        throw new Error(data?.message || data?.error || "Upload failed");
      }

      const savedFiles = Array.isArray(data.files) ? data.files : [];
      state.stagedAttachments = state.stagedAttachments.concat(savedFiles);
      renderAttachmentTray();
    } catch (err) {
      console.error("Upload failed:", err);
      alert(`Upload failed: ${err.message || err}`);
    } finally {
      setBusy(false);
      const { fileInput } = getEls();
      if (fileInput) fileInput.value = "";
    }
  }

  function buildPayload(content) {
    const history = collectHistory();

    const payload = {
      content,
      session_id: state.sessionId || "default-session",
      history,
      attachments: state.stagedAttachments.slice(),
    };

    window.NovaOutgoingPayload = payload;
    window.NovaOutgoingHistory = history;

    console.log("Nova outgoing payload", payload);
    console.log("Nova outgoing history", history);

    return payload;
  }

  async function restoreSessionOnLoad() {
    if (state.restored) return;
    state.restored = true;

    try {
      const response = await fetch(`/api/state?session_id=${encodeURIComponent(state.sessionId)}`, {
        method: "GET",
        headers: {
          "Accept": "application/json",
        },
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data?.ok) {
        throw new Error(data?.message || data?.error || "State load failed");
      }

      const activeMessages = Array.isArray(data.active_messages) ? data.active_messages : [];

      if (window.NovaRender && typeof window.NovaRender.renderMessages === "function") {
        window.NovaRender.renderMessages(activeMessages);
      }

      if (activeMessages.length) {
        hideEmptyState();
        scrollMessagesToBottom();
      }

      window.NovaRestoredState = data;
      console.log("Nova restored session", {
        session_id: state.sessionId,
        messages: activeMessages.length,
      });
    } catch (err) {
      console.warn("Nova session restore failed", err);
      window.NovaRestoreError = String(err?.message || err);
    }
  }

  async function sendCurrentMessage() {
    const { input } = getEls();
    if (!input || state.isSending) return;

    const content = normalizeText(input.value);
    if (!content && !state.stagedAttachments.length) return;

    const payload = buildPayload(content);

    renderUserMessage(content || "Uploaded attachment(s)");
    input.value = "";
    input.style.height = "";
    hideEmptyState();
    scrollMessagesToBottom();

    setBusy(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok || !data?.ok) {
        throw new Error(data?.message || data?.error || "Chat request failed");
      }

      if (data.session_id) {
        saveSessionId(data.session_id);
      }

      renderAssistantMessage(data);

      state.stagedAttachments = [];
      renderAttachmentTray();

      window.NovaLastChatDebug = data.debug || {};
      window.NovaLastChatResponse = data;
    } catch (err) {
      console.error("Chat send failed:", err);

      window.NovaLastChatDebug = {
        used_fallback: true,
        fallback_reason: String(err.message || err),
        history_included: Array.isArray(payload.history) && payload.history.length > 0,
        history_count: Array.isArray(payload.history) ? payload.history.length : 0,
        chat_service_version: "frontend-request-failed",
      };

      window.NovaLastChatResponse = {
        ok: false,
        message: `Request failed: ${err.message || err}`,
        debug: window.NovaLastChatDebug,
      };

      renderAssistantMessage({
        ok: false,
        message: `Request failed: ${err.message || err}`,
        assistant_message: {
          role: "assistant",
          content: `Request failed: ${err.message || err}`,
          created_at: new Date().toISOString(),
          attachments: [],
          meta: {
            used_fallback: true,
            fallback_reason: String(err.message || err),
            history_included: Array.isArray(payload.history) && payload.history.length > 0,
            history_count: Array.isArray(payload.history) ? payload.history.length : 0,
            chat_service_version: "frontend-request-failed",
          },
        },
        debug: window.NovaLastChatDebug,
      });
    } finally {
      setBusy(false);
      input.focus();
    }
  }

  function bindInputAutoResize() {
    const { input } = getEls();
    if (!input) return;

    const resize = () => {
      input.style.height = "auto";
      input.style.height = `${Math.min(input.scrollHeight, 240)}px`;
    };

    input.addEventListener("input", resize);
    resize();
  }

  function bindSend() {
    const { sendBtn, input } = getEls();

    if (sendBtn) {
      sendBtn.addEventListener("click", () => {
        sendCurrentMessage();
      });
    }

    if (input) {
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          sendCurrentMessage();
        }
      });
    }
  }

  function bindUploads() {
    const { uploadBtn, fileInput } = getEls();

    if (uploadBtn && fileInput) {
      uploadBtn.addEventListener("click", () => {
        fileInput.click();
      });
    }

    if (fileInput) {
      fileInput.addEventListener("change", async (event) => {
        const files = event.target && event.target.files ? event.target.files : [];
        await uploadFiles(files);
      });
    }
  }

  async function init() {
    bindInputAutoResize();
    bindSend();
    bindUploads();
    renderAttachmentTray();

    window.NovaComposerBundle = {
      version: BUNDLE_VERSION,
      state,
      collectHistory,
      collectHistoryFromDom,
      buildPayload,
      restoreSessionOnLoad,
      sendCurrentMessage,
      uploadFiles,
      renderAttachmentTray,
    };

    log(BUNDLE_VERSION);
    await restoreSessionOnLoad();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      void init();
    }, { once: true });
  } else {
    void init();
  }
})();