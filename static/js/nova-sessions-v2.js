(function () {
  "use strict";

  const LS_SID = "nova.session_id";

  function $(id) {
    return document.getElementById(id);
  }

  function setStatus(text) {
    const el = $("status");
    if (el) el.textContent = "status: " + text;
  }

  function setSessionId(id) {
    const sid = String(id || "").trim();
    if (!sid) return;

    const input = $("sid");
    if (input) input.value = sid;

    localStorage.setItem(LS_SID, sid);
    localStorage.setItem("nova_active_session_id", sid);
    localStorage.setItem("nova_session_id", sid);

    window.__NOVA_ACTIVE_SESSION_ID = sid;
  }

  function getSessionId(session) {
    return (
      session?.id ||
      session?.session_id ||
      session?.client_session_id ||
      ""
    );
  }

  function getSessionTitle(session) {
    return (
      session?.title ||
      session?.name ||
      session?.summary ||
      session?.last_message ||
      session?.preview ||
      getSessionId(session) ||
      "Untitled"
    );
  }

  async function loadSessions() {
    const list = $("desktopSessionList");
    if (!list) return;

    list.innerHTML = "<div class='session-placeholder'>Loading sessions...</div>";

    try {
      const res = await fetch("/api/sessions", { cache: "no-store" });
      const data = await res.json();

      const sessions =
        data.sessions ||
        data.items ||
        data.data ||
        [];

      list.innerHTML = "";

      if (!sessions.length) {
        list.innerHTML = "<div class='session-placeholder'>No saved sessions yet.</div>";
        return;
      }

      sessions.slice(0, 30).forEach((session) => {
        const sid = getSessionId(session);
        if (!sid) return;

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "desktop-session-item";

        const title = document.createElement("div");
        title.className = "desktop-session-title";
        title.textContent = getSessionTitle(session);

        const meta = document.createElement("div");
        meta.className = "desktop-session-meta";
        meta.textContent = sid;

        btn.appendChild(title);
        btn.appendChild(meta);

        btn.onclick = async () => {
          setSessionId(sid);
          setStatus("loading session...");

          if (typeof window.NovaDesktopFetchSession === "function") {
            await window.NovaDesktopFetchSession(sid);
          }

          setStatus("session selected");
        };

        list.appendChild(btn);
      });

      console.log("[NOVA Sessions V2] loaded", sessions.length);

    } catch (error) {
      console.warn("[NOVA Sessions V2] failed", error);
      list.innerHTML = "<div class='session-placeholder'>Could not load sessions.</div>";
      setStatus("sessions failed");
    }
  }

  async function newSession() {
    try {
      const res = await fetch("/api/sessions/new", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": "testkey123"
        },
        body: JSON.stringify({ title: "New Chat" })
      });

      const data = await res.json();

      const sid =
        data.active_session_id ||
        data.session_id ||
        data.session?.id;

      if (sid) setSessionId(sid);

      const chat = $("chat");
      if (chat) {
        chat.innerHTML =
          "<div class='msg assistant'><div class='role'>assistant</div><div class='bubble'>Nova is ready. Send a message to begin.</div></div>";
      }

      await loadSessions();
      setStatus("new session ready");

    } catch (error) {
      console.warn("[NOVA Sessions V2] new session failed", error);
      setStatus("new session failed");
    }
  }

  function bindSessions() {
    const newBtn = $("newSessionBtn");
    const openBtn = $("openSessionsBtn");

    if (newBtn) newBtn.onclick = newSession;
    if (openBtn) openBtn.onclick = loadSessions;

    loadSessions();
  }

  function boot() {
    bindSessions();
    console.log("[NOVA Sessions V2] ready");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.NovaLoadSessionsV2 = loadSessions;
  window.NovaNewSessionV2 = newSession;
})();

