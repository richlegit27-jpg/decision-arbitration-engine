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
          item.classList.toggle(
            "active",
            item.dataset.sessionId === sid
          )
        })

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

      if (!sessions.length) {
        list.innerHTML =
          "<div class='session-placeholder'>No saved sessions yet.</div>";

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
      sessions.slice(0, 30).forEach((session) => {
        const sid = getSessionId(session);

        if (!sid) {
          return;
        }

        const btn = document.createElement("button");

        btn.type = "button";
        btn.className = "desktop-session-item";
        btn.dataset.sessionId = sid;

        const title = document.createElement("div");

        title.className = "desktop-session-title";
        title.textContent = getSessionTitle(session);

        const meta = document.createElement("div");

        meta.className = "desktop-session-meta";
        meta.textContent = sid;

        btn.appendChild(title);
        btn.appendChild(meta);

        btn.addEventListener(
          "click",
          async function (event) {
            event.preventDefault();
            event.stopPropagation();

            await selectSession(session);
          }
        );

        list.appendChild(btn);
      });

      const activeId =
        String(
          getState()?.activeChatId || ""
        ).trim();

      if (activeId) {
        list
          .querySelectorAll(".desktop-session-item")
          .forEach((item) => {
            item.classList.toggle(
              "active",
              item.dataset.sessionId === activeId
            );
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
        "<div class='session-placeholder'>Could not load sessions.</div>";

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
