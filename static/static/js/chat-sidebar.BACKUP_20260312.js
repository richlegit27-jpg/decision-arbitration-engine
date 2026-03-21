// C:\Users\Owner\nova\static\js\chat-sidebar.js

(() => {
"use strict"

const chatStateApi = window.NovaChatState
const chatStorage = window.NovaChatStorage || null

if(!chatStateApi){
  throw new Error("NovaChatSidebar: window.NovaChatState is required")
}

const { state, setActiveChat } = chatStateApi

const el = {
  sidebar: document.getElementById("sidebar"),
  appShell: document.getElementById("appShell"),
  chatList: document.getElementById("chatList"),
  btnNewChat: document.getElementById("btnNewChat"),
  btnCloseSidebar: document.getElementById("btnCloseSidebar"),
  btnOpenSidebar: document.getElementById("btnOpenSidebar"),
  btnSidebarToggle: document.getElementById("btnSidebarToggle"),
}

let eventsBound = false
let callbacks = {
  onAfterCreate: null,
  onAfterSwitch: null,
  onAfterRename: null,
  onAfterDelete: null,
}

function escapeHtml(value){
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;")
}

function safeCall(fn, fallback = undefined){
  try{
    if(typeof fn === "function"){
      return fn()
    }
  }catch(error){
    console.error("NovaChatSidebar error:", error)
  }
  return fallback
}

function getChats(){
  if(!Array.isArray(state.chats)){
    state.chats = []
  }
  return state.chats
}

function getActiveChatId(){
  return String(state.activeChatId || "").trim()
}

function isSidebarOpen(){
  if(typeof state.sidebarOpen !== "boolean"){
    state.sidebarOpen = true
  }
  return state.sidebarOpen
}

function getChatId(chat){
  return String(chat?.chat_id || chat?.id || "").trim()
}

function getChatTitle(chat){
  return String(chat?.title || "New chat").trim() || "New chat"
}

function getChatMeta(chat){
  const updatedAt =
    chat?.updated_at ||
    chat?.updatedAt ||
    chat?.last_updated ||
    chat?.timestamp ||
    ""

  const rawCount =
    chat?.message_count ??
    chat?.messageCount ??
    chat?.messages_count ??
    null

  const parts = []

  if(rawCount != null && rawCount !== ""){
    const count = Number(rawCount)
    if(Number.isFinite(count)){
      parts.push(`${count} msg${count === 1 ? "" : "s"}`)
    }
  }

  if(updatedAt){
    parts.push(String(updatedAt))
  }

  return parts.join(" • ")
}

function moveFocusAfterClose(){
  const active = document.activeElement

  if(el.sidebar && active && el.sidebar.contains(active)){
    if(el.btnOpenSidebar && typeof el.btnOpenSidebar.focus === "function"){
      el.btnOpenSidebar.focus()
      return
    }

    if(el.btnSidebarToggle && typeof el.btnSidebarToggle.focus === "function"){
      el.btnSidebarToggle.focus()
      return
    }

    if(document.body && typeof document.body.focus === "function"){
      document.body.focus()
    }
  }
}

function syncSidebarState(){
  const open = isSidebarOpen()

  if(el.sidebar){
    el.sidebar.dataset.open = open ? "true" : "false"
  }

  if(document.body){
    document.body.classList.toggle("sidebar-open", open)
    document.body.classList.toggle("sidebar-closed", !open)
  }

  if(el.appShell){
    el.appShell.classList.toggle("sidebar-open", open)
    el.appShell.classList.toggle("sidebar-closed", !open)
  }

  if(el.btnOpenSidebar){
    el.btnOpenSidebar.hidden = open
    el.btnOpenSidebar.setAttribute("aria-expanded", open ? "true" : "false")
  }

  if(el.btnSidebarToggle){
    el.btnSidebarToggle.setAttribute("aria-expanded", open ? "true" : "false")
  }

  if(el.btnCloseSidebar){
    el.btnCloseSidebar.setAttribute("aria-expanded", open ? "true" : "false")
  }
}

function openSidebar(){
  state.sidebarOpen = true
  syncSidebarState()
}

function closeSidebar(){
  moveFocusAfterClose()
  state.sidebarOpen = false
  syncSidebarState()
}

function toggleSidebar(){
  if(isSidebarOpen()){
    closeSidebar()
    return
  }

  openSidebar()
}

function renderChatList(){
  const container = el.chatList
  if(!container){
    return
  }

  const chats = getChats()
  const activeChatId = getActiveChatId()

  if(!chats.length){
    container.innerHTML = `
      <div class="chat-list-empty">
        No chats yet
      </div>
    `
    return
  }

  const html = chats.map((chat) => {
    const id = getChatId(chat)
    const title = escapeHtml(getChatTitle(chat))
    const meta = escapeHtml(getChatMeta(chat))
    const active = id === activeChatId

    return `
      <div class="chat-list-row ${active ? "is-active" : ""}" data-chat-row data-chat-id="${escapeHtml(id)}">
        <button
          class="chat-list-item ${active ? "is-active" : ""}"
          type="button"
          data-chat-open
          data-chat-id="${escapeHtml(id)}"
          aria-pressed="${active ? "true" : "false"}"
          title="${title}"
        >
          <div class="chat-list-item-copy">
            <div class="chat-list-item-title" data-chat-title>${title}</div>
            <div class="chat-list-item-meta">${meta}</div>
          </div>
        </button>

        <div class="chat-list-actions">
          <button
            class="chat-list-action"
            type="button"
            data-chat-rename
            data-chat-id="${escapeHtml(id)}"
            aria-label="Rename chat"
            title="Rename"
          >✎</button>

          <button
            class="chat-list-action"
            type="button"
            data-chat-delete
            data-chat-id="${escapeHtml(id)}"
            aria-label="Delete chat"
            title="Delete"
          >✕</button>
        </div>
      </div>
    `
  }).join("")

  container.innerHTML = html
}

function updateChatTitle(chatId, title){
  const id = String(chatId || "").trim()
  const nextTitle = String(title || "").trim() || "New chat"

  if(!id){
    return false
  }

  const root = el.chatList || document
  let row = null

  try{
    row = root.querySelector(`[data-chat-id="${CSS.escape(id)}"]`)
  }catch(_error){
    row = root.querySelector(`[data-chat-id="${id.replaceAll('"', '\\"')}"]`)
  }

  if(!row){
    return false
  }

  const titleEl =
    row.querySelector("[data-chat-title]") ||
    row.querySelector(".chat-list-item-title")

  if(!titleEl){
    return false
  }

  titleEl.textContent = nextTitle
  return true
}

async function activateChat(chatId){
  const id = String(chatId || "").trim()
  if(!id){
    return null
  }

  state.activeChatId = id

  if(typeof setActiveChat === "function"){
    safeCall(() => setActiveChat(id))
  }

  if(chatStorage && typeof chatStorage.loadMessagesIntoState === "function"){
    await safeCall(() => chatStorage.loadMessagesIntoState(id))
  }

  renderChatList()

  if(typeof window.NovaChatApp?.renderAll === "function"){
    safeCall(() => window.NovaChatApp.renderAll())
  }

  closeSidebar()

  if(typeof callbacks.onAfterSwitch === "function"){
    safeCall(() => callbacks.onAfterSwitch(id))
  }

  return id
}

async function renameChat(chatId){
  const id = String(chatId || "").trim()
  if(!id){
    return null
  }

  const chats = getChats()
  const targetChat = chats.find((chat) => getChatId(chat) === id)
  if(!targetChat){
    return null
  }

  const currentTitle = getChatTitle(targetChat)
  const nextTitle = window.prompt("Rename chat", currentTitle)

  if(nextTitle === null){
    return null
  }

  const trimmed = String(nextTitle || "").trim() || "New chat"

  if(chatStorage && typeof chatStorage.renameChat === "function"){
    await safeCall(() => chatStorage.renameChat(id, trimmed))
  }else{
    targetChat.title = trimmed
  }

  updateChatTitle(id, trimmed)
  renderChatList()

  if(typeof window.NovaChatApp?.renderAll === "function"){
    safeCall(() => window.NovaChatApp.renderAll())
  }

  if(typeof callbacks.onAfterRename === "function"){
    safeCall(() => callbacks.onAfterRename(id, trimmed))
  }

  return trimmed
}

async function deleteChat(chatId){
  const id = String(chatId || "").trim()
  if(!id){
    return false
  }

  const ok = window.confirm("Delete this chat?")
  if(!ok){
    return false
  }

  if(chatStorage && typeof chatStorage.deleteChat === "function"){
    await safeCall(() => chatStorage.deleteChat(id))
  }else{
    state.chats = getChats().filter((chat) => getChatId(chat) !== id)

    if(Array.isArray(state.messages) && state.activeChatId === id){
      state.messages = []
    }
  }

  if(state.activeChatId === id){
    const remaining = getChats()
    const nextActive = remaining[0] || null
    const nextId = getChatId(nextActive)

    state.activeChatId = nextId || ""

    if(nextId && typeof setActiveChat === "function"){
      safeCall(() => setActiveChat(nextId))
    }
  }

  renderChatList()

  if(typeof window.NovaChatApp?.renderAll === "function"){
    safeCall(() => window.NovaChatApp.renderAll())
  }

  if(typeof callbacks.onAfterDelete === "function"){
    safeCall(() => callbacks.onAfterDelete(id))
  }

  return true
}

function onChatListClick(event){
  const openButton = event.target.closest("[data-chat-open]")
  if(openButton){
    const chatId = String(openButton.getAttribute("data-chat-id") || "").trim()
    if(chatId){
      safeCall(() => activateChat(chatId))
    }
    return
  }

  const renameButton = event.target.closest("[data-chat-rename]")
  if(renameButton){
    const chatId = String(renameButton.getAttribute("data-chat-id") || "").trim()
    if(chatId){
      safeCall(() => renameChat(chatId))
    }
    return
  }

  const deleteButton = event.target.closest("[data-chat-delete]")
  if(deleteButton){
    const chatId = String(deleteButton.getAttribute("data-chat-id") || "").trim()
    if(chatId){
      safeCall(() => deleteChat(chatId))
    }
  }
}

async function createNewChat(options = {}){
  if(!chatStorage || typeof chatStorage.createChat !== "function"){
    return null
  }

  const chat = await safeCall(() => chatStorage.createChat({
    title: "New chat",
  }), null)

  const chatId = getChatId(chat)

  if(chatId){
    state.activeChatId = chatId

    if(typeof setActiveChat === "function"){
      safeCall(() => setActiveChat(chatId))
    }
  }

  renderChatList()

  if(typeof window.NovaChatApp?.renderAll === "function"){
    safeCall(() => window.NovaChatApp.renderAll())
  }

  closeSidebar()

  const afterCreate =
    options?.onAfterCreate ||
    callbacks.onAfterCreate

  if(typeof afterCreate === "function"){
    safeCall(() => afterCreate(chat))
  }

  return chat
}

function bindEvents(options = {}){
  callbacks = {
    ...callbacks,
    ...options,
  }

  if(eventsBound){
    syncSidebarState()
    renderChatList()
    return
  }

  eventsBound = true

  el.chatList?.addEventListener("click", onChatListClick)

  el.btnNewChat?.addEventListener("click", async () => {
    await createNewChat()
  })

  el.btnCloseSidebar?.addEventListener("click", () => {
    closeSidebar()
  })

  el.btnOpenSidebar?.addEventListener("click", () => {
    openSidebar()
  })

  el.btnSidebarToggle?.addEventListener("click", () => {
    toggleSidebar()
  })

  window.addEventListener("resize", () => {
    syncSidebarState()
  })

  syncSidebarState()
  renderChatList()
}

function init(){
  bindEvents()
  syncSidebarState()
  renderChatList()
}

window.NovaChatSidebar = {
  init,
  bindEvents,
  renderChatList,
  createNewChat,
  updateChatTitle,
  syncSidebarState,
  openSidebar,
  closeSidebar,
  toggleSidebar,
  activateChat,
  renameChat,
  deleteChat,
}

})()