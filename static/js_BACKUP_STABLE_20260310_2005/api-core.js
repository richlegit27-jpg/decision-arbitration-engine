// C:\Users\Owner\nova\static\js\api-core.js

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

function normalizeMemoryList(payload = {}){
  const list =
    Array.isArray(payload) ? payload :
    Array.isArray(payload?.memories) ? payload.memories :
    Array.isArray(payload?.items) ? payload.items :
    []

  return list
    .map((item) => String(item || "").trim())
    .filter(Boolean)
}

window.NovaAPICore = {
  DEFAULT_HEADERS,
  joinUrl,
  safeJsonParse,
  buildHttpError,
  fetchJson,
  jsonOptions,
  getReplyText,
  normalizeChat,
  normalizeMessage,
  normalizeReplyToMessages,
  normalizeChatList,
  normalizeMessageList,
  normalizeMemoryList,
}

})()