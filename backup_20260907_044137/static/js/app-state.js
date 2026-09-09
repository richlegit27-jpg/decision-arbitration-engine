// C:\Users\Owner\nova\static\js\app-state.js

(() => {
  "use strict";

  /*
   * Legacy compatibility layer.
   *
   * NovaChatState is the single source of truth.
   * This file must never create another independent chat state.
   */

  if(!window.NovaChatState?.state){
    console.error(
      "[Nova app-state] NovaChatState must load before app-state.js"
    );

    return;
  }

  const state = window.NovaChatState.state;

  function setActiveChatId(chatId){
    const id = String(chatId || "").trim();

    if(!id){
      state.activeChatId = null;
      return;
    }

    if(typeof window.NovaChatState.setActiveChat === "function"){
      window.NovaChatState.setActiveChat(id);
      return;
    }

    state.activeChatId = id;
  }

  function getActiveChatId(){
    return state.activeChatId || null;
  }

  function getActiveChat(){
    if(
      typeof window.NovaChatState.getActiveChat ===
      "function"
    ){
      return window.NovaChatState.getActiveChat();
    }

    return null;
  }

  function setChats(chats){
    if(
      typeof window.NovaChatState.setChats ===
      "function"
    ){
      return window.NovaChatState.setChats(chats);
    }

    state.chats = Array.isArray(chats)
      ? chats
      : [];

    return state.chats;
  }

  function setMessages(chatId, messages){
    if(
      typeof window.NovaChatState.setMessages ===
      "function"
    ){
      return window.NovaChatState.setMessages(
        chatId,
        messages
      );
    }
  }

  function getMessages(chatId){
    if(
      typeof window.NovaChatState.getMessages ===
      "function"
    ){
      return window.NovaChatState.getMessages(chatId);
    }

    return [];
  }

  function addMessage(chatId, message){
    if(
      typeof window.NovaChatState.addMessage ===
      "function"
    ){
      return window.NovaChatState.addMessage(
        chatId,
        message
      );
    }
  }

  window.NovaAppState = {
    state,

    setActiveChatId,
    getActiveChatId,
    getActiveChat,
    setChats,
    setMessages,
    getMessages,
    addMessage
  };

  /*
   * Keep the legacy NovaApp object pointed at the unified state.
   */
  window.NovaApp = window.NovaApp || {};

  window.NovaApp.state = state;

  console.log(
    "[NOVA APP STATE] linked to NovaChatState"
  );
})();