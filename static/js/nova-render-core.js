(() => {
  "use strict";

  window.NovaRender = window.NovaRender || {};
  const NovaRender = window.NovaRender;

  if (NovaRender.coreLoaded) return;
  NovaRender.coreLoaded = true;

  const API = {
    state: "/api/state",
    newSession: "/api/session/new",
    renameSession: "/api/session/rename",
    deleteSession: "/api/session/delete",
    duplicateSession: "/api/session/duplicate",
    pinSession: "/api/session/pin",
    memory: "/api/memory",
    addMemory: "/api/memory/add",
    deleteMemory: "/api/memory/delete",
    stream: "/api/chat/stream",
    getChat: (sessionId) => `/api/chat/${encodeURIComponent(sessionId)}`,
  };

  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition || null;

  const els = {
    appRoot: document.getElementById("appRoot"),
    mobileBackdrop: document.getElementById("mobileBackdrop"),
    chat: document.getElementById("chat"),
    input: document.getElementById("input"),
    send: document.getElementById("send"),
    sidebar: document.getElementById("sidebar"),
    memory: document.getElementById("memory"),
    sessionList: document.getElementById("sessionList"),
    newSessionBtn: document.getElementById("newSessionBtn"),
    toggleSidebar: document.getElementById("toggleSidebar"),
    toggleMemory: document.getElementById("toggleMemory"),
    sessionStatus: document.getElementById("sessionStatus"),
    composerHint: document.getElementById("composerHint"),
    memoryList: document.getElementById("memoryList"),
    memorySearch: document.getElementById("memorySearch"),
    memoryInput: document.getElementById("memoryInput"),
    memoryKind: document.getElementById("memoryKind"),
    addMemoryBtn: document.getElementById("addMemoryBtn"),
    memoryCount: document.getElementById("memoryCount"),
    memoryRefreshBtn: document.getElementById("memoryRefreshBtn"),
    voiceBtn:
      document.getElementById("voiceBtn") ||
      document.getElementById("voiceInputBtn") ||
      document.getElementById("micBtn"),
    regenerateBtn:
      document.getElementById("regenerateBtn") ||
      document.getElementById("retryBtn"),
  };

  const state = {
    sessions: [],
    activeSessionId: null,
    isSending: false,
    memoryItems: [],
    memoryQuery: "",
    isAddingMemory: false,
    isMobile: false,
    sidebarOpen: false,
    memoryOpen: false,
    lastUserMessage: "",
    isRecognizing: false,
    recognition: null,
    recognitionSupported: !!SpeechRecognition,
  };

  const MOBILE_BREAKPOINT = 900;
  const INPUT_MAX_HEIGHT = 220;
  const MEMORY_INPUT_MAX_HEIGHT = 180;

  function text(value) {
    return String(value ?? "").trim();
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function hasEl(el) {
    return !!el;
  }

  function isMobileViewport() {
    return window.innerWidth <= MOBILE_BREAKPOINT;
  }

  async function parseResponse(res) {
    const contentType = res.headers.get("content-type") || "";
    const raw = await res.text().catch(() => "");

    if (!raw) return null;

    if (contentType.includes("application/json")) {
      try {
        return JSON.parse(raw);
      } catch {
        return { raw };
      }
    }

    try {
      return JSON.parse(raw);
    } catch {
      return raw;
    }
  }

  async function apiGet(url) {
    const res = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
    });

    const parsed = await parseResponse(res);

    if (!res.ok) {
      const msg =
        parsed?.error ||
        parsed?.message ||
        (typeof parsed === "string" ? parsed : "") ||
        `GET failed: ${url}`;
      throw new Error(msg);
    }

    return parsed ?? {};
  }

  async function apiPost(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json, text/plain;q=0.9, */*;q=0.8",
      },
      body: JSON.stringify(body || {}),
    });

    const parsed = await parseResponse(res);

    if (!res.ok) {
      const msg =
        parsed?.error ||
        parsed?.message ||
        (typeof parsed === "string" ? parsed : "") ||
        `POST failed: ${url}`;
      throw new Error(msg);
    }

    return parsed ?? {};
  }

  function getSessionTitle(session) {
    return session?.title || session?.name || session?.label || "Untitled chat";
  }

  function isPinned(session) {
    return !!(session?.pinned || session?.is_pinned || session?.pin || session?.favorite);
  }

  function sortSessions(sessions) {
    return [...safeArray(sessions)].sort((a, b) => {
      const aPinned = isPinned(a) ? 1 : 0;
      const bPinned = isPinned(b) ? 1 : 0;
      if (aPinned !== bPinned) return bPinned - aPinned;

      const aTime = new Date(a?.updated_at || a?.modified_at || a?.created_at || 0).getTime() || 0;
      const bTime = new Date(b?.updated_at || b?.modified_at || b?.created_at || 0).getTime() || 0;

      return bTime - aTime;
    });
  }

  function getMemoryId(item) {
    return item?.id || item?._id || item?.memory_id || item?.uuid || null;
  }

  function getMemoryKind(item) {
    return text(item?.kind || item?.type || item?.category || "note") || "note";
  }

  function getMemoryValue(item) {
    return text(item?.value || item?.content || item?.text || item?.note || "");
  }

  function getMemoryTimestamp(item) {
    return item?.updated_at || item?.created_at || item?.timestamp || item?.time || "";
  }

  function formatTimestamp(value) {
    if (!value) return "Saved";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "Saved";
    return date.toLocaleString();
  }

  function pickSessionsFromState(payload) {
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.sessions)) return payload.sessions;
    if (Array.isArray(payload?.items)) return payload.items;
    if (Array.isArray(payload?.data?.sessions)) return payload.data.sessions;
    return [];
  }

  function pickActiveSessionId(payload, sessions) {
    return (
      payload?.active_session_id ||
      payload?.activeSessionId ||
      payload?.session_id ||
      safeArray(sessions)?.[0]?.id ||
      null
    );
  }

  function pickMessagesFromSession(payload) {
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.messages)) return payload.messages;
    if (Array.isArray(payload?.session?.messages)) return payload.session.messages;
    if (Array.isArray(payload?.data?.messages)) return payload.data.messages;
    return [];
  }

  function pickMemoryItems(payload) {
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.items)) return payload.items;
    if (Array.isArray(payload?.memory)) return payload.memory;
    if (Array.isArray(payload?.memories)) return payload.memories;
    if (Array.isArray(payload?.data?.memory)) return payload.data.memory;
    return [];
  }

  NovaRender.API = API;
  NovaRender.els = els;
  NovaRender.state = state;
  NovaRender.SpeechRecognition = SpeechRecognition;

  NovaRender.MOBILE_BREAKPOINT = MOBILE_BREAKPOINT;
  NovaRender.INPUT_MAX_HEIGHT = INPUT_MAX_HEIGHT;
  NovaRender.MEMORY_INPUT_MAX_HEIGHT = MEMORY_INPUT_MAX_HEIGHT;

  NovaRender.text = text;
  NovaRender.escapeHtml = escapeHtml;
  NovaRender.safeArray = safeArray;
  NovaRender.hasEl = hasEl;
  NovaRender.isMobileViewport = isMobileViewport;

  NovaRender.parseResponse = parseResponse;
  NovaRender.apiGet = apiGet;
  NovaRender.apiPost = apiPost;

  NovaRender.getSessionTitle = getSessionTitle;
  NovaRender.isPinned = isPinned;
  NovaRender.sortSessions = sortSessions;

  NovaRender.getMemoryId = getMemoryId;
  NovaRender.getMemoryKind = getMemoryKind;
  NovaRender.getMemoryValue = getMemoryValue;
  NovaRender.getMemoryTimestamp = getMemoryTimestamp;
  NovaRender.formatTimestamp = formatTimestamp;

  NovaRender.pickSessionsFromState = pickSessionsFromState;
  NovaRender.pickActiveSessionId = pickActiveSessionId;
  NovaRender.pickMessagesFromSession = pickMessagesFromSession;
  NovaRender.pickMemoryItems = pickMemoryItems;
})();