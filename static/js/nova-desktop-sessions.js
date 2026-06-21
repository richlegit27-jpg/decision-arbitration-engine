(function () {
  "use strict";

  function $(id) {
    return document.getElementById(id);
  }

  const state = window.__NOVA_SESSION_STATE || {};
  window.__NOVA_SESSION_STATE = Object.assign(
    {
      activeSid: null,
      currentRequest: null,
      sessions: []
    },
    state
  );

  function text(value, fallback) {
    const out = String(value || "").trim();
    return out || fallback || "";
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function getSessionIdFromObject(session) {
    return text(
      session &&
        (
          session.id ||
          session.session_id ||
          session.sid ||
          session.uuid
        ),
      ""
    );
  }

  function getSessionTitle(session) {
    return text(
      session &&
        (
          session.title ||
          session.name ||
          session.label ||
          session.summary ||
          session.preview
        ),
      "Untitled"
    );
  }

  function getSessionPreview(session) {
    return text(
      session &&
        (
          session.preview ||
          session.last_message ||
          session.lastMessage ||
          session.description ||
          session.subtitle
        ),
      ""
    );
  }

  function getSessionTime(session) {
    return text(
      session &&
        (
          session.updated_at ||
          session.updated ||
          session.created_at ||
          session.created
        ),
      ""
    );
  }

  function sortSessions(sessions) {
    return sessions.slice().sort(function (a, b) {
      if (!!a.pinned !== !!b.pinned) return a.pinned ? -1 : 1;

      const bt = getSessionTime(b);
      const at = getSessionTime(a);

      return String(bt).localeCompare(String(at));
    });
  }

  function getSessionId() {
    const el = $("sid");

    return text(
      (el && el.value) ||
        localStorage.getItem("nova_active_session_id") ||
        localStorage.getItem("nova_session_id"),
      ""
    );
  }

  function setSessionId(id) {
    const sid = text(id, "");

    const el = $("sid");
    if (el) el.value = sid;

    try {
      if (sid) {
        localStorage.setItem("nova_session_id", sid);
        localStorage.setItem("nova_active_session_id", sid);
      }
    } catch (e) {}

    window.__NOVA_SESSION_STATE.activeSid = sid;

    return sid;
  }

  function setStatus(message) {
    if (typeof window.setStatus === "function") {
      window.setStatus(message);
    }
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, options || {});
    const raw = await response.text();

    let data = {};
    try {
      data = raw ? JSON.parse(raw) : {};
    } catch (error) {
      throw new Error("Non-JSON response from " + url + ": " + raw.slice(0, 180));
    }

    if (!response.ok || data.ok === false) {
      throw new Error(data.error || data.message || ("Request failed: " + response.status));
    }

    return data;
  }

  function markActiveSession(sid) {
    const list = $("desktopSessionList");
    if (!list) return;

    Array.from(list.querySelectorAll(".desktop-session-item")).forEach(function (item) {
      const isActive = item.getAttribute("data-nova-session-key") === sid;
      item.classList.toggle("is-active", isActive);
      item.setAttribute("aria-current", isActive ? "true" : "false");
    });
  }

  function renderSessionMessages(session) {
    const messages =
      (session && Array.isArray(session.messages) && session.messages) ||
      (session && Array.isArray(session.chat_messages) && session.chat_messages) ||
      [];

    if (typeof window.renderDesktopChatMessagesRescue === "function") {
      window.renderDesktopChatMessagesRescue(messages);
      return;
    }

    console.warn("[Nova Desktop Sessions] no renderer found for opened session");
  }

  async function openSession(sid) {
    sid = text(sid, "");
    if (!sid) return;

    const sessionState = window.__NOVA_SESSION_STATE;

    if (sessionState.currentRequest && sessionState.currentRequest.abort) {
      try {
        sessionState.currentRequest.abort();
      } catch (e) {}
    }

    const controller = new AbortController();
    sessionState.currentRequest = controller;

    setSessionId(sid);
    markActiveSession(sid);
    setStatus("loading session...");

    try {
      const detail = await fetchJson(
        "/api/sessions/" + encodeURIComponent(sid),
        {
          cache: "no-store",
          signal: controller.signal
        }
      );

      const session = detail.session || detail;

      renderSessionMessages(session);

      setStatus("session selected");
      console.log("[Nova Desktop Sessions] opened", sid);
    } catch (error) {
      if (error && error.name === "AbortError") {
        return;
      }

      console.warn("[Nova Desktop Sessions] open failed", error);
      setStatus("session load failed");
    } finally {
      if (sessionState.currentRequest === controller) {
        sessionState.currentRequest = null;
      }
    }
  }

  function renderSessions(list, sessions) {
    const active = getSessionId();
    const sorted = sortSessions(sessions);

    window.__NOVA_SESSION_STATE.sessions = sorted;

    list.innerHTML = "";

    if (!sorted.length) {
      list.innerHTML = '<div class="session-placeholder">No saved sessions yet.</div>';
      return;
    }

    sorted.slice(0, 40).forEach(function (session) {
      const sid = getSessionIdFromObject(session);
      if (!sid) return;

      const title = getSessionTitle(session);
      const preview = getSessionPreview(session);
      const when = getSessionTime(session);

      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "desktop-session-item" + (sid === active ? " is-active" : "");
      btn.setAttribute("data-nova-session-key", sid);
      btn.setAttribute("aria-current", sid === active ? "true" : "false");
      btn.title = title;

      btn.innerHTML =
        '<div class="desktop-session-title">' + escapeHtml(title) + '</div>' +
        (preview
          ? '<div class="desktop-session-preview">' + escapeHtml(preview) + '</div>'
          : '') +
        (when
          ? '<div class="desktop-session-meta">' + escapeHtml(when) + '</div>'
          : '');

      btn.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        openSession(sid);
      });

      list.appendChild(btn);
    });
  }

  async function loadDesktopSessionsExternal() {
    const list = $("desktopSessionList");
    if (!list) return;

    list.innerHTML = '<div class="session-placeholder">Loading sessions...</div>';

    try {
      const data = await fetchJson("/api/sessions", { cache: "no-store" });
      const sessions =
        data.sessions ||
        data.items ||
        data.data ||
        [];

      renderSessions(list, Array.isArray(sessions) ? sessions : []);

      console.log("[Nova Desktop Sessions] loaded", Array.isArray(sessions) ? sessions.length : 0);
    } catch (error) {
      console.warn("[Nova Desktop Sessions] load failed", error);
      list.innerHTML = '<div class="session-placeholder">Could not load sessions.</div>';
      setStatus("sessions failed");
    }
  }

  async function newSessionExternal() {
    try {
      setStatus("creating session...");

      const data = await fetchJson("/api/sessions/new", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": window.API_KEY || "dev"
        },
        body: JSON.stringify({ title: "New Chat" })
      });

      const sid =
        data.active_session_id ||
        data.session_id ||
        (data.session && data.session.id);

      if (sid) {
        setSessionId(sid);
      }

      window.NOVA_FORCE_NEW_SESSION_ON_NEXT_SEND = false;
      window.NOVA_PENDING_NEW_SESSION_ID = "";

      if (typeof window.renderDesktopChatMessagesRescue === "function") {
        window.renderDesktopChatMessagesRescue([]);
      }

      await loadDesktopSessionsExternal();

      if (sid) {
        markActiveSession(sid);
      }

      setStatus("new session ready");
      console.log("[Nova Desktop Sessions] new session", sid);
    } catch (error) {
      console.warn("[Nova Desktop Sessions] new session failed", error);
      setStatus("new session failed");
    }
  }

  function wireButtons() {
    const sessionsBtn =
      $("desktopSessionsButton") ||
      $("openSessionsBtn") ||
      $("sessionsBtn");

    if (sessionsBtn && sessionsBtn.dataset.novaExternalSessionsBound !== "true") {
      sessionsBtn.dataset.novaExternalSessionsBound = "true";
      sessionsBtn.addEventListener(
        "click",
        function () {
          loadDesktopSessionsExternal();
        },
        true
      );
    }

    const newBtn = $("newSessionBtn");
    if (newBtn && newBtn.dataset.novaExternalNewSessionBound !== "true") {
      newBtn.dataset.novaExternalNewSessionBound = "true";
      newBtn.addEventListener(
        "click",
        function (event) {
          event.preventDefault();
          event.stopPropagation();
          newSessionExternal();
        },
        true
      );
    }
  }

  window.getSessionId = window.getSessionId || getSessionId;
  window.setSessionId = window.setSessionId || setSessionId;
  window.NovaDesktopOpenSession = openSession;
  window.loadDesktopSessions = loadDesktopSessionsExternal;
  window.NovaDesktopLoadSessions = loadDesktopSessionsExternal;
  window.newSession = newSessionExternal;
  window.NovaDesktopNewSession = newSessionExternal;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wireButtons);
  } else {
    wireButtons();
  }

  setTimeout(wireButtons, 500);
  setTimeout(wireButtons, 1500);

  console.log("[Nova Desktop Sessions] ready");
})();
