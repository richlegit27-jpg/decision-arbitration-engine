(() => {
  "use strict";

  const API = {
    state: "/api/state",
    getChat: (sessionId) => `/api/chat/${encodeURIComponent(sessionId)}`,
    memory: "/api/memory",
    deleteMemory: "/api/memory/delete",
    newSession: "/api/session/new",
    renameSession: "/api/session/rename",
    deleteSession: "/api/session/delete",
    duplicateSession: "/api/session/duplicate",
    pinSession: "/api/session/pin",
    exportSession: "/api/session/export",
    stream: "/api/chat/stream",
    upload: "/api/upload",
  };

  const STORAGE_KEYS = {
    theme: "nova_mobile_theme",
    background: "nova_mobile_background",
  };

  const app = {
    state: {
      sessions: [],
      messages: [],
      memoryItems: [],
      activeSessionId: null,
      currentModel: "gpt-4.1-mini",
      isSending: false,
      attachedFiles: [],
      currentAssistantBubble: null,
      lastUserMessage: "",
    },
  };

  function byId(id) {
    return document.getElementById(id);
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

  function getSessionId(session) {
    return session?.id || session?.session_id || "";
  }

  function getMessageTimestamp(msg) {
    return msg?.created_at || msg?.timestamp || nowUnix();
  }

  function getCurrentSession() {
    return (
      app.state.sessions.find(
        (session) => getSessionId(session) === app.state.activeSessionId
      ) || null
    );
  }

  function getLastAssistantMessage() {
    for (let i = app.state.messages.length - 1; i >= 0; i -= 1) {
      if (safeText(app.state.messages[i]?.role).toLowerCase() === "assistant") {
        return app.state.messages[i];
      }
    }
    return null;
  }

  function getLastUserMessage() {
    for (let i = app.state.messages.length - 1; i >= 0; i -= 1) {
      if (safeText(app.state.messages[i]?.role).toLowerCase() === "user") {
        return app.state.messages[i];
      }
    }
    return null;
  }

  function setSendDisabled(disabled) {
    const sendBtn = byId("mobileSendBtn");
    const attachBtn = byId("mobileAttachBtn");
    const input = byId("mobileMessageInput");

    if (sendBtn) {
      sendBtn.disabled = disabled;
      sendBtn.textContent = disabled ? "..." : "Send";
    }

    if (attachBtn) {
      attachBtn.disabled = disabled;
    }

    if (input) {
      input.disabled = disabled;
    }
  }

  async function apiGet(url) {
    const res = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });

    if (!res.ok) {
      throw new Error(`GET failed: ${url}`);
    }

    return res.json();
  }

  async function apiPost(url, payload) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    });

    if (!res.ok) {
      let msg = `POST failed: ${url}`;
      try {
        const data = await res.json();
        msg = data.error || data.detail || data.message || msg;
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

  function setStatus(text) {
    const el = byId("mobileModelStatus");
    if (el) {
      el.textContent = safeText(text || "Model ready");
    }
  }

  function updateHeader() {
    const titleEl = byId("mobileChatTitle");
    const subtitleEl = byId("mobileChatSubtitle");
    const currentSession = getCurrentSession();

    if (titleEl) {
      titleEl.textContent = currentSession?.title || "Nova";
    }

    if (subtitleEl) {
      subtitleEl.textContent = app.state.isSending
        ? "Thinking..."
        : `${app.state.messages.length || 0} messages`;
    }
  }

  function openScreen(screenId) {
    const el = byId(screenId);
    if (!el) return;
    el.classList.remove("hidden");
    el.setAttribute("aria-hidden", "false");
    document.body.classList.add("mobile-screen-open");
  }

  function closeScreen(screenId) {
    const el = byId(screenId);
    if (!el) return;
    el.classList.add("hidden");
    el.setAttribute("aria-hidden", "true");

    const menuOpen = byId("mobileMenuScreen") && !byId("mobileMenuScreen").classList.contains("hidden");
    const memoryOpen = byId("mobileMemoryScreen") && !byId("mobileMemoryScreen").classList.contains("hidden");

    if (!menuOpen && !memoryOpen) {
      document.body.classList.remove("mobile-screen-open");
    }
  }

  function closeAllScreens() {
    closeScreen("mobileMenuScreen");
    closeScreen("mobileMemoryScreen");
  }

  function autosizeInput() {
    const input = byId("mobileMessageInput");
    if (!input) return;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
  }

  function scrollMessagesToBottom(behavior = "auto") {
    const container = byId("mobileChatMessages");
    if (!container) return;

    try {
      container.scrollTo({
        top: container.scrollHeight,
        behavior,
      });
    } catch {
      container.scrollTop = container.scrollHeight;
    }
  }

  function applyTheme(theme) {
    const value = theme === "light" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", value);
    localStorage.setItem(STORAGE_KEYS.theme, value);
  }

  function cycleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    applyTheme(current === "dark" ? "light" : "dark");
    setStatus(`Theme: ${document.documentElement.getAttribute("data-theme")}`);
  }

  function applyBackground(mode) {
    const body = document.body;
    if (!body) return;

    body.dataset.mobileBackground = mode;
    localStorage.setItem(STORAGE_KEYS.background, mode);

    if (mode === "flat") {
      body.style.background = "#08101f";
    } else if (mode === "deep") {
      body.style.background =
        "linear-gradient(180deg, #060d19 0%, #08101f 50%, #0d1730 100%)";
    } else {
      body.style.background =
        "radial-gradient(circle at top, rgba(90, 132, 255, 0.16), transparent 32%), linear-gradient(180deg, #0d1730 0%, #08101f 100%)";
    }
  }

  function cycleBackground() {
    const current = document.body?.dataset?.mobileBackground || "glow";
    const next = current === "glow" ? "deep" : current === "deep" ? "flat" : "glow";
    applyBackground(next);
    setStatus(`Background: ${next}`);
  }

  function initAppearance() {
    applyTheme(localStorage.getItem(STORAGE_KEYS.theme) || "dark");
    applyBackground(localStorage.getItem(STORAGE_KEYS.background) || "glow");
  }

  function renderAttachedFiles() {
    const bar = byId("mobileAttachedFiles");
    if (!bar) return;

    if (!app.state.attachedFiles.length) {
      bar.innerHTML = "";
      return;
    }

    bar.innerHTML = app.state.attachedFiles
      .map(
        (file, index) => `
          <div class="mobile-file-chip">
            <span>${escapeHtml(file.name)} (${Math.max(1, Math.round((file.size || 0) / 1024))} KB)</span>
            <button type="button" class="mobile-file-chip-remove" data-file-index="${index}" aria-label="Remove file">✕</button>
          </div>
        `
      )
      .join("");

    bar.querySelectorAll("[data-file-index]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const index = Number(btn.getAttribute("data-file-index"));
        if (Number.isInteger(index) && index >= 0) {
          app.state.attachedFiles.splice(index, 1);
          renderAttachedFiles();
          setStatus("Attachment removed");
        }
      });
    });
  }

  function renderEmptyState(container) {
    container.innerHTML = `
      <div class="mobile-empty-state">
        <div class="mobile-empty-card">
          <div class="mobile-empty-title">Nova Mobile is ready</div>
          <div class="mobile-empty-subtitle">Start a new message.</div>
        </div>
      </div>
    `;
  }

  function renderMessages() {
    const container = byId("mobileChatMessages");
    if (!container) return;

    app.state.currentAssistantBubble = null;

    if (!app.state.messages.length) {
      renderEmptyState(container);
      updateHeader();
      return;
    }

    const html = app.state.messages
      .map((msg, index) => {
        const role = safeText(msg.role || "assistant").toLowerCase();
        const content = escapeHtml(msg.content || "").replace(/\n/g, "<br>");
        const timeText = escapeHtml(formatTime(getMessageTimestamp(msg)));
        const isAssistant = role === "assistant";

        return `
          <div class="mobile-message-row ${role}">
            <div class="mobile-message-bubble">
              <div class="mobile-message-role">${escapeHtml(role)}</div>
              <div class="mobile-message-content">${content}</div>
              <div class="mobile-message-time">${timeText}</div>
              ${
                isAssistant
                  ? `
                <div class="mobile-message-actions">
                  <button type="button" class="mobile-inline-action" data-copy-index="${index}">Copy</button>
                  <button type="button" class="mobile-inline-action" data-regenerate-index="${index}">Regenerate</button>
                </div>
              `
                  : ""
              }
            </div>
          </div>
        `;
      })
      .join("");

    container.innerHTML = `<div class="mobile-message-list">${html}</div>`;

    container.querySelectorAll("[data-copy-index]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const index = Number(btn.getAttribute("data-copy-index"));
        const msg = app.state.messages[index];
        if (!msg) return;
        await copyText(msg.content || "");
      });
    });

    container.querySelectorAll("[data-regenerate-index]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const index = Number(btn.getAttribute("data-regenerate-index"));
        await regenerateFromAssistantIndex(index);
      });
    });

    scrollMessagesToBottom();
    updateHeader();
  }

  function createStreamingAssistantBubble() {
    const container = byId("mobileChatMessages");
    if (!container) return null;

    let list = container.querySelector(".mobile-message-list");
    if (!list) {
      container.innerHTML = `<div class="mobile-message-list"></div>`;
      list = container.querySelector(".mobile-message-list");
    }

    const row = document.createElement("div");
    row.className = "mobile-message-row assistant";

    const bubble = document.createElement("div");
    bubble.className = "mobile-message-bubble";

    const role = document.createElement("div");
    role.className = "mobile-message-role";
    role.textContent = "assistant";

    const content = document.createElement("div");
    content.className = "mobile-message-content";
    content.innerHTML = "";

    const time = document.createElement("div");
    time.className = "mobile-message-time";
    time.textContent = "Streaming...";

    bubble.appendChild(role);
    bubble.appendChild(content);
    bubble.appendChild(time);
    row.appendChild(bubble);
    list.appendChild(row);

    scrollMessagesToBottom("smooth");
    app.state.currentAssistantBubble = {
      row,
      bubble,
      content,
      time,
      text: "",
      done: false,
    };

    return app.state.currentAssistantBubble;
  }

  function appendStreamingDelta(delta) {
    if (!app.state.currentAssistantBubble) {
      createStreamingAssistantBubble();
    }

    if (!app.state.currentAssistantBubble) return;

    app.state.currentAssistantBubble.text += String(delta || "");
    app.state.currentAssistantBubble.content.innerHTML = escapeHtml(
      app.state.currentAssistantBubble.text
    ).replace(/\n/g, "<br>");

    scrollMessagesToBottom("smooth");
  }

  function finalizeStreamingAssistantBubble(finalText = "") {
    if (!app.state.currentAssistantBubble) return;

    const bubble = app.state.currentAssistantBubble;
    if (finalText) {
      bubble.text = String(finalText);
      bubble.content.innerHTML = escapeHtml(bubble.text).replace(/\n/g, "<br>");
    }

    bubble.done = true;
    bubble.time.textContent = formatTime(nowUnix());
  }

  function finishStreamingAssistantBubble() {
    if (!app.state.currentAssistantBubble) return;
    finalizeStreamingAssistantBubble(app.state.currentAssistantBubble.text || "");
    app.state.currentAssistantBubble = null;
  }

  function renderSessions() {
    const list = byId("mobileSessionList");
    if (!list) return;

    if (!app.state.sessions.length) {
      list.innerHTML = `<div class="mobile-card">No chats yet.</div>`;
      return;
    }

    list.innerHTML = app.state.sessions
      .map((session) => {
        const sessionId = getSessionId(session);
        const activeClass = sessionId === app.state.activeSessionId ? " is-active" : "";
        const pinned = Boolean(session.pinned);

        return `
          <div class="mobile-session-card${activeClass}">
            <button class="mobile-session-item${activeClass}" data-session-id="${escapeHtml(sessionId)}" type="button">
              <div class="mobile-session-title">${escapeHtml(session.title || "New Chat")}</div>
              <div class="mobile-session-meta">${escapeHtml(String(session.message_count || 0))} messages${pinned ? " • pinned" : ""}</div>
            </button>
            <div class="mobile-session-actions">
              <button type="button" class="mobile-session-action" data-rename-session="${escapeHtml(sessionId)}">Rename</button>
              <button type="button" class="mobile-session-action" data-duplicate-session="${escapeHtml(sessionId)}">Duplicate</button>
              <button type="button" class="mobile-session-action" data-pin-session="${escapeHtml(sessionId)}" data-pin-value="${pinned ? "0" : "1"}">${pinned ? "Unpin" : "Pin"}</button>
              <button type="button" class="mobile-session-action" data-export-session="${escapeHtml(sessionId)}">Export</button>
              <button type="button" class="mobile-session-action mobile-session-action-danger" data-delete-session="${escapeHtml(sessionId)}">Delete</button>
            </div>
          </div>
        `;
      })
      .join("");

    list.querySelectorAll("[data-session-id]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const sessionId = btn.getAttribute("data-session-id");
        await loadSession(sessionId);
        closeScreen("mobileMenuScreen");
      });
    });

    list.querySelectorAll("[data-rename-session]").forEach((btn) => {
      btn.addEventListener("click", async (event) => {
        event.stopPropagation();
        const sessionId = btn.getAttribute("data-rename-session");
        await renameSession(sessionId);
      });
    });

    list.querySelectorAll("[data-duplicate-session]").forEach((btn) => {
      btn.addEventListener("click", async (event) => {
        event.stopPropagation();
        const sessionId = btn.getAttribute("data-duplicate-session");
        await duplicateSession(sessionId);
      });
    });

    list.querySelectorAll("[data-pin-session]").forEach((btn) => {
      btn.addEventListener("click", async (event) => {
        event.stopPropagation();
        const sessionId = btn.getAttribute("data-pin-session");
        const pinned = btn.getAttribute("data-pin-value") === "1";
        await pinSession(sessionId, pinned);
      });
    });

    list.querySelectorAll("[data-export-session]").forEach((btn) => {
      btn.addEventListener("click", async (event) => {
        event.stopPropagation();
        const sessionId = btn.getAttribute("data-export-session");
        await exportSession(sessionId);
      });
    });

    list.querySelectorAll("[data-delete-session]").forEach((btn) => {
      btn.addEventListener("click", async (event) => {
        event.stopPropagation();
        const sessionId = btn.getAttribute("data-delete-session");
        await deleteSession(sessionId);
      });
    });
  }

  function renderMemory() {
    const list = byId("mobileMemoryList");
    const status = byId("mobileMemoryStatus");

    if (!list) return;

    if (status) {
      status.textContent = app.state.memoryItems.length
        ? `${app.state.memoryItems.length} memory item(s)`
        : "No saved memory yet.";
    }

    if (!app.state.memoryItems.length) {
      list.innerHTML = `<div class="mobile-card">No saved memory yet.</div>`;
      return;
    }

    list.innerHTML = app.state.memoryItems
      .map((item) => {
        const kind = escapeHtml(item.kind || "memory");
        const value = escapeHtml(item.value || "");
        const timeText = escapeHtml(formatTime(item.created_at || nowUnix()));
        const memoryId = escapeHtml(item.id || "");

        return `
          <div class="mobile-memory-item">
            <div class="mobile-memory-item-top">
              <div class="mobile-memory-kind">${kind}</div>
              <button type="button" class="mobile-memory-delete-btn" data-delete-memory="${memoryId}" aria-label="Delete memory">✕</button>
            </div>
            <div class="mobile-memory-value">${value}</div>
            <div class="mobile-message-time">${timeText}</div>
          </div>
        `;
      })
      .join("");

    list.querySelectorAll("[data-delete-memory]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const memoryId = btn.getAttribute("data-delete-memory");
        await deleteMemory(memoryId);
      });
    });
  }

  async function loadState() {
    const data = await apiGet(API.state);

    app.state.sessions = Array.isArray(data.sessions) ? data.sessions : [];
    app.state.currentModel = safeText(data.current_model || data.model || "gpt-4.1-mini");

    const preferredSessionId =
      data.active_session_id ||
      data.current_session_id ||
      (app.state.sessions[0] ? getSessionId(app.state.sessions[0]) : null);

    if (!app.state.activeSessionId && preferredSessionId) {
      app.state.activeSessionId = preferredSessionId;
    }

    renderSessions();
    updateHeader();
  }

  async function loadSession(sessionId) {
    if (!sessionId) return;

    const data = await apiGet(API.getChat(sessionId));
    app.state.activeSessionId = data.session_id || sessionId;
    app.state.messages = Array.isArray(data.messages) ? data.messages : [];

    const lastUser = getLastUserMessage();
    app.state.lastUserMessage = safeText(lastUser?.content || "");

    renderMessages();
    renderSessions();
  }

  async function loadMemory() {
    const data = await apiGet(API.memory);
    app.state.memoryItems = Array.isArray(data.memory) ? data.memory : [];
    renderMemory();
  }

  async function createNewSession() {
    const data = await apiPost(API.newSession, {});
    await loadState();

    if (data.session_id) {
      await loadSession(data.session_id);
    } else if (app.state.sessions[0]) {
      await loadSession(getSessionId(app.state.sessions[0]));
    }

    closeAllScreens();
    setStatus("New chat ready");
  }

  async function addMemory(kind, value) {
    await apiPost(API.memory, { kind, value });
    await loadMemory();
    setStatus("Memory saved");
  }

  async function deleteMemory(memoryId) {
    if (!memoryId) return;
    await apiPost(API.deleteMemory, { id: memoryId });
    await loadMemory();
    setStatus("Memory deleted");
  }

  async function renameSession(sessionId) {
    if (!sessionId) return;

    const session = app.state.sessions.find((s) => getSessionId(s) === sessionId);
    const currentTitle = session?.title || "New Chat";
    const nextTitle = window.prompt("Rename chat", currentTitle);

    if (nextTitle === null) return;

    const title = safeText(nextTitle);
    if (!title) return;

    await apiPost(API.renameSession, {
      session_id: sessionId,
      title,
    });

    await loadState();
    if (sessionId === app.state.activeSessionId) {
      await loadSession(sessionId);
    }
    setStatus("Chat renamed");
  }

  async function duplicateSession(sessionId) {
    if (!sessionId) return;

    const data = await apiPost(API.duplicateSession, {
      session_id: sessionId,
    });

    await loadState();

    const duplicatedId = getSessionId(data.session || {});
    if (duplicatedId) {
      await loadSession(duplicatedId);
    }

    setStatus("Chat duplicated");
  }

  async function pinSession(sessionId, pinned) {
    if (!sessionId) return;

    await apiPost(API.pinSession, {
      session_id: sessionId,
      pinned,
    });

    await loadState();
    renderSessions();
    setStatus(pinned ? "Chat pinned" : "Chat unpinned");
  }

  async function deleteSession(sessionId) {
    if (!sessionId) return;

    const ok = window.confirm("Delete this chat?");
    if (!ok) return;

    const wasActive = sessionId === app.state.activeSessionId;

    await apiPost(API.deleteSession, {
      session_id: sessionId,
    });

    app.state.activeSessionId = wasActive ? null : app.state.activeSessionId;

    await loadState();

    if (!app.state.activeSessionId && app.state.sessions[0]) {
      app.state.activeSessionId = getSessionId(app.state.sessions[0]);
    }

    if (app.state.activeSessionId) {
      await loadSession(app.state.activeSessionId);
    } else {
      app.state.messages = [];
      renderMessages();
    }

    setStatus("Chat deleted");
  }

  async function exportSession(sessionId) {
    if (!sessionId) return;

    const data = await apiPost(API.exportSession, {
      session_id: sessionId,
    });

    const session = data.session || {};
    const title = safeText(session.title || "nova-chat").replace(/[\\/:*?"<>|]+/g, "_");
    const blob = new Blob([JSON.stringify(session, null, 2)], {
      type: "application/json",
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title || "nova-chat"}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);

    setStatus("Chat exported");
  }

  async function copyText(text) {
    const value = String(text || "");
    if (!value) return;

    try {
      await navigator.clipboard.writeText(value);
      setStatus("Copied");
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = value;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      textarea.remove();
      setStatus("Copied");
    }
  }

  async function regenerateReply() {
    const lastUser = getLastUserMessage();
    const userText = safeText(lastUser?.content || app.state.lastUserMessage);

    if (!userText || app.state.isSending) return;

    const input = byId("mobileMessageInput");
    if (input) {
      input.value = userText;
      autosizeInput();
    }

    await sendMessage({ overrideContent: userText, isRegenerate: true });
  }

  async function regenerateFromAssistantIndex(index) {
    if (app.state.isSending) return;

    let matchedUserText = "";
    for (let i = index - 1; i >= 0; i -= 1) {
      const msg = app.state.messages[i];
      if (safeText(msg?.role).toLowerCase() === "user") {
        matchedUserText = safeText(msg.content || "");
        break;
      }
    }

    if (!matchedUserText) {
      matchedUserText = safeText(app.state.lastUserMessage);
    }

    if (!matchedUserText) return;

    const input = byId("mobileMessageInput");
    if (input) {
      input.value = matchedUserText;
      autosizeInput();
    }

    await sendMessage({ overrideContent: matchedUserText, isRegenerate: true });
  }

  function parseSSEBlock(rawBlock) {
    const lines = String(rawBlock || "").split(/\r?\n/);
    let event = "";
    const dataLines = [];

    for (const line of lines) {
      if (line.startsWith("event:")) {
        event = line.slice(6).trim();
        continue;
      }
      if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }

    const payloadText = dataLines.join("\n").trim();
    let data = {};

    if (payloadText && payloadText !== "[DONE]") {
      data = JSON.parse(payloadText);
    }

    return { event, data };
  }

  async function sendMessage(options = {}) {
    const input = byId("mobileMessageInput");
    if (!input || app.state.isSending) return;

    const overrideContent = safeText(options.overrideContent || "");
    const content = overrideContent || safeText(input.value);
    const hasFiles = app.state.attachedFiles.length > 0;
    const isRegenerate = Boolean(options.isRegenerate);

    if (!content && !hasFiles) return;

    if (!app.state.activeSessionId) {
      await createNewSession();
    }

    app.state.isSending = true;
    setSendDisabled(true);
    setStatus(isRegenerate ? "Regenerating..." : "Responding...");
    updateHeader();

    const userText = content;
    const activeSessionIdBeforeSend = app.state.activeSessionId;

    let localAssistantText = "";
    let streamFinished = false;

    try {
      let uploadedFiles = [];

      if (hasFiles && !isRegenerate) {
        setStatus("Uploading...");
        uploadedFiles = await uploadFiles(app.state.attachedFiles);
      }

      app.state.lastUserMessage = userText;

      app.state.messages.push({
        id: `local-user-${Date.now()}`,
        role: "user",
        content: userText,
        created_at: nowUnix(),
      });
      renderMessages();

      if (!overrideContent) {
        input.value = "";
      }

      if (!isRegenerate) {
        app.state.attachedFiles = [];
        renderAttachedFiles();
      }

      autosizeInput();
      createStreamingAssistantBubble();

      const res = await fetch(API.stream, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream, application/json, text/plain, */*",
        },
        body: JSON.stringify({
          session_id: activeSessionIdBeforeSend,
          content: userText,
          message: userText,
          model: app.state.currentModel,
          uploaded_files: uploadedFiles,
        }),
      });

      if (!res.ok) {
        throw new Error(`Send failed (${res.status})`);
      }

      if (!res.body || typeof res.body.getReader !== "function") {
        const fallbackText = safeText(await res.text()) || "No response.";
        localAssistantText = fallbackText;
        finalizeStreamingAssistantBubble(localAssistantText);
        finishStreamingAssistantBubble();
        streamFinished = true;
      } else {
        const reader = res.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            buffer += decoder.decode();
            break;
          }

          buffer += decoder.decode(value || new Uint8Array(), { stream: true });

          let separatorIndex;
          while ((separatorIndex = buffer.indexOf("\n\n")) !== -1) {
            const rawBlock = buffer.slice(0, separatorIndex).trim();
            buffer = buffer.slice(separatorIndex + 2);

            if (!rawBlock) continue;
            if (rawBlock === "data: [DONE]") continue;

            let parsed;
            try {
              parsed = parseSSEBlock(rawBlock);
            } catch (err) {
              console.warn("Failed to parse SSE block:", rawBlock, err);
              continue;
            }

            const data = parsed.data || {};
            const type = data.type || parsed.event || "";

            if (type === "meta") {
              if (data.session_id) {
                app.state.activeSessionId = data.session_id;
              }
              continue;
            }

            if (type === "delta") {
              const delta =
                typeof data.delta === "string"
                  ? data.delta
                  : typeof data.content === "string"
                  ? data.content
                  : "";

              if (!delta) continue;

              localAssistantText += delta;
              appendStreamingDelta(delta);
              continue;
            }

            if (type === "done") {
              const finalText =
                typeof data.response === "string"
                  ? data.response
                  : typeof data.message?.content === "string"
                  ? data.message.content
                  : typeof data.content === "string"
                  ? data.content
                  : localAssistantText;

              if (data.session_id) {
                app.state.activeSessionId = data.session_id;
              }

              localAssistantText = finalText || localAssistantText;
              finalizeStreamingAssistantBubble(localAssistantText);
              finishStreamingAssistantBubble();
              streamFinished = true;
              continue;
            }

            if (type === "error") {
              throw new Error(data.error || data.message || "Stream failed");
            }
          }
        }

        const trailing = buffer.trim();
        if (trailing && trailing !== "data: [DONE]") {
          try {
            const parsed = parseSSEBlock(trailing);
            const data = parsed.data || {};
            const type = data.type || parsed.event || "";

            if (type === "done") {
              const finalText =
                typeof data.response === "string"
                  ? data.response
                  : typeof data.message?.content === "string"
                  ? data.message.content
                  : typeof data.content === "string"
                  ? data.content
                  : localAssistantText;

              if (data.session_id) {
                app.state.activeSessionId = data.session_id;
              }

              localAssistantText = finalText || localAssistantText;
              finalizeStreamingAssistantBubble(localAssistantText);
              finishStreamingAssistantBubble();
              streamFinished = true;
            }
          } catch (err) {
            console.warn("Trailing SSE parse failed:", err);
          }
        }

        if (!streamFinished) {
          finalizeStreamingAssistantBubble(localAssistantText);
          finishStreamingAssistantBubble();
        }
      }

      await loadState();
      await loadSession(app.state.activeSessionId || activeSessionIdBeforeSend);
      await loadMemory();
      renderMessages();
      renderSessions();
      renderMemory();

      setStatus(isRegenerate ? "Regenerated" : "Model ready");
    } catch (err) {
      console.error(err);

      if (app.state.currentAssistantBubble) {
        const errorText =
          localAssistantText ||
          `Error: ${err?.message || String(err) || "Stream failed"}`;
        finalizeStreamingAssistantBubble(errorText);
        finishStreamingAssistantBubble();
      }

      await loadState().catch(() => {});
      if (app.state.activeSessionId || activeSessionIdBeforeSend) {
        await loadSession(app.state.activeSessionId || activeSessionIdBeforeSend).catch(() => {});
      }

      setStatus("Send failed");
    } finally {
      app.state.isSending = false;
      setSendDisabled(false);
      updateHeader();
      autosizeInput();
      scrollMessagesToBottom("smooth");
    }
  }

  function bindEvents() {
    byId("mobileMenuBtn")?.addEventListener("click", () => {
      renderSessions();
      openScreen("mobileMenuScreen");
    });

    byId("closeMobileMenuBtn")?.addEventListener("click", () => {
      closeScreen("mobileMenuScreen");
    });

    byId("mobileMemoryBtn")?.addEventListener("click", async () => {
      await loadMemory();
      openScreen("mobileMemoryScreen");
    });

    byId("closeMobileMemoryBtn")?.addEventListener("click", () => {
      closeScreen("mobileMemoryScreen");
    });

    byId("mobileNewSessionBtn")?.addEventListener("click", async () => {
      await createNewSession();
    });

    byId("mobileAttachBtn")?.addEventListener("click", () => {
      if (app.state.isSending) return;
      byId("mobileFileInput")?.click();
    });

    byId("mobileFileInput")?.addEventListener("change", (event) => {
      const files = Array.from(event.target.files || []);
      app.state.attachedFiles = files;
      renderAttachedFiles();

      if (files.length) {
        setStatus(`${files.length} attachment${files.length === 1 ? "" : "s"} ready`);
      }

      if (event.target) {
        event.target.value = "";
      }
    });

    byId("mobileSendBtn")?.addEventListener("click", () => sendMessage());

    byId("mobileMessageInput")?.addEventListener("input", autosizeInput);

    byId("mobileMessageInput")?.addEventListener("keydown", async (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        await sendMessage();
      }
    });

    byId("mobileMemoryForm")?.addEventListener("submit", async (event) => {
      event.preventDefault();

      const kind = safeText(byId("mobileMemoryKind")?.value || "memory");
      const value = safeText(byId("mobileMemoryValue")?.value || "");

      if (!value) return;

      await addMemory(kind, value);

      const memoryValueEl = byId("mobileMemoryValue");
      if (memoryValueEl) {
        memoryValueEl.value = "";
      }
    });

    byId("mobileThemeToggleBtn")?.addEventListener("click", () => {
      cycleTheme();
    });

    byId("mobileBackgroundBtn")?.addEventListener("click", () => {
      cycleBackground();
    });

    document.addEventListener("keydown", async (event) => {
      if (event.key === "Escape") {
        closeAllScreens();
      }

      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "r") {
        event.preventDefault();
        await regenerateReply();
      }
    });

    document.addEventListener("visibilitychange", async () => {
      if (!document.hidden) {
        try {
          await loadState();
          if (app.state.activeSessionId) {
            await loadSession(app.state.activeSessionId);
          }
        } catch (err) {
          console.error("Visibility refresh failed:", err);
        }
      }
    });
  }

  async function bootstrap() {
    initAppearance();
    bindEvents();
    setStatus("Loading...");
    setSendDisabled(false);

    await loadState();

    if (app.state.activeSessionId) {
      await loadSession(app.state.activeSessionId);
    } else {
      renderMessages();
    }

    await loadMemory();
    renderAttachedFiles();
    autosizeInput();
    setStatus("Model ready");
  }

  document.addEventListener("DOMContentLoaded", () => {
    bootstrap().catch((err) => {
      console.error("Mobile bootstrap failed:", err);
      setStatus("Bootstrap failed");
      setSendDisabled(false);
    });
  });
})();