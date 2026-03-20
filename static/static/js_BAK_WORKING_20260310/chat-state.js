// C:\Users\Owner\nova\static\js\chat-state.js

(() => {
"use strict"

/*
  Nova Chat Global State
  ----------------------
  This becomes the single source of truth for the UI.
  All other modules read/write here.
*/

function generateId(prefix = "id"){
  if(window.crypto?.randomUUID){
    return window.crypto.randomUUID()
  }

  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`
}

function escapeHtml(value){
  return String(value ?? "")
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#039;")
}

const STORAGE_KEYS = {
  activeChatId: "nova_active_chat_id"
}

const state = {

  /* chat structure */

  chats: [],
  messages: [],

  /* ids */

  activeChatId: null,

  /* ui flags */

  sidebarOpen: true,
  isStreaming: false,
  isSending: false,

  /* rename */

  renamingChatId: null,

  /* attachments */

  pendingAttachments: [],
  pendingFiles: [],

  /* scroll state */

  userScrolledUp: false,

  /* streaming */

  streamingMessageId: null,

}

/*
  Helper API
*/

function getActiveChat(){
  return state.chats.find(
    c => String(c.chat_id || c.id) === String(state.activeChatId)
  )
}

function setActiveChat(chatId){

  state.activeChatId = String(chatId)

  try{
    localStorage.setItem(
      STORAGE_KEYS.activeChatId,
      state.activeChatId
    )
  }catch(_){}
}

function restoreActiveChat(){

  try{
    const saved = localStorage.getItem(STORAGE_KEYS.activeChatId)

    if(saved){
      state.activeChatId = saved
    }
  }catch(_){}
}

function clearMessages(){
  state.messages = []
}

function addMessage(message){
  state.messages.push(message)
}

function createMessage(role, content){

  return {
    id: generateId("msg"),
    role,
    content: content || "",
    created_at: Date.now()
  }
}

window.NovaChatState = {
  state,
  STORAGE_KEYS,

  generateId,
  escapeHtml,

  getActiveChat,
  setActiveChat,
  restoreActiveChat,

  clearMessages,
  addMessage,
  createMessage
}

})()