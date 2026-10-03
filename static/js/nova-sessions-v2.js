(function () {
  "use strict";

  const LS_SID = "nova.session_id";

  function $(id) {
    return document.getElementById(id);
  }

  function setStatus(text) {
    const el = $("status");

    if (el) {
      el.textContent = "status: " + text;
    }
  }

  function getState() {
    return window.NovaChatState?.state || null;
  }

  function getSessionId(session) {
    return String(
      session?.id ||
      session?.session_id ||
      session?.client_session_id ||
      ""
    ).trim();
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

  let sessionsById = new Map();

  function closeSessionMenu(row, restoreFocus = false) {
    if (!row) return;

    const toggle = row.querySelector("[data-session-menu-toggle]");
    const menu = row.querySelector("[data-session-menu]");
    row.classList.remove("session-menu-open", "session-menu-open-above");
    if (toggle) toggle.setAttribute("aria-expanded", "false");
    if (menu) {
      menu.hidden = true;
      menu.style.removeProperty("position");
      menu.style.removeProperty("top");
      menu.style.removeProperty("left");
      menu.style.removeProperty("right");
      menu.style.removeProperty("bottom");
    }
    if (restoreFocus) toggle?.focus();
  }

  function closeAllSessionMenus(list, restoreFocus = false) {
    const openRow = list.querySelector(".desktop-session-row.session-menu-open");
    if (openRow) closeSessionMenu(openRow, restoreFocus);
  }

  function openSessionMenu(toggle, focusFirst = false) {
    const list = $("desktopSessionList");
    const row = toggle.closest(".desktop-session-row");
    if (!list || !row) return;

    closeAllSessionMenus(list);
    const menu = row.querySelector("[data-session-menu]");
    if (!menu) return;

    const toggleBounds = toggle.getBoundingClientRect();
    row.classList.add("session-menu-open");
    menu.hidden = false;
    menu.style.setProperty("position", "fixed", "important");
    menu.style.setProperty("right", "auto", "important");
    menu.style.setProperty("bottom", "auto", "important");
    const menuBounds = menu.getBoundingClientRect();
    const menuWidth = menuBounds.width || 150;
    const menuHeight = menuBounds.height || 112;
    const viewportPadding = 8;
    const left = Math.max(
      viewportPadding,
      Math.min(window.innerWidth - menuWidth - viewportPadding, toggleBounds.right - menuWidth)
    );
    const below = toggleBounds.bottom + 4;
    const top = below + menuHeight <= window.innerHeight - viewportPadding
      ? below
      : Math.max(viewportPadding, toggleBounds.top - menuHeight - 4);
    menu.style.setProperty("left", `${left}px`, "important");
    menu.style.setProperty("top", `${top}px`, "important");
    toggle.setAttribute("aria-expanded", "true");

    if (focusFirst) {
      menu.querySelector("button")?.focus();
    }
  }

  function bindSessionListActions(list) {
    if (!list || list.dataset.novaSessionActionsBound === "true") return;
    list.dataset.novaSessionActionsBound = "true";

    list.addEventListener("click", async (event) => {
      const target = event.target instanceof Element
        ? event.target.closest("button")
        : null;
      if (!target || !list.contains(target)) return;

      const row = target.closest(".desktop-session-row");
      if (!row) return;

      if (target.matches("[data-session-menu-toggle]")) {
        event.preventDefault();
        event.stopPropagation();
        if (row.classList.contains("session-menu-open")) {
          closeSessionMenu(row);
        } else {
          openSessionMenu(target);
        }
        return;
      }

      const action = target.getAttribute("data-session-action");
      if (action) {
        event.preventDefault();
        event.stopPropagation();
        const sessionId = row.dataset.sessionId || "";
        closeSessionMenu(row, true);
        const actions = window.NovaDesktopSessionActions;
        const session = sessionsById.get(sessionId);
        if (!sessionId || !session || !actions) {
          setStatus("This conversation is no longer available. Refresh the list and try again.");
          return;
        }
        if (action === "rename") await actions.rename?.(sessionId, session);
        if (action === "pin") await actions.togglePin?.(sessionId, session);
        if (action === "delete") await actions.delete?.(sessionId, session);
        return;
      }

      if (target.matches("[data-session-open]")) {
        event.preventDefault();
        const session = sessionsById.get(row.dataset.sessionId || "");
        if (session) {
          closeAllSessionMenus(list);
          await selectSession(session);
        }
      }
    });

    list.addEventListener("keydown", (event) => {
      const toggle = event.target instanceof Element
        ? event.target.closest("[data-session-menu-toggle]")
        : null;
      const menu = event.target instanceof Element
        ? event.target.closest("[data-session-menu]")
        : null;

      if (toggle && event.key === "ArrowDown") {
        event.preventDefault();
        openSessionMenu(toggle, true);
        return;
      }

      if (menu && ["ArrowDown", "ArrowUp"].includes(event.key)) {
        const items = [...menu.querySelectorAll("button")];
        const current = items.indexOf(document.activeElement);
        const step = event.key === "ArrowDown" ? 1 : -1;
        event.preventDefault();
        items[(current + step + items.length) % items.length]?.focus();
        return;
      }

      if (menu && ["Home", "End"].includes(event.key)) {
        const items = [...menu.querySelectorAll("button")];
        event.preventDefault();
        items[event.key === "Home" ? 0 : items.length - 1]?.focus();
      }
    });

    list.addEventListener("focusout", (event) => {
      const row = event.target instanceof Element
        ? event.target.closest(".desktop-session-row")
        : null;
      if (!row) return;
      window.setTimeout(() => {
        if (!row.contains(document.activeElement)) closeSessionMenu(row);
      }, 0);
    });

    document.addEventListener("click", (event) => {
      if (!list.contains(event.target)) closeAllSessionMenus(list);
    });

    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      const openRow = list.querySelector(".desktop-session-row.session-menu-open");
      if (openRow) {
        event.preventDefault();
        event.stopPropagation();
        closeSessionMenu(openRow, true);
      }
    });

    const closeOpenMenu = () => closeAllSessionMenus(list);
    window.addEventListener("resize", closeOpenMenu);
    list.addEventListener("scroll", closeOpenMenu, true);
  }

  function rememberSessionId(sid) {
    if (!sid) {
      return;
    }

    try {
      localStorage.setItem(LS_SID, sid);
      localStorage.setItem("nova_active_session_id", sid);
      localStorage.setItem("nova_session_id", sid);
      sessionStorage.setItem("nova_active_session_id", sid);
    } catch (_) {}

    window.__NOVA_ACTIVE_SESSION_ID = sid;
window.currentSessionId = sid;
window.activeSessionId = sid;
  }

  async function fetchSession(sessionId) {
    const sid = String(sessionId || "").trim();

    if (!sid) {
      return null;
    }

    const response = await fetch(
      "/api/sessions/" + encodeURIComponent(sid),
      {
        method: "GET",
        credentials: "same-origin",
        headers: {
          "Accept": "application/json"
        },
        cache: "no-store"
      }
    );

    const raw = await response.text();

    let data = null;

    try {
      data = JSON.parse(raw);
    } catch (_) {
      throw new Error("Invalid session response");
    }

    if (!response.ok) {
      throw new Error(
        "Session request failed: " + response.status
      );
    }

    return data.session || data;
  }

  async function selectSession(session) {
    const sid = getSessionId(session)

    if (!sid) {
      return
    }

    const state = getState()

    if (!state) {
      console.warn(
        "[NOVA Sessions V2] NovaChatState not ready"
      )
      return
    }

    setStatus("loading session...")

    try {
      const loaded = await fetchSession(sid)

      const messages = Array.isArray(loaded?.messages)
        ? loaded.messages.map((message) => ({
            ...message,
            content: String(
              message?.content ??
              message?.text ??
              ""
            ),
          }))
        : []

      /*
       * Update the authoritative chat state.
       * NovaChatState owns activeChatId and messages.
       */

const existing =
    window.NovaChatState.getChatById?.(sid)

if (existing) {
    existing.title =
        loaded?.title ||
        loaded?.name ||
        existing.title ||
        "Untitled"

    existing.messages = messages

    if (loaded?.meta) {
        existing.meta = loaded.meta
    }

    if (
        typeof loaded?.onboarding_complete !==
        "undefined"
    ) {
        existing.onboarding_complete =
            loaded.onboarding_complete
    }

    if (
        typeof loaded?.onboarding_version !==
        "undefined"
    ) {
        existing.onboarding_version =
            loaded.onboarding_version
    }
} else {
    const chat = {
        id: sid,
        chat_id: sid,
        title:
            loaded?.title ||
            loaded?.name ||
            getSessionTitle(session),
        created_at:
            loaded?.created_at ||
            new Date().toISOString(),
        updated_at:
            loaded?.updated_at ||
            new Date().toISOString(),
        messages,
        meta: loaded?.meta || {},
        onboarding_complete:
            loaded?.onboarding_complete ?? false,
        onboarding_version:
            loaded?.onboarding_version ?? 1,
    }

    const chats = Array.isArray(state.chats)
        ? state.chats.slice()
        : []

    chats.push(chat)

    window.NovaChatState.setChats(chats)
}
      
      const selected =
        window.NovaChatState.setActiveChat(sid)

      if (!selected) {
        throw new Error(
          "NovaChatState rejected session: " + sid
        )
      }

      /*
       * Keep the selected session persistent.
       */
      rememberSessionId(sid)

      /*
       * Synchronize the authoritative message state.
       * Do NOT directly call the legacy desktop renderers.
       */
      state.messages = messages

      if (
        state.messagesByChatId &&
        typeof state.messagesByChatId === "object"
      ) {
        state.messagesByChatId[sid] = messages
      }

      window.dispatchEvent(
        new CustomEvent("nova:chat-loaded", {
          detail: {
            chatId: sid,
            sessionId: sid,
            messages,
          },
        })
      )

      document
        .querySelectorAll(".desktop-session-item")
        .forEach((item) => {
          const active = item.dataset.sessionId === sid;
          item.classList.toggle("active", active);
          item.classList.toggle("is-active", active);
          item.setAttribute("aria-current", active ? "true" : "false");
          item.setAttribute("aria-pressed", active ? "true" : "false");
        })

      window.NovaDesktopProjects?.showChatView?.()
      setStatus("session selected")

      console.log(
        "[NOVA Sessions V2] selected",
        sid,
        "messages:",
        messages.length
      )
    } catch (error) {
      console.error(
        "[NOVA Sessions V2] session selection failed",
        error
      )
      setStatus(window.NovaDesktopUX?.formatError("session-load", error) || "Nova couldn't load this conversation. Check your connection and try again.")
    }
  }

  async function loadSessions() {
    const list = $("desktopSessionList");

    if (!list) {
      console.warn(
        "[NOVA Sessions V2] desktopSessionList missing"
      );

      return;
    }

    list.innerHTML =
      "<div class='session-placeholder'>Loading sessions...</div>";

    try {
      const response = await fetch(
        "/api/sessions",
        {
          method: "GET",
          credentials: "same-origin",
          headers: {
            "Accept": "application/json"
          },
          cache: "no-store"
        }
      );

      if (!response.ok) {
        throw new Error(
          "Sessions request failed: " +
          response.status
        );
      }

      const data = await response.json();

      const sessions =
        data.sessions ||
        data.items ||
        data.data ||
        [];

      list.innerHTML = "";
      sessionsById = new Map();

      if (!sessions.length) {
        list.innerHTML =
          "<div class='session-placeholder'>No conversations yet. Start a new chat with Nova.</div>";

        return;
      }

      const state = getState();

      if (state) {
        const normalizedChats = sessions
          .map((session) => {
            const sid = getSessionId(session);

            if (!sid) {
              return null;
            }

            return {
              id: sid,
              chat_id: sid,
              title: getSessionTitle(session),
              created_at:
                session.created_at ||
                new Date().toISOString(),
              updated_at:
                session.updated_at ||
                session.created_at ||
                new Date().toISOString(),
              messages: Array.isArray(session.messages)
                ? session.messages
                : []
            };
          })
          .filter(Boolean);

        /*
         * BACKEND SESSIONS ARE AUTHORITATIVE.
         *
         * Do not merge them with stale frontend chats.
         * Every backend session gets exactly one frontend
         * chat entry, using the backend session ID unchanged.
         */
        window.NovaChatState.setChats(normalizedChats);

        /*
         * RESTORE THE PERSISTED ACTIVE SESSION AFTER THE BACKEND
         * SESSION LIST HAS BECOME AUTHORITATIVE.
         *
         * chat-state.js starts with activeChatId = null on every
         * page load. The persisted session ID is restored here,
         * after setChats() has populated NovaChatState.
         */
        const persistedSid =
          localStorage.getItem("nova.session_id") ||
          localStorage.getItem("nova_active_session_id") ||
          localStorage.getItem("nova_session_id") ||
          window.__NOVA_ACTIVE_SESSION_ID ||
          "";

        const restoreSid = String(persistedSid).trim();

        if (
          restoreSid &&
          normalizedChats.some(
            (chat) => String(chat.id) === restoreSid
          )
        ) {
          const restoredSession = sessions.find(
            (session) =>
              getSessionId(session) === restoreSid
          );

          if (restoredSession) {
            console.log(
              "[NOVA Sessions V2] restoring persisted session:",
              restoreSid
            );

            await selectSession(restoredSession);
          }
        }

      }
      bindSessionListActions(list);

      sessions.slice(0, 30).forEach((session) => {
        const sid = getSessionId(session);

        if (!sid) {
          return;
        }

        sessionsById.set(sid, session);
        const activeId = String(getState()?.activeChatId || "").trim();
        const active = sid === activeId;
        const pinned = Boolean(session.pinned);

        const row = document.createElement("div");
        row.className = "desktop-session-row";
        row.dataset.sessionId = sid;

        const open = document.createElement("button");
        open.type = "button";
        open.className = "desktop-session-item" + (active ? " is-active" : "");
        open.dataset.sessionId = sid;
        open.dataset.sessionOpen = "true";
        open.setAttribute("aria-current", active ? "true" : "false");
        open.setAttribute("aria-pressed", active ? "true" : "false");
        open.title = getSessionTitle(session);

        const title = document.createElement("span");
        title.className = "desktop-session-title";
        title.textContent = getSessionTitle(session);
        open.appendChild(title);

        if (pinned) {
          const pinIndicator = document.createElement("span");
          pinIndicator.className = "desktop-session-pin-indicator";
          pinIndicator.textContent = "Pinned";
          pinIndicator.setAttribute("aria-label", "Pinned conversation");
          open.appendChild(pinIndicator);
        }

        const toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "desktop-session-menu-toggle";
        toggle.dataset.sessionMenuToggle = "true";
        toggle.setAttribute("aria-label", "Conversation actions for " + getSessionTitle(session));
        toggle.setAttribute("aria-haspopup", "menu");
        toggle.setAttribute("aria-expanded", "false");
        toggle.textContent = "⋯";

        const menu = document.createElement("div");
        menu.className = "desktop-session-menu";
        menu.dataset.sessionMenu = "true";
        menu.setAttribute("role", "menu");
        menu.setAttribute("aria-label", "Conversation actions");
        menu.hidden = true;

        [
          ["rename", "Rename", false],
          ["pin", pinned ? "Unpin" : "Pin", false],
          ["delete", "Delete", true],
        ].forEach(([action, label, destructive]) => {
          const item = document.createElement("button");
          item.type = "button";
          item.className = "desktop-session-menu-item" + (destructive ? " is-destructive" : "");
          item.dataset.sessionAction = action;
          item.setAttribute("role", "menuitem");
          item.textContent = label;
          menu.appendChild(item);
        });

        row.append(open, toggle, menu);
        list.appendChild(row);
      });

      const activeId =
        String(
          getState()?.activeChatId || ""
        ).trim();

      if (activeId) {
        list
          .querySelectorAll(".desktop-session-item")
          .forEach((item) => {
            const isActive = item.dataset.sessionId === activeId;
            item.classList.toggle("active", isActive);
            item.classList.toggle("is-active", isActive);
            item.setAttribute("aria-current", isActive ? "true" : "false");
            item.setAttribute("aria-pressed", isActive ? "true" : "false");
          });
      }

      console.log(
        "[NOVA Sessions V2] loaded",
        sessions.length
      );
    } catch (error) {
      console.error(
        "[NOVA Sessions V2] failed",
        error
      );

      list.innerHTML =
        "<div class='session-placeholder'>" +
        (window.NovaDesktopUX?.formatError("session-load", error) || "Nova couldn't load your conversations. Check your connection and try again.") +
        "</div>";

      setStatus("sessions failed");
    }
  }

async function newSession() {
  try {

const response = await fetch(
  "/api/sessions/new",
  {
    method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          "x-api-key": window.API_KEY || "dev"
        },
        body: JSON.stringify({
          title: "New Chat"
        })
      }
    );


    if (!response.ok) {
      throw new Error(
        "New session failed: " +
        response.status
      );
    }


    const data = await response.json();


    const session =
      data.session ||
      data.item ||
      data;


    const sid =
      session.id ||
      data.active_session_id ||
      data.session_id;


    if (!sid) {
      throw new Error(
        "Server did not return a session id"
      );
    }


    const state = getState();


    if (state) {

const chat = {
    ...session,
    id: sid,
    chat_id: sid,
    title: session.title || "New Chat",
    created_at:
        session.created_at ||
        new Date().toISOString(),
    updated_at:
        session.updated_at ||
        new Date().toISOString(),
    messages: []
};

      const chats = Array.isArray(state.chats)
        ? state.chats.filter(
            (item) =>
              String(item?.id) !== String(sid)
          )
        : [];


      chats.unshift(chat);


      if (
        window.NovaChatState &&
        typeof window.NovaChatState.setChats === "function"
      ) {
        window.NovaChatState.setChats(chats);
      } else {
        state.chats = chats;
      }


      if (
        window.NovaChatState &&
        typeof window.NovaChatState.setActiveChat === "function"
      ) {
        window.NovaChatState.setActiveChat(sid);
      } else {
        state.activeChatId = sid;
      }


      state.messages = [];
    }


    rememberSessionId(sid);


const chat = $("chat");

if (chat) {
    if (
        session &&
        session.meta &&
        session.meta.onboarding &&
        typeof window.renderDesktopOnboarding === "function"
    ) {
        window.renderDesktopOnboarding(session);
    } else {
        chat.innerHTML =
            "<div class='msg assistant'>" +
            "<div class='role'>assistant</div>" +
            "<div class='bubble'>" +
            "Nova is ready. Send a message to begin." +
            "</div>" +
            "</div>";
    }
}


    await loadSessions();


    window.NovaDesktopProjects?.showChatView?.();
    setStatus("new session ready");


    console.log(
      "[NOVA Sessions V2] new session:",
      sid
    );


    return sid;


  } catch (error) {

    console.error(
      "[NOVA Sessions V2] new session failed",
      error
    );


    setStatus("new session failed");

    return null;
  }
}

  function bindSessions() {
    const newBtn = $("newSessionBtn");
    const openBtn = $("openSessionsBtn");

    if (newBtn) {
      newBtn.onclick = newSession;
    }

    if (openBtn) {
      /*
       * V2 owns the Sessions button.
       *
       * Loading the list is idempotent, so repeated
       * clicks cannot create duplicate handlers.
       */
      openBtn.onclick = function () {
        return guardedLoadSessions();
      };
    }

    loadSessions();
  }

let booted = false;
let loadingSessions = null;

async function guardedLoadSessions() {
  if (loadingSessions) {
    console.log(
      "[NOVA Sessions V2] load already running; reusing existing load"
    );

    return loadingSessions;
  }

  loadingSessions = loadSessions();

  try {
    return await loadingSessions;
  } finally {
    loadingSessions = null;
  }
}

function boot() {
  if (booted) {
    console.log(
      "[NOVA Sessions V2] duplicate boot ignored"
    );

    return;
  }

  booted = true;

  bindSessions();

  console.log(
    "[NOVA Sessions V2] ready"
  );
}

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      boot,
      { once: true }
    );
  } else {
    boot();
  }

window.NovaLoadSessionsV2 = guardedLoadSessions;
window.NovaNewSessionV2 = newSession;

window.loadDesktopSessions = guardedLoadSessions;
window.NovaDesktopLoadSessions = guardedLoadSessions;

})();
