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

  const apiClient = api || window.NovaAPI

  let activeController = null
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
    if(!el) return true
    const threshold = 120
    return el.scrollHeight - el.scrollTop - el.clientHeight < threshold
  }

  function scrollToBottom(el){
    if(!el) return
    el.scrollTop = el.scrollHeight
  }

  function stop(){
    if(activeController){
      try{
        activeController.abort()
      }catch{}
    }
    activeController = null
    state.isStreaming = false
  }

  async function send(payload = {}){
    const {
      chatId,
      message,
      files = [],
      scrollEl,
      messageId,
    } = payload

    if(!apiClient || typeof apiClient.streamChat !== "function"){
      throw new Error("NovaAPI.streamChat missing")
    }

    stop()

    const controller = new AbortController()
    activeController = controller
    state.isStreaming = true

    const localMessageId = String(messageId || `msg_${Date.now()}_${Math.random().toString(16).slice(2)}`).trim()

    autoScrollLocked = !isNearBottom(scrollEl)

    if(typeof callbacks.onStart === "function"){
      callbacks.onStart({
        chatId,
        messageId: localMessageId,
        message,
        files,
      })
    }

    try{
      const result = await apiClient.streamChat({
        chat_id: chatId,
        message,
        files,
        signal: controller.signal,

        onMeta(data){
          if(typeof callbacks.onMeta === "function"){
            callbacks.onMeta({
              ...data,
              messageId:
                String(
                  data?.messageId ||
                  data?.assistant_message_id ||
                  localMessageId
                ).trim(),
            })
          }
        },

        onToken(token){
          if(typeof callbacks.onToken === "function"){
            callbacks.onToken(token)
          }

          if(scrollEl && !autoScrollLocked){
            requestAnimationFrame(() => {
              scrollToBottom(scrollEl)
            })
          }
        },
      })

      if(typeof callbacks.onDone === "function"){
        callbacks.onDone({
          ...result,
          messageId:
            String(
              result?.messageId ||
              result?.assistant_message_id ||
              localMessageId
            ).trim(),
        })
      }

      return result
    }catch(error){
      if(typeof callbacks.onError === "function"){
        callbacks.onError(error)
      }

      throw error
    }finally{
      activeController = null
      state.isStreaming = false

      if(typeof callbacks.onFinally === "function"){
        callbacks.onFinally()
      }

      if(scrollEl && !autoScrollLocked){
        requestAnimationFrame(() => {
          scrollToBottom(scrollEl)
        })
      }
    }
  }

  return {
    send,
    stop,
    isStreaming: () => state.isStreaming,
    setCallbacks,
  }
}

window.NovaStreamService = {
  create: createStreamService,
  createStreamService,
}

})()