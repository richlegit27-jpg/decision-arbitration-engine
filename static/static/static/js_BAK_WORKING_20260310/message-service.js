// C:\Users\Owner\nova\static\js\message-service.js

(() => {
"use strict"

function createMessageService(options = {}){
  const {
    state,
    utils = {},
  } = options

  if(!state){
    throw new Error("NovaMessageService: state is required")
  }

  function makeId(){
    if(typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"){
      return crypto.randomUUID()
    }

    return `${Date.now()}-${Math.random().toString(16).slice(2)}`
  }

  function normalizeAttachment(attachment = {}){
    return {
      attachment_id: String(
        attachment.attachment_id ||
        attachment.id ||
        ""
      ),
      name: String(
        attachment.name ||
        attachment.filename ||
        attachment.file_name ||
        "attachment"
      ),
      filename: String(
        attachment.filename ||
        attachment.name ||
        attachment.file_name ||
        "attachment"
      ),
      content_type: String(
        attachment.content_type ||
        attachment.mime_type ||
        attachment.type ||
        "application/octet-stream"
      ),
      size: Number(attachment.size || attachment.bytes || 0) || 0,
      url: String(
        attachment.url ||
        attachment.download_url ||
        attachment.href ||
        ""
      ),
      text_preview: String(
        attachment.text_preview ||
        attachment.preview ||
        attachment.readable_text ||
        ""
      ),
    }
  }

  function normalizeMessage(message = {}){
    const role = String(message.role || "assistant").toLowerCase()

    return {
      id: String(
        message.id ||
        message.message_id ||
        makeId()
      ),
      message_id: String(
        message.message_id ||
        message.id ||
        ""
      ),
      role,
      content: String(
        message.content ??
        message.text ??
        message.message ??
        ""
      ),
      created_at: String(
        message.created_at ||
        message.timestamp ||
        new Date().toISOString()
      ),
      status: String(
        message.status ||
        (role === "assistant" ? "done" : "sent")
      ),
      error: String(message.error || ""),
      attachments: Array.isArray(message.attachments)
        ? message.attachments.map(normalizeAttachment)
        : [],
      meta: message.meta && typeof message.meta === "object"
        ? { ...message.meta }
        : {},
    }
  }

  function getMessages(){
    if(!Array.isArray(state.messages)){
      state.messages = []
    }

    return state.messages
  }

  function setMessages(messages){
    state.messages = Array.isArray(messages)
      ? messages.map(normalizeMessage)
      : []

    return state.messages
  }

  function clearMessages(){
    state.messages = []
    return state.messages
  }

  function getMessageIndexById(messageId){
    const targetId = String(messageId || "").trim()

    if(!targetId){
      return -1
    }

    return getMessages().findIndex(message => {
      return (
        String(message.id || "") === targetId ||
        String(message.message_id || "") === targetId
      )
    })
  }

  function getMessageById(messageId){
    const index = getMessageIndexById(messageId)
    return index >= 0 ? getMessages()[index] : null
  }

  function addMessage(message = {}){
    const normalized = normalizeMessage(message)
    getMessages().push(normalized)
    return normalized
  }

  function prependMessage(message = {}){
    const normalized = normalizeMessage(message)
    getMessages().unshift(normalized)
    return normalized
  }

  function upsertMessage(message = {}){
    const normalized = normalizeMessage(message)
    const index = getMessageIndexById(normalized.id || normalized.message_id)

    if(index >= 0){
      getMessages()[index] = {
        ...getMessages()[index],
        ...normalized,
      }
      return getMessages()[index]
    }

    getMessages().push(normalized)
    return normalized
  }

  function replaceMessage(messageId, nextMessage = {}){
    const index = getMessageIndexById(messageId)

    if(index < 0){
      return null
    }

    const normalized = normalizeMessage({
      ...getMessages()[index],
      ...nextMessage,
      id: nextMessage.id || getMessages()[index].id,
      message_id: nextMessage.message_id || getMessages()[index].message_id,
    })

    getMessages()[index] = normalized
    return normalized
  }

  function patchMessage(messageId, patch = {}){
    const index = getMessageIndexById(messageId)

    if(index < 0){
      return null
    }

    const current = getMessages()[index]

    const merged = {
      ...current,
      ...patch,
      attachments: Array.isArray(patch.attachments)
        ? patch.attachments.map(normalizeAttachment)
        : current.attachments,
      meta: patch.meta && typeof patch.meta === "object"
        ? { ...(current.meta || {}), ...patch.meta }
        : current.meta,
    }

    const normalized = normalizeMessage(merged)
    getMessages()[index] = normalized
    return normalized
  }

  function removeMessage(messageId){
    const index = getMessageIndexById(messageId)

    if(index < 0){
      return false
    }

    getMessages().splice(index, 1)
    return true
  }

  function appendToMessageContent(messageId, chunk){
    const index = getMessageIndexById(messageId)

    if(index < 0){
      return null
    }

    const current = getMessages()[index]
    current.content = `${current.content || ""}${String(chunk || "")}`
    return current
  }

  function setMessageContent(messageId, content){
    const index = getMessageIndexById(messageId)

    if(index < 0){
      return null
    }

    getMessages()[index].content = String(content || "")
    return getMessages()[index]
  }

  function setMessageStatus(messageId, status){
    const index = getMessageIndexById(messageId)

    if(index < 0){
      return null
    }

    getMessages()[index].status = String(status || "")
    return getMessages()[index]
  }

  function setMessageError(messageId, error){
    const index = getMessageIndexById(messageId)

    if(index < 0){
      return null
    }

    getMessages()[index].error = String(error || "")
    getMessages()[index].status = "error"
    return getMessages()[index]
  }

  function addAttachments(messageId, attachments = []){
    const index = getMessageIndexById(messageId)

    if(index < 0){
      return null
    }

    const normalizedAttachments = Array.isArray(attachments)
      ? attachments.map(normalizeAttachment)
      : []

    getMessages()[index].attachments = [
      ...(Array.isArray(getMessages()[index].attachments) ? getMessages()[index].attachments : []),
      ...normalizedAttachments,
    ]

    return getMessages()[index]
  }

  function createUserMessage(content, attachments = []){
    return normalizeMessage({
      id: makeId(),
      role: "user",
      content: String(content || ""),
      created_at: new Date().toISOString(),
      status: "sent",
      attachments,
    })
  }

  function createAssistantPlaceholder(){
    return normalizeMessage({
      id: makeId(),
      role: "assistant",
      content: "",
      created_at: new Date().toISOString(),
      status: "streaming",
      attachments: [],
    })
  }

  function createSystemMessage(content){
    return normalizeMessage({
      id: makeId(),
      role: "system",
      content: String(content || ""),
      created_at: new Date().toISOString(),
      status: "done",
      attachments: [],
    })
  }

  return {
    getMessages,
    setMessages,
    clearMessages,
    normalizeAttachment,
    normalizeMessage,
    getMessageIndexById,
    getMessageById,
    addMessage,
    prependMessage,
    upsertMessage,
    replaceMessage,
    patchMessage,
    removeMessage,
    appendToMessageContent,
    setMessageContent,
    setMessageStatus,
    setMessageError,
    addAttachments,
    createUserMessage,
    createAssistantPlaceholder,
    createSystemMessage,
  }
}

window.NovaMessageService = {
  createMessageService,
}

})()