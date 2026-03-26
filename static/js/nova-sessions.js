(() => {
  "use strict";

  const Nova = (window.Nova = window.Nova || {});
  if (Nova.sessionsLoaded) return;
  Nova.sessionsLoaded = true;

  const state = Nova.state;
  const { API, STORAGE } = Nova.config;
  const { apiGet, apiPost, saveStorage } = Nova.utils;

  function normalizeSession(session) {
    if (!session || typeof session !== "object") return null;

    return {
      id: session.id || session.session_id || crypto.randomUUID(),
      title: session.title || session.name || "New chat",
      updated_at: session.updated_at || session.updatedAt || session.created_at || new Date().toISOString(),
      created_at: session.created_at || session.createdAt || session.updated_at || new Date().toISOString(),
      pinned: !!session.pinned,
      message_count:
        typeof session.message_count === "number"
          ? session.message_count
          : Array.isArray(session.messages)
            ? session.messages.length
            : 0,
      preview: session.preview || "",
    };
  }

  function sortSessions(list) {
    const pinnedIds = new Set(state.pinnedSessionIds || []);
    return [...list].sort((a, b) => {
      const aPinned = pinnedIds.has(a.id) || a.pinned;
      const bPinned = pinnedIds.has(b.id) || b.pinned;
      if (aPinned !== bPinned) return aPinned ? -1 : 1;

      const aTime = new Date(a.updated_at || 0).getTime();
      const bTime = new Date(b.updated_at || 0).getTime();
      return bTime - aTime;
    });
  }

  function setSessions(list) {
    state.sessions = sortSessions((list || []).map(normalizeSession).filter(Boolean));
  }

  function getSessionById(sessionId) {
    return (state.sessions || []).find((s) => s.id === sessionId) || null;
  }

  function upsertSession(session) {
    const normalized = normalizeSession(session);
    if (!normalized) return null;

    const index = state.sessions.findIndex((s) => s.id === normalized.id);
    if (index >= 0) {
      state.sessions[index] = { ...state.sessions[index], ...normalized };
    } else {
      state.sessions.unshift(normalized);
    }

    state.sessions = sortSessions(state.sessions);
    return normalized;
  }

  function removeSessionLocal(sessionId) {
    state.sessions = (state.sessions || []).filter((s) => s.id !== sessionId);
    if (state.activeSessionId === sessionId) {
      state.activeSessionId = state.sessions[0]?.id || null;
      saveStorage(STORAGE.activeSessionId, state.activeSessionId || "");
    }
  }

  async function loadState() {
    const data = await apiGet(API.state);
    const sessions = Array.isArray(data.sessions) ? data.sessions : [];
    setSessions(sessions);

    if (!state.activeSessionId && state.sessions.length) {
      state.activeSessionId = state.sessions[0].id;
      saveStorage(STORAGE.activeSessionId, state.activeSessionId);
    }

    if (state.activeSessionId && !getSessionById(state.activeSessionId) && state.sessions.length) {
      state.activeSessionId = state.sessions[0].id;
      saveStorage(STORAGE.activeSessionId, state.activeSessionId);
    }

    return data;
  }

  async function loadSession(sessionId) {
    if (!sessionId) return null;

    const data = await apiGet(API.getChat(sessionId));
    state.activeSessionId = sessionId;
    saveStorage(STORAGE.activeSessionId, sessionId);

    state.messages = Array.isArray(data.messages) ? data.messages : [];
    upsertSession({
      id: sessionId,
      title: data.title || getSessionById(sessionId)?.title || "New chat",
      updated_at: data.updated_at || new Date().toISOString(),
      message_count: state.messages.length,
      preview: state.messages[state.messages.length - 1]?.content || "",
    });

    return data;
  }

  async function createSession(title = "New chat") {
    const data = await apiPost(API.newSession, { title });
    const newSession =
      normalizeSession(data.session || data) ||
      normalizeSession({
        id: data.session_id,
        title,
        updated_at: new Date().toISOString(),
      });

    if (newSession) {
      upsertSession(newSession);
      state.activeSessionId = newSession.id;
      state.messages = [];
      saveStorage(STORAGE.activeSessionId, newSession.id);
    }

    return newSession;
  }

  async function deleteSession(sessionId) {
    if (!sessionId) return;
    await apiPost(API.deleteSession, { session_id: sessionId });
    removeSessionLocal(sessionId);

    if (state.activeSessionId) {
      await loadSession(state.activeSessionId).catch(() => {});
    } else {
      state.messages = [];
    }
  }

  async function renameSession(sessionId, title) {
    if (!sessionId || !title?.trim()) return null;
    const cleanTitle = title.trim();

    await apiPost(API.renameSession, {
      session_id: sessionId,
      title: cleanTitle,
    });

    const existing = getSessionById(sessionId);
    return upsertSession({
      ...existing,
      id: sessionId,
      title: cleanTitle,
      updated_at: new Date().toISOString(),
    });
  }

  async function duplicateSession(sessionId) {
    if (!sessionId) return null;

    const data = await apiPost(API.duplicateSession, { session_id: sessionId });
    const duplicated =
      normalizeSession(data.session || data) ||
      normalizeSession({
        id: data.session_id,
        title: data.title || "Copied chat",
        updated_at: new Date().toISOString(),
      });

    if (duplicated) {
      upsertSession(duplicated);
    }

    return duplicated;
  }

  async function togglePinSession(sessionId) {
    if (!sessionId) return false;

    const current = new Set(state.pinnedSessionIds || []);
    const willPin = !current.has(sessionId);

    if (willPin) current.add(sessionId);
    else current.delete(sessionId);

    state.pinnedSessionIds = Array.from(current);
    saveStorage(STORAGE.pinnedSessionIds, JSON.stringify(state.pinnedSessionIds));

    try {
      await apiPost(API.pinSession, {
        session_id: sessionId,
        pinned: willPin,
      });
    } catch (error) {
      if (willPin) current.delete(sessionId);
      else current.add(sessionId);
      state.pinnedSessionIds = Array.from(current);
      saveStorage(STORAGE.pinnedSessionIds, JSON.stringify(state.pinnedSessionIds));
      throw error;
    }

    const existing = getSessionById(sessionId);
    if (existing) {
      upsertSession({ ...existing, pinned: willPin });
    }

    return willPin;
  }

  Nova.sessions = {
    normalizeSession,
    sortSessions,
    setSessions,
    getSessionById,
    upsertSession,
    removeSessionLocal,
    loadState,
    loadSession,
    createSession,
    deleteSession,
    renameSession,
    duplicateSession,
    togglePinSession,
  };
})();