// C:\Users\Owner\nova\static\js\chat-orchestrator.js

(() => {
"use strict"

function createChatOrchestrator(options = {}){

  const {
    state,
    chatStorage,
    chatSidebar,
    chatMessages,
    composer,
    memoryPanel,
    getAttachmentsService,
    getStreamService,
  } = options

  if(!state){
    throw new Error("NovaChatOrchestrator: state is required")
  }

  if(!chatStorage){
    throw new Error("NovaChatOrchestrator: chatStorage is required")
  }

  if(!chatSidebar){
    throw new Error("NovaChatOrchestrator: chatSidebar is required")
  }

  if(!chatMessages){
    throw new Error("NovaChatOrchestrator: chatMessages is required")
  }

  if(!composer){
    throw new Error("NovaChatOrchestrator: composer is required")
  }

  if(!memoryPanel){
    throw new Error("NovaChatOrchestrator: memoryPanel is required")
  }

  function applyChatBackgroundClass(){
    const body = document.body

    if(!body){
      return "dark"
    }

    const background =
      typeof chatStorage.getChatBackground === "function"
        ? chatStorage.getChatBackground()
        : "dark"

    body.classList.remove("chat-bg-dark", "chat-bg-light")
    body.classList.add(background === "light" ? "chat-bg-light" : "chat-bg-dark")

    state.chatBackground = background
    return background
  }

  function toggleChatBackground(){
    const current =
      typeof chatStorage.getChatBackground === "function"
        ? chatStorage.getChatBackground()
        : "dark"

    const next = current === "light" ? "dark" : "light"

    if(typeof chatStorage.saveChatBackground === "function"){
      chatStorage.saveChatBackground(next)
    }

    applyChatBackgroundClass()
    renderShell()
    renderMessages()

    return next
  }

  function bindBackgroundToggleShortcut(){
    window.addEventListener("keydown", (event) => {
      const isModifier = event.ctrlKey || event.metaKey
      const key = String(event.key || "").toLowerCase()

      if(!isModifier || !event.shiftKey || key !== "b"){
        return
      }

      const tagName = String(event.target?.tagName || "").toLowerCase()

      const isTypingTarget =
        tagName === "input" ||
        tagName === "textarea" ||
        event.target?.isContentEditable

      if(isTypingTarget){
        return
      }

      event.preventDefault()
      toggleChatBackground()
    })
  }

  function renderShell(){
    if(typeof chatSidebar.renderChatList === "function"){
      chatSidebar.renderChatList()
    }

    if(typeof composer.updateComposerState === "function"){
      composer.updateComposerState()
    }
  }

  function renderMessages(){
    if(typeof chatMessages.renderMessages === "function"){
      chatMessages.renderMessages()
    }
  }

  function renderAll(){
    renderShell()
    renderMessages()
  }

  function scrollMessagesToBottom(force = false){
    if(typeof chatMessages.scrollToBottom === "function"){
      chatMessages.scrollToBottom(force)
    }
  }

  function syncSidebarAndLayout(){
    if(typeof chatSidebar.syncSidebarState === "function"){
      chatSidebar.syncSidebarState()
    }

    if(typeof chatMessages.updateScrollState === "function"){
      chatMessages.updateScrollState()
    }

    if(typeof composer.autoResizeInput === "function"){
      composer.autoResizeInput()
    }

    if(typeof composer.updateComposerState === "function"){
      composer.updateComposerState()
    }
  }

  function syncMessagesAfterLoad(messages){
    if(typeof chatMessages.syncMessagesFromStorage === "function"){
      chatMessages.syncMessagesFromStorage(messages)
    }
    scrollMessagesToBottom(true)
  }

  function getMessages(){
    if(!Array.isArray(state.messages)){
      state.messages = []
    }
    return state.messages
  }

  function getMessageId(message){
    return String(message?.message_id || message?.id || "").trim()
  }

  function getMessageRole(message){
    return String(message?.role || "").toLowerCase()
  }

  function getAttachmentIdentity(att){
    return String(
      att?.attachment_id ||
      att?.id ||
      att?.url ||
      att?.preview_url ||
      att?.storage_path ||
      att?.filename ||
      att?.name ||
      ""
    ).trim()
  }

  function hydrateChatTitle(chatId, messages = []){
    const targetChatId = String(chatId || "").trim()

    if(!targetChatId){
      return
    }

    const firstUserMessage = messages.find(m => (m.role || "").toLowerCase() === "user")
    const firstUserText = String(firstUserMessage?.content || "").trim()

    if(typeof chatStorage.hydrateChatFromMessageActivity === "function"){
      const chat = chatStorage.hydrateChatFromMessageActivity(
        targetChatId,
        firstUserText,
        []
      )

      const nextTitle = String(chat?.title || "").trim()

      if(nextTitle && typeof chatSidebar.updateChatTitle === "function"){
        chatSidebar.updateChatTitle(targetChatId, nextTitle)
      }

      return
    }
  }

  function persistCurrentMessages(){
    if(!state.activeChatId){
      return
    }

    if(typeof chatStorage.saveMessages !== "function"){
      return
    }

    const saved = chatStorage.saveMessages(state.activeChatId, state.messages)
    state.messages = Array.isArray(saved) ? saved.slice() : []
    hydrateChatTitle(state.activeChatId, state.messages)
  }

  function syncPersistedMessages(options = {}){
    const preserveScroll = !!options.preserveScroll

    persistCurrentMessages()

    if(typeof chatMessages.syncMessagesFromStorage === "function"){
      chatMessages.syncMessagesFromStorage(state.messages)
    }

    renderShell()

    if(preserveScroll){
      if(typeof chatMessages.updateScrollState === "function"){
        chatMessages.updateScrollState()
      }
    }else{
      scrollMessagesToBottom(false)
    }
  }

  function bindStreamCallbacks(){
    const streamService =
      typeof getStreamService === "function"
        ? getStreamService()
        : null

    if(!streamService || typeof streamService.setCallbacks !== "function"){
      return
    }

    streamService.setCallbacks({
      onStart(){
        state.isStreaming = true
      },
      onDone(){
        state.isStreaming = false
        persistCurrentMessages()
        renderShell()
        scrollMessagesToBottom(true)
      },
      onError(err){
        console.error("NovaChatApp stream error:", err)
        state.isStreaming = false
      },
    })
  }

  function bindAttachmentCallbacks(){
    const attachmentsService =
      typeof getAttachmentsService === "function"
        ? getAttachmentsService()
        : null

    if(!attachmentsService){
      return
    }

    if(typeof attachmentsService.setOnChange === "function"){
      attachmentsService.setOnChange(() => {
        if(typeof composer.updateComposerState === "function"){
          composer.updateComposerState()
        }
      })
    }
  }

  function bindAppEvents(){
    if(typeof composer.bindEvents === "function"){
      composer.bindEvents({
        onNeedsCreateChat: async () => {
          return await createChatAndLoad()
        },
        onAfterSend(){
          syncPersistedMessages({ preserveScroll: false })
        },
      })
    }
  }

  async function loadActiveChatMessages(){
    const activeChatId = String(state.activeChatId || "").trim()

    if(!activeChatId){
      state.messages = []
      return []
    }

    let messages = []

    if(typeof chatStorage.loadMessages === "function"){
      messages = await chatStorage.loadMessages(activeChatId)
    }

    state.messages = Array.isArray(messages) ? messages.slice() : []

    syncMessagesAfterLoad(state.messages)
    hydrateChatTitle(activeChatId, state.messages)
    renderShell()

    return state.messages
  }

  async function createChatAndLoad(){
    let chat = null

    if(typeof chatSidebar.createNewChat === "function"){
      chat = await chatSidebar.createNewChat()
    }

    await loadActiveChatMessages()
    return chat
  }

  async function init(){
    applyChatBackgroundClass()

    if(typeof chatSidebar.init === "function"){
      chatSidebar.init()
    }

    if(typeof chatSidebar.syncSidebarState === "function"){
      chatSidebar.syncSidebarState()
    }

    bindAttachmentCallbacks()
    bindStreamCallbacks()
    bindAppEvents()
    bindBackgroundToggleShortcut()

    if(typeof memoryPanel.init === "function"){
      memoryPanel.init()
    }

    if(typeof chatStorage.loadChats === "function"){
      await chatStorage.loadChats()
    }

    await loadActiveChatMessages()

    renderShell()
    scrollMessagesToBottom(true)

    if(typeof composer.focusInput === "function"){
      composer.focusInput()
    }
  }

  return {
    init,
    renderAll,
    loadActiveChatMessages,
    createChatAndLoad,
    scrollMessagesToBottom,
    syncSidebarAndLayout,
    applyChatBackgroundClass,
    toggleChatBackground,
    openMemoryPanel: typeof memoryPanel.open === "function" ? memoryPanel.open : () => {},
    closeMemoryPanel: typeof memoryPanel.close === "function" ? memoryPanel.close : () => {},
    refreshMemoryList: typeof memoryPanel.refresh === "function" ? memoryPanel.refresh : () => {},
  }

}

window.NovaChatOrchestrator = {
  create: createChatOrchestrator,
  createChatOrchestrator,
}

})()