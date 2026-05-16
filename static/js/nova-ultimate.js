(() => {
  "use strict";

  if (window.__novaUltimateLoaded) {
    console.warn("Nova ultimate already loaded. Skipping duplicate boot.");
    return;
  }
  window.__novaUltimateLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  const NovaConfig = (window.NovaConfig = window.NovaConfig || {});
  Nova.config = Nova.config || {};

  const API = {
    state: "/api/state",
    getChat: (sessionId) => `/api/chat/${encodeURIComponent(sessionId)}`,
    stream: "/api/chat/stream",
    memory: "/api/memory",
    addMemory: "/api/memory/add",
    deleteMemory: "/api/memory/delete",
    newSession: "/api/session/new",
    deleteSession: "/api/session/delete",
    renameSession: "/api/session/rename",
    duplicateSession: "/api/session/duplicate",
    pinSession: "/api/session/pin",
    upload: "/api/upload",
    models: "/api/models",
    health: "/api/health",
  };

  Nova.config.API = Nova.config.API || API;

  const STORAGE = {
    activeSessionId: "nova_active_session_id",
    currentModel: "nova_selected_model",
    sidebarOpen: "nova_sidebar_open",
    memoryOpen: "nova_memory_open",
    themeMode: "nova_theme_mode",
    backgroundMode: "nova_background_mode",
    pinnedSessionIds: "nova_pinned_session_ids",
  };

  const DEFAULT_MODEL = "gpt-5.4";
  const MAX_INPUT_HEIGHT = 220;
  const MOBILE_BREAKPOINT = 980;

  const state = (Nova.state = Nova.state || {});
  const dom = (Nova.dom = Nova.dom || {});
  const api = (Nova.api = Nova.api || {});

  if (!(state.sessions instanceof Array)) state.sessions = [];
  if (!(state.messages instanceof Array)) state.messages = [];
  if (!(state.memoryItems instanceof Array)) state.memoryItems = [];
  if (!(state.attachedFiles instanceof Array)) state.attachedFiles = [];
  if (!(state.pinnedSessionIds instanceof Set)) state.pinnedSessionIds = new Set();
  if (!(state.deletingMemoryIds instanceof Set)) state.deletingMemoryIds = new Set();

  state.activeSessionId = state.activeSessionId || null;
  state.currentModel = state.currentModel || DEFAULT_MODEL;
  state.lastUserMessage = state.lastUserMessage || "";
  state.lastAssistantMessage = state.lastAssistantMessage || "";
  state.lastRouter = state.lastRouter || null;
  state.isSending = Boolean(state.isSending);
  state.isBootstrapping = Boolean(state.isBootstrapping);
  state.isBooted = Boolean(state.isBooted);
  state.bootError = state.bootError || null;
  state.sidebarOpen = state.sidebarOpen !== false;
  state.memoryOpen = Boolean(state.memoryOpen);
  state.themeMode = state.themeMode || "dark";
  state.backgroundMode = state.backgroundMode || "default";

  function byId(id) {
    return document.getElementById(id);
  }

  function qs(selector, root = document) {
    return root.querySelector(selector);
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function asString(value, fallback = "") {
    return typeof value === "string" ? value : fallback;
  }

  function safeJsonParse(text, fallback = null) {
    try {
      return JSON.parse(text);
    } catch (_) {
      return fallback;
    }
  }

  function readStorage(key, fallback) {
    try {
      const value = window.localStorage.getItem(key);
      return value == null ? fallback : value;
    } catch (_) {
      return fallback;
    }
  }

  function writeStorage(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (_) {}
  }

  function setText(node, value) {
    if (node) node.textContent = value == null ? "" : String(value);
  }

  function setHtml(node, value) {
    if (node) node.innerHTML = value == null ? "" : String(value);
  }

  function show(node) {
    if (node) node.classList.remove("hidden");
  }

  function hide(node) {
    if (node) node.classList.add("hidden");
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function nowIso() {
    return new Date().toISOString();
  }

  function isMobile() {
    return window.innerWidth <= MOBILE_BREAKPOINT;
  }

  function formatDateLoose(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    try {
      return date.toLocaleString();
    } catch (_) {
      return "";
    }
  }

  function extractMessageText(message) {
    if (!message) return "";
    if (typeof message.content === "string") return message.content;
    if (typeof message.text === "string") return message.text;
    if (Array.isArray(message.content)) {
      return message.content
        .map((part) => {
          if (typeof part === "string") return part;
          if (part && typeof part.text === "string") return part.text;
          if (part && typeof part.content === "string") return part.content;
          return "";
        })
        .filter(Boolean)
        .join("\n");
    }
    return "";
  }

  function autosizeComposer() {
    const input = dom.composerInput;
    if (!input) return;
    input.style.height = "auto";
    input.style.height = `${Math.min(Math.max(input.scrollHeight, 44), MAX_INPUT_HEIGHT)}px`;
  }

  function persistUiState() {
    writeStorage(STORAGE.activeSessionId, state.activeSessionId || "");
    writeStorage(STORAGE.currentModel, state.currentModel || DEFAULT_MODEL);
    writeStorage(STORAGE.sidebarOpen, state.sidebarOpen ? "1" : "0");
    writeStorage(STORAGE.memoryOpen, state.memoryOpen ? "1" : "0");
    writeStorage(STORAGE.themeMode, state.themeMode || "dark");
    writeStorage(STORAGE.backgroundMode, state.backgroundMode || "default");
    writeStorage(
      STORAGE.pinnedSessionIds,
      JSON.stringify(Array.from(state.pinnedSessionIds || []))
    );
  }

  function restoreUiState() {
    state.activeSessionId = readStorage(STORAGE.activeSessionId, state.activeSessionId || "") || null;
    state.currentModel = readStorage(STORAGE.currentModel, state.currentModel || DEFAULT_MODEL) || DEFAULT_MODEL;
    state.sidebarOpen = readStorage(STORAGE.sidebarOpen, state.sidebarOpen ? "1" : "0") !== "0";
    state.memoryOpen = readStorage(STORAGE.memoryOpen, state.memoryOpen ? "1" : "0") === "1";
    state.themeMode = readStorage(STORAGE.themeMode, state.themeMode || "dark") || "dark";
    state.backgroundMode = readStorage(STORAGE.backgroundMode, state.backgroundMode || "default") || "default";

    const pinnedRaw = readStorage(STORAGE.pinnedSessionIds, "[]");
    const pinned = safeJsonParse(pinnedRaw, []);
    state.pinnedSessionIds = new Set(Array.isArray(pinned) ? pinned.filter(Boolean) : []);
  }

  function cacheDom() {
    dom.root = byId("nova-app");
    dom.sidebar = byId("sidebar");
    dom.sidebarToggle = byId("sidebarToggle");
    dom.mobileSidebarToggle = byId("mobileSidebarToggle");
    dom.newChatBtn = byId("newChatBtn");
    dom.sessionList = byId("sessionList");

    dom.chatView = byId("chatView");
    dom.chatMessages = byId("chatMessages");
    dom.emptyState = byId("emptyState");
    dom.routerBadge = byId("routerBadge");
    dom.modelSelect = byId("modelSelect");

    dom.memoryPanel = byId("memoryPanel");
    dom.memoryToggle = byId("memoryToggle");
    dom.memoryInput = byId("memoryInput");
    dom.memoryAddBtn = byId("memoryAddBtn");
    dom.memoryList = byId("memoryList");

    dom.composerShell = qs(".composer-shell");
    dom.composerBox = qs(".composer-box");
    dom.composerInput = byId("composerInput");
    dom.sendBtn = byId("sendBtn");
    dom.attachBtn = byId("attachBtn");
    dom.fileInput = byId("fileInput");
    dom.attachmentBar = byId("attachmentBar");
    dom.voiceBtn = byId("voiceBtn");
    dom.regenerateBtn = byId("regenerateBtn");
    dom.themeToggle = byId("themeToggle");

    return dom;
  }

  function ensureShell() {
    cacheDom();
    if (!dom.root) {
      console.warn("Nova bootstrap: #nova-app not found, standing by.");
      return false;
    }
    return true;
  }

  async function apiRequest(url, options = {}) {
    const requestOptions = {
      method: options.method || "GET",
      headers: {
        ...(options.headers || {}),
      },
      body: options.body,
      credentials: options.credentials || "same-origin",
    };

    if (requestOptions.body && !requestOptions.headers["Content-Type"] && !(requestOptions.body instanceof FormData)) {
      requestOptions.headers["Content-Type"] = "application/json";
    }

    const response = await fetch(url, requestOptions);
    const text = await response.text();
    const data = text ? safeJsonParse(text, null) : null;

    if (!response.ok) {
      const errorMessage =
        (data && (data.error || data.message)) ||
        `Request failed: ${response.status} ${response.statusText}`;
      throw new Error(errorMessage);
    }

    return data ?? { ok: true };
  }

  api.request = api.request || apiRequest;
  api.get = api.get || ((url) => apiRequest(url));
  api.post =
    api.post ||
    ((url, payload) =>
      apiRequest(url, {
        method: "POST",
        body: JSON.stringify(payload || {}),
      }));

  function updateRouterBadge(text, tone) {
    if (!dom.routerBadge) return;
    setText(dom.routerBadge, text || "Ready");
    dom.routerBadge.dataset.tone = tone || "neutral";
  }

  function applyTheme() {
    document.documentElement.setAttribute("data-theme", state.themeMode || "dark");
    document.body.dataset.theme = state.themeMode || "dark";
  }

  function applyPanelState() {
    if (dom.sidebar) {
      dom.sidebar.classList.toggle("is-open", !!state.sidebarOpen);
      dom.sidebar.classList.toggle("is-collapsed", !state.sidebarOpen);
    }

    if (dom.memoryPanel) {
      dom.memoryPanel.classList.toggle("is-open", !!state.memoryOpen);
      dom.memoryPanel.classList.toggle("is-collapsed", !state.memoryOpen);
    }

    if (dom.root) {
      dom.root.classList.toggle("sidebar-open", !!state.sidebarOpen);
      dom.root.classList.toggle("memory-open", !!state.memoryOpen);
    }

    if (dom.sidebarToggle) {
      dom.sidebarToggle.setAttribute("aria-expanded", state.sidebarOpen ? "true" : "false");
    }

    if (dom.mobileSidebarToggle) {
      dom.mobileSidebarToggle.setAttribute("aria-expanded", state.sidebarOpen ? "true" : "false");
    }

    if (dom.memoryToggle) {
      dom.memoryToggle.setAttribute("aria-expanded", state.memoryOpen ? "true" : "false");
    }
  }

  function sessionPreviewText(session) {
    const preview = asString(session?.preview, "").trim();
    if (preview) return preview.slice(0, 140);

    const messages = asArray(session?.messages);
    if (!messages.length) return "";

    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const text = extractMessageText(messages[i]).trim();
      if (text) return text.slice(0, 140);
    }

    return "";
  }

  function renderSessions() {
    if (!dom.sessionList) return;

    const sessions = [...asArray(state.sessions)].sort((a, b) => {
      const aPinned = state.pinnedSessionIds.has(a?.id) ? 1 : 0;
      const bPinned = state.pinnedSessionIds.has(b?.id) ? 1 : 0;
      if (aPinned !== bPinned) return bPinned - aPinned;

      const aTime = asString(a?.updated_at || a?.created_at || "");
      const bTime = asString(b?.updated_at || b?.created_at || "");
      return bTime.localeCompare(aTime);
    });

    if (!sessions.length) {
      setHtml(dom.sessionList, `<div class="empty-panel-note">No chats yet.</div>`);
      return;
    }

    setHtml(
      dom.sessionList,
      sessions
        .map((session) => {
          const id = asString(session?.id, "");
          const title = asString(session?.title, "Untitled");
          const preview = sessionPreviewText(session);
          const updated = formatDateLoose(session?.updated_at || session?.created_at || "");
          const messageCount = Number(session?.message_count || asArray(session?.messages).length || 0) || 0;
          const isPinned = state.pinnedSessionIds.has(id);
          const isActive = id && id === state.activeSessionId;

          return `
            <div class="session-item ${isActive ? "is-active" : ""} ${isPinned ? "is-pinned" : ""}" data-session-id="${escapeHtml(id)}">
              <button
                class="session-item-main"
                type="button"
                data-open-session="${escapeHtml(id)}"
                title="${escapeHtml(title)}"
              >
                <div class="session-item-row">
                  <span class="session-item-title">${escapeHtml(title)}</span>
                  ${isPinned ? `<span class="session-item-pin">📌</span>` : ``}
                </div>
                ${preview ? `<div class="session-item-preview">${escapeHtml(preview)}</div>` : ``}
                <div class="session-item-meta">
                  <span>${messageCount} msg${messageCount === 1 ? "" : "s"}</span>
                  ${updated ? `<span>${escapeHtml(updated)}</span>` : ``}
                </div>
              </button>
              <div class="session-item-actions">
                <button class="session-action-btn" type="button" data-rename-session="${escapeHtml(id)}">Rename</button>
                <button class="session-action-btn danger" type="button" data-delete-session="${escapeHtml(id)}">Delete</button>
              </div>
            </div>
          `;
        })
        .join("")
    );
  }

  function renderMemory() {
    if (!dom.memoryList) return;

    const items = asArray(state.memoryItems);

    if (!items.length) {
      setHtml(dom.memoryList, `<div class="empty-panel-note">No memory saved yet.</div>`);
      return;
    }

    setHtml(
      dom.memoryList,
      items
        .map((item) => {
          const id = asString(item?.id, "");
          const kind = asString(item?.kind, "note");
          const value = asString(item?.value, "");
          const createdAt = formatDateLoose(item?.created_at || "");
          const deleting = state.deletingMemoryIds.has(id);

          return `
            <article class="memory-card ${deleting ? "is-deleting" : ""}" data-memory-id="${escapeHtml(id)}">
              <div class="memory-card-top">
                <div>
                  <span class="memory-kind">${escapeHtml(kind)}</span>
                  ${createdAt ? `<div class="memory-date">${escapeHtml(createdAt)}</div>` : ``}
                </div>
                <button
                  class="memory-delete-btn"
                  type="button"
                  data-delete-memory="${escapeHtml(id)}"
                  ${deleting ? "disabled" : ""}
                >
                  ${deleting ? "Deleting..." : "Delete"}
                </button>
              </div>
              <div class="memory-value">${escapeHtml(value)}</div>
            </article>
          `;
        })
        .join("")
    );
  }

  function renderAttachments() {
    if (!dom.attachmentBar) return;

    const files = asArray(state.attachedFiles);
    if (!files.length) {
      setHtml(dom.attachmentBar, "");
      hide(dom.attachmentBar);
      return;
    }

    show(dom.attachmentBar);
    setHtml(
      dom.attachmentBar,
      files
        .map((file, index) => {
          const name = escapeHtml(asString(file?.name || file?.filename, `file-${index + 1}`));
          return `
            <div class="attachment-chip">
              <span class="attachment-chip-name">${name}</span>
              <button
                class="attachment-chip-remove"
                type="button"
                data-remove-attachment="${index}"
                aria-label="Remove attachment"
              >
                ×
              </button>
            </div>
          `;
        })
        .join("")
    );
  }

  function renderMessages() {
    if (!dom.chatMessages) return;

    const messages = asArray(state.messages);
    const emptyHtml = dom.emptyState ? dom.emptyState.outerHTML : "";

    if (!messages.length) {
      setHtml(dom.chatMessages, emptyHtml);
      return;
    }

    setHtml(
      dom.chatMessages,
      emptyHtml +
        messages
          .map((message, index) => {
            const role = asString(message?.role, "assistant").toLowerCase();
            const safeRole =
              role === "user" || role === "assistant" || role === "system" ? role : "assistant";
            const label =
              safeRole === "user" ? "You" : safeRole === "system" ? "System" : "Nova";
            const text = escapeHtml(extractMessageText(message));
            const createdAt = formatDateLoose(message?.created_at || "");
            const attachments = asArray(message?.attachments);
            const isStreaming = Boolean(message?.__streaming);

            return `
              <article class="message message-${safeRole} ${isStreaming ? "is-streaming" : ""}" data-message-index="${index}">
                <div class="message-head">
                  <div class="message-role">${escapeHtml(label)}</div>
                  ${createdAt ? `<div class="message-time">${escapeHtml(createdAt)}</div>` : ``}
                </div>
                <div class="message-body"><pre>${text}</pre></div>
                ${
                  attachments.length
                    ? `
                  <div class="message-attachments">
                    ${attachments
                      .map((file, fileIndex) => {
                        const fileName = escapeHtml(asString(file?.name || file?.filename, `file-${fileIndex + 1}`));
                        return `<div class="message-attachment">${fileName}</div>`;
                      })
                      .join("")}
                  </div>
                `
                    : ""
                }
                ${
                  safeRole === "assistant"
                    ? `
                  <div class="message-actions">
                    <button class="message-action-btn" type="button" data-copy-message="${index}" ${isStreaming ? "disabled" : ""}>
                      Copy
                    </button>
                  </div>
                `
                    : ""
                }
              </article>
            `;
          })
          .join("")
    );

    dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
  }

  function renderComposerState() {
    if (dom.sendBtn) {
      dom.sendBtn.disabled = !!state.isSending;
      dom.sendBtn.textContent = state.isSending ? "Sending..." : "Send";
    }
    if (dom.composerInput) {
      dom.composerInput.disabled = !!state.isSending;
    }
    if (dom.regenerateBtn) {
      dom.regenerateBtn.disabled = !!state.isSending || !asString(state.lastUserMessage, "").trim();
    }
    if (dom.attachBtn) {
      dom.attachBtn.disabled = !!state.isSending;
    }
    if (dom.voiceBtn) {
      dom.voiceBtn.disabled = !!state.isSending;
    }
  }

  function renderModelSelect() {
    if (!dom.modelSelect) return;

    const current = asString(state.currentModel, DEFAULT_MODEL) || DEFAULT_MODEL;
    const existingValues = Array.from(dom.modelSelect.options).map((option) => option.value);
    if (!existingValues.includes(current)) {
      const option = document.createElement("option");
      option.value = current;
      option.textContent = current;
      dom.modelSelect.appendChild(option);
    }
    dom.modelSelect.value = current;
  }

  function renderAll() {
    applyTheme();
    applyPanelState();
    renderModelSelect();
    renderSessions();
    renderMemory();
    renderAttachments();
    renderMessages();
    renderComposerState();
    autosizeComposer();
    updateRouterBadge(state.lastRouter?.label || "Ready", state.lastRouter?.tone || "neutral");
  }

  async function loadState() {
    const data = await api.get(API.state);
    state.sessions = asArray(data?.sessions);
    state.memoryItems = asArray(data?.memory || data?.items);
    state.currentModel = asString(data?.model, state.currentModel || DEFAULT_MODEL);

    const existingIds = new Set(state.sessions.map((s) => asString(s?.id, "")).filter(Boolean));

    if (!state.activeSessionId || !existingIds.has(state.activeSessionId)) {
      state.activeSessionId =
        asString(data?.active_session_id, "") ||
        asString(state.sessions[0]?.id, "") ||
        null;
      persistUiState();
    }

    return data;
  }

  async function loadSession(sessionId) {
    const targetId = asString(sessionId || state.activeSessionId || "");
    if (!targetId) {
      state.messages = [];
      renderAll();
      return null;
    }

    try {
      const data = await api.get(API.getChat(targetId));
      const session = data?.session || {};
      state.activeSessionId = asString(session.id, targetId);
      state.messages = asArray(session.messages);

      state.lastUserMessage = "";
      state.lastAssistantMessage = "";

      for (let i = state.messages.length - 1; i >= 0; i -= 1) {
        const msg = state.messages[i];
        if (!state.lastAssistantMessage && msg?.role === "assistant") {
          state.lastAssistantMessage = extractMessageText(msg);
        }
        if (!state.lastUserMessage && msg?.role === "user") {
          state.lastUserMessage = extractMessageText(msg);
        }
        if (state.lastAssistantMessage && state.lastUserMessage) break;
      }

      renderAll();
      persistUiState();
      return session;
    } catch (error) {
      const msg = error instanceof Error ? error.message.toLowerCase() : "";
      if (msg.includes("session not found")) {
        state.activeSessionId = asString(state.sessions[0]?.id, "") || null;
        writeStorage(STORAGE.activeSessionId, state.activeSessionId || "");
        state.messages = [];
        renderAll();
        return null;
      }
      throw error;
    }
  }

  async function createSession() {
    const data = await api.post(API.newSession, { title: "New Chat" });
    const sessionId = asString(data?.session_id || data?.session?.id, "");
    await loadState();
    if (sessionId) {
      state.activeSessionId = sessionId;
      await loadSession(sessionId);
    } else {
      renderAll();
    }
  }

  async function renameSession(sessionId) {
    const current = asArray(state.sessions).find((item) => asString(item?.id, "") === asString(sessionId, ""));
    const currentTitle = asString(current?.title, "Untitled");
    const nextTitle = window.prompt("Rename chat", currentTitle);

    if (typeof nextTitle !== "string") return;
    const trimmed = nextTitle.trim();
    if (!trimmed || trimmed === currentTitle) return;

    await api.post(API.renameSession, {
      session_id: sessionId,
      title: trimmed,
    });

    await loadState();
    renderAll();
  }

  async function deleteSession(sessionId) {
    const ok = window.confirm("Delete this chat?");
    if (!ok) return;

    await api.post(API.deleteSession, { session_id: sessionId });
    state.sessions = asArray(state.sessions).filter(
      (item) => asString(item?.id, "") !== asString(sessionId, "")
    );

    if (state.activeSessionId === sessionId) {
      state.activeSessionId = asString(state.sessions[0]?.id, "") || null;
    }

    persistUiState();
    await loadState();

    if (state.activeSessionId) {
      await loadSession(state.activeSessionId);
    } else {
      state.messages = [];
      renderAll();
    }
  }

  async function refreshMemory() {
    const data = await api.get(API.memory);
    state.memoryItems = asArray(data?.items || data?.memory);
    renderAll();
  }

  async function addMemory() {
    const value = asString(dom.memoryInput?.value, "").trim();
    if (!value) return;

    if (dom.memoryAddBtn) {
      dom.memoryAddBtn.disabled = true;
      dom.memoryAddBtn.textContent = "Saving...";
    }

    try {
      await api.post(API.addMemory, {
        kind: "note",
        value,
      });

      if (dom.memoryInput) dom.memoryInput.value = "";
      await refreshMemory();
    } finally {
      if (dom.memoryAddBtn) {
        dom.memoryAddBtn.disabled = false;
        dom.memoryAddBtn.textContent = "Add";
      }
    }
  }

  async function deleteMemory(itemId) {
    if (!itemId) return;
    if (state.deletingMemoryIds.has(itemId)) return;

    state.deletingMemoryIds.add(itemId);
    renderAll();

    try {
      await api.post(API.deleteMemory, { id: itemId, item_id: itemId });
      state.memoryItems = asArray(state.memoryItems).filter(
        (item) => asString(item?.id, "") !== asString(itemId, "")
      );
      renderAll();
      await refreshMemory();
    } finally {
      state.deletingMemoryIds.delete(itemId);
      renderAll();
    }
  }

  function normalizeAttachments(list) {
    return asArray(list)
      .map((item, index) => {
        if (!item) return null;

        if (item instanceof File) {
          return {
            id: `file-${Date.now()}-${index}`,
            name: item.name || `file-${index + 1}`,
            filename: item.name || `file-${index + 1}`,
            type: item.type || "",
            size: Number(item.size || 0) || 0,
          };
        }

        if (typeof item !== "object") {
          return {
            id: `file-${Date.now()}-${index}`,
            name: `file-${index + 1}`,
            filename: `file-${index + 1}`,
            type: "",
            size: 0,
          };
        }

        return {
          id: item.id || `file-${Date.now()}-${index}`,
          name: item.name || item.filename || `file-${index + 1}`,
          filename: item.filename || item.name || `file-${index + 1}`,
          type: item.type || item.mime_type || "",
          size: Number(item.size || 0) || 0,
          url: item.url || item.file_url || "",
        };
      })
      .filter(Boolean);
  }

  function setSending(flag) {
    state.isSending = !!flag;
    renderAll();
  }

  async function refreshAfterSend(sessionId) {
    try {
      await loadState();
    } catch (_) {}

    if (sessionId) {
      await loadSession(sessionId);
    } else {
      renderAll();
    }
  }

  async function parseSseStream(response) {
    if (!response.body) {
      throw new Error("Streaming response body missing.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let assistantText = "";
    let assistantMessage = null;

    const ensureAssistant = () => {
      const last = state.messages[state.messages.length - 1];
      if (last && last.role === "assistant" && last.__streaming) {
        assistantMessage = last;
        return last;
      }

      assistantMessage = {
        id: `assistant-stream-${Date.now()}`,
        role: "assistant",
        content: "",
        created_at: nowIso(),
        __streaming: true,
      };
      state.messages.push(assistantMessage);
      return assistantMessage;
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() || "";

      for (const block of blocks) {
        const lines = block.split("\n");
        let eventName = "message";
        const dataLines = [];

        for (const line of lines) {
          if (line.startsWith("event:")) {
            eventName = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            dataLines.push(line.slice(5).trim());
          }
        }

        const rawData = dataLines.join("\n");
        const data = safeJsonParse(rawData, {});

        if (eventName === "start") {
          const incomingSessionId = asString(data?.session_id, "");
          if (incomingSessionId) {
            state.activeSessionId = incomingSessionId;
          }
          continue;
        }

        if (eventName === "delta") {
          const delta = asString(data?.delta, "");
          if (!delta) continue;

          assistantText += delta;
          const msg = ensureAssistant();
          msg.content = assistantText;
          renderAll();
          continue;
        }

        if (eventName === "done") {
          assistantText = asString(data?.content, assistantText);
          const last = state.messages[state.messages.length - 1];
          if (last && last.role === "assistant" && last.__streaming) {
            last.content = assistantText;
            delete last.__streaming;
          } else if (assistantText) {
            state.messages.push({
              id: `assistant-final-${Date.now()}`,
              role: "assistant",
              content: assistantText,
              created_at: nowIso(),
            });
          }
          state.lastAssistantMessage = assistantText || state.lastAssistantMessage || "";
          renderAll();
          continue;
        }

        if (eventName === "error") {
          throw new Error(asString(data?.error, "Stream error."));
        }
      }
    }
  }

  async function sendMessage(override = null) {
    if (state.isSending) return;

    const content = asString(
      override && Object.prototype.hasOwnProperty.call(override, "content")
        ? override.content
        : dom.composerInput?.value,
      ""
    ).trim();

    const attachments = normalizeAttachments(
      override && Object.prototype.hasOwnProperty.call(override, "attachments")
        ? override.attachments
        : state.attachedFiles
    );

    if (!content && !attachments.length) return;

    setSending(true);
    state.lastRouter = { label: "Thinking...", tone: "working" };
    renderAll();

    try {
      let sessionId = state.activeSessionId;

      if (!sessionId) {
        const created = await api.post(API.newSession, { title: "New Chat" });
        sessionId = asString(created?.session_id || created?.session?.id, "");
        state.activeSessionId = sessionId || state.activeSessionId;
        await loadState();
      }

      state.lastUserMessage = content || state.lastUserMessage || "";

      const userMessage = {
        id: `user-local-${Date.now()}`,
        role: "user",
        content,
        created_at: nowIso(),
      };

      if (attachments.length) {
        userMessage.attachments = attachments;
      }

      state.messages.push(userMessage);

      if (!override && dom.composerInput) {
        dom.composerInput.value = "";
        autosizeComposer();
      }

      state.attachedFiles = [];
      renderAll();

      const payload = {
        session_id: state.activeSessionId || sessionId,
        content,
        model: asString(state.currentModel, DEFAULT_MODEL),
        attachments,
        files: attachments,
      };

      const response = await fetch(API.stream, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
        credentials: "same-origin",
      });

      if (!response.ok) {
        const text = await response.text().catch(() => "");
        const data = text ? safeJsonParse(text, null) : null;
        throw new Error(
          asString(data?.error || data?.message, `Stream request failed: ${response.status}`)
        );
      }

      await parseSseStream(response);
      state.lastRouter = { label: "Ready", tone: "success" };
      persistUiState();
      await refreshAfterSend(state.activeSessionId || sessionId);
    } catch (error) {
      console.error("Nova send failed:", error);
      state.lastRouter = { label: "Error", tone: "danger" };
      state.messages.push({
        id: `system-error-${Date.now()}`,
        role: "system",
        content: error instanceof Error ? error.message : "Send failed.",
        created_at: nowIso(),
      });
      renderAll();
    } finally {
      setSending(false);
      persistUiState();
    }
  }

  async function regenerateLast() {
    if (state.isSending) return;
    const lastUser = asString(state.lastUserMessage, "").trim();
    if (!lastUser) return;

    if (dom.composerInput) {
      dom.composerInput.value = lastUser;
      autosizeComposer();
    }

    await sendMessage({
      content: lastUser,
      attachments: [],
    });
  }

  function bindComposer() {
    if (dom.composerInput && !dom.composerInput.__novaBound) {
      dom.composerInput.__novaBound = true;
      dom.composerInput.addEventListener("input", autosizeComposer);
      dom.composerInput.addEventListener("keydown", async (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          await sendMessage();
        }
      });
    }

    if (dom.sendBtn && !dom.sendBtn.__novaBound) {
      dom.sendBtn.__novaBound = true;
      dom.sendBtn.addEventListener("click", async () => {
        await sendMessage();
      });
    }

    if (dom.regenerateBtn && !dom.regenerateBtn.__novaBound) {
      dom.regenerateBtn.__novaBound = true;
      dom.regenerateBtn.addEventListener("click", async () => {
        await regenerateLast();
      });
    }

    if (dom.attachBtn && dom.fileInput && !dom.attachBtn.__novaBound) {
      dom.attachBtn.__novaBound = true;
      dom.attachBtn.addEventListener("click", () => {
        dom.fileInput.click();
      });
    }

    if (dom.fileInput && !dom.fileInput.__novaBound) {
      dom.fileInput.__novaBound = true;
      dom.fileInput.addEventListener("change", (event) => {
        state.attachedFiles = normalizeAttachments(Array.from(event.target.files || []));
        renderAll();
      });
    }

    if (dom.attachmentBar && !dom.attachmentBar.__novaBound) {
      dom.attachmentBar.__novaBound = true;
      dom.attachmentBar.addEventListener("click", (event) => {
        const button = event.target.closest("[data-remove-attachment]");
        if (!button) return;
        const index = Number(button.getAttribute("data-remove-attachment"));
        if (Number.isNaN(index)) return;
        state.attachedFiles = asArray(state.attachedFiles).filter((_, i) => i !== index);
        renderAll();
      });
    }
  }

  function bindPanels() {
    if (dom.sidebarToggle && !dom.sidebarToggle.__novaBound) {
      dom.sidebarToggle.__novaBound = true;
      dom.sidebarToggle.addEventListener("click", () => {
        state.sidebarOpen = !state.sidebarOpen;
        applyPanelState();
        persistUiState();
      });
    }

    if (dom.mobileSidebarToggle && !dom.mobileSidebarToggle.__novaBound) {
      dom.mobileSidebarToggle.__novaBound = true;
      dom.mobileSidebarToggle.addEventListener("click", () => {
        state.sidebarOpen = !state.sidebarOpen;
        if (state.sidebarOpen && isMobile()) state.memoryOpen = false;
        applyPanelState();
        persistUiState();
      });
    }

    if (dom.memoryToggle && !dom.memoryToggle.__novaBound) {
      dom.memoryToggle.__novaBound = true;
      dom.memoryToggle.addEventListener("click", () => {
        state.memoryOpen = !state.memoryOpen;
        if (state.memoryOpen && isMobile()) state.sidebarOpen = false;
        applyPanelState();
        persistUiState();
      });
    }

    if (dom.themeToggle && !dom.themeToggle.__novaBound) {
      dom.themeToggle.__novaBound = true;
      dom.themeToggle.addEventListener("click", () => {
        state.themeMode = state.themeMode === "light" ? "dark" : "light";
        applyTheme();
        persistUiState();
      });
    }
  }

  function bindSessions() {
    if (dom.newChatBtn && !dom.newChatBtn.__novaBound) {
      dom.newChatBtn.__novaBound = true;
      dom.newChatBtn.addEventListener("click", async () => {
        await createSession();
      });
    }

    if (dom.sessionList && !dom.sessionList.__novaBound) {
      dom.sessionList.__novaBound = true;
      dom.sessionList.addEventListener("click", async (event) => {
        const openBtn = event.target.closest("[data-open-session]");
        if (openBtn) {
          const sessionId = asString(openBtn.getAttribute("data-open-session"), "");
          if (sessionId) {
            await loadSession(sessionId);
            if (isMobile()) {
              state.sidebarOpen = false;
              applyPanelState();
              persistUiState();
            }
          }
          return;
        }

        const renameBtn = event.target.closest("[data-rename-session]");
        if (renameBtn) {
          const sessionId = asString(renameBtn.getAttribute("data-rename-session"), "");
          if (sessionId) {
            await renameSession(sessionId);
          }
          return;
        }

        const deleteBtn = event.target.closest("[data-delete-session]");
        if (deleteBtn) {
          const sessionId = asString(deleteBtn.getAttribute("data-delete-session"), "");
          if (sessionId) {
            await deleteSession(sessionId);
          }
        }
      });
    }
  }

  function bindMemory() {
    if (dom.memoryAddBtn && !dom.memoryAddBtn.__novaBound) {
      dom.memoryAddBtn.__novaBound = true;
      dom.memoryAddBtn.addEventListener("click", async () => {
        await addMemory();
      });
    }

    if (dom.memoryInput && !dom.memoryInput.__novaBound) {
      dom.memoryInput.__novaBound = true;
      dom.memoryInput.addEventListener("keydown", async (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          await addMemory();
        }
      });
    }

    if (dom.memoryList && !dom.memoryList.__novaBound) {
      dom.memoryList.__novaBound = true;
      dom.memoryList.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-delete-memory]");
        if (!button) return;
        const itemId = asString(button.getAttribute("data-delete-memory"), "");
        if (!itemId) return;
        await deleteMemory(itemId);
      });
    }
  }

  function bindMessageActions() {
    if (dom.chatMessages && !dom.chatMessages.__novaBound) {
      dom.chatMessages.__novaBound = true;
      dom.chatMessages.addEventListener("click", async (event) => {
        const copyBtn = event.target.closest("[data-copy-message]");
        if (!copyBtn) return;

        const index = Number(copyBtn.getAttribute("data-copy-message"));
        if (Number.isNaN(index)) return;

        const message = asArray(state.messages)[index];
        const text = extractMessageText(message);
        if (!text) return;

        try {
          await navigator.clipboard.writeText(text);
          const original = copyBtn.textContent;
          copyBtn.textContent = "Copied";
          setTimeout(() => {
            copyBtn.textContent = original || "Copy";
          }, 1000);
        } catch (error) {
          console.error("Copy failed:", error);
        }
      });
    }
  }

  function bindGlobal() {
    if (!window.__novaGlobalBound) {
      window.__novaGlobalBound = true;

      window.addEventListener("resize", () => {
        autosizeComposer();
        if (!isMobile()) {
          state.sidebarOpen = true;
        }
        applyPanelState();
        persistUiState();
      });

      document.addEventListener("click", (event) => {
        if (!isMobile()) return;
        const target = event.target;
        if (!target) return;

        const clickedSidebarToggle =
          target.closest?.("#sidebarToggle") || target.closest?.("#mobileSidebarToggle");
        const clickedMemoryToggle = target.closest?.("#memoryToggle");
        const insideSidebar = target.closest?.("#sidebar");
        const insideMemory = target.closest?.("#memoryPanel");

        let changed = false;

        if (state.sidebarOpen && !clickedSidebarToggle && !insideSidebar) {
          state.sidebarOpen = false;
          changed = true;
        }

        if (state.memoryOpen && !clickedMemoryToggle && !insideMemory) {
          state.memoryOpen = false;
          changed = true;
        }

        if (changed) {
          applyPanelState();
          persistUiState();
        }
      });
    }
  }

  async function bootstrap() {
    if (state.isBootstrapping || state.isBooted) return;
    if (!ensureShell()) return;

    state.isBootstrapping = true;
    state.bootError = null;

    try {
      restoreUiState();
      cacheDom();
      bindComposer();
      bindPanels();
      bindSessions();
      bindMemory();
      bindMessageActions();
      bindGlobal();

      state.lastRouter = { label: "Loading...", tone: "working" };
      renderAll();

      await loadState();

      if (state.activeSessionId) {
        await loadSession(state.activeSessionId);
      } else {
        state.messages = [];
        renderAll();
      }

      state.isBooted = true;
      state.lastRouter = { label: "Ready", tone: "success" };
      renderAll();
    } catch (error) {
      state.bootError = error instanceof Error ? error.message : "Bootstrap failed.";
      console.error("Nova bootstrap failed:", error);
      state.lastRouter = { label: "Boot error", tone: "danger" };
      renderAll();
    } finally {
      state.isBootstrapping = false;
      persistUiState();
    }
  }

  Nova.API = API;
  Nova.STORAGE = STORAGE;
  Nova.bootstrap = bootstrap;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap, { once: true });
  } else {
    bootstrap();
  }
})();