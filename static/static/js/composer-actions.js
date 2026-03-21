// C:\Users\Owner\nova\static\js\composer-actions.js

(() => {
"use strict"

function createComposerActions(options = {}){
  const {
    state,
    elements = {},
    api = {},
    chatMessages = null,
    chatSidebar = null,
    chatStorage = null,
    streamService = null,
    inputController = null,
    attachmentsController = null,
    callbacks = {},
    onStateChange = null,
  } = options

  if(!state){
    throw new Error("NovaComposerActions: state is required")
  }

  const el = {
    sendBtn: elements.sendBtn || null,
    stopBtn: elements.stopBtn || null,
    attachBtn: elements.attachBtn || null,
    messagesScroll: elements.messagesScroll || null,
  }

  let eventsBound = false
  let sendSequence = 0
  let activeThinkingMessageId = ""

  function safeCall(fn, fallback = null){
    try{
      return typeof fn === "function" ? fn() : fallback
    }catch(error){
      console.error("NovaComposerActions safeCall error:", error)
      return fallback
    }
  }

  function generateId(prefix = "msg"){
    if(window.crypto?.randomUUID){
      return `${prefix}_${window.crypto.randomUUID()}`
    }
    return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`
  }

  function ensureMessages(){
    if(!Array.isArray(state.messages)){
      state.messages = []
    }
    return state.messages
  }

  function ensurePendingAttachmentsArray(){
    if(!Array.isArray(state.pendingAttachments)){
      state.pendingAttachments = []
    }
    return state.pendingAttachments
  }

  function getActiveChatId(){
    return String(state.activeChatId || "").trim()
  }

  function setActiveChatId(chatId){
    state.activeChatId = String(chatId || "").trim()
    syncActiveChat()
  }

  function syncActiveChat(){
    const chatId = getActiveChatId()

    try{
      if(typeof chatStorage?.setActiveChat === "function"){
        chatStorage.setActiveChat(chatId || "")
      }
    }catch(error){
      console.error("NovaComposerActions syncActiveChat error:", error)
    }
  }

  function persistCurrentChatMessages(){
    const chatId = getActiveChatId()

    if(!chatId){
      return
    }

    try{
      if(typeof chatStorage?.saveMessages === "function"){
        chatStorage.saveMessages(chatId, ensureMessages())
      }
    }catch(error){
      console.error("NovaComposerActions persistCurrentChatMessages error:", error)
    }
  }

  function rerenderMessages(){
    try{
      if(typeof chatMessages?.syncMessagesFromStorage === "function"){
        chatMessages.syncMessagesFromStorage(ensureMessages())
        return
      }

      if(typeof chatMessages?.renderMessages === "function"){
        chatMessages.renderMessages(ensureMessages())
      }
    }catch(error){
      console.error("NovaComposerActions rerenderMessages error:", error)
    }
  }

  function rerenderSidebar(){
    try{
      if(typeof window.NovaChatApp?.renderAll === "function"){
        window.NovaChatApp.renderAll()
        return
      }

      if(typeof chatSidebar?.renderChatList === "function"){
        chatSidebar.renderChatList()
      }
    }catch(error){
      console.error("NovaComposerActions rerenderSidebar error:", error)
    }
  }

  function afterMessagesChanged(){
    rerenderMessages()
    persistCurrentChatMessages()
  }

  function notifyStateChange(){
    try{
      if(typeof onStateChange === "function"){
        onStateChange()
      }
    }catch(error){
      console.error("NovaComposerActions onStateChange error:", error)
    }
  }

  function markStreaming(flag){
    state.isStreaming = !!flag
    notifyStateChange()
  }

  function getPendingAttachments(){
    const ensured = safeCall(
      () => attachmentsController?.ensurePendingAttachments?.(),
      ensurePendingAttachmentsArray()
    )

    if(Array.isArray(ensured)){
      state.pendingAttachments = ensured
      return ensured
    }

    return ensurePendingAttachmentsArray()
  }

  function makeAttachmentPayload(attachments){
    try{
      if(typeof attachmentsController?.makeAttachmentPayload === "function"){
        const payload = attachmentsController.makeAttachmentPayload(attachments)
        return Array.isArray(payload) ? payload : []
      }
    }catch(error){
      console.error("NovaComposerActions makeAttachmentPayload error:", error)
    }

    return Array.isArray(attachments) ? attachments.slice() : []
  }

  function getEffectiveOutgoingText(text, attachments = []){
    try{
      if(typeof chatStorage?.getEffectiveOutgoingText === "function"){
        return String(chatStorage.getEffectiveOutgoingText(text, attachments) || "").trim()
      }
    }catch(error){
      console.error("NovaComposerActions getEffectiveOutgoingText error:", error)
    }

    return String(text || "").trim()
  }

  function getLocalDisplayText(text, attachments = []){
    try{
      if(typeof chatStorage?.getLocalDisplayText === "function"){
        return String(chatStorage.getLocalDisplayText(text, attachments) || "").trim()
      }
    }catch(error){
      console.error("NovaComposerActions getLocalDisplayText error:", error)
    }

    return String(text || "").trim()
  }

  function updateComposerState(){
    const rawText = String(inputController?.getTrimmedInputValue?.() || "")
    const pendingAttachments = getPendingAttachments()
    const effectiveText = getEffectiveOutgoingText(rawText, pendingAttachments)
    const hasSendableContent = !!effectiveText || pendingAttachments.length > 0
    const streaming = !!state.isStreaming

    if(el.sendBtn){
      el.sendBtn.disabled = streaming || !hasSendableContent
      el.sendBtn.hidden = streaming
    }

    if(el.stopBtn){
      el.stopBtn.hidden = !streaming
      el.stopBtn.disabled = !streaming
    }

    if(el.attachBtn){
      el.attachBtn.disabled = streaming
    }

    safeCall(() => attachmentsController?.renderPendingAttachments?.(), null)
  }

  function makeBaseMessage(role, text, attachments = [], extra = {}){
    const id = generateId("msg")
    return {
      message_id: id,
      id,
      role: String(role || "assistant"),
      content: String(text || ""),
      attachments: Array.isArray(attachments) ? attachments.slice() : [],
      created_at: new Date().toISOString(),
      ...extra,
    }
  }

  function appendMessage(message){
    const messages = ensureMessages()
    messages.push(message)
    afterMessagesChanged()
    return message
  }

  function appendLocalUserMessage(text, attachments = [], extra = {}){
    return appendMessage(makeBaseMessage("user", text, attachments, extra))
  }

  function appendAssistantMessage(text, attachments = [], extra = {}){
    return appendMessage(makeBaseMessage("assistant", text, attachments, extra))
  }

  function replaceMessageById(messageId, patch = {}){
    const messages = ensureMessages()
    const targetId = String(messageId || "").trim()

    if(!targetId){
      return null
    }

    const index = messages.findIndex((item) => {
      return String(item?.message_id || item?.id || "").trim() === targetId
    })

    if(index < 0){
      return null
    }

    messages[index] = {
      ...messages[index],
      ...patch,
    }

    afterMessagesChanged()
    return messages[index]
  }

  function removeMessageById(messageId){
    const messages = ensureMessages()
    const targetId = String(messageId || "").trim()

    if(!targetId){
      return false
    }

    const nextMessages = messages.filter((item) => {
      return String(item?.message_id || item?.id || "").trim() !== targetId
    })

    if(nextMessages.length === messages.length){
      return false
    }

    state.messages = nextMessages
    afterMessagesChanged()
    return true
  }

  function clearThinkingIndicator(){
    if(!activeThinkingMessageId){
      return
    }

    removeMessageById(activeThinkingMessageId)
    activeThinkingMessageId = ""
  }

  function showThinkingIndicator(){
    clearThinkingIndicator()

    const thinkingMessage = appendAssistantMessage("● ● ●", [], {
      status: "thinking",
      message_type: "thinking",
      thinking: true,
      isThinking: true,
      streaming: true,
    })

    activeThinkingMessageId = String(
      thinkingMessage?.message_id ||
      thinkingMessage?.id ||
      ""
    ).trim()

    return thinkingMessage
  }

  function safeAutoTitle(chatId, text, attachments = []){
    if(state.__titleLocked){
      return
    }

    let resolvedTitle = ""

    try{
      if(typeof chatStorage?.resolveSmartChatTitle === "function"){
        resolvedTitle = String(
          chatStorage.resolveSmartChatTitle(
            String(text || "").trim(),
            Array.isArray(attachments) ? attachments.slice() : []
          ) || ""
        ).trim()
      }

      if(typeof chatStorage?.hydrateChatFromMessageActivity === "function"){
        chatStorage.hydrateChatFromMessageActivity(
          chatId,
          String(text || "").trim(),
          Array.isArray(attachments) ? attachments.slice() : []
        )
      }
    }catch(error){
      console.error("NovaComposerActions safeAutoTitle error:", error)
    }

    try{
      if(resolvedTitle && typeof chatSidebar?.updateChatTitle === "function"){
        const updated = chatSidebar.updateChatTitle(chatId, resolvedTitle)
        if(updated){
          state.__titleLocked = true
          return
        }
      }
    }catch(error){
      console.error("NovaComposerActions sidebar title patch error:", error)
    }

    rerenderSidebar()
    state.__titleLocked = true
  }

  async function postJson(url, payload){
    if(typeof api.fetchJson === "function"){
      return await api.fetchJson(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
    }

    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })

    if(!response.ok){
      const text = await response.text().catch(() => "")
      throw new Error(`${url} failed (${response.status}) ${text}`)
    }

    return await response.json()
  }

  async function postChat(payload){
    return await postJson("/api/chat", payload)
  }

  async function postVoiceGenerate(payload){
    return await postJson("/api/voice_generate", payload)
  }

  function parseVoiceCommand(text){
    const raw = String(text || "").trim()

    if(!raw){
      return null
    }

    if(raw.toLowerCase() === "/voice"){
      return {
        isVoice: true,
        prompt: "",
      }
    }

    if(raw.toLowerCase().startsWith("/voice ")){
      return {
        isVoice: true,
        prompt: raw.slice(7).trim(),
      }
    }

    return null
  }

  function clearPendingInputAndAttachments(){
    safeCall(() => inputController?.clearInput?.(), null)
    state.pendingAttachments = []
    safeCall(() => attachmentsController?.renderPendingAttachments?.(), null)
    updateComposerState()
  }

  function isAbortLikeError(error){
    const name = String(error?.name || "")
    const message = String(error?.message || "")

    return (
      name === "AbortError" ||
      /aborted/i.test(message) ||
      /abort/i.test(name)
    )
  }

  function snapshotRetryState(payload = {}){
    state.lastSendPayload = {
      chatId: String(payload.chatId || getActiveChatId() || "").trim(),
      text: String(payload.text || ""),
      displayText: String(payload.displayText || ""),
      attachments: Array.isArray(payload.attachments) ? payload.attachments.slice() : [],
      createdAt: new Date().toISOString(),
    }
  }

  async function ensureActiveChat(options = {}){
    let chatId = getActiveChatId()

    if(chatId){
      syncActiveChat()
      return chatId
    }

    const onNeedsCreateChat = options.onNeedsCreateChat || callbacks.onNeedsCreateChat

    if(!chatId && typeof onNeedsCreateChat === "function"){
      const created = await onNeedsCreateChat()
      chatId = String(created?.chat_id || created?.id || state.activeChatId || "").trim()
      if(chatId){
        setActiveChatId(chatId)
      }
    }

    if(!chatId && typeof chatSidebar?.createNewChat === "function"){
      const created = await chatSidebar.createNewChat({})
      chatId = String(created?.chat_id || created?.id || state.activeChatId || "").trim()
      if(chatId){
        setActiveChatId(chatId)
      }
    }

    if(!chatId){
      throw new Error("No active chat id available.")
    }

    syncActiveChat()
    return chatId
  }

  function handleResolvedChatId(reply, fallbackChatId){
    const resolvedChatId = String(
      reply?.chat_id ||
      reply?.chat?.chat_id ||
      reply?.chat?.id ||
      fallbackChatId ||
      state.activeChatId ||
      ""
    ).trim()

    if(resolvedChatId){
      setActiveChatId(resolvedChatId)
    }

    return resolvedChatId
  }

  function handleNonStreamingReply(reply, fallbackChatId){
    const resolvedChatId = handleResolvedChatId(reply, fallbackChatId)

    clearThinkingIndicator()

    if(Array.isArray(reply?.messages) && reply.messages.length){
      state.messages = reply.messages.slice()
      afterMessagesChanged()
      return reply
    }

    const responseText = String(
      reply?.response ??
      reply?.reply ??
      reply?.message ??
      ""
    )

    const responseAttachments = Array.isArray(reply?.attachments)
      ? reply.attachments.slice()
      : []

    if(responseText.trim() || responseAttachments.length){
      appendAssistantMessage(responseText, responseAttachments)
    }else{
      persistCurrentChatMessages()
    }

    return {
      ...reply,
      chat_id: resolvedChatId,
    }
  }

  async function sendVoiceCommand({ chatId, text, prompt, uploadedAttachments }){
    const reply = await postVoiceGenerate({
      chat_id: chatId,
      session_id: chatId,
      prompt,
    })

    clearThinkingIndicator()

    const responseText = String(
      reply?.response ||
      reply?.reply ||
      reply?.message ||
      (prompt ? `Generated voice for: ${prompt}` : "Voice prompt is required.")
    )

    const responseAttachments = Array.isArray(reply?.attachments)
      ? reply.attachments.slice()
      : (reply?.attachment ? [reply.attachment] : [])

    appendAssistantMessage(responseText, responseAttachments)
    persistCurrentChatMessages()
    safeAutoTitle(chatId, text, uploadedAttachments)

    return reply
  }

  async function sendCurrentMessage(options = {}){
    if(state.isStreaming){
      return null
    }

    const sendToken = ++sendSequence
    const forcedText = String(options.forcedText || "").trim()
    const forcedAttachments = Array.isArray(options.forcedAttachments)
      ? options.forcedAttachments.slice()
      : null
    const skipLocalUserAppend = !!options.skipLocalUserAppend

    const inputText = String(inputController?.getTrimmedInputValue?.() || "")
    const pendingAttachments = getPendingAttachments()

    const sourceAttachments = forcedAttachments || pendingAttachments
    const rawText = forcedText || inputText
    const effectiveText = getEffectiveOutgoingText(rawText, sourceAttachments)
    const displayText = getLocalDisplayText(rawText, sourceAttachments)

    if(!effectiveText && !sourceAttachments.length){
      updateComposerState()
      return null
    }

    const voiceCommand = parseVoiceCommand(effectiveText)
    const onAfterSend = options.onAfterSend || callbacks.onAfterSend
    const onSendError = options.onSendError || callbacks.onSendError

    let localUserMessage = null
    let aborted = false

    try{
      markStreaming(true)

      const chatId = await ensureActiveChat(options)

      let uploadedAttachments = sourceAttachments

      if(!forcedAttachments && typeof attachmentsController?.uploadPendingAttachments === "function"){
        uploadedAttachments = await attachmentsController.uploadPendingAttachments()
      }

      if(!Array.isArray(uploadedAttachments)){
        uploadedAttachments = []
      }

      const attachmentPayload = makeAttachmentPayload(uploadedAttachments)
      const finalText = getEffectiveOutgoingText(rawText, uploadedAttachments)
      const finalDisplayText = getLocalDisplayText(rawText, uploadedAttachments)

      if(!finalText && !attachmentPayload.length){
        throw new Error("Nothing to send.")
      }

      snapshotRetryState({
        chatId,
        text: finalText,
        displayText: finalDisplayText,
        attachments: uploadedAttachments,
      })

      if(!skipLocalUserAppend){
        localUserMessage = appendLocalUserMessage(finalDisplayText, uploadedAttachments, {
          status: "sent_local",
        })
      }

      safeAutoTitle(chatId, finalDisplayText, uploadedAttachments)

      if(!forcedText && !forcedAttachments){
        clearPendingInputAndAttachments()
      }else{
        safeCall(() => inputController?.clearInput?.(), null)
        state.pendingAttachments = []
        safeCall(() => attachmentsController?.renderPendingAttachments?.(), null)
        updateComposerState()
      }

      showThinkingIndicator()

      let reply = null

      if(voiceCommand?.isVoice){
        reply = await sendVoiceCommand({
          chatId,
          text: finalDisplayText,
          prompt: voiceCommand.prompt,
          uploadedAttachments,
        })
      }else if(streamService && typeof streamService.send === "function"){
        reply = await streamService.send({
          chatId,
          message: finalText,
          files: attachmentPayload,
          attachments: attachmentPayload,
          scrollEl: el.messagesScroll,
        })

        clearThinkingIndicator()
        handleResolvedChatId(reply, chatId)
        persistCurrentChatMessages()
      }else{
        reply = await postChat({
          chat_id: chatId,
          message: finalText,
          attachments: attachmentPayload,
        })

        handleNonStreamingReply(reply, chatId)
      }

      if(sendToken !== sendSequence){
        return reply
      }

      safeAutoTitle(getActiveChatId() || chatId, finalDisplayText, uploadedAttachments)

      if(typeof onAfterSend === "function"){
        onAfterSend(reply)
      }

      return reply
    }catch(error){
      aborted = isAbortLikeError(error)
      clearThinkingIndicator()

      if(localUserMessage && aborted){
        replaceMessageById(localUserMessage.message_id || localUserMessage.id, {
          status: "aborted",
        })
      }

      if(localUserMessage && !aborted){
        replaceMessageById(localUserMessage.message_id || localUserMessage.id, {
          status: "send_failed",
        })
      }

      if(!aborted){
        console.error("NovaComposerActions send error:", error)
        appendAssistantMessage("Send failed.")
      }

      if(typeof onSendError === "function"){
        onSendError(error)
      }

      return null
    }finally{
      if(sendToken === sendSequence){
        markStreaming(false)
      }
      state.__titleLocked = false
      safeCall(() => inputController?.autoResizeInput?.(), null)
      updateComposerState()
    }
  }

  async function retryLastSend(options = {}){
    const retry = state.lastSendPayload

    if(!retry){
      return null
    }

    return await sendCurrentMessage({
      ...options,
      forcedText: String(retry.text || ""),
      forcedAttachments: Array.isArray(retry.attachments) ? retry.attachments.slice() : [],
      skipLocalUserAppend: !!options.skipLocalUserAppend,
    })
  }

  function stopGenerating(){
    try{
      if(typeof streamService?.stop === "function"){
        streamService.stop()
      }
    }catch(error){
      console.error("NovaComposerActions stopGenerating error:", error)
    }

    clearThinkingIndicator()
    markStreaming(false)

    if(typeof callbacks.onStop === "function"){
      try{
        callbacks.onStop()
      }catch(error){
        console.error("NovaComposerActions onStop callback error:", error)
      }
    }

    updateComposerState()
  }

  function bindEvents(){
    if(eventsBound){
      updateComposerState()
      return
    }

    eventsBound = true

    el.sendBtn?.addEventListener("click", async () => {
      await sendCurrentMessage()
    })

    el.stopBtn?.addEventListener("click", () => {
      stopGenerating()
    })

    updateComposerState()
  }

  return {
    bindEvents,
    updateComposerState,
    markStreaming,
    sendCurrentMessage,
    retryLastSend,
    stopGenerating,
    appendLocalUserMessage,
    appendAssistantMessage,
    replaceMessageById,
    removeMessageById,
    showThinkingIndicator,
    clearThinkingIndicator,
  }
}

window.NovaComposerActions = {
  create: createComposerActions,
  createComposerActions,
}

})()