(function () {
  "use strict";

  const API = {
    list: "/api/sessions",
    create: "/api/sessions/new",
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
    if (els.status) els.status.textContent = text || "";
  }

  async function api(url, options) {
    const response = await fetch(url, {
      method: options?.method || "GET",
      headers: {
        "Content-Type": "application/json",
      },
      body: options?.body ? JSON.stringify(options.body) : undefined,
      cache: "no-store",
    });

    const payload = await response.json().catch(() => ({}));

    if (!response.ok || payload.ok === false) {
      throw new Error(payload.error || "Request failed");
    }

    return payload;
  }

  function normalizeSession(session) {
    if (!session) return null;

    return {
      id: String(session.id || ""),
      title: String(session.title || "New Chat"),
      pinned: !!session.pinned,
      updated_at: session.updated_at || "",
      created_at: session.created_at || "",
      message_count: Number(session.message_count || 0),
    };
  }

  function applyBackendState(payload, explicitActiveSessionId) {
    const data = payload || {};

    const incoming = Array.isArray(data.sessions)
      ? data.sessions.map(normalizeSession).filter(Boolean)
      : [];

    state.sessions = incoming;

    const backendActive =
      data.active_session_id ||
      (data.session && data.session.id) ||
      "";

    let preferred =
      explicitActiveSessionId ||
      backendActive ||
      state.activeSessionId ||
      (state.sessions[0] && state.sessions[0].id) ||
      "";

    state.activeSessionId = preferred;

    render();
    bindEls();
    wireNewButton();
    wireList();

    // ✅ ONLY WRITE (NO DELETE)
    try {
      if (state.activeSessionId) {
        localStorage.setItem(
          "nova_active_session_id",
          state.activeSessionId
        );
      }
    } catch {}

    document.dispatchEvent(
      new CustomEvent("nova:sessions-changed", {
        detail: {
          activeSessionId: state.activeSessionId,
          sessions: state.sessions,
        },
      })
    );
  }

  async function reloadFromBackend(preferred) {
    state.loading = true;

    try {
      const payload = await api(API.list);
      applyBackendState(payload, preferred);
      return payload;
    } finally {
      state.loading = false;
    }
  }

  async function createSession() {
    const payload = await api(API.create, {
      method: "POST",
      body: {},
    });

    return reloadFromBackend(payload?.session?.id || "");
  }

  async function selectSession(sessionId) {
    const payload = await api(API.switch, {
      method: "POST",
      body: { session_id: sessionId },
    });

    const resolved =
      payload?.active_session_id ||
      payload?.session?.id ||
      sessionId;

    state.activeSessionId = resolved;

    return reloadFromBackend(resolved);
  }

  function render() {
    bindEls();
    if (!els.list) return;

    const sessions = [...state.sessions].sort((a, b) => {
      if (!!a.pinned !== !!b.pinned) return a.pinned ? -1 : 1;
      return String(b.updated_at || "").localeCompare(
        String(a.updated_at || "")
      );
    });

    els.list.innerHTML = sessions
      .map((s) => {
        const active = s.id === state.activeSessionId;

        return `
          <div class="session ${active ? "active" : ""}">
            <button data-id="${s.id}" class="session-btn">
              ${escapeHtml(s.title)}
            </button>
          </div>
        `;
      })
      .join("");

    els.list.querySelectorAll(".session-btn").forEach((btn) => {
      btn.onclick = () => selectSession(btn.dataset.id);
    });
  }

  function wireNewButton() {
    if (!els.newBtn) return;

    // NOVA_SESSION_RAIL_NEW_BUTTON_OWNER_DISABLED_20260716
els.newBtn.onclick = null;
  }

  function wireList() {
    if (!els.list) return;
  }

  async function boot() {
    bindEls();
    wireNewButton();
    wireList();

    const preferred =
      localStorage.getItem("nova_active_session_id") || "";

    await reloadFromBackend(preferred);
  }

  window.NovaSessionRail = {
    init: boot,
    reloadFromBackend,
    selectSession,
    createSession,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();