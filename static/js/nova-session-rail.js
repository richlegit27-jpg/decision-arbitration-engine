(function () {
  "use strict";

  const API = {
    list: "/api/sessions",
    create: "/api/sessions/new",
    read() {
      return "/api/sessions";
    },
    switch: "/api/sessions/switch",
    rename: "/api/sessions/rename",
    pin: "/api/sessions/pin",
    remove: "/api/sessions/delete",
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
      q("[data-new-chat]") ||
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
      credentials: "same-origin",
    });

    let payload = {};
    try {
      payload = await response.json();
    } catch (_) {
      payload = {};
    }

    if (!response.ok || payload.ok === false) {
      const error = new Error(
        payload.error || payload.message || `HTTP ${response.status}`
      );
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
      archived: !!session.archived,
      meta: session.meta && typeof session.meta === "object" ? session.meta : {},
    };
  }

  function applyBackendState(payload, explicitActiveSessionId) {
    const data = payload && typeof payload === "object" ? payload : {};

    const incomingSessions = Array.isArray(data.sessions)
      ? data.sessions.map(normalizeSession).filter(Boolean)
      : null;

    const backendSession =
      normalizeSession(data.session) ||
      normalizeSession(data.active_session) ||
      null;

    if (incomingSessions) {
      state.sessions = incomingSessions.slice();
    } else {
      state.sessions = Array.isArray(state.sessions) ? state.sessions.slice() : [];
    }

    if (backendSession && backendSession.id) {
      const existingIndex = state.sessions.findIndex(function (s) {
        return s && s.id === backendSession.id;
      });

      if (existingIndex >= 0) {
        state.sessions[existingIndex] = Object.assign(
          {},
          state.sessions[existingIndex],
          backendSession
        );
      } else {
        state.sessions.unshift(backendSession);
      }
    }

    const availableIds = new Set(
      state.sessions
        .map(function (s) {
          return s && s.id ? s.id : "";
        })
        .filter(Boolean)
    );

    let preferredId =
      explicitActiveSessionId ||
      (backendSession && backendSession.id) ||
      state.activeSessionId ||
      (state.sessions[0] && state.sessions[0].id) ||
      "";

    if (preferredId && !availableIds.has(preferredId)) {
      preferredId =
        (backendSession && backendSession.id) ||
        (state.sessions[0] && state.sessions[0].id) ||
        "";
    }

    state.activeSessionId = preferredId;

    render();

    bindEls();
    wireNewButton();
    wireList();

    if (window.NovaComposerBundle?.applyBackendSessionState) {
      window.NovaComposerBundle.applyBackendSessionState(data, preferredId);
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
          payload: data,
        },
      })
    );
  }

  async function reloadFromBackend(preferredSessionId) {
    state.loading = true;
    setStatus("Loading...");

    try {
      let resolvedPreferredId = preferredSessionId || "";
      let payload = null;

      try {
        payload = await api(API.read());
      } catch (err) {
        try {
          localStorage.removeItem("nova_active_session_id");
        } catch (_) {}

        if (state.activeSessionId === preferredSessionId) {
          state.activeSessionId = "";
        }
        throw err;
      }

      const sessionIds = Array.isArray(payload?.sessions)
        ? payload.sessions.map(function (s) {
            return String(s?.id || "");
          })
        : [];

      if (
        resolvedPreferredId &&
        !sessionIds.includes(resolvedPreferredId) &&
        String(payload?.session?.id || "") !== resolvedPreferredId
      ) {
        try {
          localStorage.removeItem("nova_active_session_id");
        } catch (_) {}
        resolvedPreferredId = "";
      }

      applyBackendState(payload, resolvedPreferredId);
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

    await reloadFromBackend(payload?.session?.id || "");
    setStatus("");
    return payload;
  }

  async function renameSession(sessionId, nextTitle) {
    sessionId = String(sessionId || "").trim();
    nextTitle = String(nextTitle || "").trim();

    if (!sessionId || !nextTitle) return null;

    setStatus("Renaming...");

    const payload = await api(API.rename, {
      method: "POST",
      body: {
        session_id: sessionId,
        title: nextTitle,
      },
    });

    state.activeSessionId = String(
      payload?.session?.id || sessionId
    ).trim();

    await reloadFromBackend(state.activeSessionId);
    setStatus("");
    return payload;
  }

  async function selectSession(sessionId) {
    sessionId = String(sessionId || "").trim();
    if (!sessionId) return null;

    setStatus("Switching...");

    const payload = await api(API.switch, {
      method: "POST",
      body: { session_id: sessionId },
    });

    console.log("SESSION SWITCH PAYLOAD =", payload);
    console.log("SESSION SWITCH TARGET =", sessionId);

    const resolvedId = String(
      payload?.active_session_id ||
      payload?.session?.id ||
      sessionId ||
      ""
    ).trim();

    state.activeSessionId = resolvedId;

    applyBackendState(payload, resolvedId);

    try {
      await reloadFromBackend(resolvedId);
    } catch (err) {
      console.warn("SESSION SWITCH reload fallback failed:", err);
    }

    setStatus("");
    return payload;
  }  

  async function pinSession(sessionId, pinned) {
    if (!sessionId) return null;

    setStatus(pinned ? "Pinning..." : "Unpinning...");

    const payload = await api(API.pin, {
      method: "POST",
      body: {
        session_id: sessionId,
        pinned: !!pinned,
      },
    });

    await reloadFromBackend(sessionId);
    setStatus("");
    return payload;
  }

  async function deleteSession(sessionId) {
    if (!sessionId) return null;

    setStatus("Deleting...");

    const payload = await api(API.remove, {
      method: "POST",
      body: {
        session_id: sessionId,
      },
    });

    const nextId = payload?.active_session_id || payload?.session?.id || "";
    await reloadFromBackend(nextId);
    setStatus("");
    return payload;
  }

  function render() {
    bindEls();
    if (!els.list) {
      return;
    }

    const sessions = [...state.sessions].sort(function (a, b) {
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
      .map(function (session) {
        const isActive = session.id === state.activeSessionId;
        const sessionId = escapeHtml(session.id);
        const title = escapeHtml(session.title || "New Chat");
        const count = Number(session.message_count || 0);

        return `
          <div class="nova-session-item ${isActive ? "is-active" : ""}" data-session-id="${sessionId}">
            <button
              type="button"
              class="nova-session-main"
              data-session-id="${sessionId}"
              title="${title}"
            >
              <span class="nova-session-title-row">
                <span class="nova-session-title">${title}</span>
                ${session.pinned ? '<span class="nova-session-pin-badge">ðŸ“Œ</span>' : ""}
              </span>

              <span class="nova-session-meta-row">
                <span class="nova-session-preview">
                  ${count > 0 ? `${count} messages` : "No messages yet"}
                </span>
              </span>
            </button>

            <div class="nova-session-actions">
              <button
                type="button"
                class="nova-session-action"
                data-action="rename"
                data-session-id="${sessionId}"
                title="Rename"
              >âœŽ</button>

              <button
                type="button"
                class="nova-session-action"
                data-action="pin"
                data-session-id="${sessionId}"
                data-pinned="${session.pinned ? "1" : "0"}"
                title="${session.pinned ? "Unpin" : "Pin"}"
              >${session.pinned ? "â˜…" : "â˜†"}</button>

              <button
                type="button"
                class="nova-session-action danger"
                data-action="delete"
                data-session-id="${sessionId}"
                title="Delete"
              >ðŸ—‘</button>
            </div>
          </div>
        `;
      })
      .join("");

    els.list.querySelectorAll(".nova-session-main").forEach(function (btn) {
      btn.onclick = async function () {
        const id = btn.getAttribute("data-session-id");
        if (!id || id === state.activeSessionId) return;

        btn.disabled = true;
        try {
          await selectSession(id);
        } catch (err) {
          console.error("NovaSessionRail direct select failed:", err);
          setStatus(err?.payload?.message || err?.message || "Select failed");
        } finally {
          btn.disabled = false;
        }
      };
    });
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
          return;
        }

        if (action === "rename") {
          event.preventDefault();
          event.stopPropagation();

          const current = state.sessions.find(function (s) {
            return s.id === sessionId;
          });

          const nextTitle = window.prompt(
            "Rename session",
            current?.title || "New Chat"
          );

          if (nextTitle === null) return;

          await renameSession(sessionId, nextTitle);
          return;
        }

        if (action === "pin") {
          event.preventDefault();
          event.stopPropagation();

          const pinned = btn.getAttribute("data-pinned") === "1";
          await pinSession(sessionId, !pinned);
          return;
        }

        if (action === "delete") {
          event.preventDefault();
          event.stopPropagation();

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
    document.addEventListener(
      "nova:request-session-reload",
      async function (event) {
        try {
          await reloadFromBackend(
            event?.detail?.sessionId || state.activeSessionId || ""
          );
        } catch (err) {
          console.error("NovaSessionRail reload failed:", err);
          setStatus(err?.payload?.message || err?.message || "Reload failed");
        }
      }
    );

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

apiPublic.reloadArtifacts = async function () {
  try {
    await reloadFromBackend(state.activeSessionId || "");
  } catch (err) {
    console.warn("reloadArtifacts failed", err);
  }
};

  window.NovaSessionRail = apiPublic;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();

