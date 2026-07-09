(function () {
  "use strict";

  const API_BASE = "/api/sessions";

  // =========================
  // STATE
  // =========================
  const state = {
    activeSid: null,
    currentRequest: null
  };

  function $(id) {
    return document.getElementById(id);
  }

  function setStatus(text) {
    const el = $("status");
    if (el) el.textContent = "status: " + text;
  }

  function setSessionId(sid) {
    sid = String(sid || "").trim();
    if (!sid) return;

    const input = $("sid");
    if (input) input.value = sid;

    localStorage.setItem("nova_session_id", sid);
    localStorage.setItem("nova_active_session_id", sid);

    state.activeSid = sid;
    window.__NOVA_ACTIVE_SESSION_ID = sid;
  }

  // =========================
  // FETCH HELPERS
  // =========================
  async function fetchJson(url, options = {}) {
    const res = await fetch(url, {
      cache: "no-store",
      headers: { "Accept": "application/json" },
      ...options
    });

    const text = await res.text();

    let data;
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error("Invalid JSON: " + text.slice(0, 120));
    }

    if (!res.ok) {
      throw new Error(data.error || data.message || "Request failed");
    }

    return data;
  }

  // =========================
  // RENDER SESSION
  // =========================
  function getBox() {
    return $("chat") || $("messages") || $("desktopMessages");
  }

  function getMessages(session) {
    return session?.messages || session?.items || [];
  }

  function getText(m) {
    return (
      m?.text ||
      m?.content ||
      m?.assistant_message?.text ||
      m?.user_message?.text ||
      ""
    );
  }

  function getRole(m) {
    return m?.role || "message";
  }

  function renderSession(session) {
    const box = getBox();
    if (!box) return 0;

    const messages = getMessages(session);

    box.innerHTML = "";

    if (!messages.length) {
      box.innerHTML = "<div class='session-placeholder'>Empty session</div>";
      return 0;
    }

    for (const m of messages) {
      const node = document.createElement("div");
      node.className = "msg " + getRole(m);

      const bubble = document.createElement("div");
      bubble.className = "bubble";
      bubble.textContent = getText(m);

      node.appendChild(bubble);
      box.appendChild(node);
    }

    box.scrollTop = box.scrollHeight;
    return messages.length;
  }

  // =========================
  // OPEN SESSION (CORE FIX)
  // =========================
  async function openSession(sid) {
    sid = String(sid || "").trim();
    if (!sid) return;

    // abort previous
    if (state.currentRequest?.abort) {
      try { state.currentRequest.abort(); } catch {}
    }

    const controller = new AbortController();
    state.currentRequest = controller;

    setSessionId(sid);
    setStatus("loading session");

    try {
      const data = await fetchJson(`${API_BASE}/${encodeURIComponent(sid)}`, {
        signal: controller.signal
      });

      const session = data.session || data;

      renderSession(session);

      setStatus("session loaded");

      console.log("[Sessions Clean] opened", sid);
    } catch (e) {
      if (e.name === "AbortError") return;

      console.warn("[Sessions Clean] failed", e);
      setStatus("session failed");
    }
  }

  // =========================
  // LOAD LIST
  // =========================
  async function loadSessions() {
    const list = $("desktopSessionList");
    if (!list) return;

    const data = await fetchJson(API_BASE);

    const sessions = data.sessions || [];

    list.innerHTML = "";

    if (!sessions.length) {
      list.innerHTML = "<div class='session-placeholder'>No sessions</div>";
      return;
    }

    const active = state.activeSid || localStorage.getItem("nova_active_session_id");

    sessions.slice(0, 30).forEach(s => {
      const sid = s.id || s.session_id;
      if (!sid) return;

      const btn = document.createElement("button");
      btn.className = "desktop-session-item" + (sid === active ? " is-active" : "");
      btn.type = "button";

      btn.innerHTML = `
        <div class="desktop-session-title">${s.title || "Untitled"}</div>
        <div class="desktop-session-meta">${sid}</div>
      `;

      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();

        openSession(sid);
      }, true);

      list.appendChild(btn);
    });

    console.log("[Sessions Clean] loaded", sessions.length);
  }

  // =========================
  // NEW SESSION
  // =========================
  async function newSession() {
    try {
      const data = await fetchJson(`${API_BASE}/new`, {
        method: "POST",
        body: JSON.stringify({ title: "New Chat" })
      });

      const sid = data.session_id || data.active_session_id || data.session?.id;

      if (sid) {
        setSessionId(sid);
        renderSession({ messages: [] });
      }

      await loadSessions();

      setStatus("new session ready");
    } catch (e) {
      console.warn("[Sessions Clean] new failed", e);
      setStatus("new session failed");
    }
  }

  // =========================
  // BOOTSTRAP (NO DEPENDENCIES)
  // =========================
  function boot() {
    const sessionsBtn = $("desktopSessionsButton");
    const newBtn = $("newSessionBtn");

    if (sessionsBtn) {
      sessionsBtn.addEventListener("click", loadSessions, true);
    }

    if (newBtn) {
      newBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        newSession();
      }, true);
    }

    console.log("[Sessions Clean] ready");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  // =========================
  // GLOBAL EXPORT (IMPORTANT)
  // =========================
  window.NovaOpenSession = openSession;
  window.NovaLoadSessions = loadSessions;
  window.NovaNewSession = newSession;

})();

