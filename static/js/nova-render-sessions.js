(() => {
  "use strict";

  if (window.__novaRenderSessionsLoaded) {
    console.warn("Nova render sessions already loaded. Skipping duplicate module.");
    return;
  }
  window.__novaRenderSessionsLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  const state = (Nova.state = Nova.state || {});
  const dom = (Nova.dom = Nova.dom || {});
  const render = (Nova.render = Nova.render || {});
  const util = (Nova.util = Nova.util || {});
  const sessionsApi = (Nova.sessions = Nova.sessions || {});

  function byId(id) {
    return document.getElementById(id);
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function asString(value, fallback = "") {
    return typeof value === "string" ? value : fallback;
  }

  function escapeHtml(value) {
    if (typeof util.escapeHtml === "function") {
      return util.escapeHtml(value);
    }

    return String(value == null ? "" : value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function extractMessageText(message) {
    if (typeof util.extractMessageText === "function") {
      return util.extractMessageText(message);
    }

    if (!message) return "";
    if (typeof message.content === "string") return message.content;
    if (typeof message.text === "string") return message.text;

    if (Array.isArray(message.content)) {
      return message.content
        .map((part) => {
          if (typeof part === "string") return part;
          if (part && typeof part.text === "string") return part.text;
          if (part && typeof part.content === "string") return part.content;
          return "";
        })
        .filter(Boolean)
        .join("\n");
    }

    return "";
  }

  function formatDateLoose(value) {
    if (typeof util.formatDateLoose === "function") {
      return util.formatDateLoose(value);
    }

    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    try {
      return date.toLocaleString();
    } catch (_) {
      return "";
    }
  }

  function cacheDom() {
    dom.sessionList = dom.sessionList || byId("sessionList");
    return dom;
  }

  function sessionPreviewText(session) {
    const preview = asString(session?.preview, "").trim();
    if (preview) return preview.slice(0, 140);

    const messages = asArray(session?.messages);
    if (!messages.length) return "";

    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const text = extractMessageText(messages[i]).trim();
      if (text) return text.slice(0, 140);
    }

    return "";
  }

  function sortedSessions() {
    const pinnedIds = state.pinnedSessionIds instanceof Set ? state.pinnedSessionIds : new Set();

    return [...asArray(state.sessions)].sort((a, b) => {
      const aPinned = pinnedIds.has(a?.id) ? 1 : 0;
      const bPinned = pinnedIds.has(b?.id) ? 1 : 0;
      if (aPinned !== bPinned) return bPinned - aPinned;

      const aTime = asString(a?.updated_at || a?.created_at || "");
      const bTime = asString(b?.updated_at || b?.created_at || "");
      return bTime.localeCompare(aTime);
    });
  }

  function buildSessionHtml(session) {
    const id = asString(session?.id, "");
    const title = asString(session?.title, "Untitled");
    const preview = sessionPreviewText(session);
    const updated = formatDateLoose(session?.updated_at || session?.created_at || "");
    const messageCount = Number(session?.message_count || asArray(session?.messages).length || 0) || 0;

    const pinnedIds = state.pinnedSessionIds instanceof Set ? state.pinnedSessionIds : new Set();
    const isPinned = pinnedIds.has(id);
    const isActive = id && id === asString(state.activeSessionId, "");

    return `
      <div
        class="session-item ${isActive ? "is-active" : ""} ${isPinned ? "is-pinned" : ""}"
        data-session-id="${escapeHtml(id)}"
      >
        <button
          class="session-item-main"
          type="button"
          data-session-id="${escapeHtml(id)}"
          title="${escapeHtml(title)}"
        >
          <div class="session-item-row">
            <span class="session-item-title">${escapeHtml(title)}</span>
            ${isPinned ? `<span class="session-item-pin" aria-hidden="true">📌</span>` : ""}
          </div>

          ${preview ? `<div class="session-item-preview">${escapeHtml(preview)}</div>` : ""}

          <div class="session-item-meta">
            <span>${messageCount} msg${messageCount === 1 ? "" : "s"}</span>
            ${updated ? `<span>${escapeHtml(updated)}</span>` : ""}
          </div>
        </button>

        <div class="session-item-actions">
          <button
            class="session-action-btn"
            type="button"
            data-session-rename="${escapeHtml(id)}"
            title="Rename"
            aria-label="Rename chat"
          >
            Rename
          </button>
          <button
            class="session-action-btn danger"
            type="button"
            data-session-delete="${escapeHtml(id)}"
            title="Delete"
            aria-label="Delete chat"
          >
            Delete
          </button>
        </div>
      </div>
    `;
  }

  async function handleRename(sessionId) {
    const current = asArray(state.sessions).find((item) => asString(item?.id, "") === asString(sessionId, ""));
    const currentTitle = asString(current?.title, "Untitled");
    const nextTitle = window.prompt("Rename chat", currentTitle);

    if (typeof nextTitle !== "string") return;
    const trimmed = nextTitle.trim();
    if (!trimmed || trimmed === currentTitle) return;

    if (typeof sessionsApi.rename === "function") {
      await sessionsApi.rename(sessionId, trimmed);
      return;
    }

    if (Nova.api?.post) {
      await Nova.api.post("/api/session/rename", {
        session_id: sessionId,
        title: trimmed,
      });

      if (typeof sessionsApi.refresh === "function") {
        await sessionsApi.refresh();
      }
      if (render.all) render.all();
    }
  }

  async function handleDelete(sessionId) {
    const ok = window.confirm("Delete this chat?");
    if (!ok) return;

    if (typeof sessionsApi.remove === "function") {
      await sessionsApi.remove(sessionId);
      return;
    }

    if (Nova.api?.post) {
      await Nova.api.post("/api/session/delete", {
        session_id: sessionId,
      });

      state.sessions = asArray(state.sessions).filter(
        (item) => asString(item?.id, "") !== asString(sessionId, "")
      );

      if (state.activeSessionId === sessionId) {
        state.activeSessionId = asString(state.sessions[0]?.id, "") || null;
        if (state.activeSessionId && typeof sessionsApi.load === "function") {
          await sessionsApi.load(state.activeSessionId);
          return;
        }
      }

      if (render.all) render.all();
    }
  }

  function bindSessionDelegates() {
    cacheDom();
    if (!dom.sessionList || dom.sessionList.__novaSessionDelegatesBound) return;

    dom.sessionList.__novaSessionDelegatesBound = true;

    dom.sessionList.addEventListener("click", async (event) => {
      const deleteBtn = event.target.closest("[data-session-delete]");
      if (deleteBtn) {
        const sessionId = asString(deleteBtn.getAttribute("data-session-delete"), "");
        if (sessionId) {
          try {
            await handleDelete(sessionId);
          } catch (error) {
            console.error("Delete session failed:", error);
          }
        }
        return;
      }

      const renameBtn = event.target.closest("[data-session-rename]");
      if (renameBtn) {
        const sessionId = asString(renameBtn.getAttribute("data-session-rename"), "");
        if (sessionId) {
          try {
            await handleRename(sessionId);
          } catch (error) {
            console.error("Rename session failed:", error);
          }
        }
        return;
      }

      const sessionBtn = event.target.closest("[data-session-id]");
      if (!sessionBtn) return;

      const sessionId = asString(sessionBtn.getAttribute("data-session-id"), "");
      if (!sessionId) return;

      try {
        if (typeof sessionsApi.load === "function") {
          await sessionsApi.load(sessionId);
        } else {
          state.activeSessionId = sessionId;
          if (render.all) render.all();
        }
      } catch (error) {
        console.error("Load session failed:", error);
      }
    });
  }

  function renderSessions() {
    cacheDom();
    bindSessionDelegates();

    if (!dom.sessionList) return;

    const sessions = sortedSessions();
    if (!sessions.length) {
      dom.sessionList.innerHTML = `<div class="empty-panel-note">No chats yet.</div>`;
      return;
    }

    dom.sessionList.innerHTML = sessions.map(buildSessionHtml).join("");
  }

  render.sessionsImpl = renderSessions;
})();