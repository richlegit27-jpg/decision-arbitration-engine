(() => {
  "use strict";

  if (window.__novaUltimateLoaded) {
    console.warn("Nova ultimate already loaded. Skipping duplicate boot.");
    return;
  }
  window.__novaUltimateLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  const NovaConfig = (window.NovaConfig = window.NovaConfig || {});

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

  const state = (Nova.state = Nova.state || {});
  const dom = (Nova.dom = Nova.dom || {});
  const api = (Nova.api = Nova.api || {});
  const sessions = (Nova.sessions = Nova.sessions || {});
  const memory = (Nova.memory = Nova.memory || {});
  const chat = (Nova.chat = Nova.chat || {});
  const render = (Nova.render = Nova.render || {});
  const panels = (Nova.panels = Nova.panels || {});
  const util = (Nova.util = Nova.util || {});

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

  function qsa(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
  }

  function safeInvoke(fn, fallback = null) {
    try {
      return typeof fn === "function" ? fn() : fallback;
    } catch (error) {
      console.error(error);
      return fallback;
    }
  }

  function noop() {}

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

  function removeStorage(key) {
    try {
      window.localStorage.removeItem(key);
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

  function toggle(node, shouldShow) {
    if (!node) return;
    node.classList.toggle("hidden", !shouldShow);
  }

  function clamp(n, min, max) {
    return Math.max(min, Math.min(max, n));
  }

  function nowIso() {
    return new Date().toISOString();
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

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
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
    input.style.height = `${clamp(input.scrollHeight, 44, MAX_INPUT_HEIGHT)}px`;
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
    const theme = state.themeMode || "dark";
    document.documentElement.setAttribute("data-theme", theme);
    document.body.dataset.theme = theme;
  }

  function applyPanelState() {
    if (dom.sidebar) {
      dom.sidebar.classList.toggle("is-open", !!state.sidebarOpen);
      dom.sidebar.classList.toggle("is-collapsed", !state.sidebarOpen);
    }
    if (dom.memoryPanel) {
      dom.memoryPanel.classList.toggle("is-open", !!state.memoryOpen);
    }
    if (dom.root) {
      dom.root.classList.toggle("sidebar-open", !!state.sidebarOpen);
      dom.root.classList.toggle("memory-open", !!state.memoryOpen);
    }
  }

  function renderAttachmentBarFallback() {
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
          const name = escapeHtml(file.name || file.filename || `file-${index + 1}`);
          return `
            <div class="attachment-chip" data-index="${index}">
              <span class="attachment-chip-name">${name}</span>
              <button class="attachment-chip-remove" type="button" data-remove-attachment="${index}">×</button>
            </div>
          `;
        })
        .join("")
    );
  }

  function renderSessionsFallback() {
    if (!dom.sessionList) return;
    const sessionsList = asArray(state.sessions);

    if (!sessionsList.length) {
      setHtml(dom.sessionList, `<div class="empty-panel-note">No chats yet.</div>`);
      return;
    }

    setHtml(
      dom.sessionList,
      sessionsList
        .map((session) => {
          const id = asString(session.id);
          const title = escapeHtml(asString(session.title, "Untitled"));
          const active = id && id === state.activeSessionId ? "is-active" : "";
          return `
            <button class="session-item ${active}" type="button" data-session-id="${escapeHtml(id)}">
              <span class="session-item-title">${title}</span>
            </button>
          `;
        })
        .join("")
    );
  }

  function renderMessagesFallback() {
    if (!dom.chatMessages) return;
    const messages = asArray(state.messages);

    if (!messages.length) {
      if (dom.emptyState) show(dom.emptyState);
      return;
    }

    if (dom.emptyState) hide(dom.emptyState);

    const existingEmpty = dom.emptyState ? dom.emptyState.outerHTML : "";
    const html = messages
      .map((message) => {
        const role = escapeHtml(asString(message.role, "assistant"));
        const text = escapeHtml(extractMessageText(message));
        return `
          <article class="message message-${role}">
            <div class="message-role">${role}</div>
            <div class="message-body"><pre>${text}</pre></div>
          </article>
        `;
      })
      .join("");

    dom.chatMessages.innerHTML = existingEmpty + html;
    dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
  }

  function renderMemoryFallback() {
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
          const id = escapeHtml(asString(item.id));
          const kind = escapeHtml(asString(item.kind, "note"));
          const value = escapeHtml(asString(item.value, ""));
          return `
            <div class="memory-card" data-memory-id="${id}">
              <div class="memory-kind">${kind}</div>
              <div class="memory-value">${value}</div>
              <button class="memory-delete-btn" type="button" data-delete-memory="${id}">Delete</button>
            </div>
          `;
        })
        .join("")
    );
  }

  function renderAll() {
    safeInvoke(() => (typeof render.sessions === "function" ? render.sessions() : renderSessionsFallback()));
    safeInvoke(() => (typeof render.messages === "function" ? render.messages() : renderMessagesFallback()));
    safeInvoke(() => (typeof render.memory === "function" ? render.memory() : renderMemoryFallback()));
    safeInvoke(() =>
      typeof render.attachments === "function" ? render.attachments() : renderAttachmentBarFallback()
    );
    safeInvoke(applyTheme);
    safeInvoke(applyPanelState);
    safeInvoke(autosizeComposer);
    safeInvoke(() => updateRouterBadge(state.lastRouter?.label || "Ready", state.lastRouter?.tone || "neutral"));
  }

  async function loadState() {
    const data = await api.get(API.state);
    state.sessions = asArray(data?.sessions);
    state.memoryItems = asArray(data?.memory || data?.items);
    state.currentModel = asString(data?.model, state.currentModel || DEFAULT_MODEL);

    if (!state.activeSessionId) {
      state.activeSessionId = asString(data?.active_session_id, "") || asString(state.sessions[0]?.id, "") || null;
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

  async function addMemory() {
    const value = asString(dom.memoryInput?.value, "").trim();
    if (!value) return;

    await api.post(API.addMemory, {
      kind: "note",
      value,
    });

    if (dom.memoryInput) dom.memoryInput.value = "";
    await refreshMemory();
  }

  async function deleteMemory(itemId) {
    if (!itemId) return;
    if (state.deletingMemoryIds.has(itemId)) return;

    state.deletingMemoryIds.add(itemId);
    try {
      await api.post(API.deleteMemory, { id: itemId });
      await refreshMemory();
    } finally {
      state.deletingMemoryIds.delete(itemId);
    }
  }

  async function refreshMemory() {
    const data = await api.get(API.memory);
    state.memoryItems = asArray(data?.items || data?.memory);
    renderAll();
  }

  function normalizeAttachedFiles(payload) {
    return asArray(payload)
      .map((item, index) => {
        if (!item || typeof item !== "object") {
          return {
            id: `file-${Date.now()}-${index}`,
            name: `file-${index + 1}`,
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

  async function sendMessage() {
    if (state.isSending) return;

    const content = asString(dom.composerInput?.value, "").trim();
    const attachments = normalizeAttachedFiles(state.attachedFiles);

    if (!content && !attachments.length) return;

    state.isSending = true;
    updateRouterBadge("Thinking...", "working");

    try {
      const activeId = state.activeSessionId || "";
      const payload = {
        session_id: activeId,
        content,
        attachments,
        files: attachments,
        model: state.currentModel || DEFAULT_MODEL,
      };

      state.lastUserMessage = content || state.lastUserMessage || "";

      if (dom.composerInput) {
        dom.composerInput.value = "";
        autosizeComposer();
      }

      state.attachedFiles = [];
      renderAll();

      const response = await fetch(API.stream, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
        credentials: "same-origin",
      });

      if (!response.ok || !response.body) {
        const text = await response.text().catch(() => "");
        const data = safeJsonParse(text, null);
        throw new Error((data && (data.error || data.message)) || "Stream request failed.");
      }

      let assistantText = "";
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      function ensureStreamingAssistantMessage() {
        const last = state.messages[state.messages.length - 1];
        if (last && last.role === "assistant" && last.__streaming) return last;

        const msg = {
          id: `assistant-stream-${Date.now()}`,
          role: "assistant",
          content: "",
          created_at: nowIso(),
          __streaming: true,
        };
        state.messages.push(msg);
        return msg;
      }

      if (content || attachments.length) {
        state.messages.push({
          id: `user-local-${Date.now()}`,
          role: "user",
          content,
          attachments,
          created_at: nowIso(),
        });
        renderAll();
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const block of parts) {
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

          const joined = dataLines.join("\n");
          const data = safeJsonParse(joined, {});

          if (eventName === "start") {
            if (data?.session_id) {
              state.activeSessionId = data.session_id;
            }
          }

          if (eventName === "delta") {
            const delta = asString(data?.delta, "");
            if (!delta) continue;

            assistantText += delta;
            const msg = ensureStreamingAssistantMessage();
            msg.content = assistantText;
            renderAll();
          }

          if (eventName === "done") {
            assistantText = asString(data?.content, assistantText);
            const last = state.messages[state.messages.length - 1];
            if (last && last.role === "assistant") {
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
          }

          if (eventName === "error") {
            throw new Error(asString(data?.error, "Stream error."));
          }
        }
      }

      await loadState();
      if (state.activeSessionId) {
        await loadSession(state.activeSessionId);
      }
      updateRouterBadge("Ready", "success");
    } catch (error) {
      console.error("Nova send failed:", error);
      updateRouterBadge("Error", "danger");

      const message = error instanceof Error ? error.message : "Send failed.";
      state.messages.push({
        id: `system-error-${Date.now()}`,
        role: "system",
        content: message,
        created_at: nowIso(),
      });
      renderAll();
    } finally {
      state.isSending = false;
      persistUiState();
    }
  }

  async function regenerateLast() {
    if (state.isSending) return;
    const fallback = state.lastUserMessage || "";
    if (!fallback) return;

    if (dom.composerInput) {
      dom.composerInput.value = fallback;
      autosizeComposer();
    }

    await sendMessage();
  }

  function bindComposer() {
    if (dom.composerInput) {
      dom.composerInput.addEventListener("input", autosizeComposer);
      dom.composerInput.addEventListener("keydown", async (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          await sendMessage();
        }
      });
    }

    if (dom.sendBtn) {
      dom.sendBtn.addEventListener("click", sendMessage);
    }

    if (dom.regenerateBtn) {
      dom.regenerateBtn.addEventListener("click", regenerateLast);
    }

    if (dom.attachBtn && dom.fileInput) {
      dom.attachBtn.addEventListener("click", () => dom.fileInput.click());
      dom.fileInput.addEventListener("change", (event) => {
        const files = Array.from(event.target.files || []).map((file, index) => ({
          id: `picked-${Date.now()}-${index}`,
          name: file.name,
          filename: file.name,
          type: file.type || "",
          size: file.size || 0,
        }));
        state.attachedFiles = files;
        renderAll();
      });
    }

    if (dom.attachmentBar) {
      dom.attachmentBar.addEventListener("click", (event) => {
        const button = event.target.closest("[data-remove-attachment]");
        if (!button) return;
        const index = Number(button.getAttribute("data-remove-attachment"));
        if (Number.isNaN(index)) return;
        state.attachedFiles = state.attachedFiles.filter((_, i) => i !== index);
        renderAll();
      });
    }
  }

  function bindPanels() {
    if (dom.sidebarToggle) {
      dom.sidebarToggle.addEventListener("click", () => {
        state.sidebarOpen = !state.sidebarOpen;
        applyPanelState();
        persistUiState();
      });
    }

    if (dom.mobileSidebarToggle) {
      dom.mobileSidebarToggle.addEventListener("click", () => {
        state.sidebarOpen = !state.sidebarOpen;
        applyPanelState();
        persistUiState();
      });
    }

    if (dom.memoryToggle) {
      dom.memoryToggle.addEventListener("click", () => {
        state.memoryOpen = !state.memoryOpen;
        applyPanelState();
        persistUiState();
      });
    }

    if (dom.themeToggle) {
      dom.themeToggle.addEventListener("click", () => {
        state.themeMode = state.themeMode === "light" ? "dark" : "light";
        applyTheme();
        persistUiState();
      });
    }
  }

  function bindSessions() {
    if (dom.newChatBtn) {
      dom.newChatBtn.addEventListener("click", async () => {
        await createSession();
      });
    }

    if (dom.sessionList) {
      dom.sessionList.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-session-id]");
        if (!button) return;
        const sessionId = asString(button.getAttribute("data-session-id"), "");
        if (!sessionId) return;
        await loadSession(sessionId);
      });
    }
  }

  function bindMemory() {
    if (dom.memoryAddBtn) {
      dom.memoryAddBtn.addEventListener("click", addMemory);
    }

    if (dom.memoryInput) {
      dom.memoryInput.addEventListener("keydown", async (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          await addMemory();
        }
      });
    }

    if (dom.memoryList) {
      dom.memoryList.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-delete-memory]");
        if (!button) return;
        const itemId = asString(button.getAttribute("data-delete-memory"), "");
        if (!itemId) return;
        await deleteMemory(itemId);
      });
    }
  }

  function bindGlobalDelegates() {
    window.addEventListener("resize", () => {
      safeInvoke(autosizeComposer);
      if (window.innerWidth > 980 && !state.sidebarOpen) {
        applyPanelState();
      }
    });

    document.addEventListener("click", (event) => {
      if (window.innerWidth > 980) return;
      const target = event.target;
      if (!target) return;

      const clickedSidebarToggle =
        target.closest?.("#sidebarToggle") || target.closest?.("#mobileSidebarToggle");
      const insideSidebar = target.closest?.("#sidebar");
      if (!clickedSidebarToggle && !insideSidebar && state.sidebarOpen) {
        state.sidebarOpen = false;
        applyPanelState();
        persistUiState();
      }
    });
  }

  function installFallbacks() {
    dom.byId = dom.byId || byId;
    dom.qs = dom.qs || qs;
    dom.qsa = dom.qsa || qsa;

    util.safeJsonParse = util.safeJsonParse || safeJsonParse;
    util.escapeHtml = util.escapeHtml || escapeHtml;
    util.extractMessageText = util.extractMessageText || extractMessageText;
    util.formatDateLoose = util.formatDateLoose || formatDateLoose;
    util.autosizeComposer = util.autosizeComposer || autosizeComposer;
    util.persistUiState = util.persistUiState || persistUiState;
    util.restoreUiState = util.restoreUiState || restoreUiState;

    sessions.load = sessions.load || loadSession;
    sessions.create = sessions.create || createSession;

    memory.refresh = memory.refresh || refreshMemory;
    memory.add = memory.add || addMemory;
    memory.remove = memory.remove || deleteMemory;

    chat.send = chat.send || sendMessage;
    chat.regenerate = chat.regenerate || regenerateLast;

    render.all = render.all || renderAll;
    render.sessions = render.sessions || renderSessionsFallback;
    render.messages = render.messages || renderMessagesFallback;
    render.memory = render.memory || renderMemoryFallback;
    render.attachments = render.attachments || renderAttachmentBarFallback;

    panels.apply = panels.apply || applyPanelState;
    panels.theme = panels.theme || applyTheme;
  }

  async function bootstrap() {
    if (state.isBootstrapping) {
      console.warn("Nova bootstrap already running.");
      return;
    }

    if (state.isBooted) {
      console.warn("Nova already booted.");
      return;
    }

    if (!ensureShell()) return;

    state.isBootstrapping = true;
    state.bootError = null;

    try {
      restoreUiState();
      cacheDom();
      installFallbacks();
      applyTheme();
      applyPanelState();
      bindComposer();
      bindPanels();
      bindSessions();
      bindMemory();
      bindGlobalDelegates();
      autosizeComposer();
      updateRouterBadge("Loading...", "working");

      await loadState();

      if (dom.modelSelect) {
        dom.modelSelect.innerHTML = "";
        const current = state.currentModel || DEFAULT_MODEL;
        const option = document.createElement("option");
        option.value = current;
        option.textContent = current;
        dom.modelSelect.appendChild(option);
        dom.modelSelect.value = current;
        dom.modelSelect.addEventListener("change", () => {
          state.currentModel = dom.modelSelect.value || DEFAULT_MODEL;
          persistUiState();
        });
      }

      if (state.activeSessionId) {
        await loadSession(state.activeSessionId);
      } else {
        state.messages = [];
        renderAll();
      }

      state.isBooted = true;
      updateRouterBadge("Ready", "success");
      console.log("Nova bootstrap complete.");
    } catch (error) {
      state.bootError = error instanceof Error ? error.message : "Bootstrap failed.";
      console.error("Nova bootstrap failed:", error);
      updateRouterBadge("Boot error", "danger");
      renderAll();
    } finally {
      state.isBootstrapping = false;
      persistUiState();
    }
  }

  function waitForShellAndBootstrap() {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", () => {
        safeInvoke(() => bootstrap());
      }, { once: true });
      return;
    }

    safeInvoke(() => bootstrap());
  }

  Nova.API = API;
  Nova.STORAGE = STORAGE;
  Nova.bootstrap = bootstrap;
  Nova.waitForShellAndBootstrap = waitForShellAndBootstrap;

  waitForShellAndBootstrap();
})();