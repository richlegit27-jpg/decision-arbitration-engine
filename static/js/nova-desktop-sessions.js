(function () {
  "use strict";

  async function loadDesktopSessionsExternal() {
    const list = document.getElementById("desktopSessionList");
    if (!list) return;

    const data = await fetch("/api/sessions", { cache: "no-store" }).then(r => r.json());
    const sessions = data.sessions || data.items || [];

    list.innerHTML = "";

    sessions.slice(0, 20).forEach(session => {
      const sid = session.id;
      if (!sid) return;

      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "desktop-session-item";
      btn.innerHTML = `
        <div class="desktop-session-title">${session.title || "Untitled"}</div>
        <div class="desktop-session-meta">${sid}</div>
      `;

      btn.onclick = async () => {
        if (typeof setSessionId === "function") setSessionId(sid);

        const detail = await fetch("/api/sessions/" + encodeURIComponent(sid), {
          cache: "no-store"
        }).then(r => r.json());

        const sessionData = detail.session || detail;

        if (typeof window.renderDesktopChatMessagesRescue === "function") {
          window.renderDesktopChatMessagesRescue(sessionData.messages || []);
        }
      };

      list.appendChild(btn);
    });

    console.log("[Nova Desktop Sessions External] rendered", sessions.length);
  }

  window.loadDesktopSessions = loadDesktopSessionsExternal;

  console.log("[Nova Desktop Sessions External] ready");
})();