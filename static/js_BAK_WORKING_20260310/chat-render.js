// C:\Users\Owner\nova\static\js\chat-render.js

(() => {
"use strict"

function createRenderService(options = {}){

  const {
    state,
    elements = {},
    utils = {},
  } = options

  if(!state){
    throw new Error("NovaChatRender: state is required")
  }

  const el = {
    body: elements.body || document.body,
    chatList: elements.chatList || null,
    messages: elements.messages || null,
    input: elements.input || null,
    sendBtn: elements.sendBtn || null,
    stopBtn: elements.stopBtn || null,
    topbarTitle: elements.topbarTitle || null,
    jumpToLatestBtn: elements.jumpToLatestBtn || null,
    emptyState: elements.emptyState || null,
    emptySuggestions: elements.emptySuggestions || null,
    pendingAttachments: elements.pendingAttachments || null,
    messagesScroll: elements.messagesScroll || null,
  }

  const escapeHtml =
    typeof utils.escapeHtml === "function"
      ? utils.escapeHtml
      : (value) => String(value ?? "")
          .replaceAll("&","&amp;")
          .replaceAll("<","&lt;")
          .replaceAll(">","&gt;")
          .replaceAll('"',"&quot;")
          .replaceAll("'","&#039;")

  function renderMarkdown(text){
    if(window.NovaMarkdown && typeof window.NovaMarkdown.render === "function"){
      return window.NovaMarkdown.render(text || "")
    }
    return escapeHtml(text || "")
  }

  function renderMessages(){

    if(!el.messages) return

    const activeChat = state.activeChat

    if(!activeChat || !Array.isArray(activeChat.messages)){
      el.messages.innerHTML = ""
      return
    }

    const html = activeChat.messages.map((msg) => {

      const role = msg.role === "assistant" ? "assistant" : "user"

      const contentHtml = renderMarkdown(msg.content)

      return `
      <div class="message message-${role}">
        <div class="message-bubble">
          <div class="message-content">
            ${contentHtml}
          </div>
        </div>
      </div>
      `
    }).join("")

    el.messages.innerHTML = html
  }

  function renderChatList(){

    if(!el.chatList) return

    if(!Array.isArray(state.chats) || state.chats.length === 0){
      el.chatList.innerHTML = `<div class="chat-list-empty">No chats yet</div>`
      return
    }

    const html = state.chats.map((chat) => {

      const id = String(chat.chat_id || chat.id || "")
      const title = escapeHtml(chat.title || "New chat")

      const isActive = state.activeChatId === id

      return `
      <button
        type="button"
        class="chat-list-item ${isActive ? "is-active" : ""}"
        data-chat-id="${id}"
      >
        <span class="chat-list-item-title">${title}</span>
      </button>
      `
    }).join("")

    el.chatList.innerHTML = html
  }

  function renderAll(){
    renderChatList()
    renderMessages()
  }

  return {
    renderAll,
    renderMessages,
    renderChatList,
  }
}

window.NovaChatRender = {
  createRenderService,
}

})()