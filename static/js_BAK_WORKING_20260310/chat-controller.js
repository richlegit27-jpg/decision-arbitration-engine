// C:\Users\Owner\nova\static\js\chat-controller.js

(() => {
"use strict"

function createController(deps = {}){
  const {
    state,
    utils,
    el,
    sidebar,
    chatService,
    composer,
    messageService,
    uiState,
    dialog,
  } = deps

  if(!state){
    throw new Error("NovaChatController: state is required")
  }

  if(!el){
    throw new Error("NovaChatController: el is required")
  }

  function safe(fn, fallback = null){
    try {
      return typeof fn === "function" ? fn() : fallback
    } catch(error){
      console.error(error)
      return fallback
    }
  }

  function has(value){
    return value !== null && value !== undefined
  }

  function setTopbar(title, subtitle){
    if(el.topbarTitle){
      el.topbarTitle.textContent = title || "Nova"
    }

    if(el.topbarSubtitle){
      el.topbarSubtitle.textContent = subtitle || ""
    }
  }

  function getActiveChatId(){
    return state.activeChatId || state.chatId || ""
  }

  function setActiveChatId(chatId){
    state.activeChatId = chatId || ""
    state.chatId = chatId || ""
  }

  function getChats(){
    if(Array.isArray(state.chats)){
      return state.chats
    }

    state.chats = []
    return state.chats
  }

  function getMessages(){
    if(Array.isArray(state.messages)){
      return state.messages
    }

    state.messages = []
    return state.messages
  }

  function ensureChatShape(chat){
    if(!chat || typeof chat !== "object"){
      return null
    }

    return {
      chat_id: String(chat.chat_id || chat.id || ""),
      title: String(chat.title || "New chat"),
      updated: String(chat.updated || chat.updated_at || chat.created_at || ""),
    }
  }

  function sortChatsDescending(chats){
    return [...chats].sort((a, b) => {
      const aTime = Date.parse(a.updated || "") || 0
      const bTime = Date.parse(b.updated || "") || 0
      return bTime - aTime
    })
  }

  function getFilteredChats(){
    const chats = getChats()
    const raw = String(el.chatSearch?.value || "").trim().toLowerCase()

    if(!raw){
      return sortChatsDescending(chats)
    }

    return sortChatsDescending(
      chats.filter(chat => {
        const title = String(chat.title || "").toLowerCase()
        const id = String(chat.chat_id || "").toLowerCase()
        return title.includes(raw) || id.includes(raw)
      })
    )
  }

  function renderChatList(){
    if(!el.chatList){
      return
    }

    const chats = getFilteredChats()
    const activeChatId = getActiveChatId()

    el.chatList.innerHTML = ""

    if(!chats.length){
      const empty = document.createElement("div")
      empty.className = "chat-list-empty"
      empty.textContent = "No chats yet"
      el.chatList.appendChild(empty)
      return
    }

    const fragment = document.createDocumentFragment()

    chats.forEach(chat => {
      const row = document.createElement("button")
      row.type = "button"
      row.className = "chat-list-item"
      row.dataset.chatId = chat.chat_id

      if(chat.chat_id === activeChatId){
        row.classList.add("active")
      }

      const title = document.createElement("div")
      title.className = "chat-list-item-title"
      title.textContent = chat.title || "New chat"

      const meta = document.createElement("div")
      meta.className = "chat-list-item-meta"
      meta.textContent = formatChatTime(chat.updated)

      row.appendChild(title)
      row.appendChild(meta)

      row.addEventListener("click", () => {
        void openChat(chat.chat_id)
        closeSidebar()
      })

      fragment.appendChild(row)
    })

    el.chatList.appendChild(fragment)
  }

  function formatChatTime(value){
    if(!value){
      return ""
    }

    const date = new Date(value)

    if(Number.isNaN(date.getTime())){
      return ""
    }

    try {
      return new Intl.DateTimeFormat(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      }).format(date)
    } catch {
      return date.toLocaleString()
    }
  }

  function normalizeMessage(message){
    if(!message || typeof message !== "object"){
      return null
    }

    return {
      id: String(message.id || message.message_id || crypto.randomUUID()),
      role: String(message.role || "assistant"),
      content: String(message.content || message.text || ""),
      created_at: String(message.created_at || message.timestamp || ""),
      attachments: Array.isArray(message.attachments) ? message.attachments : [],
    }
  }

  function renderMessages(){
    if(typeof uiState?.renderMessages === "function"){
      uiState.renderMessages()
      return
    }

    if(typeof window.NovaRender?.renderMessages === "function"){
      window.NovaRender.renderMessages({
        container: el.messages,
        messages: getMessages(),
        activeChatId: getActiveChatId(),
      })
      return
    }

    if(!el.messages){
      return
    }

    el.messages.innerHTML = ""

    const fragment = document.createDocumentFragment()

    getMessages().forEach(message => {
      const row = document.createElement("div")
      row.className = `message-row ${message.role === "user" ? "user" : "assistant"}`

      const bubble = document.createElement("div")
      bubble.className = "message-bubble"
      bubble.textContent = message.content || ""

      row.appendChild(bubble)
      fragment.appendChild(row)
    })

    el.messages.appendChild(fragment)
    scrollToBottom()
  }

  function scrollToBottom(){
    if(!el.messages){
      return
    }

    requestAnimationFrame(() => {
      el.messages.scrollTop = el.messages.scrollHeight
    })
  }

  function renderAll(){
    renderChatList()
    renderMessages()
    updateHeader()

    if(typeof uiState?.renderAll === "function"){
      uiState.renderAll()
    }
  }

  function updateHeader(){
    const activeChatId = getActiveChatId()
    const chats = getChats()
    const active = chats.find(chat => chat.chat_id === activeChatId)

    if(active){
      setTopbar(active.title || "Chat", active.chat_id)
      return
    }

    setTopbar("Nova", "Ready")
  }

  async function refreshChats(){
    let chats = []

    if(typeof chatService?.loadChats === "function"){
      chats = await chatService.loadChats()
    } else if(typeof window.NovaAPI?.getChats === "function"){
      const response = await window.NovaAPI.getChats()
      chats = response?.chats || []
    }

    state.chats = (Array.isArray(chats) ? chats : [])
      .map(ensureChatShape)
      .filter(Boolean)

    renderChatList()
    updateHeader()

    return state.chats
  }

  async function refreshMessages(chatId){
    const targetChatId = String(chatId || getActiveChatId() || "").trim()

    if(!targetChatId){
      state.messages = []
      renderMessages()
      return []
    }

    let messages = []

    if(typeof chatService?.loadMessages === "function"){
      messages = await chatService.loadMessages(targetChatId)
    } else if(typeof window.NovaAPI?.getChat === "function"){
      const response = await window.NovaAPI.getChat(targetChatId)
      messages = response?.messages || []
    }

    state.messages = (Array.isArray(messages) ? messages : [])
      .map(normalizeMessage)
      .filter(Boolean)

    renderMessages()
    return state.messages
  }

  async function createNewChat(){
    let chat = null

    if(typeof chatService?.createChat === "function"){
      chat = await chatService.createChat()
    } else {
      chat = {
        chat_id: crypto.randomUUID(),
        title: "New chat",
        updated: new Date().toISOString(),
      }

      getChats().unshift(chat)
    }

    const normalized = ensureChatShape(chat)

    if(!normalized){
      return null
    }

    const chats = getChats()
    const existingIndex = chats.findIndex(item => item.chat_id === normalized.chat_id)

    if(existingIndex >= 0){
      chats[existingIndex] = normalized
    } else {
      chats.unshift(normalized)
    }

    setActiveChatId(normalized.chat_id)
    state.messages = []

    renderAll()
    closeSidebar()

    if(typeof composer?.focus === "function"){
      composer.focus()
    } else {
      el.input?.focus()
    }

    return normalized
  }

  async function openChat(chatId){
    const targetChatId = String(chatId || "").trim()

    if(!targetChatId){
      return
    }

    setActiveChatId(targetChatId)
    renderChatList()
    updateHeader()
    await refreshMessages(targetChatId)
    scrollToBottom()
  }

  async function ensureActiveChat(){
    const activeChatId = getActiveChatId()

    if(activeChatId){
      return activeChatId
    }

    const created = await createNewChat()
    return created?.chat_id || ""
  }

  function buildFallbackPayload(activeChatId){
    const message = typeof composer?.getText === "function"
      ? composer.getText()
      : String(el.input?.value || "").trim()

    const files = typeof attachments?.getFiles === "function"
      ? attachments.getFiles()
      : []

    return {
      chat_id: activeChatId,
      message,
      files,
    }
  }

  async function sendMessage(){
    const activeChatId = await ensureActiveChat()

    if(!activeChatId){
      return
    }

    let result = null

    if(typeof messageService?.sendMessage === "function"){
      result = await messageService.sendMessage(activeChatId)
    } else {
      const payload = buildFallbackPayload(activeChatId)

      if(!payload.message && !payload.files.length){
        return
      }

      if(typeof window.NovaAPI?.sendMessage === "function"){
        result = await window.NovaAPI.sendMessage(payload)
      }
    }

    await refreshChats()
    await refreshMessages(activeChatId)

    if(typeof composer?.clear === "function"){
      composer.clear()
    } else if(el.input){
      el.input.value = ""
    }

    if(typeof attachments?.clear === "function"){
      attachments.clear()
    }

    scrollToBottom()
    return result
  }

  async function regenerateLastAssistantReply(){
    const messages = getMessages()

    if(!messages.length){
      return
    }

    const lastUser = [...messages].reverse().find(item => item.role === "user")

    if(!lastUser?.content){
      return
    }

    if(typeof composer?.setText === "function"){
      composer.setText(lastUser.content)
    } else if(el.input){
      el.input.value = lastUser.content
    }

    await sendMessage()
  }

  function onSearchInput(){
    renderChatList()
  }

  function onMessageKeydown(event){
    if(!event){
      return
    }

    if(event.key !== "Enter"){
      return
    }

    if(event.shiftKey){
      return
    }

    event.preventDefault()
    void sendMessage()
  }

  function openSidebar(){
    el.sidebar?.classList.add("is-open")
    el.mobileOverlay?.classList.add("is-visible")

    safe(() => sidebar?.open?.())
  }

  function closeSidebar(){
    el.sidebar?.classList.remove("is-open")
    el.mobileOverlay?.classList.remove("is-visible")

    safe(() => sidebar?.close?.())
  }

  function toggleSidebar(){
    const isOpen = el.sidebar?.classList.contains("is-open")
    if(isOpen){
      closeSidebar()
    } else {
      openSidebar()
    }
  }

  function bindUI(){
    el.btnSidebarToggle?.addEventListener("click", toggleSidebar)
    el.mobileOverlay?.addEventListener("click", closeSidebar)
    el.btnNewChat?.addEventListener("click", () => void createNewChat())
    el.chatSearch?.addEventListener("input", onSearchInput)
    el.btnSend?.addEventListener("click", () => void sendMessage())
    el.input?.addEventListener("keydown", onMessageKeydown)

    document.addEventListener("click", event => {
      const actionEl = event.target?.closest?.("[data-action]")
      if(!actionEl){
        return
      }

      const action = String(actionEl.dataset.action || "").trim()

      if(action === "new-chat"){
        void createNewChat()
        return
      }

      if(action === "send"){
        void sendMessage()
        return
      }

      if(action === "regenerate"){
        void regenerateLastAssistantReply()
        return
      }

      if(action === "toggle-sidebar"){
        toggleSidebar()
      }
    })
  }

  async function hydrateInitialState(){
    await refreshChats()

    const chats = getChats()
    const activeChatId = getActiveChatId()

    if(activeChatId){
      await refreshMessages(activeChatId)
      return
    }

    if(chats.length){
      setActiveChatId(chats[0].chat_id)
      await refreshMessages(chats[0].chat_id)
      renderChatList()
      updateHeader()
      return
    }

    state.messages = []
    renderAll()
  }

  async function init(){
    bindUI()
    renderAll()

    try {
      await hydrateInitialState()
    } catch(error){
      console.error("Failed to initialize controller:", error)

      if(typeof dialog?.alert === "function"){
        dialog.alert("Failed to load chats.")
      }

      setTopbar("Nova", "Load failed")
    }
  }

  return {
    init,
    openChat,
    refreshChats,
    refreshMessages,
    createNewChat,
    sendMessage,
    regenerateLastAssistantReply,
    openSidebar,
    closeSidebar,
    toggleSidebar,
    renderAll,
  }
}

window.NovaChatController = {
  createController,
}

})()