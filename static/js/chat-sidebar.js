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
  btnVoice: document.getElementById("btnVoice"),
  btnOpenMemory: document.getElementById("btnOpenMemory"),
  btnWorkspaceFiles: document.getElementById("btnWorkspaceFiles"),
  btnChatThemeToggle: document.getElementById("btnChatThemeToggle"),
  btnDeleteAllChats: document.getElementById("btnDeleteAllChats"),
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
  onAfterDeleteAll: null,
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

function applyChatBackground(mode){
  const nextMode = String(mode || "").trim().toLowerCase() === "light" ? "light" : "dark"

  document.body.classList.remove("chat-bg-dark", "chat-bg-light")
  document.body.classList.add(nextMode === "light" ? "chat-bg-light" : "chat-bg-dark")

  state.chatBackground = nextMode

  if(chatStorage && typeof chatStorage.saveChatBackground === "function"){
    safeCall(() => chatStorage.saveChatBackground(nextMode))
  }

  if(el.btnChatThemeToggle){
    el.btnChatThemeToggle.textContent = `Chat background: ${nextMode === "light" ? "Light" : "Dark"}`
  }

  return nextMode
}

function initializeChatBackground(){
  let mode = "dark"

  if(chatStorage && typeof chatStorage.getChatBackground === "function"){
    mode = safeCall(() => chatStorage.getChatBackground(), "dark") || "dark"
  }else if(state.chatBackground){
    mode = state.chatBackground
  }

  applyChatBackground(mode)
}

function toggleChatBackground(){
  const current = String(state.chatBackground || "dark").trim().toLowerCase()
  const next = current === "light" ? "dark" : "light"
  applyChatBackground(next)
}

function openMemoryPanel(){
  if(el.btnOpenMemory){
    el.btnOpenMemory.blur()
  }

  if(typeof window.NovaMemoryPanel?.open === "function"){
    safeCall(() => window.NovaMemoryPanel.open())
    return
  }

  const panel = document.getElementById("memoryPanel")
  const backdrop = document.getElementById("memoryBackdrop")

  if(panel){
    panel.hidden = false
  }

  if(backdrop){
    backdrop.hidden = false
  }

  document.body.classList.add("memory-open")
}

function openWorkspaceFiles(){
  if(typeof window.NovaWorkspaceFiles?.open === "function"){
    safeCall(() => window.NovaWorkspaceFiles.open())
    return
  }

  const oldTrigger = document.getElementById("btnWorkspaceFilesOld")
  if(oldTrigger && typeof oldTrigger.click === "function"){
    oldTrigger.click()
  }
}

function triggerVoiceInput(){
  const voiceBtn = document.getElementById("voiceBtn")
  const composerApi = window.NovaComposer || null

  if(voiceBtn && typeof voiceBtn.click === "function"){
    voiceBtn.click()

    if(typeof composerApi?.focusInput === "function"){
      safeCall(() => composerApi.focusInput())
    }

    closeSidebar()
    return true
  }

  if(typeof composerApi?.focusInput === "function"){
    safeCall(() => composerApi.focusInput())
  }

  closeSidebar()
  return false
}

function resetUiAfterDeleteAll(){
  state.messages = []

  if(el.chatList){
    el.chatList.innerHTML = `
      <div class="chat-list-empty">
        No chats yet
      </div>
    `
  }

  const messages = document.getElementById("messages")
  if(messages){
    messages.innerHTML = ""
  }

  const topbarTitle = document.getElementById("topbarTitle")
  if(topbarTitle){
    topbarTitle.textContent = "New chat"
  }

  const emptyState = document.getElementById("emptyState")
  if(emptyState){
    emptyState.hidden = false
  }
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
  }else if(chatStorage && typeof chatStorage.loadMessages === "function"){
    state.messages = await safeCall(() => chatStorage.loadMessages(id), [])
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
  }else if(chatStorage && typeof chatStorage.removeChat === "function"){
    await safeCall(() => chatStorage.removeChat(id))
  }else{
    state.chats = getChats().filter((chat) => getChatId(chat) !== id)

    if(Array.isArray(state.messages) && state.activeChatId === id){
      state.messages = []
    }
  }

  if(chatStorage && typeof chatStorage.loadChats === "function"){
    await safeCall(() => chatStorage.loadChats())
  }

  if(state.activeChatId === id){
    const remaining = getChats()
    const nextActive = remaining[0] || null
    const nextId = getChatId(nextActive)

    state.activeChatId = nextId || ""

    if(typeof setActiveChat === "function"){
      safeCall(() => setActiveChat(nextId || ""))
    }

    if(nextId && chatStorage && typeof chatStorage.loadMessagesIntoState === "function"){
      await safeCall(() => chatStorage.loadMessagesIntoState(nextId))
    }else if(nextId && chatStorage && typeof chatStorage.loadMessages === "function"){
      state.messages = await safeCall(() => chatStorage.loadMessages(nextId), [])
    }else{
      state.messages = []
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

async function deleteAllChats(){
  const ok = window.confirm("Delete ALL chats? This cannot be undone.")
  if(!ok){
    return false
  }

  if(chatStorage && typeof chatStorage.removeAllChats === "function"){
    await safeCall(() => chatStorage.removeAllChats())
  }else{
    const chats = getChats()
    for(const chat of chats){
      const chatId = getChatId(chat)
      if(chatId){
        try{
          localStorage.removeItem(`nova_messages_${chatId}`)
        }catch(_error){}
      }
    }

    state.chats = []
    state.messages = []
    state.activeChatId = ""

    try{
      localStorage.removeItem("nova_chats")
      localStorage.removeItem("nova_active_chat_id")
    }catch(_error){}
  }

  if(chatStorage && typeof chatStorage.loadChats === "function"){
    await safeCall(() => chatStorage.loadChats())
  }

  state.activeChatId = ""

  if(typeof setActiveChat === "function"){
    safeCall(() => setActiveChat(""))
  }

  resetUiAfterDeleteAll()
  renderChatList()

  if(typeof window.NovaChatApp?.renderAll === "function"){
    safeCall(() => window.NovaChatApp.renderAll())
  }

  if(typeof callbacks.onAfterDeleteAll === "function"){
    safeCall(() => callbacks.onAfterDeleteAll())
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
    initializeChatBackground()
    return
  }

  eventsBound = true

  el.chatList?.addEventListener("click", onChatListClick)

  el.btnNewChat?.addEventListener("click", async () => {
    await createNewChat()
  })

  el.btnVoice?.addEventListener("click", () => {
    triggerVoiceInput()
  })

  el.btnOpenMemory?.addEventListener("click", () => {
    openMemoryPanel()
  })

  el.btnWorkspaceFiles?.addEventListener("click", () => {
    openWorkspaceFiles()
  })

  el.btnChatThemeToggle?.addEventListener("click", () => {
    toggleChatBackground()
  })

  el.btnDeleteAllChats?.addEventListener("click", async () => {
    await deleteAllChats()
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
  initializeChatBackground()
  renderChatList()
}

function init(){
  bindEvents()
  syncSidebarState()
  initializeChatBackground()
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
  deleteAllChats,
  applyChatBackground,
  toggleChatBackground,
  triggerVoiceInput,
}

})()