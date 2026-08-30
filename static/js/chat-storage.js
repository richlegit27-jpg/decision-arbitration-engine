(() => {
  "use strict";

  const el = {
    newChatBtn: document.getElementById("btnNewChat"),
    chatList: document.getElementById("chatList")
  };

  let createInFlight = false;

  function getState(){
    return window.NovaChatState?.state || null;
  }

  function normalizeChat(chat){
    if(!chat){
      return null;
    }

    return {
      ...chat,
      id: String(chat.id || chat.session_id || "").trim(),
      title: String(
        chat.title ||
        chat.name ||
        "New Chat"
      ),
      messages: Array.isArray(chat.messages)
        ? chat.messages
        : [],
      message_count: Number(chat.message_count || 0)
    };
  }

  function renderChatList(){
    if(!el.chatList){
      return;
    }

    el.chatList.innerHTML = "";

    const state = getState();
    const chats = Array.isArray(state?.chats)
      ? state.chats
      : [];

    if(!chats.length){
      el.chatList.innerHTML =
        "<div class='chat-list-empty'>No chats yet</div>";
      return;
    }

    chats.forEach(rawChat => {
      const chat = normalizeChat(rawChat);

      if(!chat?.id){
        return;
      }

      const li = document.createElement("div");

      li.className = "chat-list-item";
      li.dataset.chatId = chat.id;
      li.textContent = chat.title;

      if(String(state.activeChatId) === String(chat.id)){
        li.classList.add("active");
      }

      li.onclick = async event => {
        event?.stopPropagation();

        try{
          if(typeof window.NovaChatState?.setActiveChat === "function"){
            window.NovaChatState.setActiveChat(chat.id);
          }else if(state){
            state.activeChatId = chat.id;
          }

          await loadMessages(chat.id);

          renderChatList();

          if(typeof window.NovaChatOrchestrator?.loadActiveChatMessages === "function"){
            await window.NovaChatOrchestrator.loadActiveChatMessages();
          }

          window.dispatchEvent(
            new CustomEvent("nova:chat-changed", {
              detail: {
                chatId: chat.id
              }
            })
          );

        }catch(error){
          console.error(
            "[NovaChatStorage] chat selection error:",
            error
          );
        }
      };

      const del = document.createElement("button");

      del.type = "button";
      del.textContent = "×";
      del.style.float = "right";

      del.onclick = async event => {
        event?.stopPropagation();

        try{
          await deleteChat(chat.id);
          renderChatList();
        }catch(error){
          console.error(
            "[NovaChatStorage] delete chat error:",
            error
          );
        }
      };

      li.appendChild(del);
      el.chatList.appendChild(li);
    });
  }
  async function loadChats(){
    const state = getState();

    if(!state){
      throw new Error("NovaChatState missing");
    }

    /*
     * IMPORTANT:
     * An explicitly selected active chat is authoritative.
     * Background chat-list refreshes must never replace it
     * with the first populated chat or the backend's default.
     */

    const requestedActiveId = String(
      state.activeChatId || ""
    ).trim();

const response = await fetch(
    "/api/sessions/new",
      {
        method: "GET",
        credentials: "same-origin",
        cache: "no-store"
      }
    );

    if(!response.ok){
      throw new Error(
        `Failed to load chats (${response.status})`
      );
    }

    const data = await response.json();

    const rawChats =
      Array.isArray(data?.chats)
        ? data.chats
        : Array.isArray(data?.items)
          ? data.items
          : Array.isArray(data?.sessions)
            ? data.sessions
            : [];

    const chats = rawChats
      .map(normalizeChat)
      .filter(chat => chat?.id);

    state.chats = chats;

    /*
     * If the caller already selected a chat, preserve it.
     */
    if(requestedActiveId){
      const selectedChat = chats.find(
        chat =>
          String(chat.id) === requestedActiveId
      );

      if(selectedChat){
        state.activeChatId = requestedActiveId;

        state.messages =
          Array.isArray(selectedChat.messages)
            ? selectedChat.messages
            : [];

        state.messagesByChatId =
          state.messagesByChatId || {};

        state.messagesByChatId[requestedActiveId] =
          state.messages;

        console.log(
          "[NovaChatStorage] PRESERVED EXPLICIT ACTIVE CHAT:",
          requestedActiveId,
          "messages:",
          state.messages.length
        );
      }else{
        /*
         * The selected chat may have been created moments ago
         * and not yet appeared in /api/chats.
         *
         * DO NOT silently switch to another chat.
         */
        console.log(
          "[NovaChatStorage] PRESERVED ACTIVE CHAT NOT YET IN CHAT LIST:",
          requestedActiveId
        );
      }
    }else{
      /*
       * No active chat exists yet.
       * Only now may we choose an initial chat.
       */
      const backendActiveId = String(
        data?.active_session_id ||
        data?.active_chat_id ||
        data?.activeChatId ||
        ""
      ).trim();

      let initialChat = null;

      if(backendActiveId){
        initialChat = chats.find(
          chat =>
            String(chat.id) === backendActiveId
        ) || null;
      }

      if(!initialChat){
        initialChat =
          chats.find(
            chat =>
              Array.isArray(chat.messages) &&
              chat.messages.length > 0
          ) ||
          chats.find(
            chat =>
              Number(chat.message_count || 0) > 0
          ) ||
          chats[0] ||
          null;
      }

      if(initialChat){
        state.activeChatId =
          String(initialChat.id);

        state.messages =
          Array.isArray(initialChat.messages)
            ? initialChat.messages
            : [];

        state.messagesByChatId =
          state.messagesByChatId || {};

        state.messagesByChatId[state.activeChatId] =
          state.messages;

        console.log(
          "[NovaChatStorage] INITIAL ACTIVE CHAT SELECTED:",
          state.activeChatId,
          "messages:",
          state.messages.length
        );
      }else{
        state.activeChatId = null;
        state.messages = [];
      }
    }

    renderChatList();

    window.dispatchEvent(
      new CustomEvent("nova:chats-loaded", {
        detail: {
          chats,
          activeChatId: state.activeChatId
        }
      })
    );

    console.log(
      "[NovaChatStorage] loaded chats:",
      chats.length,
      "active:",
      state.activeChatId
    );

    return chats;
  }
  async function loadMessages(chatId){
    const state = getState();
    const id = String(chatId || "").trim();

    if(!id){
      return [];
    }

    try{
      const response = await fetch(
        `/api/sessions/${encodeURIComponent(id)}`,
        {
          method: "GET",
          credentials: "include",
          cache: "no-store"
        }
      );

      if(!response.ok){
        console.warn(
          "[NovaChatStorage] loadMessages failed:",
          response.status
        );

        return [];
      }

      const data = await response.json();

      const chat = normalizeChat(
        data?.session ||
        data?.item ||
        data
      );

      if(!chat?.id){
        console.warn(
          "[NovaChatStorage] loadMessages returned no session:",
          id
        );

        return [];
      }

      const messages =
        Array.isArray(chat.messages)
          ? chat.messages
          : [];

      if(state){
        state.activeChatId = chat.id;

        state.messages = messages;

        state.messagesByChatId =
          state.messagesByChatId || {};

        state.messagesByChatId[chat.id] =
          messages;

        const existingChat =
          state.chats?.find(
            item =>
              String(item.id) === String(chat.id)
          );

        if(existingChat){
          existingChat.messages = messages;

          existingChat.message_count =
            messages.length;

          existingChat.updated_at =
            chat.updated_at ||
            new Date().toISOString();
        }
      }

      console.log(
        "[NovaChatStorage] loaded messages:",
        {
          sessionId: chat.id,
          count: messages.length
        }
      );

      return messages;

    }catch(error){
      console.warn(
        "[NovaChatStorage] loadMessages failed:",
        error
      );

      return [];
    }
  }

async function saveMessages(chatId, messages){
    const state = getState();
    const id = String(chatId || "").trim();

    if(!id){
        return false;
    }

    const finalMessages = Array.isArray(messages)
        ? messages.slice()
        : [];

    try{
        const response = await fetch(
            `/api/sessions/${encodeURIComponent(id)}`,
            {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json"
                },
                credentials: "include",
                body: JSON.stringify({
                    messages: finalMessages
                })
            }
        );

        if(!response.ok){
            let errorBody = null;

            try{
                errorBody = await response.json();
            }catch{
                // ignore non-JSON error response
            }

            throw new Error(
                errorBody?.detail ||
                errorBody?.message ||
                `HTTP ${response.status}`
            );
        }

        const payload = await response.json().catch(() => ({}));

        const savedMessages =
            Array.isArray(payload?.messages)
                ? payload.messages
                : finalMessages;

        if(state){
            state.activeChatId = id;

            state.messages = savedMessages.slice();

            state.messagesByChatId =
                state.messagesByChatId || {};

            state.messagesByChatId[id] =
                savedMessages.slice();

            const existingChat =
                state.chats?.find(
                    item =>
                        String(
                            item?.id ||
                            item?.chat_id ||
                            ""
                        ) === id
                );

            if(existingChat){
                existingChat.messages =
                    savedMessages.slice();

                existingChat.message_count =
                    savedMessages.length;

                existingChat.updated_at =
                    new Date().toISOString();
            }
        }

        console.log(
            "[NovaChatStorage] messages saved:",
            {
                sessionId: id,
                count: savedMessages.length
            }
        );

        return savedMessages;

    }catch(error){

        console.warn(
            "[NovaChatStorage] saveMessages failed:",
            error
        );

        return false;
    }
}

  function setActiveChat(chatId){
    const state = getState();

    if(!state){
      return null;
    }

    const id = String(chatId || "").trim();

    if(!id){
      return null;
    }

    const chat = state.chats?.find(
      item => String(item.id) === id
    );

    if(!chat){
      console.warn(
        "[NovaChatStorage] active chat not found:",
        id
      );
      return null;
    }

    state.activeChatId = id;

    state.messages =
      Array.isArray(chat.messages)
        ? chat.messages
        : [];

    renderChatList();

    return chat;
  }

  async function createAndSaveChat(title = "New Chat"){
    if(createInFlight){
      return null;
    }

    createInFlight = true;

    try{
      const response = await fetch(
        "/api/sessions",
        {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            title
          })
        }
      );

      if(!response.ok){
        throw new Error(
          `Failed to create chat (${response.status})`
        );
      }

      const data = await response.json();

      const chat = normalizeChat(
        data?.session ||
        data?.item ||
        data
      );

      if(!chat?.id){
        throw new Error(
          "Backend returned no chat/session ID"
        );
      }

      const state = getState();

      if(state){
        state.chats = Array.isArray(state.chats)
          ? state.chats
          : [];

        state.chats = [
          chat,
          ...state.chats.filter(
            item => String(item.id) !== chat.id
          )
        ];

        state.activeChatId = chat.id;
        state.messages = chat.messages;
      }

      renderChatList();

      window.dispatchEvent(
        new CustomEvent("nova:chat-created", {
          detail: {
            chat
          }
        })
      );

      return chat;

    }finally{
      createInFlight = false;
    }
  }

  async function openNewChat(){
    if(createInFlight){
      return;
    }

    if(el.newChatBtn){
      el.newChatBtn.disabled = true;
      el.newChatBtn.textContent = "Creating...";
    }

    try{
      const chat = await createAndSaveChat("New Chat");

      if(chat){
        renderChatList();

        if(window.innerWidth <= 980){
          document.body.classList.remove("sidebar-open");
        }
      }

      return chat;

    }catch(error){
      console.error(
        "[NovaChatStorage] new chat error:",
        error
      );

      alert(
        error?.message ||
        "Could not create chat."
      );

      return null;

    }finally{
      if(el.newChatBtn){
        el.newChatBtn.disabled = false;
        el.newChatBtn.textContent = "+ New Chat";
      }
    }
  }

  async function deleteChat(chatId){
    const id = String(chatId || "").trim();

    if(!id){
      return false;
    }

    try{
      const response = await fetch(
        `/api/sessions/${encodeURIComponent(id)}`,
        {
          method: "DELETE"
        }
      );

      if(!response.ok && response.status !== 404){
        console.warn(
          "[NovaChatStorage] backend delete failed:",
          response.status
        );
      }
    }catch(error){
      console.warn(
        "[NovaChatStorage] backend delete unavailable:",
        error
      );
    }

    const state = getState();

    if(!state){
      return false;
    }

    state.chats = Array.isArray(state.chats)
      ? state.chats.filter(
          chat => String(chat.id) !== id
        )
      : [];

    if(String(state.activeChatId) === id){
      const next = state.chats[0] || null;

      state.activeChatId = next?.id || null;
      state.messages =
        next && Array.isArray(next.messages)
          ? next.messages
          : [];
    }

    window.dispatchEvent(
      new CustomEvent("nova:chat-deleted", {
        detail: {
          chatId: id
        }
      })
    );

    return true;
  }

  function getActiveChat(){
    const state = getState();

    if(!state?.activeChatId){
      return null;
    }

    return state.chats?.find(
      chat =>
        String(chat.id) ===
        String(state.activeChatId)
    ) || null;
  }

  function getEffectiveOutgoingText(
    text,
    attachments = []
  ){
    const value = String(text || "").trim();

    if(value){
      return value;
    }

    if(Array.isArray(attachments) && attachments.length){
      return attachments
        .map(
          item =>
            String(
              item?.name ||
              item?.filename ||
              ""
            ).trim()
        )
        .filter(Boolean)
        .join(", ");
    }

    return "";
  }

  function init(){
    renderChatList();

    if(el.newChatBtn){
      el.newChatBtn.addEventListener(
        "click",
        openNewChat
      );
    }
  }

  window.NovaChatStorage = {
    renderChatList,
    openNewChat,
    createAndSaveChat,
    loadChats,
    loadMessages,
    saveMessages,
    setActiveChat,
    deleteChat,
    getActiveChat,
    getEffectiveOutgoingText
  };

  if(document.readyState === "loading"){
    document.addEventListener(
      "DOMContentLoaded",
      init,
      { once: true }
    );
  }else{
    init();
  }

})();










