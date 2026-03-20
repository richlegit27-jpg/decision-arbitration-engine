// C:\Users\Owner\nova\static\js\chat-service.js

(() => {
"use strict"

function createChatService(options = {}){
  const {
    state,
    api,
    elements = {},
  } = options

  if(!state){
    throw new Error("NovaChatService: state is required")
  }

  const apiClient = api || window.NovaAPI

  if(!apiClient){
    throw new Error("NovaChatService: api is required")
  }

  const el = {
    chatList: elements.chatList || null,
  }

  function normalizeChat(raw = {}){
    const chatId = String(raw?.chat_id || raw?.id || "").trim()

    return {
      ...raw,
      chat_id: chatId,
      id: chatId,
      title: String(raw?.title || "New chat"),
      created_at: raw?.created_at || raw?.created || "",
      updated_at: raw?.updated_at || raw?.updated || raw?.created_at || raw?.created || "",
    }
  }

  function normalizeChats(payload){
    const list =
      Array.isArray(payload) ? payload :
      Array.isArray(payload?.chats) ? payload.chats :
      Array.isArray(payload?.items) ? payload.items :
      []

    return list
      .map(normalizeChat)
      .filter((chat) => String(chat?.chat_id || "").trim())
  }

  function normalizeMessages(payload){
    const list =
      Array.isArray(payload) ? payload :
      Array.isArray(payload?.messages) ? payload.messages :
      Array.isArray(payload?.items) ? payload.items :
      []

    return list.map((message) => ({
      ...message,
      message_id: String(message?.message_id || message?.id || "").trim(),
      id: String(message?.message_id || message?.id || "").trim(),
      role: String(message?.role || "assistant"),
      content: String(message?.content || ""),
      attachments: Array.isArray(message?.attachments) ? message.attachments : [],
    }))
  }

  function sortChatsNewestFirst(chats){
    return [...chats].sort((a, b) => {
      const aTime = new Date(a?.updated_at || a?.created_at || 0).getTime() || 0
      const bTime = new Date(b?.updated_at || b?.created_at || 0).getTime() || 0
      return bTime - aTime
    })
  }

  async function listChats(){
    const payload = await apiClient.listChats()
    const chats = sortChatsNewestFirst(normalizeChats(payload))

    state.chats = chats

    if(!state.activeChatId && chats.length > 0){
      const firstId = String(chats[0]?.chat_id || "").trim()
      if(firstId){
        state.activeChatId = firstId
        state.chatId = firstId
      }
    }

    return chats
  }

  async function getMessages(chatId){
    const id = String(chatId || state.activeChatId || state.chatId || "").trim()

    if(!id){
      state.messages = []
      return []
    }

    const payload = await apiClient.getMessages(id)
    const messages = normalizeMessages(payload)

    state.activeChatId = id
    state.chatId = id
    state.messages = messages

    return messages
  }

  async function loadChat(chatId){
    const id = String(chatId || "").trim()

    if(!id){
      state.messages = []
      return []
    }

    return await getMessages(id)
  }

  async function createChat(){
    const beforeActiveId = String(state.activeChatId || state.chatId || "").trim()

    const payload = await apiClient.createChat()
    const created = normalizeChat(
      payload?.chat || payload?.item || payload || {}
    )

    let createdId = String(created?.chat_id || "").trim()

    const chats = await listChats()

    if(!createdId){
      const firstId = String(chats?.[0]?.chat_id || "").trim()
      if(firstId && firstId !== beforeActiveId){
        createdId = firstId
      }
    }

    if(createdId){
      state.activeChatId = createdId
      state.chatId = createdId
      state.messages = []
      await loadChat(createdId)

      const createdChat =
        (Array.isArray(state.chats) ? state.chats.find((chat) => String(chat?.chat_id || "") === createdId) : null) ||
        created ||
        { chat_id: createdId, id: createdId, title: "New chat" }

      return createdChat
    }

    state.activeChatId = null
    state.chatId = null
    state.messages = []

    return created
  }

  async function renameChat(chatId, title){
    const id = String(chatId || "").trim()
    const nextTitle = String(title || "").trim()

    if(!id){
      throw new Error("NovaChatService.renameChat: chatId is required")
    }

    if(!nextTitle){
      throw new Error("NovaChatService.renameChat: title is required")
    }

    const payload = await apiClient.renameChat(id, nextTitle)

    if(Array.isArray(state.chats)){
      const target = state.chats.find((chat) => String(chat?.chat_id || "") === id)
      if(target){
        target.title = nextTitle
        target.updated_at = new Date().toISOString()
      }
      state.chats = sortChatsNewestFirst(state.chats)
    }

    return payload
  }

  async function deleteChat(chatId){
    const id = String(chatId || "").trim()

    if(!id){
      throw new Error("NovaChatService.deleteChat: chatId is required")
    }

    const payload = await apiClient.deleteChat(id)

    if(Array.isArray(state.chats)){
      state.chats = state.chats.filter((chat) => String(chat?.chat_id || "") !== id)
    }

    if(String(state.activeChatId || "") === id || String(state.chatId || "") === id){
      state.activeChatId = ""
      state.chatId = ""
      state.messages = []
    }

    return payload
  }

  return {
    listChats,
    getMessages,
    loadChat,
    createChat,
    renameChat,
    deleteChat,
  }
}

window.NovaChatService = {
  create: createChatService,
  createChatService,
}

})()