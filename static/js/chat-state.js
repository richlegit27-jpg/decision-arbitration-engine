(() => {
"use strict"

const STORAGE_KEYS = {
  ACTIVE_CHAT_ID: "nova_active_chat_id",
  THEME: "nova_theme",
}

const state = {
  activeChatId: null,
  chats: [],
  messages: [],
  pendingAttachments: [],
  memoryItems: [],
  ui: {
    sidebarOpen: true,
    memoryOpen: false,
    filesOpen: false,
  },
}

function generateId(prefix = "id"){
  if(window.crypto?.randomUUID){
    return `${prefix}_${window.crypto.randomUUID()}`
  }
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`
}

function nowIso(){ return new Date().toISOString() }

function createChat(title = "New Chat"){
  const id = generateId("chat")
  const timestamp = nowIso()
  const chat = { id, title, created_at: timestamp, updated_at: timestamp, messages: [] }
  state.chats.unshift(chat)
  state.activeChatId = id
  state.messages = chat.messages
  return chat
}

function getChatById(chatId){ return state.chats.find(c => c.id===chatId)||null }
function ensureActiveChat(){
  if(state.activeChatId){
    const c = getChatById(state.activeChatId)
    if(c){ state.messages=c.messages; return c }
  }
  if(state.chats.length){ state.activeChatId=state.chats[0].id; state.messages=state.chats[0].messages; return state.chats[0] }
  return createChat("New Chat")
}
function setActiveChat(chatId){
  const chat = getChatById(chatId)
  if(!chat) return null
  state.activeChatId = chat.id
  state.messages = chat.messages
  chat.updated_at = nowIso()
  window.dispatchEvent(new CustomEvent("nova:chat-changed",{detail:{chatId:chat.id}}))
  return chat
}
function updateActiveChatTitle(title){
  const chat = ensureActiveChat()
  if(!title?.trim()) return chat
  chat.title = title.trim()
  chat.updated_at = nowIso()
  window.dispatchEvent(new CustomEvent("nova:chat-title-changed",{detail:{chatId:chat.id,title:chat.title}}))
  return chat
}
function deleteChat(chatId){
  const index = state.chats.findIndex(c=>c.id===chatId)
  if(index===-1) return false
  state.chats.splice(index,1)
  if(state.activeChatId===chatId){ state.activeChatId=null; state.messages=[]; ensureActiveChat() }
  window.dispatchEvent(new CustomEvent("nova:chat-deleted",{detail:{chatId}}))
  return true
}
function getActiveChat(){ return ensureActiveChat() }

window.NovaChatState = { state, STORAGE_KEYS, generateId, nowIso, createChat, getChatById, setActiveChat, updateActiveChatTitle, deleteChat, getActiveChat }
})();