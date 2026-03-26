(() => {
  "use strict";

  const Nova = (window.Nova = window.Nova || {});

  if (Nova.coreLoaded) return;
  Nova.coreLoaded = true;

  const API = {
    state: "/api/state",
    models: "/api/models",
    memory: "/api/memory",
    addMemory: "/api/memory/add",
    deleteMemory: "/api/memory/delete",
    newSession: "/api/session/new",
    deleteSession: "/api/session/delete",
    renameSession: "/api/session/rename",
    duplicateSession: "/api/session/duplicate",
    pinSession: "/api/session/pin",
    getChat: (sessionId) => `/api/chat/${encodeURIComponent(sessionId)}`,
    stream: "/api/chat/stream",
    upload: "/api/upload",
    webFetch: "/api/web/fetch",
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

  const DEFAULT_MODEL = "gpt-4.1-mini";
  const MAX_INPUT_HEIGHT = 180;

  const state = (Nova.state = Nova.state || {
    sessions: [],
    messages: [],
    memoryItems: [],
    attachedFiles: [],
    activeSessionId: null,
    currentModel: DEFAULT_MODEL,
    isSending: false,
    isStreaming: false,
    isRecording: false,
    lastUserMessage: "",
    lastAssistantMessage: "",
    lastRouter: null,
    sidebarOpen: true,
    memoryOpen: true,
    pinnedSessionIds: [],
    themeMode: "dark",
    backgroundMode: "default",
  });

  const dom = (Nova.dom = Nova.dom || {});

  function byId(id) {
    return document.getElementById(id);
  }

  function qs(selector, root = document) {
    return root.querySelector(selector);
  }

  function qsa(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
  }

  function safeJsonParse(value, fallback) {
    try {
      return JSON.parse(value);
    } catch {
      return fallback;
    }
  }

  function loadStorage(key, fallback = null) {
    try {
      const value = localStorage.getItem(key);
      return value == null ? fallback : value;
    } catch {
      return fallback;
    }
  }

  function saveStorage(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {}
  }

  function removeStorage(key) {
    try {
      localStorage.removeItem(key);
    } catch {}
  }

  async function apiGet(url) {
    const response = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.error || `GET failed: ${url}`);
    }

    return data;
  }

  async function apiPost(url, payload = {}) {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.error || `POST failed: ${url}`);
    }

    return data;
  }

  function formatTime(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return date.toLocaleTimeString([], {
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function formatDateLabel(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return date.toLocaleDateString([], {
      month: "short",
      day: "numeric",
    });
  }

  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function setText(id, value) {
    const el = byId(id);
    if (el) el.textContent = value;
  }

  dom.byId = byId;
  dom.qs = qs;
  dom.qsa = qsa;

  Nova.config = {
    API,
    STORAGE,
    DEFAULT_MODEL,
    MAX_INPUT_HEIGHT,
  };

  Nova.utils = {
    safeJsonParse,
    loadStorage,
    saveStorage,
    removeStorage,
    apiGet,
    apiPost,
    formatTime,
    formatDateLabel,
    escapeHtml,
    setText,
  };
})();