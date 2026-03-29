(() => {
  "use strict";

  if (window.__novaRenderSessionsLoaded) return;
  window.__novaRenderSessionsLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  Nova.sessions = Nova.sessions || {};

  const API = {
    state: "/api/state",
    newSession: "/api/session/new",
    renameSession: "/api/session/rename",
    deleteSession: "/api/session/delete",
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  async function parseJsonSafe(response) {
    const text = await response.text();
    try {
      return text ? JSON.parse(text) : {};
    } catch {
      return {};
    }
  }

  async function apiGet(url) {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      credentials: "same-origin",
    });

    const data = await parseJsonSafe(response);
    if (!response.ok) {
      throw new Error(data.error || `GET failed: ${url}`);
    }
    return data;
  }

  async function apiPost(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      credentials: "same-origin",
      body: JSON.stringify(payload || {}),
    });

    const data = await parseJsonSafe(response);
    if (!response.ok) {
      throw new Error(data.error || `POST failed: ${url}`);
    }
    return data;
  }

  function getStateBucket() {
    Nova.state = Nova.state || {};
    if (!Array.isArray(Nova.state.sessions)) Nova.state.sessions = [];
    if (typeof Nova.state.activeSessionId !== "string") {
      Nova.state.activeSessionId = "";
    }
    return Nova.state;
  }

  function normalizeSessions(payload) {
    const candidates = [
      payload?.sessions,
      payload?.data?.sessions,
      payload?.items,
      payload?.data?.items,
    ];

    for (const value of candidates) {
      if (Array.isArray(value)) return value;
    }

    return [];
  }

  function formatMeta(session) {
    const count =
      Number(session?.message_count ?? session?.messages_count ?? session?.count ?? 0) || 0;

    if (count === 1) return "1 message";
    if (count > 1) return `${count} messages`;

    const updated =
      session?.updated_at ||
      session?.updated ||
      session?.created_at ||
      session?.created ||
      "";

    if (!updated) return "ready";

    const date = new Date(updated);
    if (Number.isNaN(date.getTime())) return "ready";

    return date.toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function resolveId(session) {
    return String(
      session?.id ||
      session?.session_id ||
      session?.uuid ||
      ""
    ).trim();
  }

  function resolveTitle(session, index) {
    const raw =
      session?.title ||
      session?.name ||
      session?.label ||
      session?.summary ||
      "";

    const clean = String(raw).trim();
    if (clean) return clean;
    return `Chat ${index + 1}`;
  }

  function setActiveSession(sessionId) {
    const state = getStateBucket();
    state.activeSessionId = String(sessionId || "");
  }

  function renderSessions() {
    const state = getStateBucket();
    const sessionList = byId("sessionList");
    if (!sessionList) return;

    const sessions = Array.isArray(state.sessions) ? state.sessions : [];
    const activeId = String(state.activeSessionId || "");

    if (!sessions.length) {
      sessionList.innerHTML = `<div class="session-empty">No chats yet.</div>`;
      return;
    }

    sessionList.innerHTML = sessions
      .map((session, index) => {
        const sessionId = resolveId(session);
        const title = resolveTitle(session, index);
        const meta = formatMeta(session);
        const active = sessionId && sessionId === activeId;

        return `
          <div class="session-item${active ? " is-active" : ""}" data-session-id="${escapeHtml(sessionId)}" ${active ? 'aria-current="true"' : ""}>
            <button class="session-main" type="button" data-session-open="${escapeHtml(sessionId)}" title="${escapeHtml(title)}">
              <div class="session-title">${escapeHtml(title)}</div>
              <div class="session-meta">${escapeHtml(meta)}</div>
            </button>
            <div class="session-actions">
              <button class="icon-btn" type="button" data-session-rename="${escapeHtml(sessionId)}" aria-label="Rename chat" title="Rename chat">✎</button>
              <button class="icon-btn" type="button" data-session-delete="${escapeHtml(sessionId)}" aria-label="Delete chat" title="Delete chat">🗑</button>
            </div>
          </div>
        `;
      })
      .join("");
  }

  async function loadSession(sessionId) {
    const id = String(sessionId || "").trim();
    if (!id) return;

    const state = getStateBucket();
    state.activeSessionId = id;

    if (Nova.chat && typeof Nova.chat.loadSession === "function") {
      await Nova.chat.loadSession(id);
    } else if (Nova.messages && typeof Nova.messages.loadSession === "function") {
      await Nova.messages.loadSession(id);
    } else if (Nova.messages && typeof Nova.messages.refresh === "function") {
      await Nova.messages.refresh();
    }

    renderSessions();
  }

  async function refresh() {
    const payload = await apiGet(API.state);
    const state = getStateBucket();
    state.sessions = normalizeSessions(payload);

    if (!state.activeSessionId && state.sessions.length) {
      state.activeSessionId = resolveId(state.sessions[0]);
    }

    renderSessions();
    return state.sessions;
  }

  async function createNewSession() {
    const payload = await apiPost(API.newSession, {});
    const createdId = String(
      payload?.session_id ||
      payload?.id ||
      payload?.session?.id ||
      ""
    ).trim();

    await refresh();

    if (createdId) {
      await loadSession(createdId);
    } else {
      renderSessions();
    }
  }

  async function renameSession(sessionId) {
    const id = String(sessionId || "").trim();
    if (!id) return;

    const state = getStateBucket();
    const current = (state.sessions || []).find((item) => resolveId(item) === id);
    const currentTitle = resolveTitle(current || {}, 0);
    const nextTitle = window.prompt("Rename chat", currentTitle);

    if (!nextTitle || !nextTitle.trim()) return;

    await apiPost(API.renameSession, {
      session_id: id,
      title: nextTitle.trim(),
      name: nextTitle.trim(),
    });

    await refresh();
  }

  async function deleteSession(sessionId) {
    const id = String(sessionId || "").trim();
    if (!id) return;

    const ok = window.confirm("Delete this chat?");
    if (!ok) return;

    await apiPost(API.deleteSession, {
      session_id: id,
      id,
    });

    const state = getStateBucket();
    if (state.activeSessionId === id) {
      state.activeSessionId = "";
    }

    await refresh();
  }

  function bindListEvents() {
    const sessionList = byId("sessionList");
    if (!sessionList || sessionList.__novaSessionsBound) return;

    sessionList.__novaSessionsBound = true;

    sessionList.addEventListener("click", async (event) => {
      const openBtn = event.target.closest("[data-session-open]");
      const renameBtn = event.target.closest("[data-session-rename]");
      const deleteBtn = event.target.closest("[data-session-delete]");

      try {
        if (openBtn) {
          event.preventDefault();
          await loadSession(openBtn.getAttribute("data-session-open"));
          return;
        }

        if (renameBtn) {
          event.preventDefault();
          await renameSession(renameBtn.getAttribute("data-session-rename"));
          return;
        }

        if (deleteBtn) {
          event.preventDefault();
          await deleteSession(deleteBtn.getAttribute("data-session-delete"));
        }
      } catch (error) {
        console.error("Nova sessions action failed:", error);
      }
    });
  }

  function bindNewChat() {
    const newChatBtn = byId("newChatBtn");
    if (!newChatBtn || newChatBtn.__novaNewChatBound) return;

    newChatBtn.__novaNewChatBound = true;
    newChatBtn.addEventListener("click", async (event) => {
      event.preventDefault();
      try {
        await createNewSession();
      } catch (error) {
        console.error("Nova new chat failed:", error);
      }
    });
  }

  async function bootstrap() {
    bindListEvents();
    bindNewChat();

    try {
      await refresh();
    } catch (error) {
      console.error("Nova sessions bootstrap failed:", error);
      renderSessions();
    }

    return true;
  }

  Nova.sessions.refresh = refresh;
  Nova.sessions.render = renderSessions;
  Nova.sessions.loadSession = loadSession;
  Nova.sessions.createNewSession = createNewSession;
  Nova.sessions.renameSession = renameSession;
  Nova.sessions.deleteSession = deleteSession;
  Nova.sessions.bootstrap = bootstrap;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      bootstrap().catch((error) => {
        console.error("Nova sessions DOM bootstrap failed:", error);
      });
    }, { once: true });
  } else {
    bootstrap().catch((error) => {
      console.error("Nova sessions immediate bootstrap failed:", error);
    });
  }
})();