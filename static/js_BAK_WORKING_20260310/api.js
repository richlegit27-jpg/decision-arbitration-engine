// C:\Users\Owner\nova\static\js\api.js

(() => {
"use strict"

const DEFAULT_HEADERS = {
  Accept: "application/json",
}

function joinUrl(path){
  return String(path || "").trim()
}

function safeJsonParse(text){
  try{
    return JSON.parse(text)
  }catch(_error){
    return null
  }
}

function buildHttpError(response, text){
  const message = text && String(text).trim()
    ? String(text)
    : `${response.status} ${response.statusText}`

  const error = new Error(message)
  error.name = "NovaHttpError"
  error.status = response.status
  error.statusText = response.statusText
  error.response = response
  error.bodyText = text
  error.bodyJson = safeJsonParse(text)
  return error
}

async function fetchJson(path, options = {}){
  const response = await fetch(joinUrl(path), {
    credentials: "same-origin",
    cache: "no-store",
    ...options,
    headers: {
      ...DEFAULT_HEADERS,
      ...(options.headers || {}),
    },
  })

  const text = await response.text()

  if(!response.ok){
    throw buildHttpError(response, text)
  }

  if(!text){
    return {}
  }

  const json = safeJsonParse(text)
  if(json === null){
    const error = new Error(`Expected JSON but received: ${text.slice(0, 200)}`)
    error.name = "NovaParseError"
    error.bodyText = text
    throw error
  }

  return json
}

function jsonOptions(method, body){
  return {
    method,
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body || {}),
  }
}

function getReplyText(payload = {}){
  return String(
    payload?.reply ??
    payload?.response ??
    payload?.output ??
    payload?.message?.content ??
    payload?.message ??
    payload?.content ??
    payload?.text ??
    ""
  )
}

function normalizeChat(payload = {}, fallback = {}){
  const chatId =
    payload.chat_id ||
    payload.id ||
    payload.session_id ||
    fallback.chat_id ||
    fallback.id ||
    "default-chat"

  const title =
    payload.title ||
    payload.name ||
    fallback.title ||
    fallback.name ||
    "New chat"

  return {
    ...payload,
    chat_id: String(chatId),
    id: String(chatId),
    title: String(title),
    created_at: payload.created_at || payload.created || fallback.created_at || fallback.created || null,
    updated_at: payload.updated_at || payload.updated || payload.created_at || payload.created || fallback.updated_at || fallback.updated || null,
  }
}

function normalizeMessage(payload = {}, fallback = {}){
  const messageId =
    payload.message_id ||
    payload.id ||
    fallback.message_id ||
    fallback.id ||
    `msg_${Date.now()}_${Math.random().toString(16).slice(2)}`

  return {
    ...payload,
    message_id: String(messageId),
    id: String(messageId),
    role: String(payload.role || fallback.role || "assistant"),
    content: String(
      payload.content ??
      payload.text ??
      fallback.content ??
      fallback.text ??
      ""
    ),
    attachments: Array.isArray(payload.attachments)
      ? payload.attachments
      : Array.isArray(fallback.attachments)
        ? fallback.attachments
        : [],
    created_at: payload.created_at || payload.created || fallback.created_at || fallback.created || null,
  }
}

function normalizeReplyToMessages(payload = {}, fallbackMessage = ""){
  const replyText = getReplyText(payload)
  const userText = String(fallbackMessage || "")
  const stamp = Date.now()

  const items = []

  if(userText){
    items.push(normalizeMessage({
      message_id: `local-user-${stamp}`,
      role: "user",
      content: userText,
      attachments: [],
      created_at: null,
    }))
  }

  if(replyText){
    items.push(normalizeMessage({
      message_id: `local-assistant-${stamp + 1}`,
      role: "assistant",
      content: replyText,
      attachments: [],
      created_at: null,
    }))
  }

  return items
}

function normalizeChatList(payload){
  const list =
    Array.isArray(payload) ? payload :
    Array.isArray(payload?.chats) ? payload.chats :
    Array.isArray(payload?.items) ? payload.items :
    Array.isArray(payload?.sessions) ? payload.sessions :
    []

  return list
    .map((item) => normalizeChat(item))
    .filter((item) => String(item.chat_id || "").trim())
}

function normalizeMessageList(payload){
  const list =
    Array.isArray(payload) ? payload :
    Array.isArray(payload?.messages) ? payload.messages :
    Array.isArray(payload?.items) ? payload.items :
    []

  return list.map((item) => normalizeMessage(item))
}

async function listChats(){
  const payload = await fetchJson("/api/chats")
  const chats = normalizeChatList(payload)
  return {
    ...payload,
    chats,
  }
}

async function getMessages(chatId){
  const id = String(chatId || "").trim()
  if(!id){
    return { messages: [] }
  }

  const payload = await fetchJson(`/api/chats/${encodeURIComponent(id)}/messages`)
  const messages = normalizeMessageList(payload)
  return {
    ...payload,
    messages,
  }
}

async function createChat(payload = {}){
  const body = {
    title: String(payload?.title || "New chat"),
  }

  const result = await fetchJson("/api/chats", jsonOptions("POST", body))
  const chat = normalizeChat(result?.chat || result?.item || result || {}, body)
  return {
    ...result,
    chat,
    chat_id: chat.chat_id,
    id: chat.id,
    title: chat.title,
  }
}

async function renameChat(chatId, title){
  const id = String(chatId || "").trim()
  const nextTitle = String(title || "").trim() || "New chat"

  if(!id){
    throw new Error("NovaAPI.renameChat: chatId is required")
  }

  const result = await fetchJson(
    `/api/chats/${encodeURIComponent(id)}`,
    jsonOptions("PATCH", { title: nextTitle })
  )

  const chat = normalizeChat(
    result?.chat || result?.item || result || {},
    {
      chat_id: id,
      title: nextTitle,
    }
  )

  return {
    ...result,
    chat,
    chat_id: chat.chat_id,
    id: chat.id,
    title: chat.title,
  }
}

async function deleteChat(chatId){
  const id = String(chatId || "").trim()

  if(!id){
    throw new Error("NovaAPI.deleteChat: chatId is required")
  }

  return fetchJson(`/api/chats/${encodeURIComponent(id)}`, {
    method: "DELETE",
  })
}

async function postMessage(chatId, payload = {}){
  const body = {
    chat_id: String(chatId || "default-chat"),
    message: String(
      payload?.message ??
      payload?.content ??
      payload?.text ??
      ""
    ),
    files: Array.isArray(payload?.files) ? payload.files : [],
    attachments: Array.isArray(payload?.attachments) ? payload.attachments : [],
  }

  return fetchJson("/api/chat", jsonOptions("POST", body))
}

function splitSseEvents(buffer){
  const normalized = buffer.replaceAll("\r\n", "\n")
  const parts = normalized.split("\n\n")
  const remainder = parts.pop() ?? ""
  return {
    events: parts,
    remainder,
  }
}

function parseSseEventBlock(block){
  const lines = String(block || "").split("\n")
  const dataLines = []
  let eventName = ""

  for(const rawLine of lines){
    const line = String(rawLine || "")
    if(!line.trim()){
      continue
    }

    if(line.startsWith(":")){
      continue
    }

    if(line.startsWith("event:")){
      eventName = line.slice(6).trim()
      continue
    }

    if(line.startsWith("data:")){
      dataLines.push(line.slice(5).trim())
      continue
    }
  }

  return {
    event: eventName,
    payloadText: dataLines.join("\n").trim(),
  }
}

function handleRawStreamPayload(payloadText, handlers = {}, eventName = ""){
  const text = String(payloadText || "").trim()
  if(!text){
    return
  }

  if(text === "[DONE]"){
    handlers.onDone?.({
      done: true,
      event: eventName || "done",
    })
    return
  }

  const parsed = safeJsonParse(text)

  if(parsed && typeof parsed === "object"){
    if(eventName && !parsed.event){
      parsed.event = eventName
    }

    if(
      parsed.done === true ||
      parsed.event === "done" ||
      parsed.type === "done"
    ){
      handlers.onDone?.(parsed)
      return
    }

    const token =
      parsed?.token ??
      parsed?.delta ??
      parsed?.content_delta ??
      parsed?.text_delta ??
      null

    if(token){
      handlers.onToken?.(String(token), parsed)
    }else{
      const replyText = getReplyText(parsed)
      if(replyText && eventName !== "done"){
        handlers.onToken?.(replyText, parsed)
      }
    }

    handlers.onChunk?.(parsed)
    return
  }

  handlers.onToken?.(text, {
    event: eventName || "",
    raw: true,
  })
}

async function readStreamResponse(response, handlers = {}){
  if(!response.ok){
    const text = await response.text()
    throw buildHttpError(response, text)
  }

  const contentType = String(response.headers.get("content-type") || "").toLowerCase()
  const isJsonLike = contentType.includes("application/json")

  if(isJsonLike){
    const text = await response.text()
    const parsed = safeJsonParse(text || "") || {}
    const token = getReplyText(parsed)

    if(token){
      handlers.onToken?.(token, parsed)
    }

    handlers.onDone?.(parsed)
    return
  }

  const reader = response.body?.getReader?.()

  if(!reader){
    const text = await response.text()
    const parsed = safeJsonParse(text || "") || {}
    const token = getReplyText(parsed)

    if(token){
      handlers.onToken?.(token, parsed)
    }

    handlers.onDone?.(parsed)
    return
  }

  const decoder = new TextDecoder()
  let buffer = ""
  let doneCalled = false

  function doneOnce(payload){
    if(doneCalled){
      return
    }
    doneCalled = true
    handlers.onDone?.(payload)
  }

  while(true){
    const result = await reader.read()
    if(result.done){
      break
    }

    buffer += decoder.decode(result.value, { stream: true })

    const { events, remainder } = splitSseEvents(buffer)
    buffer = remainder

    for(const eventBlock of events){
      const { event, payloadText } = parseSseEventBlock(eventBlock)

      if(!payloadText){
        continue
      }

      handleRawStreamPayload(payloadText, {
        ...handlers,
        onDone(payload){
          doneOnce(payload)
        },
      }, event)
    }
  }

  buffer += decoder.decode()

  const trailing = buffer.trim()
  if(trailing){
    if(trailing.includes("\n\n") || trailing.startsWith("data:") || trailing.startsWith("event:")){
      const { events, remainder } = splitSseEvents(`${trailing}\n\n`)

      for(const eventBlock of events){
        const { event, payloadText } = parseSseEventBlock(eventBlock)
        handleRawStreamPayload(payloadText, {
          ...handlers,
          onDone(payload){
            doneOnce(payload)
          },
        }, event)
      }

      if(remainder.trim()){
        const { event, payloadText } = parseSseEventBlock(remainder)
        handleRawStreamPayload(payloadText, {
          ...handlers,
          onDone(payload){
            doneOnce(payload)
          },
        }, event)
      }
    }else{
      const parsed = safeJsonParse(trailing)
      if(parsed && typeof parsed === "object"){
        if(
          parsed.done === true ||
          parsed.event === "done" ||
          parsed.type === "done"
        ){
          doneOnce(parsed)
        }else{
          const token =
            parsed?.token ??
            parsed?.delta ??
            parsed?.content_delta ??
            parsed?.text_delta ??
            getReplyText(parsed)

          if(token){
            handlers.onToken?.(String(token), parsed)
          }

          handlers.onChunk?.(parsed)
        }
      }else{
        handlers.onToken?.(trailing)
      }
    }
  }

  doneOnce()
}

async function streamChat(payload = {}, handlers = {}){
  const body = {
    chat_id: String(payload?.chatId || payload?.chat_id || "default-chat"),
    message: String(payload?.message || ""),
    files: Array.isArray(payload?.files) ? payload.files : [],
    attachments: Array.isArray(payload?.attachments) ? payload.attachments : [],
  }

  const endpoints = [
    "/api/chat/stream",
    "/api/chat_stream",
    "/api/chat",
  ]

  let lastError = null

  for(const endpoint of endpoints){
    const response = await fetch(joinUrl(endpoint), {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json, text/event-stream",
      },
      body: JSON.stringify(body),
      signal: handlers.signal,
    })

    if(response.status === 404){
      lastError = response
      continue
    }

    await readStreamResponse(response, handlers)
    return { ok: true }
  }

  if(lastError){
    const text = await lastError.text()
    throw buildHttpError(lastError, text)
  }

  return { ok: false }
}

async function uploadFiles(files){
  const list = Array.isArray(files) ? files : Array.from(files || [])
  if(!list.length){
    return []
  }

  const formData = new FormData()
  for(const file of list){
    formData.append("files", file)
  }

  const response = await fetch("/api/upload", {
    method: "POST",
    credentials: "same-origin",
    cache: "no-store",
    body: formData,
  })

  const text = await response.text()

  if(!response.ok){
    throw buildHttpError(response, text)
  }

  const json = text ? safeJsonParse(text) : {}
  return Array.isArray(json?.files) ? json.files : (Array.isArray(json) ? json : [])
}

window.NovaAPI = {
  buildHttpError,
  fetchJson,
  listChats,
  getMessages,
  createChat,
  renameChat,
  deleteChat,
  postMessage,
  streamChat,
  uploadFiles,
  normalizeReplyToMessages,
  normalizeChat,
  normalizeMessage,
}

})()