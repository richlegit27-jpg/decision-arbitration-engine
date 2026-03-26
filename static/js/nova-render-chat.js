(() => {
  "use strict";

  if (window.__novaRenderChatLoaded) return;
  window.__novaRenderChatLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  Nova.chat = Nova.chat || {};
  Nova.sessions = Nova.sessions || {};

  const API = {
    getChat: (sessionId) => `/api/chat/${encodeURIComponent(sessionId)}`,
    stream: "/api/chat/stream",
  };

  const state = {
    activeSessionId: null,
    messages: [],
    isSending: false,
    lastUserMessage: "",
    lastAttachments: [],
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function qs(sel, root = document) {
    return root.querySelector(sel);
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  async function safeJson(res) {
    try {
      return await res.json();
    } catch {
      return {};
    }
  }

  async function apiGet(url) {
    try {
      const res = await fetch(url, { method: "GET" });
      const data = await safeJson(res);

      if (!res.ok || data.ok === false) {
        throw new Error(data.error || `GET failed: ${url}`);
      }

      return data;
    } catch (err) {
      console.error("API GET error:", url, err);
      return { ok: false, error: err.message || "request failed" };
    }
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatText(text) {
    const escaped = escapeHtml(text || "");
    return escaped
      .replace(/\r\n/g, "\n")
      .replace(/\n{3,}/g, "\n\n")
      .replace(/\n/g, "<br>");
  }

  function getMessagesRoot() {
    return (
      byId("novaMessages") ||
      byId("chatMessages") ||
      qs(".nova-messages") ||
      qs(".chat-messages")
    );
  }

  function getComposerInput() {
    return (
      byId("novaComposerInput") ||
      byId("novaInput") ||
      byId("composerInput") ||
      qs("textarea")
    );
  }

  function getSendButton() {
    return (
      byId("novaSendBtn") ||
      byId("sendBtn") ||
      qs('[data-action="send"]')
    );
  }

  function getRegenerateButton() {
    return (
      byId("novaRegenerateBtn") ||
      byId("regenerateBtn") ||
      qs('[data-action="regenerate"]')
    );
  }

  function injectChatPolishStyles() {
    if (document.getElementById("nova-render-chat-polish")) return;

    const style = document.createElement("style");
    style.id = "nova-render-chat-polish";
    style.textContent = `
      .nova-empty-chat {
        min-height: 100%;
        display: grid;
        place-items: center;
        text-align: center;
        padding: 32px 18px;
        opacity: 0.96;
      }

      .nova-empty-chat-title {
        font-size: 1.15rem;
        font-weight: 700;
        margin-bottom: 6px;
      }

      .nova-empty-chat-subtitle {
        font-size: 0.95rem;
        opacity: 0.72;
      }

      .message {
        width: 100%;
        display: flex;
        margin: 0 0 14px;
      }

      .message-user {
        justify-content: flex-end;
      }

      .message-assistant,
      .message-system,
      .message-tool {
        justify-content: flex-start;
      }

      .message-bubble {
        max-width: min(920px, 92%);
        border-radius: 18px;
        padding: 14px 16px 12px;
        position: relative;
        overflow-wrap: anywhere;
      }

      .message-user .message-bubble {
        border-bottom-right-radius: 8px;
      }

      .message-assistant .message-bubble,
      .message-system .message-bubble,
      .message-tool .message-bubble {
        border-bottom-left-radius: 8px;
      }

      .message-content {
        line-height: 1.55;
        font-size: 0.98rem;
        white-space: normal;
      }

      .message-attachments {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 10px;
      }

      .message-attachment-chip {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        min-height: 30px;
        padding: 0 10px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.10);
        background: rgba(255,255,255,0.06);
        font-size: 0.76rem;
        font-weight: 600;
        line-height: 1;
        opacity: 0.95;
      }

      .message-attachment-chip-ext {
        opacity: 0.7;
        font-weight: 800;
        font-size: 0.7rem;
      }

      .message-actions {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 10px;
        flex-wrap: wrap;
      }

      .message-action-btn,
      #novaRegenerateBtn,
      #regenerateBtn,
      [data-action="regenerate"] {
        appearance: none;
        border: 1px solid rgba(255,255,255,0.10);
        background: rgba(255,255,255,0.06);
        color: inherit;
        border-radius: 999px;
        min-height: 34px;
        padding: 0 12px;
        font-size: 0.82rem;
        font-weight: 600;
        line-height: 1;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        cursor: pointer;
        transition:
          transform 0.16s ease,
          opacity 0.16s ease,
          background 0.16s ease,
          border-color 0.16s ease,
          box-shadow 0.16s ease;
        box-shadow: 0 6px 18px rgba(0,0,0,0.14);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
      }

      .message-action-btn:hover,
      #novaRegenerateBtn:hover,
      #regenerateBtn:hover,
      [data-action="regenerate"]:hover {
        transform: translateY(-1px);
        background: rgba(255,255,255,0.10);
        border-color: rgba(255,255,255,0.16);
      }

      .message-action-btn:active,
      #novaRegenerateBtn:active,
      #regenerateBtn:active,
      [data-action="regenerate"]:active {
        transform: translateY(0);
      }

      .message-action-btn:disabled,
      #novaRegenerateBtn:disabled,
      #regenerateBtn:disabled,
      [data-action="regenerate"]:disabled {
        cursor: not-allowed;
        opacity: 0.45;
        transform: none;
        box-shadow: none;
      }

      .message-action-btn.is-success,
      #novaRegenerateBtn.is-success,
      #regenerateBtn.is-success,
      [data-action="regenerate"].is-success {
        opacity: 1;
      }

      .message-action-btn.is-failed,
      #novaRegenerateBtn.is-failed,
      #regenerateBtn.is-failed,
      [data-action="regenerate"].is-failed {
        opacity: 0.85;
      }

      @media (max-width: 720px) {
        .message-bubble {
          max-width: 100%;
          padding: 12px 13px 11px;
        }

        .message-actions {
          gap: 7px;
          margin-top: 9px;
        }

        .message-action-btn,
        #novaRegenerateBtn,
        #regenerateBtn,
        [data-action="regenerate"] {
          min-height: 32px;
          padding: 0 11px;
          font-size: 0.78rem;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function scrollToBottom(force = false) {
    const root = getMessagesRoot();
    if (!root) return;

    if (force) {
      root.scrollTop = root.scrollHeight;
      return;
    }

    const nearBottom =
      root.scrollHeight - root.scrollTop - root.clientHeight < 180;

    if (nearBottom) {
      root.scrollTop = root.scrollHeight;
    }
  }

  function setButtonFeedback(btn, label, className = "") {
    if (!btn) return;
    const original = btn.dataset.originalLabel || btn.textContent || "";
    btn.textContent = label;
    btn.classList.remove("is-success", "is-failed");
    if (className) btn.classList.add(className);

    clearTimeout(btn.__novaFeedbackTimer);
    btn.__novaFeedbackTimer = setTimeout(() => {
      btn.textContent = original;
      btn.classList.remove("is-success", "is-failed");
    }, 1200);
  }

  function updateRegenerateVisualState() {
    const regenBtn = getRegenerateButton();
    if (!regenBtn) return;

    if (!regenBtn.dataset.originalLabel) {
      regenBtn.dataset.originalLabel = regenBtn.textContent?.trim() || "Regenerate";
    }

    const enabled = !state.isSending && !!state.lastUserMessage && !!state.activeSessionId;

    regenBtn.disabled = !enabled;
    regenBtn.textContent = state.isSending
      ? "Working..."
      : (regenBtn.dataset.originalLabel || "Regenerate");
    regenBtn.title = enabled
      ? "Regenerate the last reply"
      : "Send a message first";
  }

  function setSending(isSending) {
    state.isSending = !!isSending;

    const sendBtn = getSendButton();
    if (sendBtn) {
      sendBtn.disabled = state.isSending;
      sendBtn.classList.toggle("is-loading", state.isSending);
    }

    const input = getComposerInput();
    if (input) {
      input.disabled = state.isSending;
    }

    updateRegenerateVisualState();
  }

  function messageRoleClass(role) {
    const value = String(role || "assistant").toLowerCase();
    if (value === "user") return "user";
    if (value === "system") return "system";
    if (value === "tool") return "tool";
    return "assistant";
  }

  function extOf(fileName) {
    const name = String(fileName || "");
    const idx = name.lastIndexOf(".");
    return idx >= 0 ? name.slice(idx + 1).toUpperCase() : "FILE";
  }

  function normalizeAttachment(file) {
    if (!file) return null;

    return {
      id: String(file.__uploadedId || file.id || ""),
      url: String(file.__uploadedUrl || file.url || file.file_url || ""),
      name: String(file.name || "file"),
      size: Number(file.size || 0),
      type: String(file.type || ""),
      ext: extOf(file.name || file.filename || "file"),
    };
  }

  function normalizeAttachments(files) {
    return safeArray(files)
      .map(normalizeAttachment)
      .filter(Boolean);
  }

  function renderAttachmentPreviewList(files) {
    const list = normalizeAttachments(files);
    if (!list.length) return "";

    return `
      <div class="message-attachments">
        ${list.map((file) => `
          <div class="message-attachment-chip" title="${escapeHtml(file.name)}">
            <span class="message-attachment-chip-ext">${escapeHtml(file.ext)}</span>
            <span class="message-attachment-chip-name">${escapeHtml(file.name)}</span>
          </div>
        `).join("")}
      </div>
    `;
  }

  function buildMessageActions(message, index) {
    const isAssistant = String(message?.role || "").toLowerCase() === "assistant";
    if (!isAssistant) return "";

    return `
      <div class="message-actions">
        <button
          class="message-action-btn"
          data-action="copy-message"
          data-index="${index}"
          type="button"
          aria-label="Copy message"
          title="Copy message"
        >
          Copy
        </button>
      </div>
    `;
  }

  function renderMessages(messages = []) {
    const root = getMessagesRoot();
    if (!root) return;

    state.messages = safeArray(messages);

    if (!state.messages.length) {
      root.innerHTML = `
        <div class="nova-empty-chat">
          <div>
            <div class="nova-empty-chat-title">Nova is ready</div>
            <div class="nova-empty-chat-subtitle">Send a message to begin.</div>
          </div>
        </div>
      `;
      setSending(false);
      return;
    }

    root.innerHTML = state.messages
      .map((message, index) => {
        const role = messageRoleClass(message?.role);
        const content = extractMessageText(message);
        const attachments = safeArray(
          message?.attachments ||
          message?.files ||
          message?.meta?.attachments
        );

        return `
          <div class="message message-${role}" data-role="${role}">
            <div class="message-bubble">
              <div class="message-content">${formatText(content)}</div>
              ${role === "user" ? renderAttachmentPreviewList(attachments) : ""}
              ${buildMessageActions(message, index)}
            </div>
          </div>
        `;
      })
      .join("");

    bindMessageActions(root);
    scrollToBottom(true);
    setSending(false);
  }

  function bindMessageActions(root) {
    root.querySelectorAll('[data-action="copy-message"]').forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";

      if (!btn.dataset.originalLabel) {
        btn.dataset.originalLabel = btn.textContent?.trim() || "Copy";
      }

      btn.addEventListener("click", async (e) => {
        e.preventDefault();
        e.stopPropagation();

        const index = Number(btn.dataset.index || "-1");
        const msg = state.messages[index];
        const text = extractMessageText(msg);

        if (!text) return;

        try {
          await navigator.clipboard.writeText(text);
          setButtonFeedback(btn, "Copied", "is-success");
        } catch (err) {
          console.error("Copy failed:", err);
          setButtonFeedback(btn, "Failed", "is-failed");
        }
      });
    });
  }

  function extractMessageText(message) {
    if (!message) return "";

    if (typeof message.content === "string") {
      return message.content;
    }

    if (Array.isArray(message.content)) {
      return message.content
        .map((part) => {
          if (typeof part === "string") return part;
          if (part && typeof part.text === "string") return part.text;
          if (part && typeof part.content === "string") return part.content;
          return "";
        })
        .join("\n")
        .trim();
    }

    if (typeof message.text === "string") {
      return message.text;
    }

    return "";
  }

  function appendMessage(role, content = "", meta = {}) {
    state.messages.push({
      role,
      content: String(content || ""),
      ...meta,
    });
    renderMessages(state.messages);
  }

  function upsertStreamingAssistant(content = "") {
    const last = state.messages[state.messages.length - 1];
    if (last && String(last.role).toLowerCase() === "assistant" && last.__streaming) {
      last.content = String(content || "");
    } else {
      state.messages.push({
        role: "assistant",
        content: String(content || ""),
        __streaming: true,
      });
    }

    renderMessages(state.messages);
    scrollToBottom();
  }

  function finalizeStreamingAssistant(finalText = "") {
    const last = state.messages[state.messages.length - 1];
    if (last && String(last.role).toLowerCase() === "assistant") {
      if (finalText) {
        last.content = String(finalText);
      }
      delete last.__streaming;
    }
    renderMessages(state.messages);
  }

  function addErrorMessage(text) {
    state.messages.push({
      role: "system",
      content: text || "Something went wrong.",
    });
    renderMessages(state.messages);
  }

  async function loadSession(sessionId) {
    if (!sessionId) return;

    state.activeSessionId = sessionId;
    Nova.chat.activeSessionId = sessionId;

    const data = await apiGet(API.getChat(sessionId));
    if (!data.ok) {
      renderMessages([]);
      addErrorMessage(data.error || "Failed to load session.");
      updateRegenerateVisualState();
      return;
    }

    const session = data.session || data.chat || data;
    const messages = safeArray(session?.messages || data.messages);

    renderMessages(messages);
    setSending(false);
    updateRegenerateVisualState();
  }

  function parseSSEChunk(raw) {
    const lines = String(raw || "").split("\n");
    let event = "message";
    const dataLines = [];

    for (const line of lines) {
      if (line.startsWith("event:")) {
        event = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }

    const dataText = dataLines.join("\n");
    let payload = dataText;

    try {
      payload = JSON.parse(dataText);
    } catch {
      // keep raw text
    }

    return { event, payload };
  }

  async function readStreamResponse(res) {
    const reader = res.body?.getReader?.();
    if (!reader) {
      const text = await res.text().catch(() => "");
      return { mode: "text", text };
    }

    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    let assistantText = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const part of parts) {
        if (!part.trim()) continue;

        const { event, payload } = parseSSEChunk(part);

        if (event === "delta") {
          let delta = "";

          if (typeof payload === "string") {
            delta = payload;
          } else if (payload && typeof payload.delta === "string") {
            delta = payload.delta;
          } else if (payload && typeof payload.content === "string") {
            delta = payload.content;
          }

          if (delta) {
            assistantText += delta;
            upsertStreamingAssistant(assistantText);
          }
        } else if (event === "done") {
          let finalText = assistantText;

          if (payload && typeof payload === "object") {
            if (typeof payload.content === "string") finalText = payload.content;
            else if (typeof payload.message === "string") finalText = payload.message;
            else if (payload.message && typeof payload.message.content === "string") {
              finalText = payload.message.content;
            }
          } else if (typeof payload === "string" && payload.trim()) {
            finalText = payload;
          }

          finalizeStreamingAssistant(finalText || assistantText);
          return { mode: "sse", text: finalText || assistantText };
        } else if (event === "error") {
          let errorText = "Stream failed.";
          if (payload && typeof payload.error === "string") errorText = payload.error;
          else if (typeof payload === "string" && payload) errorText = payload;

          throw new Error(errorText);
        }
      }
    }

    if (assistantText) {
      finalizeStreamingAssistant(assistantText);
      return { mode: "sse", text: assistantText };
    }

    return { mode: "empty", text: "" };
  }

  function getAttachmentModule() {
    return Nova.attachments || {};
  }

  function getCurrentAttachments() {
    const attachmentsModule = getAttachmentModule();

    if (typeof attachmentsModule.getFiles === "function") {
      try {
        return safeArray(attachmentsModule.getFiles());
      } catch (err) {
        console.warn("Attachment getFiles failed:", err);
      }
    }

    return safeArray(Nova.chat.attachments);
  }

  async function prepareAttachmentsForSend() {
    const attachmentsModule = getAttachmentModule();

    if (typeof attachmentsModule.uploadAll === "function") {
      try {
        const uploaded = await attachmentsModule.uploadAll();
        return normalizeAttachments(uploaded);
      } catch (err) {
        console.warn("Attachment uploadAll failed, using local attachment metadata only:", err);
      }
    }

    return normalizeAttachments(getCurrentAttachments());
  }

  function buildStreamPayload(content, attachments) {
    const payload = {
      session_id: state.activeSessionId,
      content,
    };

    if (attachments.length) {
      payload.attachments = attachments;
      payload.files = attachments;
    }

    return payload;
  }

  async function clearComposerAttachments() {
    const attachmentsModule = getAttachmentModule();
    if (typeof attachmentsModule.clear === "function") {
      try {
        attachmentsModule.clear();
        return;
      } catch (err) {
        console.warn("Attachment clear failed:", err);
      }
    }

    Nova.chat.attachments = [];
  }

  async function sendMessage(contentOverride = "", options = {}) {
    if (state.isSending) return;

    const input = getComposerInput();
    const content = String(contentOverride || input?.value || "").trim();
    const useLastAttachments = !!options.useLastAttachments;

    let attachments = [];

    if (useLastAttachments) {
      attachments = normalizeAttachments(state.lastAttachments);
    } else {
      attachments = await prepareAttachmentsForSend();
    }

    if (!content && !attachments.length) return;

    if (!state.activeSessionId) {
      if (Nova.sessions && typeof Nova.sessions.refresh === "function") {
        await Nova.sessions.refresh();
      }
    }

    if (!state.activeSessionId) {
      addErrorMessage("No active session.");
      updateRegenerateVisualState();
      return;
    }

    state.lastUserMessage = content;
    state.lastAttachments = attachments.slice();
    setSending(true);

    appendMessage("user", content, attachments.length ? { attachments } : {});

    if (input && !contentOverride) {
      input.value = "";
      input.style.height = "";
    }

    try {
      const res = await fetch(API.stream, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildStreamPayload(content, attachments)),
      });

      if (!res.ok) {
        const data = await safeJson(res);
        throw new Error(data.error || `POST failed: ${API.stream}`);
      }

      const result = await readStreamResponse(res);

      if (!result.text) {
        upsertStreamingAssistant("No response received.");
        finalizeStreamingAssistant("No response received.");
      }

      if (!useLastAttachments) {
        await clearComposerAttachments();
      }

      if (Nova.sessions && typeof Nova.sessions.refresh === "function") {
        await Nova.sessions.refresh();
      }
    } catch (err) {
      console.error("sendMessage failed:", err);
      addErrorMessage(err.message || "Failed to send message.");
    } finally {
      setSending(false);
      updateRegenerateVisualState();
    }
  }

  async function regenerateLast() {
    if (state.isSending) return;
    if (!state.lastUserMessage) return;

    const btn = getRegenerateButton();
    if (btn) {
      if (!btn.dataset.originalLabel) {
        btn.dataset.originalLabel = btn.textContent?.trim() || "Regenerate";
      }
      btn.textContent = "Working...";
    }

    await sendMessage(state.lastUserMessage, {
      useLastAttachments: false,
    });
  }

  function bindComposer() {
    const sendBtn = getSendButton();
    const input = getComposerInput();
    const regenBtn = getRegenerateButton();

    if (sendBtn && sendBtn.dataset.bound !== "1") {
      sendBtn.dataset.bound = "1";
      sendBtn.addEventListener("click", () => {
        sendMessage();
      });
    }

    if (regenBtn && regenBtn.dataset.bound !== "1") {
      regenBtn.dataset.bound = "1";
      if (!regenBtn.dataset.originalLabel) {
        regenBtn.dataset.originalLabel = regenBtn.textContent?.trim() || "Regenerate";
      }
      regenBtn.addEventListener("click", () => {
        regenerateLast();
      });
    }

    if (input && input.dataset.bound !== "1") {
      input.dataset.bound = "1";
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          sendMessage();
        }
      });
    }
  }

  function bootstrap() {
    injectChatPolishStyles();
    bindComposer();
    setSending(false);
    updateRegenerateVisualState();
  }

  Nova.chat.loadSession = loadSession;
  Nova.chat.renderMessages = renderMessages;
  Nova.chat.sendMessage = sendMessage;
  Nova.chat.regenerate = regenerateLast;
  Nova.chat.state = state;

  document.addEventListener("DOMContentLoaded", bootstrap);
})();