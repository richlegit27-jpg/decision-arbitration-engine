// C:\Users\Owner\nova\static\js\chat-sidebar-render.js

(() => {
"use strict"

function createChatSidebarRender(options = {}){
  const {
    state,
    elements = {},
  } = options

  if(!state){
    throw new Error("NovaChatSidebarRender: state is required")
  }

  const el = {
    chatList: elements.chatList || null,
    topbarTitle: elements.topbarTitle || null,
  }

  function ensureChatsArray(){
    if(!Array.isArray(state.chats)){
      state.chats = []
    }
    return state.chats
  }

  function getChatId(chat){
    return String(chat?.chat_id || chat?.id || "").trim()
  }

  function escapeHtml(value){
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;")
  }

  function updateTopbarTitle(){
    if(!el.topbarTitle){
      return
    }

    const chats = ensureChatsArray()
    const activeChatId = String(state.activeChatId || "").trim()
    const activeChat = chats.find((chat) => getChatId(chat) === activeChatId)

    el.topbarTitle.textContent = activeChat?.title || "New chat"
  }

  function renderChatList(){
    if(!el.chatList){
      return
    }

    const chats = ensureChatsArray()

    if(!chats.length){
      el.chatList.innerHTML = `<div class="chat-list-empty">No chats yet</div>`
      updateTopbarTitle()
      return
    }

    const activeChatId = String(state.activeChatId || "").trim()

    el.chatList.innerHTML = chats.map((chat) => {
      const chatId = getChatId(chat)
      const title = escapeHtml(chat?.title || "New chat")
      const isActive = chatId === activeChatId

      return `
        <div class="chat-list-row ${isActive ? "is-active" : ""}" data-chat-id="${escapeHtml(chatId)}">
          <button
            type="button"
            class="chat-list-item ${isActive ? "is-active" : ""}"
            data-chat-id="${escapeHtml(chatId)}"
            title="${title}"
          >
            <span class="chat-list-item-title">${title}</span>
          </button>

          <div class="chat-list-actions">
            <button type="button" class="chat-list-action" data-action="rename" data-chat-id="${escapeHtml(chatId)}" aria-label="Rename chat">✎</button>
            <button type="button" class="chat-list-action" data-action="delete" data-chat-id="${escapeHtml(chatId)}" aria-label="Delete chat">🗑</button>
          </div>
        </div>
      `
    }).join("")

    updateTopbarTitle()
  }

  return {
    ensureChatsArray,
    getChatId,
    escapeHtml,
    updateTopbarTitle,
    renderChatList,
  }
}

window.NovaChatSidebarRender = {
  create: createChatSidebarRender,
  createChatSidebarRender,
}

})()