(function () {
  "use strict";

  console.log("nova-session-rail loaded");

  const API = {
    state: "/api/state",
    sessionNew: "/api/sessions/new",
    sessionRename: "/api/sessions/rename",
    sessionPin: "/api/sessions/pin",
    sessionDelete: "/api/sessions/delete"
  };

  const state = {
    sessions: [],
    currentSessionId: localStorage.getItem("nova_active_session_id") || "default-session",
    loading: false
  };

  function el(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function getSessionsListEl() {
    return el("sessionsList");
  }

  function getSessionTitleTextEl() {
    return el("sessionTitleText");
  }

  function getActiveSessionMetaEl() {
    return el("activeSessionMeta");
  }

  function getSessionStatusEl() {
    return el("sessionStatus");
  }

  function setStatus(text, tone) {
    const node = getSessionStatusEl();
    if (!node) return;
    node.textContent = text || "Ready";
    node.dataset.tone = tone || "muted";
  }

  function formatRelativeSessionMeta(session) {
    const count = Number(session?.message_count || 0);
    const pinned = session?.pinned ? " • pinned" : "";
    return `${count} msg${count === 1 ? "" : "s"}${pinned}`;
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, options || {});
    const text = await response.text();

    let data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch (error) {
      throw new Error(`Invalid JSON from ${url}: ${text.slice(0, 300)}`);
    }

    if (!response.ok) {
      throw new Error(data?.message || data?.error || `HTTP ${response.status}`);
    }

    return data;
  }

  function setCurrentSessionId(sessionId) {
    const resolved = String(sessionId || "default-session").trim() || "default-session";
    state.currentSessionId = resolved;
    localStorage.setItem("nova_active_session_id", resolved);
    document.body.dataset.sessionId = resolved;

    if (window.NovaComposerBundle && typeof window.NovaComposerBundle.setSessionId === "function") {
      window.NovaComposerBundle.setSessionId(resolved);
    }
  }

  function getCurrentSessionId() {
    return state.currentSessionId || "default-session";
  }

  function getCurrentSession() {
    return state.sessions.find((item) => item.id === state.currentSessionId) || null;
  }

  function renderTopbarFromCurrentSession() {
    const session = getCurrentSession();
    const titleEl = getSessionTitleTextEl();
    const metaEl = getActiveSessionMetaEl();

    if (titleEl) {
      titleEl.textContent = session?.title || "New Chat";
    }

    if (metaEl) {
      metaEl.textContent = formatRelativeSessionMeta(session || {});
    }
  }

  function renderSessions() {
    const listEl = getSessionsListEl();
    if (!listEl) return;

    if (!Array.isArray(state.sessions) || !state.sessions.length) {
      listEl.innerHTML = '<div class="session-empty">No sessions yet.</div>';
      renderTopbarFromCurrentSession();
      return;
    }

    listEl.innerHTML = state.sessions
      .map((session) => {
        const isActive = session.id === state.currentSessionId;
        const title = session?.title || "Untitled Session";
        const preview = session?.last_message_preview || "No messages yet.";
        const pinned = !!session?.pinned;

        return `
          <button
            type="button"
            class="session-item${isActive ? " is-active" : ""}"
            data-session-id="${escapeHtml(session.id || "")}"
            title="${escapeHtml(title)}"
          >
            <div class="session-item-top">
              <div class="session-item-title">${escapeHtml(title)}</div>
              ${pinned ? '<div class="session-pin-indicator">★</div>' : ""}
            </div>
            <div class="session-item-bottom">
              <span>${escapeHtml(preview)}</span>
            </div>
          </button>
        `;
      })
      .join("");

    renderTopbarFromCurrentSession();
  }

  async function refreshSessions(preferredSessionId) {
    if (state.loading) return;
    state.loading = true;

    try {
      const targetSessionId = preferredSessionId || getCurrentSessionId();
      const data = await fetchJson(`${API.state}?session_id=${encodeURIComponent(targetSessionId)}`);

      state.sessions = Array.isArray(data?.sessions) ? data.sessions : [];

      const returnedSessionId =
        data?.active_session_id ||
        data?.session?.id ||
        targetSessionId ||
        state.sessions[0]?.id ||
        "default-session";

      setCurrentSessionId(returnedSessionId);
      renderSessions();
      setStatus("Ready", "ok");

      document.dispatchEvent(
        new CustomEvent("nova:sessions-refreshed", {
          detail: {
            session_id: returnedSessionId,
            sessions: state.sessions,
            state: data
          }
        })
      );
    } catch (error) {
      console.error("refreshSessions failed:", error);
      setStatus(`Session load failed: ${error.message || error}`, "error");
    } finally {
      state.loading = false;
    }
  }

  async function switchSession(sessionId) {
    const target = String(sessionId || "").trim();
    if (!target) return;

    setStatus("Switching session...", "muted");
    setCurrentSessionId(target);
    renderSessions();

    try {
      if (window.NovaComposerBundle && typeof window.NovaComposerBundle.restoreSessionState === "function") {
        await window.NovaComposerBundle.restoreSessionState();
      } else {
        await fetchJson(`${API.state}?session_id=${encodeURIComponent(target)}`);
      }

      await refreshSessions(target);

      if (window.NovaArtifacts && typeof window.NovaArtifacts.refresh === "function") {
        await window.NovaArtifacts.refresh({
          reason: "session_switch",
          session_id: target
        });
      }

      document.dispatchEvent(
        new CustomEvent("nova:session-changed", {
          detail: {
            session_id: target
          }
        })
      );

      setStatus("Session switched", "ok");
    } catch (error) {
      console.error("switchSession failed:", error);
      setStatus(`Switch failed: ${error.message || error}`, "error");
    }
  }

  async function createSession() {
    setStatus("Creating session...", "muted");

    try {
      const data = await fetchJson(API.sessionNew, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({})
      });

      const newSessionId =
        data?.session?.id ||
        data?.active_session_id ||
        "default-session";

      await refreshSessions(newSessionId);
      await switchSession(newSessionId);
      setStatus("Session created", "ok");
    } catch (error) {
      console.error("createSession failed:", error);
      setStatus(`Create failed: ${error.message || error}`, "error");
    }
  }

  async function renameCurrentSession() {
    const current = getCurrentSession();
    const currentId = current?.id || getCurrentSessionId();
    if (!currentId) return;

    const nextTitle = window.prompt("Rename session:", current?.title || "New Chat");
    if (nextTitle == null) return;

    const trimmed = String(nextTitle).trim();
    if (!trimmed) return;

    setStatus("Renaming session...", "muted");

    try {
      await fetchJson(API.sessionRename, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          session_id: currentId,
          title: trimmed
        })
      });

      await refreshSessions(currentId);
      renderTopbarFromCurrentSession();
      setStatus("Session renamed", "ok");
    } catch (error) {
      console.error("renameCurrentSession failed:", error);
      setStatus(`Rename failed: ${error.message || error}`, "error");
    }
  }

  async function pinCurrentSession() {
    const current = getCurrentSession();
    const currentId = current?.id || getCurrentSessionId();
    if (!currentId) return;

    try {
      setStatus("Updating pin...", "muted");

      await fetchJson(API.sessionPin, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          session_id: currentId,
          pinned: !current?.pinned
        })
      });

      await refreshSessions(currentId);
      setStatus("Session pin updated", "ok");
    } catch (error) {
      console.error("pinCurrentSession failed:", error);
      setStatus(`Pin failed: ${error.message || error}`, "error");
    }
  }

  async function deleteCurrentSession() {
    const current = getCurrentSession();
    const currentId = current?.id || getCurrentSessionId();
    if (!currentId) return;

    const confirmed = window.confirm("Delete this session?");
    if (!confirmed) return;

    try {
      setStatus("Deleting session...", "muted");

      const data = await fetchJson(API.sessionDelete, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          session_id: currentId
        })
      });

      const nextSessionId =
        data?.next_session_id ||
        data?.active_session_id ||
        "default-session";

      await refreshSessions(nextSessionId);
      await switchSession(nextSessionId);
      setStatus("Session deleted", "ok");
    } catch (error) {
      console.error("deleteCurrentSession failed:", error);
      setStatus(`Delete failed: ${error.message || error}`, "error");
    }
  }

  function bindSessionList() {
    const listEl = getSessionsListEl();
    if (!listEl || listEl.dataset.boundNovaRail === "true") return;

    listEl.dataset.boundNovaRail = "true";

    listEl.addEventListener("click", async function (event) {
      const button = event.target.closest("[data-session-id]");
      if (!button) return;

      const sessionId = button.dataset.sessionId;
      if (!sessionId) return;

      await switchSession(sessionId);
    });
  }

  function bindControls() {
    const newBtn = el("newSessionBtn");
    const renameBtn = el("renameSessionBtn");
    const pinBtn = el("pinSessionBtn");
    const deleteBtn = el("deleteSessionBtn");

    if (newBtn && newBtn.dataset.boundNovaRail !== "true") {
      newBtn.dataset.boundNovaRail = "true";
      newBtn.addEventListener("click", createSession);
    }

    if (renameBtn && renameBtn.dataset.boundNovaRail !== "true") {
      renameBtn.dataset.boundNovaRail = "true";
      renameBtn.addEventListener("click", renameCurrentSession);
    }

    if (pinBtn && pinBtn.dataset.boundNovaRail !== "true") {
      pinBtn.dataset.boundNovaRail = "true";
      pinBtn.addEventListener("click", pinCurrentSession);
    }

    if (deleteBtn && deleteBtn.dataset.boundNovaRail !== "true") {
      deleteBtn.dataset.boundNovaRail = "true";
      deleteBtn.addEventListener("click", deleteCurrentSession);
    }
  }

  async function init() {
    bindSessionList();
    bindControls();
    setCurrentSessionId(getCurrentSessionId());
    await refreshSessions(getCurrentSessionId());
  }

  window.NovaSessionRail = {
    init,
    refreshSessions,
    switchSession,
    createSession,
    renameCurrentSession,
    pinCurrentSession,
    deleteCurrentSession,
    getCurrentSessionId,
    setCurrentSessionId
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();