// C:\Users\Owner\nova\static\js\ui-state-service.js

(() => {
"use strict"

function createUIStateService(deps){
  const {
    state,
    el,
    sidebar,
    render,
    chatService,
  } = deps

  function renderChats(){
    sidebar.renderChatList(
      el.chatList,
      state.chats,
      state.activeChatId,
      state.searchTerm,
    )
  }

  function renderMessages(){
    render.renderMessages(
      el.messages,
      state.messages,
    )
  }

  function renderTopbar(){
    const active = chatService.getActiveChat()

    if(el.topbarTitle){
      el.topbarTitle.textContent = active?.title || "Nova"
    }

    if(el.topbarSubtitle){
      el.topbarSubtitle.textContent = state.activeChatId ? "Chat ready" : "Local AI chat"
    }
  }

  function renderApp(){
    renderChats()
    renderMessages()
    renderTopbar()
  }

  function setSending(isSending){
    state.sending = Boolean(isSending)

    if(el.btnSend){
      el.btnSend.disabled = state.sending
      el.btnSend.textContent = state.sending ? "Sending..." : "Send"
    }

    if(el.input){
      el.input.disabled = state.sending
    }

    if(el.btnAttach){
      el.btnAttach.disabled = state.sending
    }
  }

  function focusInput(){
    el.input?.focus()
  }

  return {
    renderChats,
    renderMessages,
    renderTopbar,
    renderApp,
    setSending,
    focusInput,
  }
}

window.NovaUIStateService = {
  createUIStateService,
}

})()