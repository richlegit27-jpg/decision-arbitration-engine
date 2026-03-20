// C:\Users\Owner\nova\static\js\chat-sidebar-actions.js

(() => {
"use strict"

function createChatSidebarActions(options = {}){
  const {
    state,
    chatStorage,
    renderController,
    layoutController,
    callbacks = {},
  } = options

  if(!state){
    throw new Error("NovaChatSidebarActions: state is required")
  }

  if(!chatStorage){
    throw new Error("NovaChatSidebarActions: chatStorage is required")
  }

  if(!renderController){
    throw new Error("NovaChatSidebarActions: renderController is required")
  }

  if(!layoutController){
    throw new Error("NovaChatSidebarActions: layoutController is required")
  }

  const {
    ensureChatsArray,
    getChatId,
    renderChatList,
  } = renderController

  function syncActiveChatMessages(chatId){
    const nextId = String(chatId || "").trim()

    if(!nextId){
      state.messages = []
      return state.messages
    }

    if(typeof chatStorage.loadMessagesIntoState === "function"){
      return chatStorage.loadMessagesIntoState(nextId)
    }

    state.messages = typeof chatStorage.loadMessages === "function"
      ? chatStorage.loadMessages(nextId)
      : []

    return state.messages
  }

  function resetUiAfterDeleteAll(){
    state.messages = []

    const chatList = document.getElementById("chatList")
    if(chatList){
      chatList.innerHTML = `<div class="chat-list-empty">No chats yet</div>`
    }

    const messages = document.getElementById("messages")
    if(messages){
      messages.innerHTML = ""
    }

    const topbarTitle = document.getElementById("topbarTitle")
    if(topbarTitle){
      topbarTitle.textContent = "New chat"
    }

    const emptyState = document.getElementById("emptyState")
    if(emptyState){
      emptyState.hidden = false
    }
  }

  async function createNewChat({ onAfterCreate } = {}){
    const created = await chatStorage.createChat({
      title: "New chat",
    })

    const chatId = getChatId(created)

    if(chatId){
      state.activeChatId = chatId

      if(typeof chatStorage.setActiveChat === "function"){
        chatStorage.setActiveChat(chatId)
      }

      syncActiveChatMessages(chatId)
    }else{
      state.messages = []
    }

    await chatStorage.loadChats()
    renderChatList()

    if(typeof onAfterCreate === "function"){
      onAfterCreate(created)
    }

    if(typeof callbacks.onAfterCreate === "function"){
      callbacks.onAfterCreate(created)
    }

    if(layoutController.isMobile()){
      layoutController.closeSidebar()
    }

    return created
  }

  async function switchChat(chatId){
    const nextId = String(chatId || "").trim()
    if(!nextId){
      return
    }

    state.activeChatId = nextId

    if(typeof chatStorage.setActiveChat === "function"){
      chatStorage.setActiveChat(nextId)
    }

    syncActiveChatMessages(nextId)
    renderChatList()

    if(typeof callbacks.onAfterSwitch === "function"){
      callbacks.onAfterSwitch(nextId)
    }

    if(layoutController.isMobile()){
      layoutController.closeSidebar()
    }
  }

  async function renameChat(chatId){
    const targetId = String(chatId || "").trim()
    if(!targetId){
      return
    }

    const chats = ensureChatsArray()
    const current = chats.find((chat) => getChatId(chat) === targetId)
    const nextTitle = window.prompt("Rename chat", current?.title || "New chat")

    if(nextTitle === null){
      return
    }

    await chatStorage.renameChat(targetId, String(nextTitle || "").trim() || "New chat")
    await chatStorage.loadChats()
    renderChatList()

    if(typeof callbacks.onAfterRename === "function"){
      callbacks.onAfterRename(targetId)
    }
  }

  async function deleteChat(chatId){
    const targetId = String(chatId || "").trim()
    if(!targetId){
      return
    }

    const ok = window.confirm("Delete this chat?")
    if(!ok){
      return
    }

    const deletingActive = String(state.activeChatId || "").trim() === targetId

    if(typeof chatStorage.deleteChat === "function"){
      await chatStorage.deleteChat(targetId)
    }else if(typeof chatStorage.removeChat === "function"){
      await chatStorage.removeChat(targetId)
    }else{
      throw new Error("NovaChatSidebarActions: deleteChat/removeChat is not available")
    }

    await chatStorage.loadChats()

    const chats = ensureChatsArray()
    const nextActiveId = getChatId(chats[0]) || ""

    if(deletingActive){
      state.activeChatId = nextActiveId

      if(typeof chatStorage.setActiveChat === "function"){
        chatStorage.setActiveChat(nextActiveId || "")
      }

      if(nextActiveId){
        syncActiveChatMessages(nextActiveId)
      }else{
        state.messages = []
      }
    }else if(!ensureChatsArray().some((chat) => getChatId(chat) === String(state.activeChatId || "").trim())){
      state.activeChatId = nextActiveId

      if(typeof chatStorage.setActiveChat === "function"){
        chatStorage.setActiveChat(nextActiveId || "")
      }

      if(nextActiveId){
        syncActiveChatMessages(nextActiveId)
      }else{
        state.messages = []
      }
    }

    renderChatList()

    if(typeof callbacks.onAfterDelete === "function"){
      callbacks.onAfterDelete(targetId)
    }
  }

  async function deleteAllChats(){
    const ok = window.confirm("Delete ALL chats? This cannot be undone.")
    if(!ok){
      return false
    }

    if(typeof chatStorage.removeAllChats !== "function"){
      throw new Error("NovaChatSidebarActions: removeAllChats is not available")
    }

    await chatStorage.removeAllChats()

    if(typeof chatStorage.loadChats === "function"){
      await chatStorage.loadChats()
    }

    state.activeChatId = ""

    if(typeof chatStorage.setActiveChat === "function"){
      chatStorage.setActiveChat("")
    }

    resetUiAfterDeleteAll()
    renderChatList()

    if(typeof callbacks.onAfterDeleteAll === "function"){
      callbacks.onAfterDeleteAll()
    }

    return true
  }

  return {
    createNewChat,
    switchChat,
    renameChat,
    deleteChat,
    deleteAllChats,
  }
}

window.NovaChatSidebarActions = {
  create: createChatSidebarActions,
  createChatSidebarActions,
}

})()