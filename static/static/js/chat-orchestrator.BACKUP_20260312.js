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

  function getFirstMeaningfulUserMessage(messages = []){
    const list = Array.isArray(messages) ? messages : []

    for(const message of list){
      if(getMessageRole(message) !== "user"){
        continue
      }

      const text = String(message?.content || "").trim()
      const attachments = Array.isArray(message?.attachments) ? message.attachments : []

      if(text || attachments.length){
        return message
      }
    }

    return null
  }

  function hydrateChatTitle(chatId, messages = []){
    const targetChatId = String(chatId || "").trim()

    if(!targetChatId){
      return
    }

    const firstUserMessage = getFirstMeaningfulUserMessage(messages)
    const firstUserText = String(firstUserMessage?.content || "").trim()
    const firstUserAttachments = Array.isArray(firstUserMessage?.attachments)
      ? firstUserMessage.attachments.slice()
      : []

    if(typeof chatStorage.hydrateChatFromMessageActivity === "function"){
      const chat = chatStorage.hydrateChatFromMessageActivity(
        targetChatId,
        firstUserText,
        firstUserAttachments
      )

      const nextTitle = String(chat?.title || "").trim()

      if(nextTitle && typeof chatSidebar.updateChatTitle === "function"){
        chatSidebar.updateChatTitle(targetChatId, nextTitle)
      }

      return
    }

    if(typeof chatStorage.hydrateChatTitleFromMessages === "function"){
      chatStorage.hydrateChatTitleFromMessages(targetChatId, messages)
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

  function mergeStreamingAttachments(messageId, incomingAttachments = []){
    const targetId = String(messageId || "").trim()

    if(!targetId){
      return
    }

    if(typeof chatMessages.findMessageById !== "function"){
      return
    }

    const existingMessage = chatMessages.findMessageById(targetId)
    if(!existingMessage){
      return
    }

    const existing = Array.isArray(existingMessage.attachments)
      ? existingMessage.attachments.slice()
      : []

    const merged = existing.slice()

    for(const att of Array.isArray(incomingAttachments) ? incomingAttachments : []){
      if(!att){
        continue
      }

      const incomingId = getAttachmentIdentity(att)

      const alreadyExists = merged.some(existingAtt => {
        const existingId = getAttachmentIdentity(existingAtt)

        if(incomingId && existingId){
          return incomingId === existingId
        }

        return false
      })

      if(!alreadyExists){
        merged.push(att)
      }
    }

    if(typeof chatMessages.replaceMessage === "function"){
      chatMessages.replaceMessage(targetId, {
        attachments: merged,
      })
    }
  }

  function getMessageIndexById(messageId){
    const targetId = String(messageId || "").trim()

    return getMessages().findIndex(message => {
      return getMessageId(message) === targetId
    })
  }

  function findPreviousUserIndex(startIndex){
    const messages = getMessages()

    for(let i = Number(startIndex) - 1; i >= 0; i -= 1){
      if(getMessageRole(messages[i]) === "user"){
        return i
      }
    }

    return -1
  }

  function findNextUserIndex(startIndex){
    const messages = getMessages()

    for(let i = Number(startIndex) + 1; i < messages.length; i += 1){
      if(getMessageRole(messages[i]) === "user"){
        return i
      }
    }

    return -1
  }

  function isFailureAssistantMessage(message){
    if(getMessageRole(message) !== "assistant"){
      return false
    }

    const text = String(message?.content || "").replace(/\s+/g, " ").trim().toLowerCase()
    return text === "send failed."
  }

  function removeMessageRange(startIndex, endIndex){
    const messages = getMessages().slice()

    const start = Number(startIndex)
    const end = Number(endIndex)

    if(!Number.isFinite(start) || !Number.isFinite(end)){
      return false
    }

    if(start < 0 || end < start || start >= messages.length){
      return false
    }

    messages.splice(start, end - start + 1)
    state.messages = messages
    return true
  }

  function removeAssistantChainAfterUser(userIndex){
    const messages = getMessages()

    if(userIndex < 0 || userIndex >= messages.length){
      return false
    }

    const nextUserIndex = findNextUserIndex(userIndex)
    const startIndex = userIndex + 1
    const endIndex = nextUserIndex === -1 ? messages.length - 1 : nextUserIndex - 1

    if(startIndex > endIndex){
      return false
    }

    const slice = messages.slice(startIndex, endIndex + 1)
    const hasAssistant = slice.some(message => getMessageRole(message) === "assistant")

    if(!hasAssistant){
      return false
    }

    return removeMessageRange(startIndex, endIndex)
  }

  function removeFailureAssistantAfterUser(userIndex){
    const messages = getMessages()

    if(userIndex < 0 || userIndex >= messages.length){
      return false
    }

    const nextIndex = userIndex + 1
    if(nextIndex >= messages.length){
      return false
    }

    const nextMessage = messages[nextIndex]
    if(!isFailureAssistantMessage(nextMessage)){
      return false
    }

    return removeMessageRange(nextIndex, nextIndex)
  }

  function deleteMessageAndPersist(messageId){
    const targetId = String(messageId || "").trim()
    if(!targetId){
      return
    }

    const targetIndex = getMessageIndexById(targetId)
    if(targetIndex === -1){
      return
    }

    const targetMessage = getMessages()[targetIndex]
    const targetRole = getMessageRole(targetMessage)

    let changed = false

    if(targetRole === "user"){
      const nextUserIndex = findNextUserIndex(targetIndex)
      const endIndex = nextUserIndex === -1 ? getMessages().length - 1 : nextUserIndex - 1
      changed = removeMessageRange(targetIndex, endIndex)
    }else{
      changed = removeMessageRange(targetIndex, targetIndex)
    }

    if(!changed){
      return
    }

    syncPersistedMessages({ preserveScroll: false })
  }

  function getRetryTarget(messageId){
    if(typeof chatMessages.findMessageById !== "function"){
      return null
    }

    const target = chatMessages.findMessageById(messageId)
    if(!target){
      return null
    }

    const targetRole = getMessageRole(target)
    const targetIndex = getMessageIndexById(messageId)

    if(targetIndex === -1){
      return null
    }

    if(targetRole === "assistant"){
      const userIndex = findPreviousUserIndex(targetIndex)
      if(userIndex === -1){
        return null
      }

      return {
        mode: "assistant",
        target,
        targetIndex,
        userIndex,
        userMessage: getMessages()[userIndex] || null,
      }
    }

    if(targetRole === "user"){
      return {
        mode: "user",
        target,
        targetIndex,
        userIndex: targetIndex,
        userMessage: target,
      }
    }

    return null
  }

  async function loadActiveChatMessages(){
    const activeChatId = String(state.activeChatId || "").trim()

    if(!activeChatId){
      state.messages = []

      if(typeof chatMessages.clearMessages === "function"){
        chatMessages.clearMessages()
      }

      renderShell()
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
    }else if(typeof chatStorage.createChat === "function"){
      chat = await chatStorage.createChat({ title: "New chat" })
      const chatId = String(chat?.chat_id || chat?.id || "").trim()
      if(chatId){
        state.activeChatId = chatId
      }
    }

    await loadActiveChatMessages()
    return chat
  }

  async function retryMessage(messageId){
    if(state.isStreaming){
      return
    }

    const retryTarget = getRetryTarget(messageId)
    if(!retryTarget){
      return
    }

    const {
      mode,
      userIndex,
      targetIndex,
      userMessage,
    } = retryTarget

    if(!userMessage){
      return
    }

    const retryText = String(userMessage.content || "").trim()
    const retryAttachments = Array.isArray(userMessage.attachments) ? userMessage.attachments : []

    if(!retryText && retryAttachments.length === 0){
      return
    }

    let changed = false

    if(mode === "assistant"){
      changed = removeMessageRange(targetIndex, targetIndex)
      removeFailureAssistantAfterUser(userIndex)
    }else if(mode === "user"){
      changed = removeAssistantChainAfterUser(userIndex)
      removeFailureAssistantAfterUser(userIndex)
    }

    if(changed){
      syncPersistedMessages({ preserveScroll: false })
    }

    if(typeof composer.setInputValue === "function"){
      composer.setInputValue("")
    }

    if(typeof composer.setPendingFiles === "function"){
      composer.setPendingFiles([])
    }

    renderShell()
    scrollMessagesToBottom(true)

    if(typeof composer.sendCurrentMessage === "function"){
      await composer.sendCurrentMessage({
        forcedText: retryText,
        forcedAttachments: retryAttachments,
        skipLocalUserAppend: true,
        onNeedsCreateChat: createChatAndLoad,
        onAfterSend(){
          syncPersistedMessages({ preserveScroll: false })
        },
        onSendError(){
          renderShell()
        },
      })
    }
  }

  async function editMessage(messageId){
    if(state.isStreaming){
      return
    }

    if(typeof chatMessages.findMessageById !== "function"){
      return
    }

    const target = chatMessages.findMessageById(messageId)
    if(!target){
      return
    }

    if(getMessageRole(target) !== "user"){
      return
    }

    const targetIndex = getMessageIndexById(messageId)
    if(targetIndex === -1){
      return
    }

    const currentText = String(target.content || "")
    const nextText = window.prompt("Edit message", currentText)

    if(nextText === null){
      return
    }

    const trimmedNextText = String(nextText || "").trim()
    const existingAttachments = Array.isArray(target.attachments) ? target.attachments : []

    if(!trimmedNextText && existingAttachments.length === 0){
      return
    }

    const messages = getMessages().slice()

    messages[targetIndex] = {
      ...messages[targetIndex],
      content: trimmedNextText,
    }

    state.messages = messages

    removeAssistantChainAfterUser(targetIndex)
    removeFailureAssistantAfterUser(targetIndex)

    syncPersistedMessages({ preserveScroll: false })

    if(typeof composer.setInputValue === "function"){
      composer.setInputValue("")
    }

    if(typeof composer.setPendingFiles === "function"){
      composer.setPendingFiles([])
    }

    renderShell()
    scrollMessagesToBottom(true)

    if(typeof composer.sendCurrentMessage === "function"){
      await composer.sendCurrentMessage({
        forcedText: trimmedNextText,
        forcedAttachments: existingAttachments,
        skipLocalUserAppend: true,
        onNeedsCreateChat: createChatAndLoad,
        onAfterSend(){
          syncPersistedMessages({ preserveScroll: false })
        },
        onSendError(){
          renderShell()
        },
      })
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

      onStart(payload = {}){
        const messageId = String(payload?.messageId || payload?.id || `msg_${Date.now()}`).trim()

        state.isStreaming = true
        state.streamingMessageId = messageId
        state._thinkingStart = performance.now()

        if(typeof composer.markStreaming === "function"){
          composer.markStreaming(true)
        }

        if(typeof composer.updateComposerState === "function"){
          composer.updateComposerState()
        }

        if(typeof chatMessages.showThinkingIndicator === "function"){
          chatMessages.showThinkingIndicator()
        }

        scrollMessagesToBottom(true)
      },

      onMeta(payload = {}){
        const messageId = String(
          payload?.messageId ||
          payload?.assistant_message_id ||
          payload?.message_id ||
          state.streamingMessageId ||
          ""
        ).trim()

        if(!messageId){
          return
        }

        state.streamingMessageId = messageId

        const MIN_THINK = 500
        const elapsed = performance.now() - (state._thinkingStart || 0)

        const startStream = () => {
          if(typeof chatMessages.removeThinkingIndicator === "function"){
            chatMessages.removeThinkingIndicator()
          }

          if(typeof chatMessages.upsertStreamingAssistantMessage === "function"){
            chatMessages.upsertStreamingAssistantMessage(messageId)
          }

          scrollMessagesToBottom(true)
        }

        if(elapsed < MIN_THINK){
          setTimeout(startStream, MIN_THINK - elapsed)
        }else{
          startStream()
        }
      },

      onToken(token){
        const messageId = String(state.streamingMessageId || "").trim()

        if(!messageId){
          return
        }

        if(typeof chatMessages.appendToStreamingMessage === "function"){
          chatMessages.appendToStreamingMessage(messageId, token)
        }

        scrollMessagesToBottom(false)
      },

      onAttachment(attachment, payload = {}){
        const messageId = String(
          payload?.messageId ||
          payload?.message_id ||
          payload?.assistant_message_id ||
          state.streamingMessageId ||
          ""
        ).trim()

        if(!messageId || !attachment){
          return
        }

        if(typeof chatMessages.upsertStreamingAssistantMessage === "function"){
          chatMessages.upsertStreamingAssistantMessage(messageId)
        }

        if(typeof chatMessages.removeThinkingIndicator === "function"){
          chatMessages.removeThinkingIndicator()
        }

        mergeStreamingAttachments(messageId, [attachment])
        scrollMessagesToBottom(false)
      },

      onAttachments(attachments, payload = {}){
        const messageId = String(
          payload?.messageId ||
          payload?.message_id ||
          payload?.assistant_message_id ||
          state.streamingMessageId ||
          ""
        ).trim()

        if(!messageId || !Array.isArray(attachments) || !attachments.length){
          return
        }

        if(typeof chatMessages.upsertStreamingAssistantMessage === "function"){
          chatMessages.upsertStreamingAssistantMessage(messageId)
        }

        if(typeof chatMessages.removeThinkingIndicator === "function"){
          chatMessages.removeThinkingIndicator()
        }

        mergeStreamingAttachments(messageId, attachments)
        scrollMessagesToBottom(false)
      },

      onDone(payload = {}){
        const messageId = String(
          payload?.messageId ||
          payload?.message_id ||
          payload?.assistant_message_id ||
          state.streamingMessageId ||
          ""
        ).trim()

        if(messageId && typeof chatMessages.upsertStreamingAssistantMessage === "function"){
          chatMessages.upsertStreamingAssistantMessage(messageId)

          const existingMessage = typeof chatMessages.findMessageById === "function"
            ? chatMessages.findMessageById(messageId)
            : null

          const existingAttachments = Array.isArray(existingMessage?.attachments)
            ? existingMessage.attachments.slice()
            : []

          const doneAttachments = Array.isArray(payload?.attachments)
            ? payload.attachments.slice()
            : []

          const mergedAttachments = existingAttachments.slice()

          for(const att of doneAttachments){
            const incomingId = getAttachmentIdentity(att)

            const alreadyExists = mergedAttachments.some(existingAtt => {
              const existingId = getAttachmentIdentity(existingAtt)

              if(incomingId && existingId){
                return incomingId === existingId
              }

              return false
            })

            if(!alreadyExists){
              mergedAttachments.push(att)
            }
          }

          if(typeof chatMessages.replaceMessage === "function"){
            chatMessages.replaceMessage(messageId, {
              content: String(payload?.content || existingMessage?.content || ""),
              attachments: mergedAttachments,
            })
          }
        }

        state.isStreaming = false
        state.streamingMessageId = null

        if(typeof chatMessages.finishStreamingMessage === "function"){
          chatMessages.finishStreamingMessage()
        }

        persistCurrentMessages()

        if(typeof composer.markStreaming === "function"){
          composer.markStreaming(false)
        }

        if(typeof composer.updateComposerState === "function"){
          composer.updateComposerState()
        }

        renderShell()
        scrollMessagesToBottom(true)
      },

      onError(err){
        console.error("NovaChatApp stream error:", err)

        state.isStreaming = false
        state.streamingMessageId = null

        if(typeof chatMessages.finishStreamingMessage === "function"){
          chatMessages.finishStreamingMessage()
        }

        if(typeof composer.markStreaming === "function"){
          composer.markStreaming(false)
        }

        if(typeof composer.updateComposerState === "function"){
          composer.updateComposerState()
        }

        renderShell()
      },

      onFinally(){
        state.isStreaming = false
        state.streamingMessageId = null

        if(typeof composer.markStreaming === "function"){
          composer.markStreaming(false)
        }

        if(typeof chatMessages.finishStreamingMessage === "function"){
          chatMessages.finishStreamingMessage()
        }

        if(typeof composer.updateComposerState === "function"){
          composer.updateComposerState()
        }
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
    if(typeof chatMessages.bindEvents === "function"){
      chatMessages.bindEvents({
        onRetry: async (messageId) => {
          await retryMessage(messageId)
        },
        onDelete: async (messageId) => {
          deleteMessageAndPersist(messageId)
        },
        onEdit: async (messageId) => {
          await editMessage(messageId)
        },
      })
    }

    if(typeof composer.bindEvents === "function"){
      composer.bindEvents({
        onNeedsCreateChat: async () => {
          return await createChatAndLoad()
        },
        onAfterSend(){
          syncPersistedMessages({ preserveScroll: false })
        },
        onSendError(){
          renderShell()
        },
        onStop(){
          renderShell()
        },
      })
    }
  }

  async function init(){
    if(typeof chatSidebar.init === "function"){
      chatSidebar.init()
    }

    if(typeof chatSidebar.syncSidebarState === "function"){
      chatSidebar.syncSidebarState()
    }

    bindAttachmentCallbacks()
    bindStreamCallbacks()
    bindAppEvents()

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
    retryMessage,
    editMessage,
    scrollMessagesToBottom,
    syncSidebarAndLayout,
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