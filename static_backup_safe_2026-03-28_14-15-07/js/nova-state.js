// C:\Users\Owner\nova\static\js\nova-state.js

(() => {
  "use strict";

  window.Nova = window.Nova || {};

  if (window.Nova.stateModuleLoaded) {
    console.warn("nova-state.js already loaded");
    return;
  }
  window.Nova.stateModuleLoaded = true;

  const DEFAULT_MODEL = "gpt-4.1-mini";
  const MAX_INPUT_HEIGHT = 180;

  const STORAGE = {
    activeSessionId: "nova_active_session_id",
    currentModel: "nova_selected_model",
    sidebarOpen: "nova_sidebar_open",
    memoryOpen: "nova_memory_open",
    themeMode: "nova_theme_mode",
    backgroundMode: "nova_background_mode",
    pinnedSessionIds: "nova_pinned_session_ids",
  };

  const API = {
    state: "/api/state",
    health: "/api/health",
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
    send: "/api/chat/send",
    stream: "/api/chat/stream",
    upload: "/api/upload",
    authMe: "/api/auth/me",
    authLogin: "/api/auth/login",
    authRegister: "/api/auth/register",
    authLogout: "/api/auth/logout",
  };

  const state = {
    sessions: [],
    messages: [],
    memoryItems: [],
    sourceItems: [],
    activeSessionId: null,
    currentModel: DEFAULT_MODEL,
    isSending: false,
    isBootstrapping: false,
    isLoadingSession: false,
    streamController: null,
    streamAssistantIndex: -1,
    lastUserMessage: "",
    lastRouter: null,
    lastRouterMeta: null,
    attachedFiles: [],
    sidebarOpen: true,
    memoryOpen: false,
    themeMode: "dark",
    backgroundMode: "default",
    pinnedSessionIds: [],
    username: "",
    devBypassAuth: false,
    authChecked: false,
    sourcePanelOpen: false,
  };

  function safeJsonParse(raw, fallback) {
    try {
      return JSON.parse(raw);
    } catch (_error) {
      return fallback;
    }
  }

  function loadPreference(key, fallback = null) {
    try {
      const raw = window.localStorage.getItem(key);
      if (raw === null || raw === undefined || raw === "") {
        return fallback;
      }
      return safeJsonParse(raw, fallback);
    } catch (_error) {
      return fallback;
    }
  }

  function savePreference(key, value) {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch (_error) {
      // ignore localStorage write failures
    }
  }

  function removePreference(key) {
    try {
      window.localStorage.removeItem(key);
    } catch (_error) {
      // ignore localStorage remove failures
    }
  }

  function loadArrayPreference(key) {
    const value = loadPreference(key, []);
    return Array.isArray(value) ? value : [];
  }

  function loadBooleanPreference(key, fallback = false) {
    const value = loadPreference(key, fallback);
    return typeof value === "boolean" ? value : fallback;
  }

  function loadStringPreference(key, fallback = "") {
    const value = loadPreference(key, fallback);
    return typeof value === "string" && value.trim() ? value : fallback;
  }

  function setActiveSessionId(sessionId) {
    state.activeSessionId = sessionId || null;
    if (state.activeSessionId) {
      savePreference(STORAGE.activeSessionId, state.activeSessionId);
    } else {
      removePreference(STORAGE.activeSessionId);
    }
  }

  function setCurrentModel(model) {
    const nextModel = String(model || "").trim() || DEFAULT_MODEL;
    state.currentModel = nextModel;
    savePreference(STORAGE.currentModel, nextModel);
  }

  function setSidebarOpen(isOpen) {
    state.sidebarOpen = !!isOpen;
    savePreference(STORAGE.sidebarOpen, state.sidebarOpen);
  }

  function setMemoryOpen(isOpen) {
    state.memoryOpen = !!isOpen;
    savePreference(STORAGE.memoryOpen, state.memoryOpen);
  }

  function setThemeMode(mode) {
    const next = String(mode || "").trim() || "dark";
    state.themeMode = next;
    savePreference(STORAGE.themeMode, next);
  }

  function setBackgroundMode(mode) {
    const next = String(mode || "").trim() || "default";
    state.backgroundMode = next;
    savePreference(STORAGE.backgroundMode, next);
  }

  function setPinnedSessionIds(ids) {
    state.pinnedSessionIds = Array.isArray(ids) ? [...ids] : [];
    savePreference(STORAGE.pinnedSessionIds, state.pinnedSessionIds);
  }

  function bootstrapStateFromStorage() {
    state.activeSessionId = loadStringPreference(STORAGE.activeSessionId, "");
    state.currentModel = loadStringPreference(STORAGE.currentModel, DEFAULT_MODEL);
    state.sidebarOpen = loadBooleanPreference(STORAGE.sidebarOpen, true);
    state.memoryOpen = loadBooleanPreference(STORAGE.memoryOpen, false);
    state.themeMode = loadStringPreference(STORAGE.themeMode, "dark");
    state.backgroundMode = loadStringPreference(STORAGE.backgroundMode, "default");
    state.pinnedSessionIds = loadArrayPreference(STORAGE.pinnedSessionIds);
  }

  bootstrapStateFromStorage();

  window.Nova.constants = {
    DEFAULT_MODEL,
    MAX_INPUT_HEIGHT,
  };

  window.Nova.storage = STORAGE;
  window.Nova.apiPaths = API;
  window.Nova.state = state;
  window.Nova.stateUtils = {
    loadPreference,
    savePreference,
    removePreference,
    setActiveSessionId,
    setCurrentModel,
    setSidebarOpen,
    setMemoryOpen,
    setThemeMode,
    setBackgroundMode,
    setPinnedSessionIds,
    bootstrapStateFromStorage,
  };
})();