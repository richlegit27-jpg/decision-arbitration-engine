(() => {
  "use strict";

  if (window.__novaUltimateLoaded) {
    console.warn("Nova ultimate already loaded.");
    return;
  }
  window.__novaUltimateLoaded = true;

  const API = {
    state: "/api/state",
    chat: "/api/chat",
    stream: "/api/chat/stream",
    getChat: (sessionId) => `/api/chat/${encodeURIComponent(sessionId)}`,
    models: "/api/models",
    memory: "/api/memory",
    addMemory: "/api/memory/add",
    deleteMemory: "/api/memory/delete",
    newSession: "/api/session/new",
    deleteSession: "/api/session/delete",
    renameSession: "/api/session/rename",
    duplicateSession: "/api/session/duplicate",
    upload: "/api/upload",
  };

  const STORAGE_KEYS = {
    activeSessionId: "nova_active_session_id",
    selectedModel: "nova_selected_model",
    sidebarOpen: "nova_sidebar_open",
    memoryOpen: "nova_memory_open",
    themeMode: "nova_theme_mode",
    backgroundMode: "nova_background_mode",
    pinnedSessionIds: "nova_pinned_session_ids",
  };

  const SIDEBAR_WIDTH = "290px";
  const MEMORY_WIDTH = "350px";
  const INPUT_MIN_HEIGHT = 44;
  const INPUT_MAX_HEIGHT = 140;

  const MEMORY_LABELS = {
    name: "Name",
    preference: "Preference",
    goal: "Goal",
    project: "Project",
    skill: "Skill",
    workflow: "Workflow",
    memory: "Memory",
  };

  const THEMES = {
    dark: {
      "--bg": "#0a0f1f",
      "--bg-2": "#121a30",
      "--panel": "rgba(16, 24, 44, 0.88)",
      "--panel-2": "rgba(22, 32, 58, 0.90)",
      "--panel-3": "rgba(31, 44, 77, 0.94)",
      "--text": "#eaf1ff",
      "--muted": "#97a7cf",
      "--line": "rgba(148, 163, 255, 0.12)",
      "--line-strong": "rgba(148, 163, 255, 0.24)",
      "--accent": "#8b5cf6",
      "--accent-strong": "#7c3aed",
      "--accent-soft": "rgba(139, 92, 246, 0.16)",
      "--accent-2": "#22c55e",
      "--accent-2-soft": "rgba(34, 197, 94, 0.14)",
      "--danger": "#fb7185",
      "--danger-soft": "rgba(251, 113, 133, 0.14)",
      "--button-text": "#f5f8ff",
      "--select-bg": "#18223d",
      "--select-text": "#f5f8ff",
      "--input-bg": "rgba(15, 23, 42, 0.92)",
      "--shadow": "0 18px 45px rgba(0, 0, 0, 0.28)",
    },
    light: {
      "--bg": "#eef2ff",
      "--bg-2": "#dfe8ff",
      "--panel": "rgba(255, 255, 255, 0.92)",
      "--panel-2": "rgba(247, 249, 255, 0.95)",
      "--panel-3": "rgba(231, 238, 255, 0.96)",
      "--text": "#14213d",
      "--muted": "#5c6b8a",
      "--line": "rgba(20, 33, 61, 0.10)",
      "--line-strong": "rgba(20, 33, 61, 0.20)",
      "--accent": "#7c3aed",
      "--accent-strong": "#6d28d9",
      "--accent-soft": "rgba(124, 58, 237, 0.12)",
      "--accent-2": "#16a34a",
      "--accent-2-soft": "rgba(22, 163, 74, 0.10)",
      "--danger": "#e11d48",
      "--danger-soft": "rgba(225, 29, 72, 0.10)",
      "--button-text": "#14213d",
      "--select-bg": "#ffffff",
      "--select-text": "#14213d",
      "--input-bg": "#ffffff",
      "--shadow": "0 18px 45px rgba(17, 24, 39, 0.10)",
    },
  };

  const BACKGROUNDS = {
    default: `
      radial-gradient(circle at 15% 18%, rgba(139, 92, 246, 0.22), transparent 22%),
      radial-gradient(circle at 82% 14%, rgba(34, 197, 94, 0.14), transparent 18%),
      radial-gradient(circle at 50% 100%, rgba(59, 130, 246, 0.14), transparent 28%),
      linear-gradient(180deg, var(--bg) 0%, var(--bg-2) 100%)
    `,
    aurora: `
      radial-gradient(circle at 12% 10%, rgba(34, 197, 94, 0.24), transparent 20%),
      radial-gradient(circle at 88% 10%, rgba(6, 182, 212, 0.18), transparent 18%),
      radial-gradient(circle at 50% 85%, rgba(168, 85, 247, 0.18), transparent 28%),
      linear-gradient(180deg, #07111e 0%, #0b1730 100%)
    `,
    steel: `
      radial-gradient(circle at top left, rgba(255, 255, 255, 0.08), transparent 22%),
      radial-gradient(circle at bottom right, rgba(148, 163, 184, 0.10), transparent 26%),
      linear-gradient(180deg, #12161f 0%, #1a2230 100%)
    `,
  };

  const app = {
    state: {
      sessions: [],
      messages: [],
      memoryItems: [],
      activeSessionId: null,
      currentModel: "gpt-4.1-mini",
      isSending: false,
      sidebarOpen: true,
      memoryOpen: true,
      themeMode: "dark",
      backgroundMode: "default",
      pinnedSessionIds: [],
      attachedFiles: [],
      isVoiceListening: false,
      lastUserContent: "",
    },
    streaming: {
      controller: null,
    },
    voice: {
      recognition: null,
    },
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function qs(selectors) {
    for (const selector of selectors) {
      const el = document.querySelector(selector);
      if (el) return el;
    }
    return null;
  }

  function qsa(selectors) {
    for (const selector of selectors) {
      const els = document.querySelectorAll(selector);
      if (els && els.length) return Array.from(els);
    }
    return [];
  }

  function safeText(value) {
    return String(value ?? "").trim();
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

  function formatMemoryKind(kind) {
    const clean = safeText(kind).toLowerCase();
    return MEMORY_LABELS[clean] || "Memory";
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function getAppShell() { return byId("appShell"); }
  function getSidebar() { return byId("sidebar"); }
  function getMemoryPanel() { return byId("memoryPanel"); }
  function getToggleSidebarBtn() { return byId("toggleSidebar"); }
  function getMobileSidebarBtn() { return byId("mobileSidebarBtn"); }
  function getMemoryToggleBtnTop() { return byId("memoryToggleBtnTop"); }
  function getCloseMemoryBtn() { return byId("closeMemoryBtn"); }
  function getChatTitleEl() { return byId("chatTitle"); }
  function getChatSubtitleEl() { return byId("chatSubtitle"); }
  function getModelStatusEl() { return byId("modelStatus"); }
  function getMemoryStatusTextEl() { return byId("memoryStatusText"); }
  function getDuplicateSessionBtn() { return byId("duplicateSessionBtn"); }
  function getPinSessionBtn() { return byId("pinSessionBtn"); }
  function getExportSessionBtn() { return byId("exportSessionBtn"); }
  function getThemeToggleBtn() { return byId("themeToggleBtn"); }
  function getBackgroundBtn() { return byId("backgroundBtn"); }
  function getAttachBtn() { return byId("attachBtn"); }
  function getVoiceBtn() { return byId("voiceBtn"); }
  function getFileInput() { return byId("fileInput"); }
  function getAttachedFilesBar() { return byId("attachedFiles"); }

  function getChatContainer() {
    return qs([
      "#chatMessages",
      "#messages",
      "#chatContainer",
      ".chat-messages",
      ".messages",
    ]);
  }

  function getMessageInput() {
    return qs([
      "#messageInput",
      "#composerInput",
      "textarea[name='message']",
      "textarea",
    ]);
  }

  function getSendBtn() {
    return qs([
      "#sendBtn",
      "#sendButton",
      "button[data-action='send']",
    ]);
  }

  function getStopBtn() {
    return qs([
      "#stopBtn",
      "#stopButton",
      "button[data-action='stop']",
    ]);
  }

  function getSessionList() {
    return qs([
      "#sessionList",
      "#chatList",
      ".session-list",
      ".chat-list",
      "#sidebarSessionList",
    ]);
  }

  function getSessionCountEl() {
    return qs([
      "#sessionCount",
      "#chatCount",
      ".session-count",
    ]);
  }

  function getNewSessionBtn() {
    return qs([
      "#newSessionBtn",
      "button[data-action='new-session']",
    ]);
  }

  function getDeleteSessionBtn() {
    return qs([
      "#deleteSessionBtn",
      "button[data-action='delete-session']",
    ]);
  }

  function getRenameSessionBtn() {
    return qs([
      "#renameSessionBtn",
      "button[data-action='rename-session']",
    ]);
  }

  function getModelSelect() {
    return qs([
      "#modelSelect",
      "select[data-role='model-select']",
    ]);
  }

  function getMemoryList() {
    return qs([
      "#memoryList",
      "#memoryItems",
      ".memory-list",
      ".memory-items",
      "[data-role='memory-list']",
    ]);
  }

  function getMemoryEmpty() {
    return qs([
      "#memoryEmpty",
      ".memory-empty",
      "[data-role='memory-empty']",
    ]);
  }

  function getMemoryForm() {
    return qs([
      "#memoryForm",
      "[data-role='memory-form']",
    ]);
  }

  function getMemoryKindInput() {
    return qs([
      "#memoryKind",
      "select[name='memoryKind']",
      "input[name='memoryKind']",
      "[data-role='memory-kind']",
    ]);
  }

  function getMemoryValueInput() {
    return qs([
      "#memoryValue",
      "input[name='memoryValue']",
      "textarea[name='memoryValue']",
      "[data-role='memory-value']",
    ]);
  }

  function getMemoryRefreshBtn() {
    return qs([
      "#refreshMemoryBtn",
      "button[data-action='refresh-memory']",
    ]);
  }

  function injectRuntimeStyles() {
    let styleEl = byId("novaRuntimeStyles");
    if (!styleEl) {
      styleEl = document.createElement("style");
      styleEl.id = "novaRuntimeStyles";
      document.head.appendChild(styleEl);
    }

    styleEl.textContent = `
      html, body {
        background: var(--bg) !important;
        color: var(--text) !important;
      }

      body {
        background-attachment: fixed !important;
        background-repeat: no-repeat !important;
        background-size: cover !important;
        color: var(--text) !important;
      }

      #appShell, .app-shell {
        color: var(--text) !important;
      }

      #sidebar, #memoryPanel, .left-sidebar, .right-panel, .memory-panel, .topbar, .chat-header, .composer, .sidebar-content, .main-panel {
        background: var(--panel) !important;
        color: var(--text) !important;
        border-color: var(--line) !important;
        backdrop-filter: blur(14px);
      }

      button, select, input, textarea {
        font-family: inherit;
      }

      button,
      .session-item,
      .rail-toggle,
      .topbar button,
      .sidebar-controls button,
      .chat-actions button,
      .composer-actions button,
      .message-action-btn {
        background: linear-gradient(180deg, var(--panel-2), var(--panel-3)) !important;
        color: var(--button-text) !important;
        border: 1px solid var(--line) !important;
        border-radius: 12px !important;
        box-shadow: var(--shadow);
        transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease, background 140ms ease;
      }

      button:hover,
      .session-item:hover,
      .rail-toggle:hover,
      .message-action-btn:hover {
        transform: translateY(-1px);
        border-color: var(--line-strong) !important;
        box-shadow: 0 12px 28px rgba(0,0,0,0.18);
      }

      button:active,
      .message-action-btn:active {
        transform: translateY(0);
      }

      select,
      input,
      textarea {
        background: var(--input-bg) !important;
        color: var(--text) !important;
        border: 1px solid var(--line) !important;
        border-radius: 14px !important;
      }

      select option {
        background: var(--select-bg) !important;
        color: var(--select-text) !important;
      }

      #modelSelect {
        background: var(--select-bg) !important;
        color: var(--select-text) !important;
        padding: 10px 12px !important;
        min-height: 44px !important;
      }

      .message {
        background: var(--panel) !important;
        border: 1px solid var(--line) !important;
        color: var(--text) !important;
        border-radius: 18px;
        padding: 14px;
        margin-bottom: 14px;
        box-shadow: var(--shadow);
      }

      .message.user {
        background: linear-gradient(180deg, var(--panel-2), var(--panel-3)) !important;
        border-color: var(--accent-soft) !important;
      }

      .message.assistant {
        background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00)), var(--panel) !important;
      }

      .message-role {
        font-size: 11px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--muted) !important;
        margin-bottom: 8px;
      }

      .message-body {
        white-space: pre-wrap;
        word-break: break-word;
        color: var(--text) !important;
        line-height: 1.6;
        font-size: 15px;
      }

      .message-time {
        margin-top: 8px;
        font-size: 12px;
        color: var(--muted) !important;
      }

      .message-files {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 10px;
      }

      .message-file {
        font-size: 12px;
        padding: 6px 10px;
        border-radius: 999px;
        background: var(--accent-soft) !important;
        border: 1px solid var(--line) !important;
        color: var(--text) !important;
      }

      .message-actions {
        display: flex;
        gap: 8px;
        margin-top: 10px;
      }

      .message-action-btn {
        font-size: 12px;
        padding: 6px 10px;
      }

      .empty-card {
        background: linear-gradient(180deg, var(--panel), var(--panel-2)) !important;
        color: var(--text) !important;
        border: 1px solid var(--line) !important;
        border-radius: 20px;
        padding: 24px;
        box-shadow: var(--shadow);
      }

      .empty-title {
        font-size: 24px;
        font-weight: 800;
        margin-bottom: 8px;
      }

      .empty-subtitle {
        color: var(--muted) !important;
      }

      .session-item {
        display: block;
        width: 100%;
        text-align: left;
        padding: 12px;
        margin-bottom: 10px;
        background: linear-gradient(180deg, var(--panel-2), var(--panel)) !important;
      }

      .session-item.active {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 1px var(--accent-soft) inset, 0 14px 30px rgba(0,0,0,0.14);
      }

      .session-item-main {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 10px;
      }

      .session-title-wrap {
        flex: 1;
        min-width: 0;
      }

      .session-title {
        font-weight: 700;
        color: var(--text) !important;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-bottom: 6px;
      }

      .session-meta {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        font-size: 12px;
        color: var(--muted) !important;
      }

      .session-row-actions {
        display: flex;
        gap: 6px;
        flex-shrink: 0;
      }

      .session-row-btn {
        min-width: 30px;
        height: 30px;
        padding: 0 8px !important;
        font-size: 12px;
        border-radius: 10px !important;
      }

      .session-row-btn.delete {
        background: linear-gradient(180deg, var(--danger-soft), rgba(0,0,0,0)) !important;
      }

      .session-row-btn.rename {
        background: linear-gradient(180deg, var(--accent-soft), rgba(0,0,0,0)) !important;
      }

      .memory-item {
        background: linear-gradient(180deg, var(--panel-2), var(--panel)) !important;
        color: var(--text) !important;
        border: 1px solid var(--line) !important;
        border-radius: 16px;
        padding: 12px;
        margin-bottom: 10px;
        box-shadow: var(--shadow);
      }

      .memory-kind, .memory-meta {
        color: var(--muted) !important;
      }

      #attachedFiles.has-files {
        margin: 8px 0 10px;
      }

      .chat-header, .topbar {
        box-shadow: var(--shadow);
      }

      .composer textarea {
        transition: none !important;
      }
    `;
  }

  function updateModelStatus(text) {
    const el = getModelStatusEl();
    if (el) el.textContent = safeText(text || "Model ready");
  }

  function updateMemoryStatus(text) {
    const el = getMemoryStatusTextEl();
    if (el) el.textContent = safeText(text || "Memory panel ready.");
  }

  function updateChatHeader() {
    const titleEl = getChatTitleEl();
    const subtitleEl = getChatSubtitleEl();

    const currentSession = app.state.sessions.find(
      (session) => session.session_id === app.state.activeSessionId
    );

    const title = currentSession?.title || "Nova";

    let subtitle = "Ready";
    if (app.state.isSending) {
      subtitle = "Thinking...";
    } else if (app.state.messages.length > 0) {
      subtitle = `${app.state.messages.length} messages`;
    }

    if (titleEl) titleEl.textContent = title;
    if (subtitleEl) subtitleEl.textContent = subtitle;
  }

  function setStatusSending(isSending) {
    app.state.isSending = !!isSending;

    const sendBtn = getSendBtn();
    const stopBtn = getStopBtn();

    if (sendBtn) sendBtn.disabled = isSending;

    if (stopBtn) {
      stopBtn.disabled = !isSending;
      stopBtn.classList.toggle("hidden", !isSending);
    }

    updateModelStatus(isSending ? "Responding..." : `Using ${app.state.currentModel}`);
    updateChatHeader();
  }

  let autosizeFrame = null;

  function autosizeInput() {
    const input = getMessageInput();
    if (!input) return;

    if (autosizeFrame) cancelAnimationFrame(autosizeFrame);

    autosizeFrame = requestAnimationFrame(() => {
      input.style.height = "auto";
      const next = Math.min(input.scrollHeight, INPUT_MAX_HEIGHT);
      input.style.height = `${Math.max(INPUT_MIN_HEIGHT, next)}px`;
      input.style.overflowY = input.scrollHeight > INPUT_MAX_HEIGHT ? "auto" : "hidden";
    });
  }

  function persistState() {
    try {
      localStorage.setItem(STORAGE_KEYS.activeSessionId, safeText(app.state.activeSessionId));
      localStorage.setItem(STORAGE_KEYS.selectedModel, safeText(app.state.currentModel));
      localStorage.setItem(STORAGE_KEYS.sidebarOpen, String(!!app.state.sidebarOpen));
      localStorage.setItem(STORAGE_KEYS.memoryOpen, String(!!app.state.memoryOpen));
      localStorage.setItem(STORAGE_KEYS.themeMode, safeText(app.state.themeMode));
      localStorage.setItem(STORAGE_KEYS.backgroundMode, safeText(app.state.backgroundMode));
      localStorage.setItem(STORAGE_KEYS.pinnedSessionIds, JSON.stringify(app.state.pinnedSessionIds || []));
    } catch (err) {
      console.warn("LocalStorage save failed:", err);
    }
  }

  function restoreState() {
    try {
      const savedSessionId = localStorage.getItem(STORAGE_KEYS.activeSessionId);
      const savedModel = localStorage.getItem(STORAGE_KEYS.selectedModel);
      const savedSidebarOpen = localStorage.getItem(STORAGE_KEYS.sidebarOpen);
      const savedMemoryOpen = localStorage.getItem(STORAGE_KEYS.memoryOpen);
      const savedThemeMode = localStorage.getItem(STORAGE_KEYS.themeMode);
      const savedBackgroundMode = localStorage.getItem(STORAGE_KEYS.backgroundMode);
      const savedPinnedSessionIds = localStorage.getItem(STORAGE_KEYS.pinnedSessionIds);

      if (savedSessionId) app.state.activeSessionId = savedSessionId;
      if (savedModel) app.state.currentModel = savedModel;
      if (savedSidebarOpen !== null) app.state.sidebarOpen = savedSidebarOpen === "true";
      if (savedMemoryOpen !== null) app.state.memoryOpen = savedMemoryOpen === "true";
      if (savedThemeMode && THEMES[savedThemeMode]) app.state.themeMode = savedThemeMode;
      if (savedBackgroundMode && BACKGROUNDS[savedBackgroundMode]) app.state.backgroundMode = savedBackgroundMode;

      if (savedPinnedSessionIds) {
        try {
          const parsed = JSON.parse(savedPinnedSessionIds);
          app.state.pinnedSessionIds = Array.isArray(parsed) ? parsed : [];
        } catch {
          app.state.pinnedSessionIds = [];
        }
      }
    } catch (err) {
      console.warn("LocalStorage restore failed:", err);
    }
  }

  async function apiGet(url) {
    const res = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(text || `GET ${url} failed with ${res.status}`);
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
      let message = `POST ${url} failed with ${res.status}`;
      try {
        const data = await res.json();
        message = data.detail || data.message || message;
      } catch {
        const text = await res.text().catch(() => "");
        if (text) message = text;
      }
      throw new Error(message);
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
      let message = `Upload failed with ${res.status}`;
      try {
        const data = await res.json();
        message = data.detail || data.message || message;
      } catch {
        const text = await res.text().catch(() => "");
        if (text) message = text;
      }
      throw new Error(message);
    }

    const data = await res.json();
    return Array.isArray(data.files) ? data.files : [];
  }

  function sortMemoryItems(items) {
    return [...items].sort((a, b) => {
      const aTime = Number(a?.updated_at || a?.created_at || 0);
      const bTime = Number(b?.updated_at || b?.created_at || 0);
      return bTime - aTime;
    });
  }

  function isPinnedSession(sessionId) {
    return (app.state.pinnedSessionIds || []).includes(sessionId);
  }

  function togglePinnedSession(sessionId) {
    if (!sessionId) return;
    const current = new Set(app.state.pinnedSessionIds || []);
    if (current.has(sessionId)) {
      current.delete(sessionId);
    } else {
      current.add(sessionId);
    }
    app.state.pinnedSessionIds = Array.from(current);
    persistState();
    renderSessions();
    syncPinButtonLabel();
  }

  function getOrderedSessions() {
    const sessions = Array.isArray(app.state.sessions) ? [...app.state.sessions] : [];
    return sessions.sort((a, b) => {
      const aPinned = isPinnedSession(a.session_id) ? 1 : 0;
      const bPinned = isPinnedSession(b.session_id) ? 1 : 0;
      if (aPinned !== bPinned) return bPinned - aPinned;

      const aTime = Number(a?.updated_at || 0);
      const bTime = Number(b?.updated_at || 0);
      return bTime - aTime;
    });
  }

  function applyThemeMode() {
    const root = document.documentElement;
    const body = document.body;
    const themeName = THEMES[app.state.themeMode] ? app.state.themeMode : "dark";
    const vars = THEMES[themeName];

    root.setAttribute("data-theme", themeName);

    Object.entries(vars).forEach(([key, value]) => {
      root.style.setProperty(key, value);
    });

    if (body) {
      body.style.color = vars["--text"];
    }

    const btn = getThemeToggleBtn();
    if (btn) {
      btn.textContent = themeName === "dark" ? "Theme: Dark" : "Theme: Light";
      btn.title = "Toggle theme";
    }
  }

  function applyBackgroundMode() {
    const body = document.body;
    const mode = BACKGROUNDS[app.state.backgroundMode] ? app.state.backgroundMode : "default";

    if (body) {
      body.style.background = BACKGROUNDS[mode];
      body.style.backgroundAttachment = "fixed";
      body.style.backgroundRepeat = "no-repeat";
      body.style.backgroundSize = "cover";
    }

    const btn = getBackgroundBtn();
    if (btn) {
      const label =
        mode === "default" ? "Background: Default" :
        mode === "aurora" ? "Background: Aurora" :
        "Background: Steel";
      btn.textContent = label;
      btn.title = "Cycle background";
    }
  }

  function cycleThemeMode() {
    app.state.themeMode = app.state.themeMode === "dark" ? "light" : "dark";
    applyThemeMode();
    applyBackgroundMode();
    persistState();
  }

  function cycleBackgroundMode() {
    const order = ["default", "aurora", "steel"];
    const index = order.indexOf(app.state.backgroundMode);
    app.state.backgroundMode = order[(index + 1) % order.length];
    applyBackgroundMode();
    persistState();
  }

  function syncPinButtonLabel() {
    const btn = getPinSessionBtn();
    if (!btn) return;
    const pinned = isPinnedSession(app.state.activeSessionId);
    btn.textContent = pinned ? "Unpin" : "Pin";
    btn.title = pinned ? "Unpin active chat" : "Pin active chat";
  }

  function applyLayout() {
    const appShell = getAppShell();
    const sidebar = getSidebar();
    const memoryPanel = getMemoryPanel();
    const toggleSidebarBtn = getToggleSidebarBtn();
    const mobileSidebarBtn = getMobileSidebarBtn();
    const memoryToggleBtnTop = getMemoryToggleBtnTop();

    if (!appShell || !sidebar || !memoryPanel) return;

    let columns = "minmax(0, 1fr)";

    if (app.state.sidebarOpen && app.state.memoryOpen) {
      columns = `${SIDEBAR_WIDTH} minmax(0, 1fr) ${MEMORY_WIDTH}`;
    } else if (app.state.sidebarOpen && !app.state.memoryOpen) {
      columns = `${SIDEBAR_WIDTH} minmax(0, 1fr)`;
    } else if (!app.state.sidebarOpen && app.state.memoryOpen) {
      columns = `minmax(0, 1fr) ${MEMORY_WIDTH}`;
    }

    appShell.style.gridTemplateColumns = columns;

    sidebar.style.display = app.state.sidebarOpen ? "" : "none";
    sidebar.setAttribute("aria-hidden", app.state.sidebarOpen ? "false" : "true");

    memoryPanel.style.display = app.state.memoryOpen ? "" : "none";
    memoryPanel.setAttribute("aria-hidden", app.state.memoryOpen ? "false" : "true");

    if (toggleSidebarBtn) {
      toggleSidebarBtn.textContent = app.state.sidebarOpen ? "×" : "☰";
      toggleSidebarBtn.title = app.state.sidebarOpen ? "Close sidebar" : "Open sidebar";
    }

    if (mobileSidebarBtn) {
      mobileSidebarBtn.textContent = "☰";
      mobileSidebarBtn.title = "Toggle sidebar";
    }

    if (memoryToggleBtnTop) {
      memoryToggleBtnTop.textContent = "Memory";
      memoryToggleBtnTop.title = app.state.memoryOpen ? "Close memory panel" : "Open memory panel";
    }

    persistState();
  }

  function toggleSidebar() {
    app.state.sidebarOpen = !app.state.sidebarOpen;
    applyLayout();
  }

  function toggleMemoryPanel() {
    app.state.memoryOpen = !app.state.memoryOpen;
    applyLayout();
  }

  function closeMemoryPanel() {
    app.state.memoryOpen = false;
    applyLayout();
  }

  function copyToClipboard(text) {
    const clean = safeText(text);
    if (!clean) return;
    navigator.clipboard.writeText(clean).then(() => {
      updateModelStatus("Copied");
    }).catch(() => {
      updateModelStatus("Copy failed");
    });
  }

  function getPreviousUserPrompt(index) {
    if (!Array.isArray(app.state.messages)) return "";
    for (let i = index - 1; i >= 0; i -= 1) {
      const msg = app.state.messages[i];
      if (msg?.role === "user" && safeText(msg?.content)) {
        return safeText(msg.content);
      }
    }
    return safeText(app.state.lastUserContent);
  }

  async function regenerateFromAssistantIndex(index) {
    const prompt = getPreviousUserPrompt(index);
    if (!prompt) {
      alert("No earlier user prompt found to regenerate.");
      return;
    }
    await sendMessage(prompt, { regenerate: true });
  }

  function renderUploadedFilesForMessage(msg) {
    const files = Array.isArray(msg?.uploaded_files) ? msg.uploaded_files : [];
    if (!files.length) return "";

    const fileRows = files.map((file) => {
      const originalName = escapeHtml(file?.original_name || file?.name || "file");
      const size = Number(file?.size || 0);
      const kb = Math.max(1, Math.round(size / 1024));
      return `<div class="message-file">📎 ${originalName} (${kb} KB)</div>`;
    }).join("");

    return `<div class="message-files">${fileRows}</div>`;
  }

  function buildAssistantActionsHtml() {
    return `
      <div class="message-actions">
        <button type="button" class="message-action-btn" data-action="copy-message">Copy</button>
        <button type="button" class="message-action-btn" data-action="regenerate-message">Regenerate</button>
      </div>
    `;
  }

  function attachAssistantMessageActions(node, content, index) {
    const copyBtn = node.querySelector('[data-action="copy-message"]');
    if (copyBtn) {
      copyBtn.addEventListener("click", () => copyToClipboard(content));
    }

    const regenBtn = node.querySelector('[data-action="regenerate-message"]');
    if (regenBtn) {
      regenBtn.addEventListener("click", async () => {
        try {
          await regenerateFromAssistantIndex(index);
        } catch (err) {
          console.error(err);
          alert(`Failed to regenerate: ${err.message}`);
        }
      });
    }
  }

  function renderMessage(msg, index = -1) {
    const container = getChatContainer();
    if (!container) return;

    const role = safeText(msg?.role || "assistant").toLowerCase();
    const content = safeText(msg?.content);
    const timestamp = msg?.timestamp || nowUnix();
    const filesHtml = renderUploadedFilesForMessage(msg);

    const div = document.createElement("div");
    div.className = `message ${role}`;
    div.dataset.messageIndex = String(index);

    let actionsHtml = "";
    if (role === "assistant") {
      actionsHtml = buildAssistantActionsHtml();
    }

    div.innerHTML = `
      <div class="message-role">${escapeHtml(role)}</div>
      ${filesHtml}
      <div class="message-body">${escapeHtml(content).replace(/\n/g, "<br>")}</div>
      <div class="message-time">${escapeHtml(formatTime(timestamp))}</div>
      ${actionsHtml}
    `;

    if (role === "assistant") {
      attachAssistantMessageActions(div, content, index);
    }

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  }

  function renderMessages(messages) {
    const container = getChatContainer();
    if (!container) return;

    container.innerHTML = "";
    const list = Array.isArray(messages) ? messages : [];

    if (!list.length) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-card">
            <div class="empty-title">Nova is ready</div>
            <div class="empty-subtitle">Start a new message, use voice, attach files, or open memory.</div>
          </div>
        </div>
      `;
      updateChatHeader();
      return;
    }

    list.forEach((msg, index) => renderMessage(msg, index));
    updateChatHeader();
  }

  function removeStreamingShell() {
    const existing = getChatContainer()?.querySelector(".message.streaming");
    if (existing) existing.remove();
  }

  function renderStreamingAssistantShell() {
    const container = getChatContainer();
    if (!container) return null;

    removeStreamingShell();

    const div = document.createElement("div");
    div.className = "message assistant streaming";
    div.innerHTML = `
      <div class="message-role">assistant</div>
      <div class="message-body"></div>
      <div class="message-time">${escapeHtml(new Date().toLocaleString())}</div>
    `;

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div.querySelector(".message-body");
  }

  async function renameSessionById(sessionId) {
    const current = app.state.sessions.find((session) => session.session_id === sessionId);
    const title = prompt("Rename chat", current?.title || "New Chat");
    if (!title || !title.trim()) return;

    await apiPost(API.renameSession, {
      session_id: sessionId,
      title: title.trim(),
    });

    await loadState();

    if (app.state.activeSessionId === sessionId) {
      updateChatHeader();
    }
  }

  async function deleteSessionById(sessionId) {
    const ok = confirm("Delete this chat?");
    if (!ok) return;

    app.state.pinnedSessionIds = (app.state.pinnedSessionIds || []).filter((id) => id !== sessionId);
    await apiPost(API.deleteSession, { session_id: sessionId });

    if (app.state.activeSessionId === sessionId) {
      app.state.messages = [];
    }

    await loadState();

    if (app.state.activeSessionId) {
      await loadSession(app.state.activeSessionId);
    } else {
      renderMessages([]);
    }
  }

  function renderSessions() {
    const listEl = getSessionList();
    const countEl = getSessionCountEl();
    const sessions = getOrderedSessions();

    if (countEl) countEl.textContent = String(sessions.length);
    if (!listEl) return;

    listEl.innerHTML = "";

    if (!sessions.length) {
      listEl.innerHTML = `<div class="session-empty">No chats yet.</div>`;
      updateChatHeader();
      syncPinButtonLabel();
      return;
    }

    for (const session of sessions) {
      const pinned = isPinnedSession(session.session_id);
      const item = document.createElement("div");
      item.className = `session-item ${session.session_id === app.state.activeSessionId ? "active" : ""}`;

      item.innerHTML = `
        <div class="session-item-main">
          <div class="session-title-wrap">
            <div class="session-title">${pinned ? "📌 " : ""}${escapeHtml(session.title || "New Chat")}</div>
            <div class="session-meta">
              <span>${escapeHtml(String(session.message_count || 0))} messages</span>
              <span>${escapeHtml(formatTime(session.updated_at || nowUnix()))}</span>
            </div>
          </div>
          <div class="session-row-actions">
            <button type="button" class="session-row-btn rename" title="Rename">✎</button>
            <button type="button" class="session-row-btn delete" title="Delete">🗑</button>
          </div>
        </div>
      `;

      item.addEventListener("click", (event) => {
        if (event.target.closest(".session-row-btn")) return;
        loadSession(session.session_id).catch((err) => {
          console.error(err);
          alert(`Failed to load session: ${err.message}`);
        });
      });

      const renameBtn = item.querySelector(".session-row-btn.rename");
      if (renameBtn) {
        renameBtn.addEventListener("click", async (event) => {
          event.stopPropagation();
          try {
            await renameSessionById(session.session_id);
          } catch (err) {
            console.error(err);
            alert(`Failed to rename session: ${err.message}`);
          }
        });
      }

      const deleteBtn = item.querySelector(".session-row-btn.delete");
      if (deleteBtn) {
        deleteBtn.addEventListener("click", async (event) => {
          event.stopPropagation();
          try {
            await deleteSessionById(session.session_id);
          } catch (err) {
            console.error(err);
            alert(`Failed to delete session: ${err.message}`);
          }
        });
      }

      listEl.appendChild(item);
    }

    updateChatHeader();
    syncPinButtonLabel();
  }

  function renderMemory() {
    const listEl = getMemoryList();
    const emptyEl = getMemoryEmpty();
    const rawItems = Array.isArray(app.state.memoryItems) ? app.state.memoryItems : [];
    const items = sortMemoryItems(rawItems);

    if (!listEl) return;

    listEl.innerHTML = "";

    if (!items.length) {
      if (emptyEl) emptyEl.style.display = "";
      listEl.innerHTML = `<div class="memory-empty-fallback">No saved memory yet.</div>`;
      updateMemoryStatus("No saved memory yet.");
      return;
    }

    if (emptyEl) emptyEl.style.display = "none";

    for (const item of items) {
      const row = document.createElement("div");
      row.className = "memory-item";
      row.dataset.memoryId = safeText(item.id);

      const kind = formatMemoryKind(item.kind || "memory");
      const value = safeText(item.value);
      const source = safeText(item.source || "manual");
      const updated = formatTime(item.updated_at || item.created_at);

      row.innerHTML = `
        <div class="memory-item-main">
          <div class="memory-kind">${escapeHtml(kind)}</div>
          <div class="memory-value">${escapeHtml(value)}</div>
          <div class="memory-meta">${escapeHtml(source)}${updated ? " • " + escapeHtml(updated) : ""}</div>
        </div>
        <button type="button" class="memory-delete-btn" title="Delete memory">×</button>
      `;

      const deleteBtn = row.querySelector(".memory-delete-btn");
      if (deleteBtn) {
        deleteBtn.addEventListener("click", async (event) => {
          event.stopPropagation();
          try {
            await deleteMemoryItem(item.id);
          } catch (err) {
            console.error(err);
            alert(`Failed to delete memory: ${err.message}`);
          }
        });
      }

      listEl.appendChild(row);
    }

    updateMemoryStatus(`${items.length} saved ${items.length === 1 ? "memory item" : "memory items"}.`);
  }

  function renderAttachedFiles() {
    const bar = getAttachedFilesBar();
    if (!bar) return;

    const files = Array.isArray(app.state.attachedFiles) ? app.state.attachedFiles : [];
    bar.innerHTML = "";

    if (!files.length) {
      bar.classList.remove("has-files");
      return;
    }

    bar.classList.add("has-files");

    files.forEach((file, index) => {
      const chip = document.createElement("div");
      chip.style.display = "inline-flex";
      chip.style.alignItems = "center";
      chip.style.gap = "8px";
      chip.style.padding = "6px 10px";
      chip.style.borderRadius = "999px";
      chip.style.border = "1px solid var(--line)";
      chip.style.background = "var(--accent-soft)";
      chip.style.fontSize = "0.78rem";
      chip.style.color = "var(--text)";
      chip.innerHTML = `
        <span>${escapeHtml(file.name)} (${Math.max(1, Math.round(file.size / 1024))} KB)</span>
        <button type="button" title="Remove file" style="border:0;background:transparent;color:inherit;cursor:pointer;">×</button>
      `;

      const removeBtn = chip.querySelector("button");
      if (removeBtn) {
        removeBtn.addEventListener("click", () => {
          app.state.attachedFiles.splice(index, 1);
          renderAttachedFiles();
          if (!app.state.attachedFiles.length) {
            updateModelStatus(`Using ${app.state.currentModel}`);
          }
        });
      }

      bar.appendChild(chip);
    });
  }

  async function loadModels() {
    const select = getModelSelect();
    if (!select) return;

    try {
      const data = await apiGet(API.models);
      const models = Array.isArray(data.models) ? data.models : [];

      select.innerHTML = "";
      for (const model of models) {
        const option = document.createElement("option");
        option.value = model;
        option.textContent = model;
        select.appendChild(option);
      }

      const wanted = app.state.currentModel || data.default || "gpt-4.1-mini";
      select.value = models.includes(wanted) ? wanted : (data.default || models[0] || "gpt-4.1-mini");
      app.state.currentModel = select.value;
      persistState();
      updateModelStatus(`Using ${app.state.currentModel}`);
    } catch (err) {
      console.warn("Model load failed:", err);
      updateModelStatus("Model load failed");
    }
  }

  async function loadState() {
    const data = await apiGet(API.state);
    app.state.sessions = Array.isArray(data.sessions) ? data.sessions : [];

    if (!app.state.activeSessionId && app.state.sessions.length) {
      app.state.activeSessionId = app.state.sessions[0].session_id;
    }

    const stillExists = app.state.sessions.some(
      (session) => session.session_id === app.state.activeSessionId
    );

    if (!stillExists) {
      app.state.activeSessionId = app.state.sessions[0]?.session_id || null;
    }

    persistState();
    renderSessions();
  }

  async function loadSession(sessionId) {
    if (!sessionId) return;

    const data = await apiGet(API.getChat(sessionId));
    app.state.activeSessionId = data.session_id;
    app.state.messages = Array.isArray(data.messages) ? data.messages : [];
    persistState();
    renderSessions();
    renderMessages(app.state.messages);
  }

  async function loadMemory() {
    const data = await apiGet(API.memory);
    app.state.memoryItems = Array.isArray(data.items) ? data.items : [];
    renderMemory();
  }

  async function addMemoryItem(kind, value) {
    const data = await apiPost(API.addMemory, { kind, value });
    app.state.memoryItems = Array.isArray(data.memory?.items) ? data.memory.items : [];
    renderMemory();

    const kindInput = getMemoryKindInput();
    const valueInput = getMemoryValueInput();
    if (kindInput) kindInput.value = "preference";
    if (valueInput) valueInput.value = "";
  }

  async function deleteMemoryItem(id) {
    const data = await apiPost(API.deleteMemory, { id });
    app.state.memoryItems = Array.isArray(data.memory?.items) ? data.memory.items : [];
    renderMemory();
  }

  async function createNewSession() {
    const data = await apiPost(API.newSession, {});
    await loadState();

    if (data.session_id) {
      await loadSession(data.session_id);
    } else if (app.state.sessions[0]?.session_id) {
      await loadSession(app.state.sessions[0].session_id);
    } else {
      app.state.messages = [];
      renderMessages([]);
    }
  }

  async function duplicateCurrentSession() {
    const sessionId = app.state.activeSessionId;
    if (!sessionId) return;

    const data = await apiPost(API.duplicateSession, { session_id: sessionId });

    await loadState();

    const newSessionId = safeText(data?.session?.session_id);
    if (newSessionId) {
      await loadSession(newSessionId);
      updateModelStatus("Chat duplicated");
      return;
    }

    if (app.state.sessions[0]?.session_id) {
      await loadSession(app.state.sessions[0].session_id);
      updateModelStatus("Chat duplicated");
    }
  }

  async function deleteCurrentSession() {
    const sessionId = app.state.activeSessionId;
    if (!sessionId) return;
    await deleteSessionById(sessionId);
  }

  async function renameCurrentSession() {
    const sessionId = app.state.activeSessionId;
    if (!sessionId) return;
    await renameSessionById(sessionId);
  }

  function exportCurrentSession() {
    const current = app.state.sessions.find(
      (session) => session.session_id === app.state.activeSessionId
    );

    const payload = {
      exported_at: new Date().toISOString(),
      session_id: app.state.activeSessionId,
      title: current?.title || "New Chat",
      model: app.state.currentModel,
      messages: Array.isArray(app.state.messages) ? app.state.messages : [],
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const safeTitle = (current?.title || "nova-chat")
      .replace(/[^\w\-]+/g, "_")
      .replace(/^_+|_+$/g, "")
      .toLowerCase();

    a.href = url;
    a.download = `${safeTitle || "nova-chat"}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function appendVoiceTranscript(text) {
    const input = getMessageInput();
    if (!input || !text) return;

    const current = input.value || "";
    input.value = current ? `${current} ${text}`.trim() : text.trim();
    input.focus();
    autosizeInput();
  }

  function stopVoiceRecognition() {
    if (app.voice.recognition) {
      try {
        app.voice.recognition.stop();
      } catch {
        // ignore
      }
    }
    app.state.isVoiceListening = false;

    const voiceBtn = getVoiceBtn();
    if (voiceBtn) {
      voiceBtn.textContent = "Voice";
      voiceBtn.title = "Voice input";
    }
  }

  function toggleVoiceRecognition() {
    const VoiceRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!VoiceRecognition) {
      alert("Voice input is not supported in this browser.");
      return;
    }

    if (app.state.isVoiceListening) {
      stopVoiceRecognition();
      updateModelStatus(`Using ${app.state.currentModel}`);
      return;
    }

    const recognition = new VoiceRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    app.voice.recognition = recognition;
    app.state.isVoiceListening = true;

    const voiceBtn = getVoiceBtn();
    if (voiceBtn) {
      voiceBtn.textContent = "Listening";
      voiceBtn.title = "Stop voice input";
    }

    updateModelStatus("Listening...");

    recognition.onresult = (event) => {
      const text = event?.results?.[0]?.[0]?.transcript || "";
      appendVoiceTranscript(text);
      updateModelStatus("Voice captured");
    };

    recognition.onerror = () => {
      updateModelStatus("Voice input failed");
      stopVoiceRecognition();
    };

    recognition.onend = () => {
      stopVoiceRecognition();
      if (!app.state.isSending) {
        updateModelStatus(`Using ${app.state.currentModel}`);
      }
    };

    recognition.start();
  }

  async function finalizeStreamingMessage(finalAssistantMessage, assistantText, model) {
    const streamingNode = getChatContainer()?.querySelector(".message.streaming");
    const finalMessage = finalAssistantMessage || {
      id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
      role: "assistant",
      content: assistantText || "No response returned.",
      timestamp: nowUnix(),
      model,
    };

    if (streamingNode) {
      streamingNode.classList.remove("streaming");
      streamingNode.dataset.messageIndex = String(app.state.messages.length);
      streamingNode.innerHTML = `
        <div class="message-role">assistant</div>
        <div class="message-body">${escapeHtml(finalMessage.content || assistantText).replace(/\n/g, "<br>")}</div>
        <div class="message-time">${escapeHtml(formatTime(finalMessage.timestamp || nowUnix()))}</div>
        ${buildAssistantActionsHtml()}
      `;
      attachAssistantMessageActions(
        streamingNode,
        finalMessage.content || assistantText,
        app.state.messages.length
      );
    } else {
      renderMessage(finalMessage, app.state.messages.length);
    }

    app.state.messages.push(finalMessage);
    updateChatHeader();
  }

  async function sendMessage(overrideContent = null, options = {}) {
    const input = getMessageInput();
    if (!input) return;

    const content = safeText(overrideContent ?? input.value);
    const hasFiles = Array.isArray(app.state.attachedFiles) && app.state.attachedFiles.length > 0;

    if (!content && !hasFiles) return;
    if (app.state.isSending) return;

    if (!app.state.activeSessionId) {
      await createNewSession();
    }

    const sessionId = app.state.activeSessionId;
    const model = getModelSelect()?.value || app.state.currentModel || "gpt-4.1-mini";
    const pendingFiles = Array.isArray(app.state.attachedFiles) ? [...app.state.attachedFiles] : [];

    app.state.lastUserContent = content;

    const userMsg = {
      id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
      role: "user",
      content,
      timestamp: nowUnix(),
      model,
      uploaded_files: pendingFiles.map((file) => ({
        original_name: file.name,
        size: file.size,
      })),
    };

    app.state.messages.push(userMsg);
    renderMessages(app.state.messages);

    if (!options.regenerate) {
      input.value = "";
      autosizeInput();
    }

    removeStreamingShell();
    const streamBodyEl = renderStreamingAssistantShell();

    const controller = new AbortController();
    app.streaming.controller = controller;
    setStatusSending(true);

    try {
      let uploadedFiles = [];

      if (pendingFiles.length) {
        updateModelStatus(`Uploading ${pendingFiles.length} file${pendingFiles.length === 1 ? "" : "s"}...`);
        uploadedFiles = await uploadFiles(pendingFiles);

        const lastUserMessage = app.state.messages[app.state.messages.length - 1];
        if (lastUserMessage && lastUserMessage.role === "user") {
          lastUserMessage.uploaded_files = uploadedFiles;
        }
      }

      updateModelStatus("Responding...");

      const response = await fetch(API.stream, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          content,
          model,
          uploaded_files: uploadedFiles,
        }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        let errorMessage = `Stream failed with ${response.status}`;
        try {
          const data = await response.json();
          errorMessage = data.detail || data.message || errorMessage;
        } catch {
          // ignore
        }
        throw new Error(errorMessage);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      let assistantText = "";
      let finished = false;
      let shouldStopReading = false;

      while (true) {
        if (shouldStopReading) break;

        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        let splitIndex;
        while ((splitIndex = buffer.indexOf("\n\n")) !== -1) {
          const rawEvent = buffer.slice(0, splitIndex);
          buffer = buffer.slice(splitIndex + 2);

          if (!rawEvent.trim()) continue;

          const lines = rawEvent.split("\n");
          let eventName = "message";
          const dataLines = [];

          for (const line of lines) {
            if (line.startsWith("event:")) {
              eventName = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              dataLines.push(line.slice(5).trim());
            }
          }

          const dataText = dataLines.join("\n");

          let payload = {};
          try {
            payload = dataText ? JSON.parse(dataText) : {};
          } catch {
            payload = {};
          }

          if (eventName === "start") {
            if (payload.session_id) {
              app.state.activeSessionId = payload.session_id;
              persistState();
            }
          } else if (eventName === "delta") {
            const delta = String(payload.text ?? "");
            assistantText += delta;
            if (streamBodyEl) {
              streamBodyEl.innerHTML = escapeHtml(assistantText).replace(/\n/g, "<br>");
            }
          } else if (eventName === "done") {
            finished = true;
            app.state.activeSessionId = payload.session_id || app.state.activeSessionId;

            await finalizeStreamingMessage(payload.message, assistantText, model);

            app.state.attachedFiles = [];
            const fileInput = getFileInput();
            if (fileInput) fileInput.value = "";
            renderAttachedFiles();

            await loadState();
            await loadMemory();
            updateChatHeader();
            updateModelStatus(`Using ${app.state.currentModel}`);

            shouldStopReading = true;
            try {
              await reader.cancel();
            } catch {
              // ignore
            }
            break;
          } else if (eventName === "error") {
            throw new Error(payload.message || "Unknown streaming error");
          }
        }
      }

      if (!finished) {
        await finalizeStreamingMessage(null, assistantText, model);

        app.state.attachedFiles = [];
        const fileInput = getFileInput();
        if (fileInput) fileInput.value = "";
        renderAttachedFiles();

        await loadState();
        await loadMemory();
        updateChatHeader();
        updateModelStatus(`Using ${app.state.currentModel}`);
      }
    } catch (err) {
      console.error(err);
      removeStreamingShell();

      if (err.name === "AbortError") {
        updateModelStatus("Stopped");
        await loadState();
        if (app.state.activeSessionId) {
          await loadSession(app.state.activeSessionId);
        }
      } else {
        const errorMsg = {
          id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
          role: "assistant",
          content: `Error: ${err.message}`,
          timestamp: nowUnix(),
          model,
        };

        app.state.messages.push(errorMsg);
        renderMessages(app.state.messages);
        updateModelStatus("Response failed");
      }
    } finally {
      app.streaming.controller = null;
      setStatusSending(false);
    }
  }

  function stopStreaming() {
    if (app.streaming.controller) {
      app.streaming.controller.abort();
      app.streaming.controller = null;
    }
    app.state.isSending = false;
    const sendBtn = getSendBtn();
    const stopBtn = getStopBtn();
    if (sendBtn) sendBtn.disabled = false;
    if (stopBtn) {
      stopBtn.disabled = true;
      stopBtn.classList.add("hidden");
    }
    updateModelStatus(`Using ${app.state.currentModel}`);
    updateChatHeader();
  }

  function bindEvents() {
    const input = getMessageInput();
    const sendBtn = getSendBtn();
    const stopBtn = getStopBtn();
    const newBtn = getNewSessionBtn();
    const deleteBtn = getDeleteSessionBtn();
    const renameBtn = getRenameSessionBtn();
    const duplicateBtn = getDuplicateSessionBtn();
    const pinBtn = getPinSessionBtn();
    const exportBtn = getExportSessionBtn();
    const modelSelect = getModelSelect();
    const memoryForm = getMemoryForm();
    const refreshMemoryBtn = getMemoryRefreshBtn();
    const toggleSidebarBtn = getToggleSidebarBtn();
    const mobileSidebarBtn = getMobileSidebarBtn();
    const memoryToggleBtnTop = getMemoryToggleBtnTop();
    const closeMemoryBtn = getCloseMemoryBtn();
    const themeToggleBtn = getThemeToggleBtn();
    const backgroundBtn = getBackgroundBtn();
    const attachBtn = getAttachBtn();
    const voiceBtn = getVoiceBtn();
    const fileInput = getFileInput();

    if (input) {
      input.style.height = `${INPUT_MIN_HEIGHT}px`;
      input.addEventListener("input", autosizeInput);
      input.addEventListener("keydown", async (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          if (!app.state.isSending) await sendMessage();
        }
      });
      autosizeInput();
    }

    if (sendBtn) {
      sendBtn.addEventListener("click", async () => {
        if (!app.state.isSending) await sendMessage();
      });
    }

    if (stopBtn) stopBtn.addEventListener("click", stopStreaming);

    if (newBtn) {
      newBtn.addEventListener("click", async () => {
        try {
          await createNewSession();
        } catch (err) {
          console.error(err);
          alert(`Failed to create session: ${err.message}`);
        }
      });
    }

    if (deleteBtn) {
      deleteBtn.addEventListener("click", async () => {
        try {
          await deleteCurrentSession();
        } catch (err) {
          console.error(err);
          alert(`Failed to delete session: ${err.message}`);
        }
      });
    }

    if (renameBtn) {
      renameBtn.addEventListener("click", async () => {
        try {
          await renameCurrentSession();
        } catch (err) {
          console.error(err);
          alert(`Failed to rename session: ${err.message}`);
        }
      });
    }

    if (duplicateBtn) {
      duplicateBtn.addEventListener("click", async () => {
        try {
          await duplicateCurrentSession();
        } catch (err) {
          console.error(err);
          alert(`Failed to duplicate session: ${err.message}`);
        }
      });
    }

    if (pinBtn) {
      pinBtn.addEventListener("click", () => {
        togglePinnedSession(app.state.activeSessionId);
      });
    }

    if (exportBtn) {
      exportBtn.addEventListener("click", () => {
        try {
          exportCurrentSession();
        } catch (err) {
          console.error(err);
          alert(`Failed to export chat: ${err.message}`);
        }
      });
    }

    if (modelSelect) {
      modelSelect.addEventListener("change", () => {
        app.state.currentModel = modelSelect.value || "gpt-4.1-mini";
        persistState();
        updateModelStatus(`Using ${app.state.currentModel}`);
      });
    }

    if (memoryForm) {
      memoryForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const kind = safeText(getMemoryKindInput()?.value || "preference");
        const value = safeText(getMemoryValueInput()?.value || "");

        if (!kind || !value) {
          alert("Memory kind and value are required.");
          return;
        }

        try {
          await addMemoryItem(kind, value);
        } catch (err) {
          console.error(err);
          alert(`Failed to add memory: ${err.message}`);
        }
      });
    }

    if (refreshMemoryBtn) {
      refreshMemoryBtn.addEventListener("click", async () => {
        try {
          updateMemoryStatus("Refreshing memory...");
          await loadMemory();
        } catch (err) {
          console.error(err);
          alert(`Failed to refresh memory: ${err.message}`);
        }
      });
    }

    for (const btn of qsa(["button[data-action='add-memory']"])) {
      btn.addEventListener("click", async () => {
        const kind = safeText(getMemoryKindInput()?.value || "preference");
        const value = safeText(getMemoryValueInput()?.value || "");

        if (!value) {
          alert("Enter a memory value first.");
          return;
        }

        try {
          await addMemoryItem(kind, value);
        } catch (err) {
          console.error(err);
          alert(`Failed to add memory: ${err.message}`);
        }
      });
    }

    if (toggleSidebarBtn) toggleSidebarBtn.addEventListener("click", toggleSidebar);
    if (mobileSidebarBtn) mobileSidebarBtn.addEventListener("click", toggleSidebar);
    if (memoryToggleBtnTop) memoryToggleBtnTop.addEventListener("click", toggleMemoryPanel);
    if (closeMemoryBtn) closeMemoryBtn.addEventListener("click", closeMemoryPanel);

    if (themeToggleBtn) {
      themeToggleBtn.addEventListener("click", cycleThemeMode);
    }

    if (backgroundBtn) {
      backgroundBtn.addEventListener("click", cycleBackgroundMode);
    }

    if (attachBtn && fileInput) {
      attachBtn.addEventListener("click", () => fileInput.click());
    }

    if (fileInput) {
      fileInput.addEventListener("change", () => {
        const files = Array.from(fileInput.files || []);
        app.state.attachedFiles = files;
        renderAttachedFiles();

        const total = files.length;
        if (total > 0) {
          updateModelStatus(`${total} file${total === 1 ? "" : "s"} selected`);
        } else {
          updateModelStatus(`Using ${app.state.currentModel}`);
        }
      });
    }

    if (voiceBtn) {
      voiceBtn.addEventListener("click", toggleVoiceRecognition);
    }
  }

  async function bootstrap() {
    restoreState();
    injectRuntimeStyles();
    applyThemeMode();
    applyBackgroundMode();
    bindEvents();
    renderAttachedFiles();
    setStatusSending(false);
    applyLayout();
    updateChatHeader();
    updateMemoryStatus("Loading memory...");

    await Promise.allSettled([loadModels(), loadState(), loadMemory()]);

    if (app.state.activeSessionId) {
      try {
        await loadSession(app.state.activeSessionId);
      } catch (err) {
        console.warn("Initial session load failed:", err);
        renderMessages([]);
      }
    } else {
      renderMessages([]);
    }

    applyLayout();
    applyThemeMode();
    applyBackgroundMode();
    updateChatHeader();
    syncPinButtonLabel();
    autosizeInput();

    window.NovaApp = window.NovaApp || {};
    window.NovaApp.state = app.state;
  }

  document.addEventListener("DOMContentLoaded", () => {
    bootstrap().catch((err) => {
      console.error("Nova bootstrap failed:", err);
      updateModelStatus("Bootstrap failed");
    });
  });
})();