(function () {
  "use strict";

function $(id) {
  return document.getElementById(id);
}

// 👇 ADD THIS RIGHT HERE (GLOBAL STATE)
window.__NOVA_SESSION_STATE = {
  activeSid: null,
  currentRequest: null
};

  function getSessionId() {
    const el = $("sid");
return (
  (el && el.value) ||
  localStorage.getItem("nova_active_session_id") ||
  localStorage.getItem("nova_session_id") ||
  ""
).trim();
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

  const state = window.__NOVA_SESSION_STATE;

  // cancel previous request if still running
  if (state.currentRequest && state.currentRequest.abort) {
    try { state.currentRequest.abort(); } catch (e) {}
  }

  const controller = new AbortController();
  state.currentRequest = controller;
  state.activeSid = sid;

  setSessionId(sid);

  try {
    const detail = await fetchJson(
      "/api/sessions/" + encodeURIComponent(sid),
      {
        cache: "no-store",
        signal: controller.signal
      }
    );

    const session = detail.session || detail;

    window.renderDesktopChatMessagesRescue?.(session.messages || []);

    window.setStatus?.("session selected");

    console.log("[Session] opened:", sid);

  } catch (e) {
    if (e.name === "AbortError") {
      console.log("[Session] aborted:", sid);
      return;
    }

    console.warn("[Session] open failed", e);
    window.setStatus?.("session load failed");
  }
}

async function loadDesktopSessionsExternal() {
  const list = $("desktopSessionList");
  if (!list) return;

  const data = await fetchJson("/api/sessions", { cache: "no-store" });
  const sessions = data.sessions || data.items || [];

  list.innerHTML = "";

  if (!sessions.length) {
    list.innerHTML =
      '<div class="session-placeholder">No saved sessions yet.</div>';
    return;
  }

  const active = getSessionId();

  sessions.slice(0, 30).forEach(session => {
    const sid = session.id || session.session_id;
    if (!sid) return;

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className =
      "desktop-session-item" + (sid === active ? " is-active" : "");

    btn.innerHTML = `
      <div class="desktop-session-title">${session.title || "Untitled"}</div>
      <div class="desktop-session-meta">${sid}</div>
    `;

btn.onclick = () => {
  openSession(sid);
};

list.appendChild(btn);
  });

  console.log("[Nova Sessions External] rendered", sessions.length);
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

    const sid =
      data.active_session_id ||
      data.session_id ||
      (data.session && data.session.id);

    if (sid) {
      setSessionId(sid);
    }

    window.NOVA_FORCE_NEW_SESSION_ON_NEXT_SEND = false;
    window.NOVA_PENDING_NEW_SESSION_ID = "";

    // IMPORTANT: reset UI AFTER session is confirmed
    if (typeof window.renderDesktopChatMessagesRescue === "function") {
      window.renderDesktopChatMessagesRescue([]);
    }

    await loadDesktopSessionsExternal();

    window.setStatus?.("new session ready");

    console.log("[Nova Desktop Sessions External] new session", sid);

  } catch (error) {
    console.warn("[Nova Desktop Sessions External] new session failed", error);
    window.setStatus?.("new session failed");
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