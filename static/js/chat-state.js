// C:\Users\Owner\nova\static\js\chat-state.js

(() => {
  "use strict";

  /*
   * Nova unified chat state.
   *
   * This is now the authoritative chat state.
   *
   * Legacy NovaApp.state is linked to this state so the older
   * app.js code and the newer modular chat system cannot drift
   * apart.
   */

  const STORAGE_KEYS = {
    ACTIVE_CHAT_ID: "nova_active_chat_id",
    THEME: "nova_theme"
  };

  const state = {
    activeChatId: null,
    chats: [],
    messages: [],
    messagesByChatId: {},
    pendingAttachments: [],
    attachedFiles: [],
    memoryItems: [],
    models: [],
    selectedModel: "gpt-4.1-mini",
    isLoadingChat: false,
    isAuthenticated: true,

    ui: {
      sidebarOpen: true,
      memoryOpen: false,
      filesOpen: false
    },

    voice: {
      supported: false,
      listening: false,
      recognition: null,
      blockedReason: ""
    },

    memory: {
      isOpen: false
    }
  };

  function generateId(prefix = "id") {
    if(window.crypto?.randomUUID){
      return `${prefix}_${window.crypto.randomUUID()}`;
    }

    return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
  }

  function nowIso() {
    return new Date().toISOString();
  }

  function syncMessagesForActiveChat() {
    if(!state.activeChatId){
      state.messages = [];
      return state.messages;
    }

    if(!state.messagesByChatId){
      state.messagesByChatId = {};
    }

    if(!Array.isArray(state.messagesByChatId[state.activeChatId])){
      state.messagesByChatId[state.activeChatId] = [];
    }

    state.messages = state.messagesByChatId[state.activeChatId];

    return state.messages;
  }

  function createChat(title = "New Chat") {
    const id = generateId("chat");
    const timestamp = nowIso();

    const chat = {
      id,
      chat_id: id,
      title: String(title || "New Chat"),
      created_at: timestamp,
      updated_at: timestamp,
      message_count: 0,
      messages: []
    };

    state.chats.unshift(chat);
    state.activeChatId = id;
    state.messagesByChatId[id] = chat.messages;
    state.messages = chat.messages;

    try{
      localStorage.setItem(
        STORAGE_KEYS.ACTIVE_CHAT_ID,
        id
      );
    }catch(error){
      console.warn(
        "[NovaChatState] could not save active chat:",
        error
      );
    }

    window.dispatchEvent(
      new CustomEvent("nova:chat-created", {
        detail: {
          chat
        }
      })
    );

    return chat;
  }

  function getChatById(chatId) {
    const id = String(chatId || "").trim();

    if(!id){
      return null;
    }

    return (
      state.chats.find(
        chat => String(chat?.id || chat?.chat_id || "") === id
      ) || null
    );
  }

  function ensureActiveChat() {
    if(state.activeChatId){
      const existing = getChatById(state.activeChatId);

      if(existing){
        state.activeChatId = String(
          existing.id || existing.chat_id
        );

        if(!Array.isArray(existing.messages)){
          existing.messages = [];
        }

        state.messagesByChatId[state.activeChatId] =
          existing.messages;

        state.messages = existing.messages;

        return existing;
      }
    }

    if(Array.isArray(state.chats) && state.chats.length){
      const chat = state.chats[0];

      state.activeChatId = String(
        chat.id || chat.chat_id || ""
      );

      if(!Array.isArray(chat.messages)){
        chat.messages = [];
      }

      state.messagesByChatId[state.activeChatId] =
        chat.messages;

      state.messages = chat.messages;

      return chat;
    }

    return createChat("New Chat");
  }

  function setActiveChat(chatId) {
    const id = String(chatId || "").trim();

    if(!id){
      return null;
    }

    const chat = getChatById(id);

    if(!chat){
      console.warn(
        "[NovaChatState] active chat not found:",
        id
      );

      return null;
    }

    state.activeChatId = id;

    if(!Array.isArray(chat.messages)){
      chat.messages = [];
    }

    state.messagesByChatId[id] = chat.messages;
    state.messages = chat.messages;

    try{
      localStorage.setItem(
        STORAGE_KEYS.ACTIVE_CHAT_ID,
        id
      );
    }catch(error){
      console.warn(
        "[NovaChatState] could not save active chat:",
        error
      );
    }

    window.dispatchEvent(
      new CustomEvent("nova:chat-changed", {
        detail: {
          chatId: id
        }
      })
    );

    return chat;
  }

  function setChats(chats) {
    state.chats = Array.isArray(chats)
      ? chats
      : [];

    state.messagesByChatId = {};

    for(const chat of state.chats){
      const id = String(
        chat?.id ||
        chat?.chat_id ||
        ""
      ).trim();

      if(!id){
        continue;
      }

      chat.id = id;
      chat.chat_id = id;

      if(!chat.title){
        chat.title = "New Chat";
      }

      if(!Array.isArray(chat.messages)){
        chat.messages = [];
      }

      chat.message_count = Number(
        chat.message_count || chat.messages.length || 0
      );

      state.messagesByChatId[id] = chat.messages;
    }

    return state.chats;
  }

  function setMessages(chatId, messages) {
    const id = String(chatId || "").trim();

    if(!id){
      return;
    }

    const normalized = Array.isArray(messages)
      ? messages
      : [];

    state.messagesByChatId[id] = normalized;

    const chat = getChatById(id);

    if(chat){
      chat.messages = normalized;
      chat.message_count = normalized.length;
      chat.updated_at = nowIso();
    }

    if(String(state.activeChatId) === id){
      state.messages = normalized;
    }
  }

  function getMessages(chatId) {
    const id = String(chatId || "").trim();

    if(!id){
      return [];
    }

    return Array.isArray(state.messagesByChatId[id])
      ? state.messagesByChatId[id]
      : [];
  }

  function addMessage(chatId, message) {
    const id = String(chatId || "").trim();

    if(!id || !message){
      return;
    }

    const messages = getMessages(id);

    messages.push(message);

    setMessages(id, messages);
  }

  function replaceMessage(
    chatId,
    messageId,
    nextMessage
  ){
    const id = String(chatId || "").trim();

    if(!id || !messageId || !nextMessage){
      return false;
    }

    const messages = getMessages(id);

    const index = messages.findIndex(
      item => item && item.id === messageId
    );

    if(index === -1){
      return false;
    }

    messages[index] = nextMessage;

    setMessages(id, messages);

    return true;
  }

  function updateMessageContent(
    chatId,
    messageId,
    content
  ){
    const id = String(chatId || "").trim();

    if(!id || !messageId){
      return false;
    }

    const messages = getMessages(id);

    const index = messages.findIndex(
      item => item && item.id === messageId
    );

    if(index === -1){
      return false;
    }

    messages[index] = {
      ...messages[index],
      content: String(content ?? "")
    };

    setMessages(id, messages);

    return true;
  }

  function removeMessage(chatId, messageId) {
    const id = String(chatId || "").trim();

    if(!id || !messageId){
      return false;
    }

    const messages = getMessages(id);

    const next = messages.filter(
      item => item && item.id !== messageId
    );

    if(next.length === messages.length){
      return false;
    }

    setMessages(id, next);

    return true;
  }

  function updateActiveChatTitle(title) {
    const chat = ensureActiveChat();

    if(!chat){
      return null;
    }

    const nextTitle = String(title || "").trim();

    if(!nextTitle){
      return chat;
    }

    chat.title = nextTitle;
    chat.updated_at = nowIso();

    window.dispatchEvent(
      new CustomEvent("nova:chat-title-changed", {
        detail: {
          chatId: chat.id,
          title: chat.title
        }
      })
    );

    return chat;
  }

  function deleteChat(chatId) {
    const id = String(chatId || "").trim();

    if(!id){
      return false;
    }

    const index = state.chats.findIndex(
      chat =>
        String(chat?.id || chat?.chat_id || "") === id
    );

    if(index === -1){
      return false;
    }

    state.chats.splice(index, 1);

    delete state.messagesByChatId[id];

    if(String(state.activeChatId) === id){
      state.activeChatId = null;
      state.messages = [];

      if(state.chats.length){
        setActiveChat(state.chats[0].id);
      }
    }

    try{
      if(String(state.activeChatId) === id){
        localStorage.removeItem(
          STORAGE_KEYS.ACTIVE_CHAT_ID
        );
      }
    }catch(error){
      console.warn(
        "[NovaChatState] could not clear active chat:",
        error
      );
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

  function getActiveChat() {
    return ensureActiveChat();
  }

  function setAttachedFiles(files) {
    state.attachedFiles = Array.isArray(files)
      ? files
      : [];

    state.pendingAttachments = state.attachedFiles;

    return state.attachedFiles;
  }

  function addAttachedFile(file) {
    if(!file){
      return;
    }

    if(!Array.isArray(state.attachedFiles)){
      state.attachedFiles = [];
    }

    state.attachedFiles.push(file);
    state.pendingAttachments = state.attachedFiles;
  }

  function getStoredActiveChatId() {
    try{
      return localStorage.getItem(
        STORAGE_KEYS.ACTIVE_CHAT_ID
      );
    }catch(error){
      return null;
    }
  }

  /*
   * Create the public state object first.
   */
  window.NovaChatState = {
    state,

    STORAGE_KEYS,

    generateId,

    nowIso,

    createChat,

    getChatById,

    ensureActiveChat,

    setActiveChat,

    setChats,

    setMessages,

    getMessages,

    addMessage,

    replaceMessage,

    updateMessageContent,

    removeMessage,

    updateActiveChatTitle,

    deleteChat,

    getActiveChat,

    setAttachedFiles,

    addAttachedFile,

    getStoredActiveChatId,

    syncMessagesForActiveChat
  };

  /*
   * CRITICAL:
   *
   * If the legacy NovaApp exists, make it reference the SAME
   * state object instead of maintaining another independent
   * chat state.
   */
  if(window.NovaApp){
    window.NovaApp.state = state;
  }

  console.log(
    "[NOVA CHAT STATE] unified state initialized",
    {
      activeChatId: state.activeChatId,
      chats: state.chats.length
    }
  );
})();