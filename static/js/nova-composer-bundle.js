(() => {
  "use strict";

  const BUNDLE_VERSION = "history-hard-fallback-2026-03-30-004";
  const MAX_HISTORY_MESSAGES = 12;

  const state = {
    isSending: false,
    stagedAttachments: [],
    sessionId: loadSessionId(),
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
    return "default-session";
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

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
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

    const roleFromData =
      normalizeText(node.getAttribute?.("data-role")).toLowerCase() ||
      normalizeText(node.dataset?.role).toLowerCase();

    if (roleFromData === "user" || roleFromData === "assistant") {
      return roleFromData;
    }

    const cls = String(node.className || "");
    if (/nova-message-user/i.test(cls)) return "user";
    if (/nova-message-assistant/i.test(cls)) return "assistant";

    const author =
      qs(".nova-message-author", node) ||
      qs(".nova-message-role", node) ||
      qs(".message-role", node) ||
      qs(".role", node);

    const authorRole = getRoleFromText(author ? author.textContent : "");
    if (authorRole) return authorRole;

    return "";
  }

  function getMessageContentFromNode(node) {
    if (!node) return "";

    const candidates = [
      ".nova-message-markdown",
      ".nova-message-text",
      ".message-content",
      ".nova-message-body",
      ".content",
    ];

    for (const selector of candidates) {
      const el = qs(selector, node);
      const text = normalizeText(el ? el.textContent : "");
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

  function collectHistoryFromRichNodes(messagesEl) {
    const nodes = qsa(".nova-message, .nova-message-wrap, [data-role]", messagesEl);
    const items = [];

    for (const node of nodes) {
      let target = node;

      if (!String(node.className || "").includes("nova-message")) {
        const nested = qs(".nova-message", node);
        if (nested) target = nested;
      }

      const role = getMessageRoleFromNode(target);
      if (role !== "user" && role !== "assistant") continue;

      let content = getMessageContentFromNode(target);
      if (!content) continue;

      content = content.replace(/\s+\n/g, "\n").trim();
      if (!content) continue;

      items.push({ role, content });
    }

    return dedupeSequentialHistory(items).slice(-MAX_HISTORY_MESSAGES);
  }

  function collectHistoryFromDirectChildren(messagesEl) {
    const items = [];
    const children = Array.from(messagesEl.children || []);

    for (const child of children) {
      if (child.id === "novaEmptyState") continue;

      const article = child.matches?.(".nova-message")
        ? child
        : child.querySelector?.(".nova-message");

      const container = article || child;
      let role = getMessageRoleFromNode(container);

      if (!role) {
        const raw = normalizeText(container.textContent);
        if (raw.startsWith("You")) role = "user";
        if (raw.startsWith("Nova")) role = "assistant";
      }

      if (role !== "user" && role !== "assistant") continue;

      let content = getMessageContentFromNode(container);

      if (!content) {
        const text = normalizeText(container.textContent);
        const lines = text
          .split("\n")
          .map((line) => normalizeText(line))
          .filter(Boolean);

        if (lines.length > 1) {
          const first = getRoleFromText(lines[0]);
          if (first) {
            lines.shift();
          }
          if (lines.length && /^\d{1,2}:\d{2}/.test(lines[0])) {
            lines.shift();
          }
          content = normalizeText(lines.join("\n"));
        }
      }

      if (!content) continue;

      items.push({ role, content });
    }

    return dedupeSequentialHistory(items).slice(-MAX_HISTORY_MESSAGES);
  }

  function collectHistoryFromDom() {
    const { messages } = getEls();
    if (!messages) return [];

    const rich = collectHistoryFromRichNodes(messages);
    if (rich.length) {
      window.NovaHistoryCollectorUsed = "rich";
      window.NovaLastCollectedHistory = rich;
      return rich;
    }

    const direct = collectHistoryFromDirectChildren(messages);
    window.NovaHistoryCollectorUsed = "direct";
    window.NovaLastCollectedHistory = direct;
    return direct;
  }

  function collectHistory() {
    const domHistory = collectHistoryFromDom();
    return domHistory.slice(-MAX_HISTORY_MESSAGES);
  }

  function appendFallbackMessage(role, content, meta = {}) {
    const { messages } = getEls();
    if (!messages) return null;

    hideEmptyState();

    const wrap = document.createElement("div");
    wrap.className = "nova-message-wrap";
    wrap.setAttribute("data-role", role);

    const article = document.createElement("article");
    article.className = `nova-message nova-message-${role}`;
    article.setAttribute("data-role", role);

    const inner = document.createElement("div");
    inner.className = "nova-message-inner";

    const head = document.createElement("div");
    head.className = "nova-message-head";

    const roleEl = document.createElement("div");
    roleEl.className = "nova-message-role";
    roleEl.textContent = role === "user" ? "You" : "Nova";

    const timeEl = document.createElement("div");
    timeEl.className = "nova-message-time";
    try {
      timeEl.textContent = new Date().toLocaleTimeString([], {
        hour: "numeric",
        minute: "2-digit",
      });
    } catch (_err) {
      timeEl.textContent = "";
    }

    head.appendChild(roleEl);
    head.appendChild(timeEl);

    const markdown = document.createElement("div");
    markdown.className = "nova-message-markdown";
    markdown.innerHTML = escapeHtml(content).replace(/\n/g, "<br>");

    inner.appendChild(head);

    if (meta && typeof meta === "object") {
      const badges = [];

      if (meta.used_fallback === true) badges.push("Fallback");
      if (meta.history_included === true || Number(meta.history_count || 0) > 0) {
        badges.push(`History ${Number(meta.history_count || 0)}`);
      }
      if (meta.chat_service_version) badges.push(String(meta.chat_service_version));

      if (badges.length) {
        const badgeRow = document.createElement("div");
        badgeRow.className = "nova-message-badges";
        badgeRow.style.display = "flex";
        badgeRow.style.flexWrap = "wrap";
        badgeRow.style.gap = "6px";
        badgeRow.style.marginBottom = "10px";

        for (const badgeText of badges) {
          const badge = document.createElement("span");
          badge.className = "nova-badge";
          badge.textContent = badgeText;
          badgeRow.appendChild(badge);
        }

        inner.appendChild(badgeRow);
      }
    }

    inner.appendChild(markdown);
    article.appendChild(inner);
    wrap.appendChild(article);
    messages.appendChild(wrap);
    scrollMessagesToBottom();
    return wrap;
  }

  function renderMessage(role, content, payload = {}) {
    hideEmptyState();

    if (window.NovaRender && typeof window.NovaRender.appendMessage === "function") {
      try {
        window.NovaRender.appendMessage(
          {
            role,
            content,
            created_at: new Date().toISOString(),
            meta: payload.meta || {},
            attachments: payload.attachments || [],
          },
          {
            debug: payload.debug || {},
          }
        );
        scrollMessagesToBottom();
        return;
      } catch (err) {
        console.warn("NovaRender.appendMessage failed, using fallback DOM render.", err);
      }
    }

    appendFallbackMessage(role, content, payload.meta || payload.debug || {});
  }

  function renderUserMessage(content) {
    renderMessage("user", content, {});
  }

  function renderAssistantMessage(responsePayload) {
    const assistant = responsePayload && responsePayload.assistant_message
      ? responsePayload.assistant_message
      : null;

    const content = normalizeText(
      (assistant && assistant.content) ||
      (responsePayload && responsePayload.message) ||
      ""
    );

    renderMessage("assistant", content, {
      assistant_message: assistant,
      message: (responsePayload && responsePayload.message) || content,
      debug: (responsePayload && responsePayload.debug) || {},
      meta: (assistant && assistant.meta) || {},
      attachments: Array.isArray(assistant && assistant.attachments) ? assistant.attachments : [],
    });
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

    console.log("Nova history collector used:", window.NovaHistoryCollectorUsed);
    console.log("Nova outgoing payload", payload);
    console.log("Nova outgoing history", history);

    return payload;
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

      renderMessage("assistant", `Request failed: ${err.message || err}`, {
        debug: {
          used_fallback: true,
          fallback_reason: String(err.message || err),
          history_included: Array.isArray(payload.history) && payload.history.length > 0,
          history_count: Array.isArray(payload.history) ? payload.history.length : 0,
          chat_service_version: "frontend-request-failed",
        },
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

  function init() {
    bindInputAutoResize();
    bindSend();
    bindUploads();
    renderAttachmentTray();

    window.NovaComposerBundle = {
      version: BUNDLE_VERSION,
      state,
      collectHistory,
      collectHistoryFromDom,
      collectHistoryFromRichNodes,
      collectHistoryFromDirectChildren,
      buildPayload,
      sendCurrentMessage,
      uploadFiles,
      renderAttachmentTray,
    };

    log(BUNDLE_VERSION);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();