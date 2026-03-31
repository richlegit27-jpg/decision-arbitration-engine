(function () {
  "use strict";

  const API = {
    list: "/api/sessions",
    create: "/api/sessions/create",
    read(id) {
      return `/api/sessions/${encodeURIComponent(id)}`;
    },
    rename(id) {
      return `/api/sessions/${encodeURIComponent(id)}/rename`;
    },
    pin(id) {
      return `/api/sessions/${encodeURIComponent(id)}/pin`;
    },
    remove(id) {
      return `/api/sessions/${encodeURIComponent(id)}`;
    },
  };

  const state = {
    sessions: [],
    activeSessionId: "",
    loading: false,
    initialized: false,
  };

  const els = {
    rail: null,
    list: null,
    newBtn: null,
    status: null,
  };

  function q(sel) {
    return document.querySelector(sel);
  }

  function qq(sel) {
    return Array.from(document.querySelectorAll(sel));
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function getListEl() {
    return (
      q("#sessionRailList") ||
      q("#novaSessionRailList") ||
      q("#sessionList") ||
      q("[data-session-list]") ||
      q(".nova-session-list")
    );
  }

  function getRailEl() {
    return (
      q("#sessionRail") ||
      q("#novaSessionRail") ||
      q("[data-session-rail]") ||
      q(".nova-session-rail")
    );
  }

  function getNewBtnEl() {
    return (
      q("#newSessionBtn") ||
      q("#sessionNewBtn") ||
      q("[data-session-new]") ||
      q(".nova-session-new")
    );
  }

  function getStatusEl() {
    return (
      q("#sessionRailStatus") ||
      q("#novaSessionRailStatus") ||
      q("[data-session-status]") ||
      q(".nova-session-status")
    );
  }

  function bindEls() {
    els.rail = getRailEl();
    els.list = getListEl();
    els.newBtn = getNewBtnEl();
    els.status = getStatusEl();
  }

  function setStatus(text) {
    if (els.status) {
      els.status.textContent = text || "";
    }
  }

  async function api(url, options) {
    const response = await fetch(url, {
      method: options?.method || "GET",
      headers: {
        "Content-Type": "application/json",
        ...(options?.headers || {}),
      },
      body: options?.body ? JSON.stringify(options.body) : undefined,
      cache: "no-store",
    });

    let payload = {};
    try {
      payload = await response.json();
    } catch (_) {
      payload = {};
    }

    if (!response.ok || payload.ok === false) {
      const error = new Error(payload.message || `HTTP ${response.status}`);
      error.payload = payload;
      error.status = response.status;
      throw error;
    }

    return payload;
  }

  function normalizeSession(session) {
    if (!session || typeof session !== "object") {
      return null;
    }
    return {
      id: String(session.id || ""),
      title: String(session.title || "New Chat"),
      pinned: !!session.pinned,
      created_at: String(session.created_at || ""),
      updated_at: String(session.updated_at || ""),
      message_count: Number(session.message_count || 0),
      last_message_preview: String(session.last_message_preview || ""),
      messages: Array.isArray(session.messages) ? session.messages : [],
    };
  }

  function applyBackendState(payload, explicitActiveSessionId) {
    const incomingSessions = Array.isArray(payload?.sessions) ? payload.sessions : [];
    state.sessions = incomingSessions.map(normalizeSession).filter(Boolean);

    const backendSession = normalizeSession(payload?.session);
    const preferredId =
      explicitActiveSessionId ||
      backendSession?.id ||
      state.activeSessionId ||
      state.sessions[0]?.id ||
      "";

    state.activeSessionId = preferredId;

    if (backendSession && !state.sessions.some((s) => s.id === backendSession.id)) {
      state.sessions.unshift(backendSession);
    }

    render();

    if (window.NovaComposerBundle?.applyBackendSessionState) {
      window.NovaComposerBundle.applyBackendSessionState(payload, preferredId);
    }

    try {
      if (state.activeSessionId) {
        localStorage.setItem("nova_active_session_id", state.activeSessionId);
      } else {
        localStorage.removeItem("nova_active_session_id");
      }
    } catch (_) {}

    document.dispatchEvent(
      new CustomEvent("nova:sessions-changed", {
        detail: {
          activeSessionId: state.activeSessionId,
          sessions: state.sessions,
          payload,
        },
      })
    );
  }

  async function reloadFromBackend(preferredSessionId) {
    state.loading = true;
    setStatus("Loading...");
    try {
      const payload = preferredSessionId
        ? await api(API.read(preferredSessionId))
        : await api(API.list);

      applyBackendState(payload, preferredSessionId);
      setStatus("");
      return payload;
    } finally {
      state.loading = false;
    }
  }

  async function createSession() {
    setStatus("Creating...");
    const payload = await api(API.create, {
      method: "POST",
      body: {},
    });
    applyBackendState(payload, payload?.session?.id || "");
    return payload;
  }

  async function selectSession(sessionId) {
    if (!sessionId) return null;
    setStatus("Switching...");
    const payload = await api(API.read(sessionId));
    applyBackendState(payload, sessionId);
    setStatus("");
    return payload;
  }

  async function renameSession(sessionId, title) {
    if (!sessionId) return null;
    setStatus("Renaming...");
    const payload = await api(API.rename(sessionId), {
      method: "POST",
      body: { title },
    });
    applyBackendState(payload, payload?.session?.id || sessionId);
    setStatus("");
    return payload;
  }

  async function pinSession(sessionId, pinned) {
    if (!sessionId) return null;
    setStatus(pinned ? "Pinning..." : "Unpinning...");
    const payload = await api(API.pin(sessionId), {
      method: "POST",
      body: { pinned: !!pinned },
    });
    applyBackendState(payload, payload?.session?.id || sessionId);
    setStatus("");
    return payload;
  }

  async function deleteSession(sessionId) {
    if (!sessionId) return null;
    setStatus("Deleting...");
    const payload = await api(API.remove(sessionId), {
      method: "DELETE",
    });
    applyBackendState(payload, payload?.session?.id || "");
    setStatus("");
    return payload;
  }

  function render() {
    bindEls();
    if (!els.list) {
      return;
    }

    const sessions = [...state.sessions].sort((a, b) => {
      if (!!a.pinned !== !!b.pinned) return a.pinned ? -1 : 1;
      return String(b.updated_at || "").localeCompare(String(a.updated_at || ""));
    });

    if (!sessions.length) {
      els.list.innerHTML = `
        <div class="nova-session-empty">
          <div class="nova-session-empty-title">No sessions yet</div>
          <div class="nova-session-empty-subtitle">Create a new chat to begin.</div>
        </div>
      `;
      return;
    }

    els.list.innerHTML = sessions
      .map((session) => {
        const isActive = session.id === state.activeSessionId;
        const title = escapeHtml(session.title || "New Chat");
        const preview = escapeHtml(session.last_message_preview || "");
        const count = Number(session.message_count || 0);

        return `
          <div class="nova-session-item ${isActive ? "is-active" : ""}" data-session-id="${escapeHtml(session.id)}">
            <button type="button" class="nova-session-main" data-action="select" data-session-id="${escapeHtml(session.id)}" title="${title}">
              <span class="nova-session-title-row">
                <span class="nova-session-title">${title}</span>
                ${session.pinned ? '<span class="nova-session-pin-badge">📌</span>' : ""}
              </span>
              <span class="nova-session-meta-row">
                <span class="nova-session-count">${count}</span>
                <span class="nova-session-preview">${preview || "No messages yet"}</span>
              </span>
            </button>

            <div class="nova-session-actions">
              <button type="button" class="nova-session-action" data-action="rename" data-session-id="${escapeHtml(session.id)}" title="Rename">✎</button>
              <button type="button" class="nova-session-action" data-action="pin" data-session-id="${escapeHtml(session.id)}" data-pinned="${session.pinned ? "1" : "0"}" title="${session.pinned ? "Unpin" : "Pin"}">
                ${session.pinned ? "★" : "☆"}
              </button>
              <button type="button" class="nova-session-action danger" data-action="delete" data-session-id="${escapeHtml(session.id)}" title="Delete">🗑</button>
            </div>
          </div>
        `;
      })
      .join("");
  }

  function wireNewButton() {
    if (!els.newBtn || els.newBtn.dataset.novaBound === "1") {
      return;
    }
    els.newBtn.dataset.novaBound = "1";
    els.newBtn.addEventListener("click", async function () {
      try {
        await createSession();
      } catch (err) {
        console.error("NovaSessionRail createSession failed:", err);
        setStatus(err?.payload?.message || err?.message || "Create failed");
      }
    });
  }

  function wireList() {
    if (!els.list || els.list.dataset.novaBound === "1") {
      return;
    }

    els.list.dataset.novaBound = "1";
    els.list.addEventListener("click", async function (event) {
      const btn = event.target.closest("[data-action]");
      if (!btn) return;

      const action = btn.getAttribute("data-action");
      const sessionId = btn.getAttribute("data-session-id") || "";

      try {
        if (action === "select") {
          await selectSession(sessionId);
          return;
        }

        if (action === "rename") {
          const current = state.sessions.find((s) => s.id === sessionId);
          const nextTitle = window.prompt("Rename session", current?.title || "New Chat");
          if (nextTitle === null) return;
          await renameSession(sessionId, nextTitle);
          return;
        }

        if (action === "pin") {
          const pinned = btn.getAttribute("data-pinned") === "1";
          await pinSession(sessionId, !pinned);
          return;
        }

        if (action === "delete") {
          const okay = window.confirm("Delete this session?");
          if (!okay) return;
          await deleteSession(sessionId);
        }
      } catch (err) {
        console.error("NovaSessionRail action failed:", action, err);
        setStatus(err?.payload?.message || err?.message || "Action failed");
      }
    });
  }

  function wireEvents() {
    document.addEventListener("nova:request-session-reload", async function (event) {
      try {
        await reloadFromBackend(event?.detail?.sessionId || state.activeSessionId || "");
      } catch (err) {
        console.error("NovaSessionRail reload failed:", err);
        setStatus(err?.payload?.message || err?.message || "Reload failed");
      }
    });

    document.addEventListener("nova:select-session", async function (event) {
      const sessionId = event?.detail?.sessionId || "";
      if (!sessionId) return;
      try {
        await selectSession(sessionId);
      } catch (err) {
        console.error("NovaSessionRail select event failed:", err);
        setStatus(err?.payload?.message || err?.message || "Select failed");
      }
    });

    document.addEventListener("nova:create-session", async function () {
      try {
        await createSession();
      } catch (err) {
        console.error("NovaSessionRail create event failed:", err);
        setStatus(err?.payload?.message || err?.message || "Create failed");
      }
    });
  }

  async function boot() {
    bindEls();
    wireNewButton();
    wireList();
    wireEvents();

    if (state.initialized) return;
    state.initialized = true;

    let preferred = "";
    try {
      preferred = localStorage.getItem("nova_active_session_id") || "";
    } catch (_) {}

    try {
      await reloadFromBackend(preferred);
    } catch (err) {
      console.error("NovaSessionRail boot failed:", err);
      setStatus(err?.payload?.message || err?.message || "Session load failed");
    }
  }

  const apiPublic = {
    init: boot,
    reloadFromBackend,
    selectSession,
    createSession,
    renameSession,
    pinSession,
    deleteSession,
    getActiveSessionId() {
      return state.activeSessionId || "";
    },
    getSessions() {
      return [...state.sessions];
    },
    applyBackendState,
  };

  window.NovaSessionRail = apiPublic;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();