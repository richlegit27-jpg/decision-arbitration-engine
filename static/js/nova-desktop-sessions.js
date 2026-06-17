(function () {
  "use strict";

  function $(id) {
    return document.getElementById(id);
  }

  function getSessionId() {
    const el = $("sid");
    return (el && el.value ? el.value : "").trim();
  }

  function setSessionId(id) {
    const sid = String(id || "").trim();

    const el = $("sid");
    if (el) el.value = sid;

    try {
      if (sid) {
        localStorage.setItem("nova_session_id", sid);
        localStorage.setItem("nova_active_session_id", sid);
      }
    } catch (e) {}

    return sid;
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, options || {});
    const text = await response.text();

    let data = {};
    try {
      data = JSON.parse(text);
    } catch (error) {
      throw new Error("Non-JSON response from " + url + ": " + text.slice(0, 160));
    }

    if (!response.ok || data.ok === false) {
      throw new Error(data.error || data.message || ("Request failed: " + response.status));
    }

    return data;
  }

  async function openSession(sid) {
    sid = String(sid || "").trim();
    if (!sid) return;

    setSessionId(sid);

    const detail = await fetchJson("/api/sessions/" + encodeURIComponent(sid), {
      cache: "no-store"
    });

    const sessionData = detail.session || detail;

    if (typeof window.renderDesktopChatMessagesRescue === "function") {
      window.renderDesktopChatMessagesRescue(sessionData.messages || []);
    }

    if (typeof window.setStatus === "function") {
      window.setStatus("session selected");
    }

    console.log("[Nova Desktop Sessions External] opened", sid);
  }

  async function loadDesktopSessionsExternal() {
    const list = $("desktopSessionList");
    if (!list) return;

    const data = await fetchJson("/api/sessions", { cache: "no-store" });
    const sessions = data.sessions || data.items || [];

    list.innerHTML = "";

    if (!sessions.length) {
      list.innerHTML = '<div class="session-placeholder">No saved sessions yet.</div>';
      return;
    }

    sessions.slice(0, 30).forEach(session => {
      const sid = session.id || session.session_id;
      if (!sid) return;

      const btn = document.createElement("button");
      btn.type = "button";
      btn.className =
        "desktop-session-item" + (sid === getSessionId() ? " is-active" : "");

      btn.innerHTML = `
        <div class="desktop-session-title">${session.title || "Untitled"}</div>
        <div class="desktop-session-meta">${sid}</div>
      `;

      btn.onclick = () => {
        openSession(sid).catch(error => {
          console.warn("[Nova Desktop Sessions External] open failed", error);
          if (typeof window.setStatus === "function") {
            window.setStatus("session load failed");
          }
        });
      };

      list.appendChild(btn);
    });

    console.log("[Nova Desktop Sessions External] rendered", sessions.length);
  }

  async function newSessionExternal() {
    try {
      const data = await fetchJson("/api/sessions/new", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": window.API_KEY || "dev"
        },
        body: JSON.stringify({ title: "New Chat" })
      });

      const sid = data.active_session_id || data.session_id || (data.session && data.session.id);
      if (sid) setSessionId(sid);

      window.NOVA_FORCE_NEW_SESSION_ON_NEXT_SEND = false;
      window.NOVA_PENDING_NEW_SESSION_ID = "";

      if (typeof window.renderDesktopChatMessagesRescue === "function") {
        window.renderDesktopChatMessagesRescue([]);
      }

      await loadDesktopSessionsExternal();

      if (typeof window.setStatus === "function") {
        window.setStatus("new session ready");
      }

      console.log("[Nova Desktop Sessions External] new session", sid);
    } catch (error) {
      console.warn("[Nova Desktop Sessions External] new session failed", error);
      if (typeof window.setStatus === "function") {
        window.setStatus("new session failed");
      }
    }
  }

  function wireButtons() {
    const sessionsBtn =
      $("desktopSessionsButton") ||
      $("openSessionsBtn") ||
      $("sessionsBtn");

    if (sessionsBtn && sessionsBtn.dataset.novaExternalSessionsBound !== "true") {
      sessionsBtn.dataset.novaExternalSessionsBound = "true";
      sessionsBtn.addEventListener("click", function () {
        loadDesktopSessionsExternal();
      }, true);
    }

    const newBtn = $("newSessionBtn");
    if (newBtn && newBtn.dataset.novaExternalNewSessionBound !== "true") {
      newBtn.dataset.novaExternalNewSessionBound = "true";
      newBtn.onclick = function (event) {
        event.preventDefault();
        event.stopPropagation();
        newSessionExternal();
      };
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

  console.log("[Nova Desktop Sessions External] ready");
})();