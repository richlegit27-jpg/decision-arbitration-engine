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

  function getChatTitle(chat){
    return String(chat?.title || "New chat").trim() || "New chat"
  }

  function getChatMessageCount(chat){
    const value = Number(chat?.message_count || chat?.messages_count || 0)
    return Number.isFinite(value) && value > 0 ? value : 0
  }

  function getChatUpdatedAt(chat){
    return String(chat?.updated_at || chat?.modified_at || chat?.created_at || "").trim()
  }

  function formatChatMeta(chat){
    const parts = []
    const messageCount = getChatMessageCount(chat)
    const updatedAt = getChatUpdatedAt(chat)

    if(messageCount > 0){
      parts.push(messageCount === 1 ? "1 message" : `${messageCount} messages`)
    }

    if(updatedAt){
      parts.push(updatedAt)
    }

    return parts.join(" • ")
  }

  function updateTopbarTitle(){
    if(!el.topbarTitle){
      return
    }

    const chats = ensureChatsArray()
    const activeChatId = String(state.activeChatId || "").trim()
    const activeChat = chats.find((chat) => getChatId(chat) === activeChatId)

    el.topbarTitle.textContent = getChatTitle(activeChat)
  }

  function renderEmptyState(){
    if(!el.chatList){
      return
    }

    el.chatList.innerHTML = `<div class="chat-list-empty">No chats yet</div>`
    updateTopbarTitle()
  }

  function renderChatRow(chat, activeChatId){
    const chatId = getChatId(chat)
    const titleText = getChatTitle(chat)
    const title = escapeHtml(titleText)
    const metaText = formatChatMeta(chat)
    const meta = escapeHtml(metaText)
    const isActive = chatId === activeChatId
    const safeChatId = escapeHtml(chatId)

    return `
      <div class="chat-list-row ${isActive ? "is-active" : ""}" data-chat-id="${safeChatId}">
        <button
          type="button"
          class="chat-list-item ${isActive ? "is-active" : ""}"
          data-chat-id="${safeChatId}"
          title="${title}"
          aria-current="${isActive ? "page" : "false"}"
        >
          <span class="chat-list-item-copy">
            <span class="chat-list-item-title">${title}</span>
            ${meta ? `<span class="chat-list-item-meta">${meta}</span>` : ""}
          </span>
        </button>

        <div class="chat-list-actions">
          <button type="button" class="chat-list-action" data-action="rename" data-chat-id="${safeChatId}" aria-label="Rename chat">✎</button>
          <button type="button" class="chat-list-action" data-action="delete" data-chat-id="${safeChatId}" aria-label="Delete chat">🗑</button>
        </div>
      </div>
    `
  }

  function renderChatList(){
    if(!el.chatList){
      return
    }

    const chats = ensureChatsArray()

    if(!chats.length){
      renderEmptyState()
      return
    }

    const activeChatId = String(state.activeChatId || "").trim()

    el.chatList.innerHTML = chats.map((chat) => {
      return renderChatRow(chat, activeChatId)
    }).join("")

    updateTopbarTitle()
  }

  return {
    ensureChatsArray,
    getChatId,
    escapeHtml,
    getChatTitle,
    getChatMessageCount,
    getChatUpdatedAt,
    formatChatMeta,
    updateTopbarTitle,
    renderEmptyState,
    renderChatList,
  }
}

window.NovaChatSidebarRender = {
  create: createChatSidebarRender,
  createChatSidebarRender,
}

})()