(function () {
  "use strict";

function $(id) {
  return document.getElementById(id);
}

// ðŸ‘‡ ADD THIS RIGHT HERE (GLOBAL STATE)
window.__NOVA_SESSION_STATE = {
  activeSid: null,
  currentRequest: null
};

function getSessionId() {
  const el = $("sid");

  let value = "";

  if (el && typeof el === "object" && "value" in el) {
    value = el.value;
  }

  if (!value) {
    value = localStorage.getItem("nova_active_session_id") || "";
  }

  if (!value) {
    value = localStorage.getItem("nova.session_id") || "";
  }

  if (!value) {
    value = localStorage.getItem("nova_session_id") || "";
  }

  return String(value || "").trim();
}

function setSessionId(id) {
  let sid = "";

  if (typeof id === "string") {
    sid = id.trim();
  } else if (id && typeof id === "object" && "value" in id) {
    sid = String(id.value || "").trim();
  }

  if (!sid || sid === "[object HTMLInputElement]") {
    return "";
  }

  const el = $("sid");
  if (el && "value" in el) {
    el.value = sid;
  }

  try {
    localStorage.setItem("nova_session_id", sid);
    localStorage.setItem("nova_active_session_id", sid);
    localStorage.setItem("nova.session_id", sid);
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

  if (response.status === 404 && url.includes("/api/sessions/")) {
    try {
      localStorage.removeItem("nova.session_id");
      localStorage.removeItem("nova_session_id");
      localStorage.removeItem("nova_active_session_id");
      sessionStorage.removeItem("nova_session_id");
      sessionStorage.removeItem("nova_active_session_id");
    } catch (e) {}
  }

  throw new Error(
    data.error ||
    data.message ||
    ("Request failed: " + response.status)
  );
}

    return data;
  }

async function openSession(sessionId) {
  let sid = "";

  if (typeof sessionId === "string") {
    sid = sessionId.trim();
  } else if (sessionId && typeof sessionId === "object" && "value" in sessionId) {
    sid = String(sessionId.value || "").trim();
  }

  if (!sid || sid === "[object HTMLInputElement]") {
    console.warn(
      "[Nova Desktop Sessions External] rejected invalid session id",
      sessionId
    );
    return;
  }

  console.log("[Nova Desktop Sessions External] open session", sid);

  window.setStatus?.("loading session...");

  try {
    try {
      localStorage.setItem("nova.session_id", sid);
      localStorage.setItem("nova_session_id", sid);
      localStorage.setItem("nova_active_session_id", sid);
      sessionStorage.setItem("nova_session_id", sid);
      sessionStorage.setItem("nova_active_session_id", sid);

      window.__NOVA_ACTIVE_SESSION_ID = sid;
      window.currentSessionId = sid;
      window.activeSessionId = sid;
      window.novaCurrentSessionId = sid;
    } catch (e) {}

    if (typeof window.NovaDesktopFetchSession === "function") {
      await window.NovaDesktopFetchSession(sid);
    } else {
      const data = await fetchJson(
        "/api/sessions/" + encodeURIComponent(sid),
        {
          cache: "no-store"
        }
      );

      const session = data.session || data;

      if (session && Array.isArray(session.messages)) {
        if (typeof window.renderDesktopChatMessages === "function") {
          window.renderDesktopChatMessages(session.messages);
        } else if (
          typeof window.renderDesktopChatMessagesRescue === "function"
        ) {
          window.renderDesktopChatMessagesRescue(session.messages);
        }
      }
    }

    document.querySelectorAll(".desktop-session-item").forEach(function (item) {
      item.classList.toggle(
        "is-active",
        item.dataset.sessionId === sid
      );
    });

    window.setStatus?.("session selected");

  } catch (error) {
    console.warn(
      "[Nova Desktop Sessions External] open session failed",
      error
    );
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

    const btn = document.createElement("div");
    btn.className = "desktop-session-item" + (sid === active ? " is-active" : "");
    btn.dataset.sessionId = sid;

btn.setAttribute("role", "button");
btn.tabIndex = 0;

btn.addEventListener("mouseenter", function () {
  const actions = btn.querySelector(".desktop-session-actions");
  if (actions) actions.style.display = "flex";
});

btn.addEventListener("mouseleave", function () {
  const actions = btn.querySelector(".desktop-session-actions");
  if (actions) actions.style.display = "none";
});

    btn.innerHTML = `
      <div class="desktop-session-title">
        ${session.title || "Untitled"}
      </div>

      <div class="desktop-session-meta">
        ${sid}
      </div>

      <div class="desktop-session-actions" style="display:none;">
        <button type="button" data-action="rename">Rename</button>
        <button type="button" data-action="pin">
          ${session.pinned ? "Unpin" : "Pin"}
        </button>
        <button type="button" data-action="delete">Delete</button>
      </div>
    `;

btn.onclick = (event) => {
  if (event.target.closest("[data-action]")) {
    return;
  }

  openSession(sid);
};

    btn.querySelector('[data-action="rename"]').onclick = async (event) => {
      event.stopPropagation();

      const title = prompt(
        "Rename session:",
        session.title || "Untitled"
      );

      if (!title || !title.trim()) return;

      await fetch("/api/sessions/rename", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          session_id: sid,
          title: title.trim()
        })
      });

      await loadDesktopSessionsExternal();
    };


    btn.querySelector('[data-action="pin"]').onclick = async (event) => {
      event.stopPropagation();

      await fetch("/api/sessions/pin", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          session_id: sid,
          pinned: !session.pinned
        })
      });

      await loadDesktopSessionsExternal();
    };


    btn.querySelector('[data-action="delete"]').onclick = async (event) => {
      event.stopPropagation();

      if (!confirm("Delete this session?")) {
        return;
      }

const response = await fetch("/api/sessions/delete", {
  method: "POST",
  headers: {
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    session_id: sid
  })
});

if (!response.ok) {
  console.warn("delete failed", await response.text());
  return;
}

await loadDesktopSessionsExternal();

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

