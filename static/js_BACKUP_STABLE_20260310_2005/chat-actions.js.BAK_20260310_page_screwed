// C:\Users\Owner\nova\static\js\chat-actions.js

(() => {
"use strict"

function createChatActionsService(options = {}){
  const {
    state,
    elements = {},
    services = {},
    utils = {},
    ui = {},
    render = {},
  } = options

  if(!state){
    throw new Error("NovaChatActions: state is required")
  }

  const el = {
    input: elements.input || null,
  }

  const chatService = services.chatService || null
  const attachmentsService = services.attachmentsService || null
  const streamService = services.streamService || null

  const ensureChatsArray =
    typeof utils.ensureChatsArray === "function"
      ? utils.ensureChatsArray
      : (() => {
          if(!Array.isArray(state.chats)){
            state.chats = []
          }
          return state.chats
        })

  const ensureMessagesArray =
    typeof utils.ensureMessagesArray === "function"
      ? utils.ensureMessagesArray
      : (() => {
          if(!Array.isArray(state.messages)){
            state.messages = []
          }
          return state.messages
        })

  const getChatId =
    typeof utils.getChatId === "function"
      ? utils.getChatId
      : ((chat) => String(chat?.chat_id || chat?.id || ""))

  const makeId =
    typeof utils.makeId === "function"
      ? utils.makeId
      : ((prefix) => `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`)

  const normalizeChat =
    typeof utils.normalizeChat === "function"
      ? utils.normalizeChat
      : ((chat) => {
          const chatId = String(chat?.chat_id || chat?.id || makeId("chat"))
          return {
            ...chat,
            id: chatId,
            chat_id: chatId,
            title: String(chat?.title || chat?.name || "New chat").trim() || "New chat",
          }
        })

  const normalizeMessage =
    typeof utils.normalizeMessage === "function"
      ? utils.normalizeMessage
      : ((message) => ({
          ...message,
          id: String(message?.id || message?.message_id || makeId("msg")),
          role: String(message?.role || "assistant"),
          content: String(message?.content || ""),
          attachments: Array.isArray(message?.attachments) ? message.attachments : [],
        }))

  const autoResizeInput = ui.autoResizeInput || (() => {})
  const focusInput = ui.focusInput || (() => {})
  const scrollToBottom = ui.scrollToBottom || (() => {})

  const updateComposerState = render.updateComposerState || (() => {})
  const renderMessages = render.renderMessages || (() => {})
  const renderPendingAttachments = render.renderPendingAttachments || (() => {})
  const renderAll = render.renderAll || (() => {})

  function setPendingFiles(files = []){
    const normalized = Array.isArray(files) ? files.filter(Boolean) : []
    state.pendingFiles = normalized
    state.pendingAttachments = normalized
    renderPendingAttachments()
    updateComposerState()
  }

  function removePendingFileByIndex(index){
    const fileIndex = Number(index)
    if(!Number.isFinite(fileIndex) || fileIndex < 0){
      return
    }

    const next = [...(state.pendingFiles || [])]
    next.splice(fileIndex,1)
    setPendingFiles(next)

    if(attachmentsService?.setPendingFiles){
      attachmentsService.setPendingFiles(next)
    }
  }

  function openFilePicker(){
    if(attachmentsService?.openFilePicker){
      attachmentsService.openFilePicker()
      return
    }

    if(attachmentsService?.openPicker){
      attachmentsService.openPicker()
      return
    }

    if(attachmentsService?.pickFiles){
      attachmentsService.pickFiles()
    }
  }

  function stopStreaming(){
    try{
      streamService?.stop?.()
      streamService?.abort?.()
    }catch(e){
      console.error("Nova stopStreaming error:", e)
    }

    state.isStreaming = false
    updateComposerState()
    renderAll()
  }

  async function createChat(){
    try{
      const created = await chatService?.createChat?.()
      const chat = normalizeChat(created || {})

      const chats = ensureChatsArray()
      chats.unshift(chat)

      state.activeChatId = getChatId(chat)
      state.messages = []
      renderAll()
      focusInput()

      return chat
    }catch(err){
      console.error("Nova createChat error:", err)
    }
  }

  async function loadChats(){
    try{
      const result = await chatService?.listChats?.()
      const incoming = Array.isArray(result)
        ? result
        : result?.chats || []

      state.chats = incoming.map(normalizeChat)
    }catch(err){
      console.error("Nova loadChats error:", err)
      state.chats = []
    }

    renderAll()
    return ensureChatsArray()
  }

  async function loadChat(chatId){
    const id = String(chatId || "").trim()
    if(!id){
      return
    }

    state.activeChatId = id
    renderAll()

    try{
      const result = await chatService?.getMessages?.(id)
      const incoming = Array.isArray(result)
        ? result
        : result?.messages || []

      state.messages = incoming.map(normalizeMessage)
      renderAll()
      scrollToBottom(true)
      focusInput()
    }catch(err){
      console.error("Nova loadChat error:", err)
    }

    return ensureMessagesArray()
  }

  async function sendCurrentMessage(){
    if(state.isStreaming){
      return
    }

    const text = String(el.input?.value || "").trim()
    const files = Array.isArray(state.pendingFiles) ? [...state.pendingFiles] : []

    if(!text && files.length === 0){
      updateComposerState()
      return
    }

    let activeChatId = String(state.activeChatId || "")

    if(!activeChatId){
      const chat = await createChat()
      activeChatId = getChatId(chat)
    }

    const messages = ensureMessagesArray()

    messages.push(normalizeMessage({
      id: makeId("msg"),
      role: "user",
      content: text,
      attachments: files,
    }))

    state.isStreaming = true

    messages.push(normalizeMessage({
      id: makeId("msg"),
      role: "assistant",
      content: "",
      attachments: [],
    }))

    if(el.input){
      el.input.value = ""
    }

    state.pendingFiles = []
    state.pendingAttachments = []

    attachmentsService?.clearPendingFiles?.()

    autoResizeInput()
    renderAll()
    scrollToBottom(true)

    try{
      if(streamService?.send){
        await streamService.send({
          chatId: activeChatId,
          message: text,
          files,
          scrollEl: document.getElementById("messagesScroll"),
        })
      }
    }catch(err){
      console.error("Nova sendCurrentMessage error:", err)
    }finally{
      autoResizeInput()
      updateComposerState()
      focusInput()
    }
  }

  return {
    loadChats,
    loadChat,
    createChat,
    sendCurrentMessage,
    setPendingFiles,
    removePendingFileByIndex,
    stopStreaming,
    openFilePicker,
  }
}

window.NovaChatActions = {
  create: createChatActionsService,
  createChatActionsService,
}

})()