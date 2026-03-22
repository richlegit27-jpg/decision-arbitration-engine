(() => {
  "use strict";

  if (window.__novaUltimateLoaded) return;
  window.__novaUltimateLoaded = true;

  const API = {
    state: "/api/state",
    newSession: "/api/session/new",
    getChat: (sessionId) => `/api/chat/${encodeURIComponent(sessionId)}`,
    stream: "/api/chat/stream",
    memory: "/api/memory",
    addMemory: "/api/memory/add",
    upload: "/api/upload",
  };

  const DEFAULT_MODEL = "gpt-4.1-mini";
  const MAX_INPUT_HEIGHT = 180;

  const state = {
    sessions: [],
    messages: [],
    memoryItems: [],
    activeSessionId: null,
    currentModel: DEFAULT_MODEL,
    isSending: false,
    attachedFiles: [],
    lastUserMessage: "",
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function qs(sel, root = document) {
    return root.querySelector(sel);
  }

  function qsa(sel, root = document) {
    return Array.from(root.querySelectorAll(sel));
  }

  function safeText(value) {
    return String(value ?? "").trim();
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function nowUnix() {
    return Math.floor(Date.now() / 1000);
  }

  function formatTime(ts) {
    if (!ts) return "";
    try {
      return new Date(Number(ts) * 1000).toLocaleString();
    } catch {
      return "";
    }
  }

  function setStatus(text) {
    const el =
      byId("statusText") ||
      byId("modelStatus") ||
      byId("chatStatus") ||
      byId("mobileModelStatus");
    if (el) el.textContent = safeText(text || "Ready");
  }

  function autosizeInput() {
    const input = byId("messageInput");
    if (!input) return;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, MAX_INPUT_HEIGHT)}px`;
  }

  function scrollChatToBottom() {
    const container = byId("chatMessages");
    if (!container) return;
    container.scrollTop = container.scrollHeight;
  }

  function updateLastUserMessage() {
    const last = [...state.messages]
      .reverse()
      .find((msg) => safeText(msg.role).toLowerCase() === "user" && safeText(msg.content));
    state.lastUserMessage = last ? String(last.content || "") : "";

    const regenBtn = byId("regenerateBtn");
    if (regenBtn) {
      regenBtn.disabled = state.isSending || !state.lastUserMessage;
    }
  }

  function setSendingState(isSending) {
    state.isSending = Boolean(isSending);

    const sendBtn = byId("sendBtn");
    const regenBtn = byId("regenerateBtn");
    const input = byId("messageInput");
    const attachBtn = byId("attachBtn");
    const newBtn = byId("newSessionBtn");

    if (sendBtn) {
      sendBtn.disabled = state.isSending;
      sendBtn.setAttribute("aria-busy", state.isSending ? "true" : "false");
    }

    if (regenBtn) {
      regenBtn.disabled = state.isSending || !state.lastUserMessage;
      regenBtn.setAttribute("aria-busy", state.isSending ? "true" : "false");
    }

    if (input) input.disabled = state.isSending;
    if (attachBtn) attachBtn.disabled = state.isSending;
    if (newBtn) newBtn.disabled = state.isSending;

    document.body.classList.toggle("is-sending", state.isSending);
  }

  async function apiGet(url) {
    const res = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
    });

    if (!res.ok) {
      throw new Error(`GET failed: ${url}`);
    }

    return res.json();
  }

  async function apiPost(url, payload) {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload || {}),
    });

    if (!res.ok) {
      let msg = `POST failed: ${url}`;
      try {
        const data = await res.json();
        msg = data.detail || data.message || msg;
      } catch {}
      throw new Error(msg);
    }

    return res.json();
  }

  async function uploadFiles(files) {
    const list = Array.isArray(files) ? files : [];
    if (!list.length) return [];

    const formData = new FormData();
    for (const file of list) {
      formData.append("files", file);
    }

    const res = await fetch(API.upload, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      throw new Error("Upload failed");
    }

    const data = await res.json();
    return Array.isArray(data.files) ? data.files : [];
  }

  async function copyTextToClipboard(text) {
    const value = String(text ?? "");
    if (!value) return false;

    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
        return true;
      }
    } catch {}

    try {
      const temp = document.createElement("textarea");
      temp.value = value;
      temp.setAttribute("readonly", "readonly");
      temp.style.position = "fixed";
      temp.style.left = "-9999px";
      document.body.appendChild(temp);
      temp.focus();
      temp.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(temp);
      return ok;
    } catch {
      return false;
    }
  }

  function ensureDesktopActionButtons() {
    const composer =
      byId("composerActions") ||
      byId("chatComposerActions") ||
      qs(".composer-actions") ||
      qs(".input-actions") ||
      byId("sendBtn")?.parentElement;

    if (!composer) return;

    if (!byId("regenerateBtn")) {
      const regenBtn = document.createElement("button");
      regenBtn.type = "button";
      regenBtn.id = "regenerateBtn";
      regenBtn.className = "nova-action-btn secondary";
      regenBtn.textContent = "Regenerate";

      const sendBtn = byId("sendBtn");
      if (sendBtn && sendBtn.parentElement === composer) {
        composer.insertBefore(regenBtn, sendBtn);
      } else {
        composer.appendChild(regenBtn);
      }
    }
  }

  function renderAttachedFiles() {
    const bar = byId("attachedFilesBar") || byId("attachedFiles");
    if (!bar) return;

    bar.innerHTML = "";

    if (!state.attachedFiles.length) {
      bar.classList.remove("has-files");
      return;
    }

    bar.classList.add("has-files");

    state.attachedFiles.forEach((file, index) => {
      const chip = document.createElement("div");
      chip.className = "file-chip";
      chip.innerHTML = `
        <span>${escapeHtml(file.name)} (${Math.max(1, Math.round((Number(file.size) || 0) / 1024))} KB)</span>
        <button type="button" data-file-index="${index}" aria-label="Remove file">✕</button>
      `;
      bar.appendChild(chip);
    });

    qsa("[data-file-index]", bar).forEach((btn) => {
      btn.addEventListener("click", () => {
        const index = Number(btn.getAttribute("data-file-index"));
        if (Number.isNaN(index)) return;
        state.attachedFiles.splice(index, 1);
        renderAttachedFiles();

        const fileInput = byId("fileInput");
        if (!state.attachedFiles.length && fileInput) {
          fileInput.value = "";
        }
      });
    });
  }

  function updateSessionBadge() {
    const titleEl = byId("chatTitle") || byId("sessionTitle");
    const subtitleEl = byId("chatSubtitle") || byId("sessionSubtitle");

    const currentSession = state.sessions.find(
      (item) => item.session_id === state.activeSessionId
    );

    if (titleEl) titleEl.textContent = currentSession?.title || "Nova";
    if (subtitleEl) {
      subtitleEl.textContent = state.isSending
        ? "Thinking..."
        : `${state.messages.length || 0} messages`;
    }
  }

  function renderSessions() {
    const list =
      byId("sessionList") ||
      byId("sessionsList") ||
      qs("[data-role='session-list']");

    if (!list) return;

    if (!state.sessions.length) {
      list.innerHTML = `<div class="session-empty">No chats yet.</div>`;
      return;
    }

    list.innerHTML = state.sessions
      .map((session) => {
        const isActive = session.session_id === state.activeSessionId;
        return `
          <button
            class="session-item ${isActive ? "active" : ""}"
            type="button"
            data-session-id="${escapeHtml(session.session_id)}"
          >
            <div class="session-item-title">${escapeHtml(session.title || "New Chat")}</div>
            <div class="session-item-meta">${escapeHtml(String(session.message_count || 0))} messages</div>
          </button>
        `;
      })
      .join("");

    qsa("[data-session-id]", list).forEach((btn) => {
      btn.addEventListener("click", async () => {
        const sessionId = btn.getAttribute("data-session-id");
        if (!sessionId || sessionId === state.activeSessionId) return;

        try {
          setStatus("Loading chat...");
          await loadSession(sessionId);
          setStatus("Ready");
        } catch (err) {
          console.error(err);
          setStatus("Load failed");
        }
      });
    });
  }

  function renderMemory() {
    const list = byId("memoryList");
    if (!list) return;

    if (!state.memoryItems.length) {
      list.innerHTML = `<div class="memory-empty">No saved memory yet.</div>`;
      return;
    }

    list.innerHTML = state.memoryItems
      .map((item) => `
        <div class="memory-item">
          <div class="memory-item-kind">${escapeHtml(item.kind || "memory")}</div>
          <div class="memory-item-value">${escapeHtml(item.value || "")}</div>
          <div class="memory-item-meta">${escapeHtml(
            formatTime(item.updated_at || item.created_at || nowUnix())
          )}</div>
        </div>
      `)
      .join("");
  }

  function renderMessages() {
    const container = byId("chatMessages");
    if (!container) return;

    if (!state.messages.length) {
      container.innerHTML = `
        <div class="chat-empty-state">
          <div class="chat-empty-card">
            <div class="chat-empty-title">Nova is ready</div>
            <div class="chat-empty-subtitle">Start a new message.</div>
          </div>
        </div>
      `;
      updateLastUserMessage();
      updateSessionBadge();
      return;
    }

    container.innerHTML = state.messages
      .map((msg, index) => {
        const role = safeText(msg.role || "assistant").toLowerCase();
        const content = escapeHtml(msg.content || "").replace(/\n/g, "<br>");
        const time = formatTime(msg.timestamp || nowUnix());
        const isAssistant = role === "assistant";

        return `
          <article class="chat-message ${escapeHtml(role)}">
            <div class="chat-message-role">${escapeHtml(role)}</div>
            <div class="chat-message-content">${content || "&nbsp;"}</div>
            <div class="chat-message-footer">
              <div class="chat-message-time">${escapeHtml(time)}</div>
              ${
                isAssistant
                  ? `
                <div class="chat-message-actions">
                  <button
                    type="button"
                    class="chat-message-action-btn"
                    data-copy-index="${index}"
                    aria-label="Copy message"
                  >
                    Copy
                  </button>
                </div>
              `
                  : ""
              }
            </div>
          </article>
        `;
      })
      .join("");

    qsa("[data-copy-index]", container).forEach((btn) => {
      btn.addEventListener("click", async () => {
        const index = Number(btn.getAttribute("data-copy-index"));
        if (Number.isNaN(index)) return;

        const msg = state.messages[index];
        if (!msg) return;

        const original = btn.textContent;
        const ok = await copyTextToClipboard(msg.content || "");
        btn.textContent = ok ? "Copied" : "Failed";

        setTimeout(() => {
          btn.textContent = original || "Copy";
        }, 1200);
      });
    });

    updateLastUserMessage();
    updateSessionBadge();
    scrollChatToBottom();
  }

  function addLocalMessage(role, content) {
    state.messages.push({
      role: safeText(role || "assistant"),
      content: String(content ?? ""),
      timestamp: nowUnix(),
    });
    renderMessages();
  }

  async function loadState() {
    const data = await apiGet(API.state);
    state.sessions = Array.isArray(data.sessions) ? data.sessions : [];

    if (state.activeSessionId) {
      const exists = state.sessions.some((s) => s.session_id === state.activeSessionId);
      if (!exists) {
        state.activeSessionId = state.sessions[0]?.session_id || null;
      }
    } else if (state.sessions.length) {
      state.activeSessionId = state.sessions[0].session_id;
    }

    renderSessions();
    updateSessionBadge();
  }

  async function loadSession(sessionId) {
    if (!sessionId) return;

    const data = await apiGet(API.getChat(sessionId));
    state.activeSessionId = data.session_id || sessionId;
    state.messages = Array.isArray(data.messages) ? data.messages : [];
    renderMessages();
    renderSessions();
  }

  async function loadMemory() {
    const data = await apiGet(API.memory);
    state.memoryItems = Array.isArray(data.items) ? data.items : [];
    renderMemory();
  }

  async function createNewSession() {
    const data = await apiPost(API.newSession, {});
    await loadState();

    if (data.session_id) {
      await loadSession(data.session_id);
    } else {
      state.messages = [];
      renderMessages();
    }
  }

  async function addMemory(kind, value) {
    await apiPost(API.addMemory, { kind, value });
    await loadMemory();
  }

  async function streamSend(content, attachedFilesOverride = null) {
    const input = byId("messageInput");
    const normalizedContent = safeText(content);
    const pendingFiles = Array.isArray(attachedFilesOverride)
      ? [...attachedFilesOverride]
      : [...state.attachedFiles];

    if (!normalizedContent && !pendingFiles.length) return;

    if (!state.activeSessionId) {
      await createNewSession();
    }

    setSendingState(true);
    setStatus("Responding...");

    try {
      if (normalizedContent) {
        addLocalMessage("user", normalizedContent);
      } else if (pendingFiles.length) {
        addLocalMessage("user", `[Uploaded ${pendingFiles.length} file(s)]`);
      }

      if (input && attachedFilesOverride === null) {
        input.value = "";
        autosizeInput();
      }

      let uploadedFiles = [];
      if (pendingFiles.length) {
        setStatus("Uploading...");
        uploadedFiles = await uploadFiles(pendingFiles);
      }

      const model = safeText(state.currentModel) || DEFAULT_MODEL;

      const res = await fetch(API.stream, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/plain, */*",
        },
        body: JSON.stringify({
          session_id: state.activeSessionId,
          content: normalizedContent,
          model,
          uploaded_files: uploadedFiles,
        }),
      });

      if (!res.ok) {
        throw new Error("Send failed");
      }

      if (res.body && typeof res.body.getReader === "function") {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          decoder.decode(value, { stream: true });
        }
      } else {
        try {
          await res.text();
        } catch {}
      }

      if (attachedFilesOverride === null) {
        state.attachedFiles = [];
        renderAttachedFiles();
        const fileInput = byId("fileInput");
        if (fileInput) fileInput.value = "";
      }

      await loadState();
      await loadSession(state.activeSessionId);
      await loadMemory();
      setStatus("Ready");
    } catch (err) {
      console.error(err);
      addLocalMessage("assistant", "Something went wrong sending that message.");
      setStatus("Send failed");
    } finally {
      setSendingState(false);
      renderMessages();
    }
  }

  async function sendMessage() {
    if (state.isSending) return;
    const input = byId("messageInput");
    if (!input) return;
    await streamSend(input.value, null);
  }

  async function regenerateLastReply() {
    if (state.isSending) return;

    const content = safeText(state.lastUserMessage);
    if (!content) {
      setStatus("Nothing to regenerate");
      return;
    }

    await streamSend(content, []);
  }

  function bindEvents() {
    ensureDesktopActionButtons();

    byId("newSessionBtn")?.addEventListener("click", async () => {
      try {
        setStatus("Creating chat...");
        await createNewSession();
        setStatus("Ready");
      } catch (err) {
        console.error(err);
        setStatus("Create failed");
      }
    });

    byId("sendBtn")?.addEventListener("click", sendMessage);
    byId("regenerateBtn")?.addEventListener("click", regenerateLastReply);

    byId("messageInput")?.addEventListener("input", autosizeInput);

    byId("messageInput")?.addEventListener("keydown", async (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        await sendMessage();
      }
    });

    byId("attachBtn")?.addEventListener("click", () => {
      if (state.isSending) return;
      byId("fileInput")?.click();
    });

    byId("fileInput")?.addEventListener("change", (event) => {
      const files = Array.from(event.target.files || []);
      if (!files.length) return;

      const existing = new Map(
        state.attachedFiles.map((file) => [`${file.name}__${file.size}`, file])
      );

      for (const file of files) {
        existing.set(`${file.name}__${file.size}`, file);
      }

      state.attachedFiles = Array.from(existing.values());
      renderAttachedFiles();

      const input = byId("fileInput");
      if (input) input.value = "";
    });

    byId("memoryForm")?.addEventListener("submit", async (event) => {
      event.preventDefault();

      const kind = safeText(byId("memoryKind")?.value || "memory");
      const valueEl = byId("memoryValue");
      const value = safeText(valueEl?.value || "");

      if (!value) return;

      try {
        setStatus("Saving memory...");
        await addMemory(kind, value);
        if (valueEl) valueEl.value = "";
        setStatus("Ready");
      } catch (err) {
        console.error(err);
        setStatus("Save failed");
      }
    });
  }

  async function bootstrap() {
    bindEvents();
    setStatus("Loading...");

    await loadState();

    if (state.activeSessionId) {
      await loadSession(state.activeSessionId);
    } else {
      renderMessages();
    }

    await loadMemory();
    renderAttachedFiles();
    autosizeInput();
    setSendingState(false);
    setStatus("Ready");
  }

  document.addEventListener("DOMContentLoaded", () => {
    bootstrap().catch((err) => {
      console.error("Desktop bootstrap failed:", err);
      setStatus("Bootstrap failed");
      setSendingState(false);
    });
  });
})();