(() => {
  "use strict";

  if (window.NovaCore) return;

  const API = {
    state: "/api/state",
    memory: "/api/memory",
    newSession: "/api/session/new",
    renameSession: "/api/session/rename",
    duplicateSession: "/api/session/duplicate",
    deleteSession: "/api/session/delete",
    pinSession: "/api/session/pin",
    stream: "/api/chat/stream",
    chat: "/api/chat",
    getChat(sessionId) {
      return `/api/chat/${encodeURIComponent(sessionId)}`;
    },
  };

  const state = {
    sessions: [],
    activeSessionId: null,
    messages: [],
    memoryItems: [],
    currentModel: "gpt-4.1-mini",
    sending: false,
    routeMeta: {
      route: "general",
      reason: "default route",
      memory_scope: "general",
      model: "gpt-4.1-mini",
    },
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function qs(selector, root = document) {
    return root.querySelector(selector);
  }

  function qsa(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
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

  async function request(url, options = {}) {
    const config = {
      method: options.method || "GET",
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(options.headers || {}),
      },
      cache: "no-store",
    };

    if (options.body !== undefined) {
      config.body = options.body;
    }

    const response = await fetch(url, config);
    const rawText = await response.text();

    let data = null;
    try {
      data = rawText ? JSON.parse(rawText) : null;
    } catch {
      data = rawText;
    }

    if (!response.ok) {
      const message =
        (data && typeof data === "object" && (data.error || data.message)) ||
        rawText ||
        `Request failed: ${response.status}`;
      throw new Error(message);
    }

    return data;
  }

  function normalizeSessions(payload) {
    const raw =
      payload?.sessions ||
      payload?.items ||
      payload?.data?.sessions ||
      [];

    if (!Array.isArray(raw)) return [];

    return raw.map((item, index) => {
      if (typeof item === "string") {
        return {
          id: item,
          title: item,
          pinned: false,
          created_at: index,
          updated_at: index,
        };
      }

      return {
        id: String(item.id || item.session_id || `session-${index}`),
        title: String(item.title || item.name || "Untitled Chat"),
        pinned: Boolean(item.pinned || item.is_pinned),
        created_at: Number(item.created_at || index),
        updated_at: Number(item.updated_at || item.created_at || index),
      };
    });
  }

  function normalizeMessages(payload) {
    const raw =
      payload?.messages ||
      payload?.chat ||
      payload?.items ||
      [];

    if (!Array.isArray(raw)) return [];

    return raw.map((item, index) => ({
      id: String(item.id || `msg-${index}`),
      role: String(item.role || item.sender || "assistant"),
      content: String(item.content || item.text || item.message || ""),
      created_at: Number(item.created_at || index),
    }));
  }

  function normalizeMemory(payload) {
    const raw =
      payload?.memory ||
      payload?.items ||
      payload?.data ||
      [];

    if (!Array.isArray(raw)) return [];

    return raw.map((item, index) => ({
      id: String(item.id || `memory-${index}`),
      kind: String(item.kind || item.type || "memory"),
      value: String(item.value || item.text || item.content || ""),
      created_at: Number(item.created_at || index),
    }));
  }

  function applyRouteMeta(meta) {
    if (!meta || typeof meta !== "object") return;
    state.routeMeta = {
      route: String(meta.route || meta.intent || state.routeMeta.route || "general"),
      reason: String(meta.reason || state.routeMeta.reason || "default route"),
      memory_scope: String(
        meta.memory_scope || meta.memory || state.routeMeta.memory_scope || "general"
      ),
      model: String(meta.model || state.currentModel || state.routeMeta.model || "gpt-4.1-mini"),
    };
  }

  async function loadState() {
    const data = await request(API.state, { method: "GET" });

    state.sessions = normalizeSessions(data);
    state.activeSessionId = data?.active_session_id || state.sessions[0]?.id || null;
    state.currentModel = String(data?.current_model || state.currentModel || "gpt-4.1-mini");
    applyRouteMeta(data?.route_meta);

    return data;
  }

  async function loadChat(sessionId) {
    if (!sessionId) {
      state.messages = [];
      return [];
    }

    const data = await request(API.getChat(sessionId), { method: "GET" });
    state.messages = normalizeMessages(data);
    applyRouteMeta(data?.route_meta);
    return state.messages;
  }

  async function loadMemory() {
    const data = await request(API.memory, { method: "GET" });
    state.memoryItems = normalizeMemory(data);
    return state.memoryItems;
  }

  async function createSession() {
    const data = await request(API.newSession, {
      method: "POST",
      body: JSON.stringify({}),
    });

    const sessionId =
      data?.session_id ||
      data?.id ||
      data?.session?.id ||
      null;

    await loadState();

    if (sessionId) {
      state.activeSessionId = sessionId;
      state.messages = [];
    }

    return data;
  }

  async function renameSession(sessionId, title) {
    return request(API.renameSession, {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        title,
      }),
    });
  }

  async function duplicateSession(sessionId) {
    return request(API.duplicateSession, {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
      }),
    });
  }

  async function deleteSession(sessionId) {
    const data = await request(API.deleteSession, {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
      }),
    });

    await loadState();

    if (state.activeSessionId) {
      await loadChat(state.activeSessionId);
    } else {
      state.messages = [];
    }

    return data;
  }

  async function pinSession(sessionId) {
    return request(API.pinSession, {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
      }),
    });
  }

  async function saveMemory(kind, value) {
    return request(API.memory, {
      method: "POST",
      body: JSON.stringify({
        kind,
        value,
      }),
    });
  }

  async function deleteMemory(memoryId) {
    return request(API.memory, {
      method: "DELETE",
      body: JSON.stringify({
        id: memoryId,
      }),
    });
  }

  async function sendMessage(message, handlers = {}) {
    if (state.sending) return;
    state.sending = true;

    const payload = {
      session_id: state.activeSessionId,
      message,
      model: state.currentModel || "gpt-4.1-mini",
    };

    const onStart = handlers.onStart || (() => {});
    const onChunk = handlers.onChunk || (() => {});
    const onDone = handlers.onDone || (() => {});
    const onMeta = handlers.onMeta || (() => {});

    try {
      onStart();

      const response = await fetch(API.stream, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(`Stream failed: ${response.status}`);
      }

      const rawText = await response.text();

      try {
        const data = rawText ? JSON.parse(rawText) : {};
        const text = String(data?.answer || data?.content || data?.message || "");
        const meta = data?.route_meta || null;

        if (text) {
          onChunk(text);
          onDone(text);
        } else {
          onDone("");
        }

        if (meta) {
          applyRouteMeta(meta);
          onMeta(state.routeMeta);
        }

        await loadState();
        if (state.activeSessionId) {
          await loadChat(state.activeSessionId);
        }

        return data;
      } catch {
        onChunk(rawText);
        onDone(rawText);

        await loadState();
        if (state.activeSessionId) {
          await loadChat(state.activeSessionId);
        }

        return rawText;
      }
    } catch (streamError) {
      const data = await request(API.chat, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      const text = String(data?.answer || data?.content || data?.message || "");
      if (text) {
        onDone(text);
      } else {
        onDone("");
      }

      if (data?.route_meta) {
        applyRouteMeta(data.route_meta);
        onMeta(state.routeMeta);
      }

      await loadState();
      if (state.activeSessionId) {
        await loadChat(state.activeSessionId);
      }

      return data;
    } finally {
      state.sending = false;
    }
  }

  window.NovaCore = {
    API,
    state,
    byId,
    qs,
    qsa,
    safeText,
    escapeHtml,
    request,
    loadState,
    loadChat,
    loadMemory,
    createSession,
    renameSession,
    duplicateSession,
    deleteSession,
    pinSession,
    saveMemory,
    deleteMemory,
    sendMessage,
  };
})();