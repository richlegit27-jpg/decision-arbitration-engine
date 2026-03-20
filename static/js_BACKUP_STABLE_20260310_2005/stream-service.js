// C:\Users\Owner\nova\static\js\stream-service.js

(() => {
"use strict"

function createStreamService(options = {}){
  const {
    state,
    api,
    onStart,
    onMeta,
    onToken,
    onDone,
    onError,
    onFinally,
  } = options

  if(!state){
    throw new Error("NovaStreamService: state is required")
  }

  const apiClient = api || window.NovaAPI

  if(!apiClient || typeof apiClient.streamChat !== "function"){
    throw new Error("NovaStreamService: api.streamChat is required")
  }

  let activeController = null
  let activeStreamId = 0
  let autoScrollLocked = false

  const callbacks = {
    onStart: typeof onStart === "function" ? onStart : null,
    onMeta: typeof onMeta === "function" ? onMeta : null,
    onToken: typeof onToken === "function" ? onToken : null,
    onDone: typeof onDone === "function" ? onDone : null,
    onError: typeof onError === "function" ? onError : null,
    onFinally: typeof onFinally === "function" ? onFinally : null,
  }

  function setCallbacks(next = {}){
    callbacks.onStart = typeof next.onStart === "function" ? next.onStart : callbacks.onStart
    callbacks.onMeta = typeof next.onMeta === "function" ? next.onMeta : callbacks.onMeta
    callbacks.onToken = typeof next.onToken === "function" ? next.onToken : callbacks.onToken
    callbacks.onDone = typeof next.onDone === "function" ? next.onDone : callbacks.onDone
    callbacks.onError = typeof next.onError === "function" ? next.onError : callbacks.onError
    callbacks.onFinally = typeof next.onFinally === "function" ? next.onFinally : callbacks.onFinally
  }

  function isNearBottom(el){
    if(!el){
      return true
    }

    const threshold = 120
    return (el.scrollHeight - el.scrollTop - el.clientHeight) < threshold
  }

  function scrollToBottom(el){
    if(!el){
      return
    }

    el.scrollTop = el.scrollHeight
  }

  function makeLocalMessageId(){
    return `msg_${Date.now()}_${Math.random().toString(16).slice(2)}`
  }

  function normalizeMessageId(value, fallback){
    const resolved = String(value || fallback || "").trim()
    return resolved || String(fallback || makeLocalMessageId())
  }

  function finishActiveStream(streamId){
    if(streamId !== activeStreamId){
      return false
    }

    activeController = null
    state.isStreaming = false
    return true
  }

  function stop(){
    if(activeController){
      try{
        activeController.abort()
      }catch(_error){
        // ignore abort cleanup errors
      }
    }

    activeController = null
    state.isStreaming = false
  }

  async function send(payload = {}){
    const {
      chatId,
      message,
      files = [],
      attachments = [],
      scrollEl = null,
      messageId,
    } = payload

    stop()

    const controller = new AbortController()
    const streamId = ++activeStreamId
    const localMessageId = normalizeMessageId(messageId, makeLocalMessageId())

    activeController = controller
    state.isStreaming = true
    autoScrollLocked = !isNearBottom(scrollEl)

    if(typeof callbacks.onStart === "function"){
      callbacks.onStart({
        chatId: String(chatId || "").trim(),
        messageId: localMessageId,
        message: String(message || ""),
        files: Array.isArray(files) ? files : [],
        attachments: Array.isArray(attachments) ? attachments : [],
      })
    }

    try{
      const result = await apiClient.streamChat(
        {
          chat_id: String(chatId || "").trim(),
          message: String(message || ""),
          files: Array.isArray(files) ? files : [],
          attachments: Array.isArray(attachments) ? attachments : [],
        },
        {
          signal: controller.signal,

          onMeta(data){
            if(streamId !== activeStreamId){
              return
            }

            if(typeof callbacks.onMeta === "function"){
              callbacks.onMeta({
                ...(data || {}),
                messageId: normalizeMessageId(
                  data?.messageId || data?.assistant_message_id,
                  localMessageId
                ),
              })
            }
          },

          onToken(token, data){
            if(streamId !== activeStreamId){
              return
            }

            if(typeof callbacks.onToken === "function"){
              callbacks.onToken(token, data)
            }

            if(scrollEl && !autoScrollLocked){
              requestAnimationFrame(() => {
                if(streamId === activeStreamId){
                  scrollToBottom(scrollEl)
                }
              })
            }
          },

          onChunk(data){
            if(streamId !== activeStreamId){
              return
            }

            if(data && typeof callbacks.onMeta === "function" && (data.event === "meta" || data.type === "meta")){
              callbacks.onMeta({
                ...data,
                messageId: normalizeMessageId(
                  data?.messageId || data?.assistant_message_id,
                  localMessageId
                ),
              })
            }
          },

          onDone(data){
            if(streamId !== activeStreamId){
              return
            }

            if(typeof callbacks.onDone === "function"){
              callbacks.onDone({
                ...(data || {}),
                messageId: normalizeMessageId(
                  data?.messageId || data?.assistant_message_id,
                  localMessageId
                ),
              })
            }
          },
        }
      )

      return result || { ok: true, messageId: localMessageId }
    }catch(error){
      if(streamId === activeStreamId && typeof callbacks.onError === "function"){
        callbacks.onError(error)
      }

      throw error
    }finally{
      const isActive = finishActiveStream(streamId)

      if(isActive && typeof callbacks.onFinally === "function"){
        callbacks.onFinally()
      }

      if(isActive && scrollEl && !autoScrollLocked){
        requestAnimationFrame(() => {
          scrollToBottom(scrollEl)
        })
      }
    }
  }

  return {
    send,
    stop,
    isStreaming(){
      return !!state.isStreaming
    },
    setCallbacks,
  }
}

window.NovaStreamService = {
  create: createStreamService,
  createStreamService,
}

})()