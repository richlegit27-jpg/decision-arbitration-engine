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

  function renderAll(){
    chatSidebar.renderChatList()
    chatMessages.renderMessages()
    composer.updateComposerState()
  }

  function scrollMessagesToBottom(force = false){
    chatMessages.scrollToBottom(force)
  }

  function syncSidebarAndLayout(){
    chatSidebar.syncSidebarState()
    chatMessages.updateScrollState()
    composer.autoResizeInput()
    composer.updateComposerState()
  }

  function syncMessagesAfterLoad(messages){
    chatMessages.syncMessagesFromStorage(messages)
    scrollMessagesToBottom(true)
  }

  async function loadActiveChatMessages(){
    const activeChatId = String(state.activeChatId || "").trim()

    if(!activeChatId){
      chatMessages.clearMessages()
      renderAll()
      return []
    }

    const messages = await chatStorage.loadMessages(activeChatId)
    syncMessagesAfterLoad(messages)
    renderAll()
    return messages
  }

  async function createChatAndLoad(){
    const chat = await chatSidebar.createNewChat({
      onAfterCreate(createdChat){
        const chatId = String(createdChat?.chat_id || createdChat?.id || "").trim()

        if(chatId){
          state.activeChatId = chatId
        }

        state.messages = []

        renderAll()
        scrollMessagesToBottom(true)
      },
    })

    return chat
  }

  async function retryMessage(text){
    composer.setInputValue(text)
    composer.focusInput()

    await composer.sendCurrentMessage({
      onNeedsCreateChat: createChatAndLoad,

      onAfterSend(){
        renderAll()
        scrollMessagesToBottom(true)
      },

      onSendError(){
        renderAll()
      },
    })
  }

  function bindStreamCallbacks(){
    const streamService = typeof getStreamService === "function"
      ? getStreamService()
      : null

    if(!streamService || typeof streamService.setCallbacks !== "function"){
      return
    }

    streamService.setCallbacks({
      onStart(payload = {}){
        const messageId = String(payload?.messageId || payload?.id || `msg_${Date.now()}`).trim()

        state.isStreaming = true
        state.streamingMessageId = messageId

        chatMessages.upsertStreamingAssistantMessage(messageId)

        renderAll()
        scrollMessagesToBottom(true)
      },

      onMeta(payload = {}){
        const messageId = String(
          payload?.messageId ||
          payload?.assistant_message_id ||
          state.streamingMessageId ||
          ""
        ).trim()

        if(!messageId){
          return
        }

        state.streamingMessageId = messageId
        chatMessages.upsertStreamingAssistantMessage(messageId)
        renderAll()
      },

      onToken(token){
        const messageId = String(state.streamingMessageId || "").trim()

        if(!messageId){
          return
        }

        chatMessages.appendToStreamingMessage(messageId, token)
        scrollMessagesToBottom(false)
      },

      onDone(payload = {}){
        const messageId = String(
          payload?.messageId ||
          payload?.assistant_message_id ||
          state.streamingMessageId ||
          ""
        ).trim()

        if(
          messageId &&
          payload?.content &&
          !chatMessages.findMessageById(messageId)?.content
        ){
          chatMessages.replaceMessage(messageId, {
            content: String(payload.content || ""),
          })
        }

        state.isStreaming = false
        state.streamingMessageId = null

        chatMessages.finishStreamingMessage()

        renderAll()
        scrollMessagesToBottom(true)
      },

      onError(err){
        console.error("NovaChatApp stream error:", err)

        state.isStreaming = false
        state.streamingMessageId = null

        chatMessages.finishStreamingMessage()

        renderAll()
      },

      onFinally(){
        state.isStreaming = false
        state.streamingMessageId = null

        composer.markStreaming(false)
        chatMessages.finishStreamingMessage()
        composer.updateComposerState()

        renderAll()
      },
    })
  }

  function bindAttachmentCallbacks(){
    const attachmentsService = typeof getAttachmentsService === "function"
      ? getAttachmentsService()
      : null

    if(!attachmentsService){
      return
    }

    if(typeof attachmentsService.setOnChange === "function"){
      attachmentsService.setOnChange((files) => {
        composer.setPendingFiles(Array.isArray(files) ? files : [])
        composer.updateComposerState()
      })
    }
  }

  function bindAppEvents(){
    chatSidebar.bindEvents({
      onAfterCreate(){
        renderAll()
        scrollMessagesToBottom(true)
        composer.focusInput()
      },

      onAfterSwitch(){
        renderAll()
        scrollMessagesToBottom(true)
        composer.focusInput()
      },

      onAfterRename(){
        renderAll()
        composer.focusInput()
      },

      onAfterDelete(){
        renderAll()
        scrollMessagesToBottom(true)
        composer.focusInput()
      },
    })

    chatMessages.bindEvents({
      onRetry: async (text) => {
        await retryMessage(text)
      },
    })

    composer.bindEvents({
      onNeedsCreateChat: async () => {
        return await createChatAndLoad()
      },

      onAfterSend(){
        renderAll()
        scrollMessagesToBottom(true)
      },

      onSendError(){
        renderAll()
      },

      onStop(){
        renderAll()
      },
    })
  }

  async function init(){
    chatSidebar.syncSidebarState()

    bindAttachmentCallbacks()
    bindStreamCallbacks()
    bindAppEvents()

    memoryPanel.init()

    await chatStorage.loadChats()
    await loadActiveChatMessages()

    renderAll()
    scrollMessagesToBottom(true)
    composer.focusInput()
  }

  return {
    init,
    renderAll,
    loadActiveChatMessages,
    createChatAndLoad,
    retryMessage,
    scrollMessagesToBottom,
    syncSidebarAndLayout,
    openMemoryPanel: memoryPanel.open,
    closeMemoryPanel: memoryPanel.close,
    refreshMemoryList: memoryPanel.refresh,
  }
}

window.NovaChatOrchestrator = {
  create: createChatOrchestrator,
  createChatOrchestrator,
}

})()