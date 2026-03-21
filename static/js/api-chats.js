// C:\Users\Owner\nova\static\js\api-chats.js

(() => {
"use strict"

const core = window.NovaAPICore

if(!core){
  throw new Error("NovaAPIChats: window.NovaAPICore is required")
}

const {
  fetchJson,
  jsonOptions,
  normalizeChat,
  normalizeChatList,
  normalizeMessageList,
} = core

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

window.NovaAPIChats = {
  listChats,
  getMessages,
  createChat,
  renameChat,
  deleteChat,
  postMessage,
}

})()