// C:\Users\Owner\nova\static\js\stream-service.js

(() => {
"use strict"

let activeController = null
let activeReader = null
let activeMessageId = ""
let activeRequestId = 0
let streaming = false
let stopRequested = false

let callbacks = {
  onStart: null,
  onMeta: null,
  onToken: null,
  onDone: null,
  onError: null,
  onFinally: null,
}

function generateMessageId(prefix = "msg"){
  if(window.crypto?.randomUUID){
    return `${prefix}_${window.crypto.randomUUID()}`
  }

  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`
}

function setCallbacks(nextCallbacks = {}){
  callbacks = {
    ...callbacks,
    ...nextCallbacks,
  }
}

function isStreaming(){
  return streaming
}

function stop(){
  stopRequested = true

  if(activeReader){
    try{
      activeReader.cancel()
    }catch(_error){
      // ignore reader cancel cleanup errors
    }
  }

  if(activeController){
    try{
      activeController.abort()
    }catch(_error){
      // ignore abort cleanup errors
    }
  }

  return true
}

function safeJsonParse(value){
  try{
    return JSON.parse(value)
  }catch(_error){
    return null
  }
}

function emit(name, payload){
  const handler = callbacks?.[name]
  if(typeof handler !== "function"){
    return
  }

  try{
    handler(payload)
  }catch(error){
    console.error(`NovaStreamService ${name} callback error:`, error)
  }
}

function isAbortLikeError(error){
  const name = String(error?.name || "")
  const message = String(error?.message || "")

  return (
    name === "AbortError" ||
    /aborted/i.test(message) ||
    /abort/i.test(name) ||
    /The operation was aborted/i.test(message)
  )
}

async function send(payload = {}){
  if(streaming){
    stop()
  }

  const controller = new AbortController()
  const requestId = Date.now() + Math.random()

  activeController = controller
  activeReader = null
  activeRequestId = requestId
  streaming = true
  stopRequested = false

  const chatId = String(payload.chatId || payload.chat_id || "").trim()
  const message = String(payload.message || "").trim()
  const attachments = Array.isArray(payload.attachments)
    ? payload.attachments.slice()
    : Array.isArray(payload.files)
      ? payload.files.slice()
      : []

  const messageId = String(payload.messageId || payload.message_id || generateMessageId("msg")).trim()
  activeMessageId = messageId

  emit("onStart", {
    messageId,
    chatId,
  })

  let finalContent = ""
  let resolvedAssistantMessageId = messageId
  let donePayload = null
  let aborted = false

  try{
    const response = await fetch("/api/chat_stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        chat_id: chatId,
        message,
        attachments,
      }),
      signal: controller.signal,
    })

    if(requestId !== activeRequestId){
      return {
        ok: false,
        aborted: true,
        stale: true,
        message_id: resolvedAssistantMessageId || messageId,
        assistant_message_id: resolvedAssistantMessageId || messageId,
        content: finalContent,
        chat_id: chatId,
      }
    }

    if(!response.ok){
      const errorText = await response.text().catch(() => "")
      throw new Error(`/api/chat_stream failed (${response.status}) ${errorText}`.trim())
    }

    if(!response.body){
      throw new Error("Streaming response body missing.")
    }

    const reader = response.body.getReader()
    activeReader = reader

    const decoder = new TextDecoder()
    let buffer = ""

    while(true){
      const { done, value } = await reader.read()

      if(requestId !== activeRequestId){
        aborted = true
        break
      }

      if(done){
        break
      }

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n")
      buffer = lines.pop() || ""

      for(const rawLine of lines){
        if(requestId !== activeRequestId){
          aborted = true
          break
        }

        const line = String(rawLine || "").trim()
        if(!line){
          continue
        }

        const data = safeJsonParse(line)
        if(!data){
          continue
        }

        const type = String(data.type || "").trim().toLowerCase()

        if(type === "meta" || type === "start"){
          resolvedAssistantMessageId = String(
            data.message_id ||
            data.assistant_message_id ||
            resolvedAssistantMessageId ||
            messageId
          ).trim()

          emit("onMeta", {
            ...data,
            messageId: resolvedAssistantMessageId,
            assistant_message_id: resolvedAssistantMessageId,
            chatId,
          })

          continue
        }

        if(type === "token"){
          const token = String(data.token || "")
          const tokenMessageId = String(
            data.message_id ||
            data.assistant_message_id ||
            resolvedAssistantMessageId ||
            messageId
          ).trim()

          if(tokenMessageId){
            resolvedAssistantMessageId = tokenMessageId
          }

          finalContent += token
          emit("onToken", token)
          continue
        }

        if(type === "done"){
          const doneMessageId = String(
            data.message_id ||
            data.assistant_message_id ||
            resolvedAssistantMessageId ||
            messageId
          ).trim()

          if(doneMessageId){
            resolvedAssistantMessageId = doneMessageId
          }

          donePayload = {
            ...data,
            messageId: resolvedAssistantMessageId,
            assistant_message_id: resolvedAssistantMessageId,
            content: String(data.content || finalContent || ""),
            chat_id: String(data.chat_id || chatId || "").trim(),
          }

          continue
        }

        if(type === "error"){
          throw new Error(String(data.error || data.message || "Streaming request failed."))
        }
      }

      if(aborted){
        break
      }
    }

    if(!aborted){
      const flushed = decoder.decode()
      if(flushed){
        buffer += flushed
      }

      if(buffer.trim()){
        const data = safeJsonParse(buffer.trim())
        const type = String(data?.type || "").trim().toLowerCase()

        if(type === "done"){
          const doneMessageId = String(
            data?.message_id ||
            data?.assistant_message_id ||
            resolvedAssistantMessageId ||
            messageId
          ).trim()

          if(doneMessageId){
            resolvedAssistantMessageId = doneMessageId
          }

          donePayload = {
            ...data,
            messageId: resolvedAssistantMessageId,
            assistant_message_id: resolvedAssistantMessageId,
            content: String(data?.content || finalContent || ""),
            chat_id: String(data?.chat_id || chatId || "").trim(),
          }
        }
      }
    }

    if(stopRequested){
      aborted = true
    }

    if(aborted){
      return {
        ok: false,
        aborted: true,
        message_id: resolvedAssistantMessageId || messageId,
        assistant_message_id: resolvedAssistantMessageId || messageId,
        content: finalContent,
        chat_id: chatId,
      }
    }

    const finalPayload = donePayload || {
      messageId: resolvedAssistantMessageId || messageId,
      assistant_message_id: resolvedAssistantMessageId || messageId,
      content: finalContent,
      chat_id: chatId,
    }

    emit("onDone", finalPayload)

    return {
      ok: true,
      aborted: false,
      message_id: String(finalPayload.messageId || "").trim(),
      assistant_message_id: String(finalPayload.assistant_message_id || "").trim(),
      content: String(finalPayload.content || ""),
      chat_id: String(finalPayload.chat_id || chatId || "").trim(),
    }
  }catch(error){
    aborted = stopRequested || isAbortLikeError(error)

    if(aborted){
      return {
        ok: false,
        aborted: true,
        message_id: resolvedAssistantMessageId || messageId,
        assistant_message_id: resolvedAssistantMessageId || messageId,
        content: finalContent,
        chat_id: chatId,
      }
    }

    emit("onError", error)
    throw error
  }finally{
    const finalMessageId = activeMessageId
    const finalAborted = aborted || stopRequested

    if(activeRequestId === requestId){
      streaming = false
      activeController = null
      activeReader = null
      activeMessageId = ""
      activeRequestId = 0
      stopRequested = false
    }

    emit("onFinally", {
      messageId: finalMessageId,
      aborted: finalAborted,
      content: finalContent,
    })
  }
}

window.NovaStreamService = {
  setCallbacks,
  send,
  stop,
  isStreaming,
}
})()