(() => {
  "use strict";

  const PANELS_VERSION = "session-rail-2026-03-31-001";

  function qs(selector, root = document) {
    return root.querySelector(selector);
  }

  function formatWhen(value) {
    if (!value) return "";
    try {
      const d = new Date(value);
      if (Number.isNaN(d.getTime())) return "";
      return d.toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
    } catch (_err) {
      return "";
    }
  }

  function text(value) {
    if (value == null) return "";
    return String(value).replace(/\r\n/g, "\n").trim();
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  const NovaPanels = {
    version: PANELS_VERSION,

    getSessionListEl() {
      return qs("#sessionList");
    },

    getActiveSessionChipEl() {
      return qs("#activeSessionChip");
    },

    setActiveSessionChip(sessionId, title = "") {
      const el = this.getActiveSessionChipEl();
      if (!el) return;
      const shownTitle = text(title) || "New Chat";
      const shortId = text(sessionId).slice(0, 8) || "none";
      el.textContent = `Session: ${shownTitle} · ${shortId}`;
    },

    renderSessionList(sessions, activeSessionId) {
      const el = this.getSessionListEl();
      if (!el) return;

      const items = Array.isArray(sessions) ? sessions.slice() : [];
      items.sort((a, b) => {
        const aTime = Date.parse(a?.updated_at || a?.created_at || 0) || 0;
        const bTime = Date.parse(b?.updated_at || b?.created_at || 0) || 0;
        return bTime - aTime;
      });

      if (!items.length) {
        el.innerHTML = `<div class="nova-session-empty">No sessions yet.</div>`;
        this.setActiveSessionChip(activeSessionId || "", "New Chat");
        return;
      }

      el.innerHTML = items.map((session) => {
        const id = text(session?.id);
        const title = text(session?.title) || "New Chat";
        const updated = formatWhen(session?.updated_at || session?.created_at || "");
        const preview = text(session?.last_message_preview || "");
        const count = Number(session?.message_count || 0);
        const isActive = id === activeSessionId;

        return `
          <button
            type="button"
            class="nova-session-card${isActive ? " is-active" : ""}"
            data-session-id="${escapeHtml(id)}"
            title="${escapeHtml(title)}"
          >
            <div class="nova-session-title">${escapeHtml(title)}</div>
            <div class="nova-session-meta">${escapeHtml(updated)} · ${escapeHtml(String(count))} messages</div>
            <div class="nova-session-preview">${escapeHtml(preview || "No preview yet.")}</div>
          </button>
        `;
      }).join("");

      const active = items.find((item) => text(item?.id) === text(activeSessionId)) || items[0];
      this.setActiveSessionChip(text(active?.id), text(active?.title));
    },

    bindSessionClicks(onSelect) {
      const el = this.getSessionListEl();
      if (!el) return;

      el.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-session-id]");
        if (!btn) return;
        const sessionId = text(btn.getAttribute("data-session-id"));
        if (!sessionId) return;
        if (typeof onSelect === "function") {
          onSelect(sessionId);
        }
      });
    },

    bindToolbar({ onNewChat, onRefresh }) {
      const newBtn = qs("#newChatBtn");
      const refreshBtn = qs("#refreshSessionsBtn");

      if (newBtn) {
        newBtn.addEventListener("click", () => {
          if (typeof onNewChat === "function") {
            onNewChat();
          }
        });
      }

      if (refreshBtn) {
        refreshBtn.addEventListener("click", () => {
          if (typeof onRefresh === "function") {
            onRefresh();
          }
        });
      }
    },

    init() {
      window.NovaPanels = this;
      console.log("nova-panels loaded", PANELS_VERSION);
      return this;
    },
  };

  NovaPanels.init();
})();