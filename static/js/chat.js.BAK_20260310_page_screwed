// C:\Users\Owner\nova\static\js\chat.js

(() => {
"use strict"

function byId(id){
  return document.getElementById(id)
}

function escapeHtml(value){
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;")
}

function makeId(prefix){
  if(window.crypto && typeof window.crypto.randomUUID === "function"){
    return window.crypto.randomUUID()
  }
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`
}

const SCROLL_LOCK_THRESHOLD = 120
const MOBILE_BREAKPOINT = 620

const el = {
  body: document.body,
  appShell: byId("appShell"),
  sidebar: byId("sidebar"),
  mobileOverlay: byId("mobileOverlay"),
  btnSidebarToggle: byId("btnSidebarToggle"),
  btnCloseSidebar: byId("btnCloseSidebar"),
  btnNewChat: byId("btnNewChat"),
  chatList: byId("chatList"),
  messagesScroll: byId("messagesScroll"),
  messages: byId("messages"),
  composerWrap: byId("composerWrap"),
  composerForm: byId("composerForm"),
  input: byId("chatInput"),
  sendBtn: byId("btnSend"),
  stopBtn: byId("btnStop"),
  attachBtn: byId("btnAttach"),
  topbarTitle: byId("topbarTitle"),
  jumpToLatestBtn: byId("jumpToLatestBtn"),
  emptyState: byId("emptyState"),
  emptySuggestions: byId("emptySuggestions"),
  pendingAttachments: byId("pendingAttachments"),
  fileInput: byId("fileInput"),
}

let stateService = null
let renderService = null
let uiService = null
let eventsService = null
let actionsService = null

let state = null
let getStoredActiveChatId = null
let setStoredActiveChatId = null
let ensureChatsArray = null
let ensureMessagesArray = null
let getActiveChat = null
let getChatTitle = null
let getChatId = null
let normalizeChat = null
let normalizeMessage = null

const api = window.NovaAPI || null

let chatService = null
let attachmentsService = null
let streamService = null
let hasBooted = false

let pendingStreamingRenderId = 0
let pendingStreamingMessage = null

function saveDraftForActiveChat(){
  const chatId = String(state?.activeChatId || "")
  if(!chatId || !el.input || !state){
    return
  }

  if(!state.draftByChatId || typeof state.draftByChatId !== "object"){
    state.draftByChatId = {}
  }

  state.draftByChatId[chatId] = el.input.value || ""
}

function restoreDraftForActiveChat(){
  if(!el.input || !state){
    return
  }

  if(!state.draftByChatId || typeof state.draftByChatId !== "object"){
    state.draftByChatId = {}
  }

  const chatId = String(state.activeChatId || "")
  const nextValue = chatId ? String(state.draftByChatId[chatId] || "") : ""
  el.input.value = nextValue
  autoResizeInput()
  updateComposerState()
}

function autoResizeInput(){
  uiService?.autoResizeInput?.()
}

function focusInput(){
  uiService?.focusInput?.()
}

function isNearBottom(){
  return uiService?.isNearBottom?.() ?? true
}

function scrollToBottom(force = false){
  uiService?.scrollToBottom?.(force)
}

function openSidebar(){
  document.body.classList.add("sidebar-open")
}

function closeSidebar(){
  document.body.classList.remove("sidebar-open")
}

function toggleSidebar(){
  document.body.classList.toggle("sidebar-open")
}

function syncSidebarForViewport(){
  uiService?.syncSidebarForViewport?.()
}

function handleMessagesScroll(){
  uiService?.handleMessagesScroll?.()
}

function updateComposerState(){
  renderService?.updateComposerState?.()
}

function renderMessages(){
  renderService?.renderMessages?.()
}

function renderPendingAttachments(){
  renderService?.renderPendingAttachments?.()
}

function renderAll(){
  renderService?.renderAll?.()
}

function handleResize(){
  renderService?.updateJumpButton?.()
  uiService?.syncSidebarForViewport?.()
}

function cancelPendingStreamingRender(){
  if(pendingStreamingRenderId){
    cancelAnimationFrame(pendingStreamingRenderId)
    pendingStreamingRenderId = 0
  }
  pendingStreamingMessage = null
}

function flushPendingStreamingRender(){
  pendingStreamingRenderId = 0

  if(!pendingStreamingMessage){
    return
  }

  const patched = renderService?.patchStreamingMessage?.(pendingStreamingMessage)
  if(!patched){
    renderMessages()
  }

  renderService?.updateJumpButton?.()
  scrollToBottom()
  pendingStreamingMessage = null
}

function scheduleStreamingRender(message){
  pendingStreamingMessage = message

  if(pendingStreamingRenderId){
    return
  }

  pendingStreamingRenderId = requestAnimationFrame(() => {
    flushPendingStreamingRender()
  })
}

function ensureStreamingAssistantPlaceholder(){
  const messages = ensureMessagesArray()
  let lastMessage = messages[messages.length - 1]

  if(lastMessage && String(lastMessage.role || "") === "assistant"){
    return lastMessage
  }

  lastMessage = normalizeMessage({
    id: makeId("msg"),
    role: "assistant",
    content: "",
  })

  messages.push(lastMessage)
  return lastMessage
}

function mergeDoneMessages(payloadMessages = []){
  const currentMessages = ensureMessagesArray()
  const incomingMessages = Array.isArray(payloadMessages)
    ? payloadMessages.map(normalizeMessage)
    : []

  if(!incomingMessages.length){
    return
  }

  const localAssistantIndex = [...currentMessages]
    .map((message, index) => ({ message, index }))
    .reverse()
    .find((entry) => String(entry.message?.role || "") === "assistant")
    ?.index

  const incomingAssistantIndex = [...incomingMessages]
    .map((message, index) => ({ message, index }))
    .reverse()
    .find((entry) => String(entry.message?.role || "") === "assistant")
    ?.index

  if(
    Number.isInteger(localAssistantIndex) &&
    Number.isInteger(incomingAssistantIndex)
  ){
    const localAssistant = currentMessages[localAssistantIndex]
    const incomingAssistant = incomingMessages[incomingAssistantIndex]

    const localContent = String(localAssistant?.content || "")
    const incomingContent = String(incomingAssistant?.content || "")

    if(localContent && incomingContent && incomingContent === localContent){
      currentMessages[localAssistantIndex] = {
        ...incomingAssistant,
        content: localContent,
      }

      const nextMessages = [...currentMessages]
      const seen = new Set()
      const deduped = []

      for(const message of nextMessages){
        const key = String(message?.id || message?.message_id || "")
        if(key && seen.has(key)){
          continue
        }
        if(key){
          seen.add(key)
        }
        deduped.push(normalizeMessage(message))
      }

      state.messages = deduped
      return
    }
  }

  state.messages = incomingMessages
}

async function initStateService(){
  const stateFactory =
    window.NovaChatState?.create ||
    window.NovaChatState?.createChatStateService ||
    null

  if(typeof stateFactory !== "function"){
    throw new Error("Nova chat state service failed to initialize.")
  }

  stateService = stateFactory({ makeId })

  state = stateService.state
  getStoredActiveChatId = stateService.getStoredActiveChatId
  setStoredActiveChatId = stateService.setStoredActiveChatId
  ensureChatsArray = stateService.ensureChatsArray
  ensureMessagesArray = stateService.ensureMessagesArray
  getActiveChat = stateService.getActiveChat
  getChatTitle = stateService.getChatTitle
  getChatId = stateService.getChatId
  normalizeChat = stateService.normalizeChat
  normalizeMessage = stateService.normalizeMessage
}

async function initCoreServices(){
  chatService = window.NovaChatService?.create?.({
    state,
    api,
    elements: el,
  }) || null

  attachmentsService =
    window.NovaAttachmentsService?.create?.({
      state,
      elements: {
        pendingAttachments: el.pendingAttachments,
        fileInput: el.fileInput,
      },
      onChange(files){
        actionsService?.setPendingFiles?.(files)
      },
    }) ||
    window.NovaAttachments?.create?.({
      state,
      elements: {
        pendingAttachments: el.pendingAttachments,
        fileInput: el.fileInput,
      },
      onChange(files){
        actionsService?.setPendingFiles?.(files)
      },
    }) ||
    null

  const streamFactory =
    window.NovaStreamService?.create ||
    window.NovaStreamService?.createStreamService ||
    null

  streamService = typeof streamFactory === "function"
    ? streamFactory({
        state,
        api,
        elements: {
          messages: el.messages,
        },
        onStart(){
          cancelPendingStreamingRender()
          state.isStreaming = true
          ensureStreamingAssistantPlaceholder()
          renderMessages()
          updateComposerState()
          renderService?.updateJumpButton?.()
          scrollToBottom(true)
        },
        onMeta(payload = {}){
          if(payload?.chat){
            const incoming = normalizeChat(payload.chat)
            const chats = ensureChatsArray()
            const existingIndex = chats.findIndex((chat) => getChatId(chat) === getChatId(incoming))

            if(existingIndex >= 0){
              chats[existingIndex] = incoming
            }else{
              chats.unshift(incoming)
            }

            if(!state.activeChatId){
              state.activeChatId = getChatId(incoming)
              setStoredActiveChatId(state.activeChatId)
            }

            renderService?.renderChatList?.()
            renderService?.updateTopbar?.()
          }
        },
        onToken(token){
          const messages = ensureMessagesArray()
          let lastMessage = messages[messages.length - 1]
          let createdNewAssistant = false

          if(!lastMessage || String(lastMessage.role) !== "assistant"){
            lastMessage = normalizeMessage({
              id: makeId("msg"),
              role: "assistant",
              content: "",
            })
            messages.push(lastMessage)
            createdNewAssistant = true
          }

          lastMessage.content = `${lastMessage.content || ""}${token || ""}`

          if(createdNewAssistant){
            renderMessages()
            renderService?.updateJumpButton?.()
            scrollToBottom()
            return
          }

          scheduleStreamingRender(lastMessage)
        },
        onDone(payload = {}){
          cancelPendingStreamingRender()
          state.isStreaming = false

          if(Array.isArray(payload?.messages)){
            mergeDoneMessages(payload.messages)
          }

          if(payload?.chat){
            const incoming = normalizeChat(payload.chat)
            const chats = ensureChatsArray()
            const existingIndex = chats.findIndex((chat) => getChatId(chat) === getChatId(incoming))

            if(existingIndex >= 0){
              chats[existingIndex] = incoming
            }else{
              chats.unshift(incoming)
            }

            state.activeChatId = getChatId(incoming)
            setStoredActiveChatId(state.activeChatId)
          }

          renderAll()
          scrollToBottom(true)
        },
        onError(error){
          cancelPendingStreamingRender()
          console.error("Nova stream error:", error)
          state.isStreaming = false
          renderAll()
        },
        onFinally(){
          cancelPendingStreamingRender()
          state.isStreaming = false
          updateComposerState()
        },
      })
    : null
}

async function initRenderService(){
  const renderFactory =
    window.NovaChatRender?.create ||
    window.NovaChatRender?.createRenderService ||
    null

  if(typeof renderFactory !== "function"){
    throw new Error("Nova chat render service failed to initialize.")
  }

  renderService = renderFactory({
    state,
    elements: el,
    utils: {
      escapeHtml,
      getChatTitle,
      getChatId,
      ensureChatsArray,
      ensureMessagesArray,
      getActiveChat,
    },
  })
}

async function initUiService(){
  const uiFactory =
    window.NovaChatUi?.create ||
    window.NovaChatUi?.createChatUiService ||
    null

  if(typeof uiFactory !== "function"){
    throw new Error("Nova chat ui service failed to initialize.")
  }

  uiService = uiFactory({
    state,
    elements: el,
    renderService,
    constants: {
      SCROLL_LOCK_THRESHOLD,
    },
  })
}

async function initActionsService(){
  const actionsFactory =
    window.NovaChatActions?.create ||
    window.NovaChatActions?.createChatActionsService ||
    null

  if(typeof actionsFactory !== "function"){
    throw new Error("Nova chat actions service failed to initialize.")
  }

  actionsService = actionsFactory({
    state,
    elements: el,
    services: {
      chatService,
      attachmentsService,
      streamService,
    },
    utils: {
      ensureChatsArray,
      ensureMessagesArray,
      getChatId,
      getChatTitle,
      normalizeChat,
      normalizeMessage,
      makeId,
      getStoredActiveChatId,
      setStoredActiveChatId,
      saveDraftForActiveChat,
      restoreDraftForActiveChat,
    },
    ui: {
      autoResizeInput,
      focusInput,
      isNearBottom,
      scrollToBottom,
    },
    render: {
      updateComposerState,
      renderMessages,
      renderPendingAttachments,
      renderAll,
    },
  })
}

async function initEventsService(){
  const eventsFactory =
    window.NovaChatEvents?.create ||
    window.NovaChatEvents?.createChatEventsService ||
    null

  if(typeof eventsFactory !== "function"){
    throw new Error("Nova chat events service failed to initialize.")
  }

  eventsService = eventsFactory({
    state,
    elements: el,
    actions: {
      saveDraftForActiveChat,
      updateComposerState,
      createChat: (...args) => actionsService?.createChat?.(...args),
      loadChat: (...args) => actionsService?.loadChat?.(...args),
      deleteChat: (...args) => actionsService?.deleteChat?.(...args),
      startRenameChat: (...args) => actionsService?.startRenameChat?.(...args),
      cancelRenameChat: (...args) => actionsService?.cancelRenameChat?.(...args),
      commitRenameFromInput: (...args) => actionsService?.commitRenameFromInput?.(...args),
      copyMessage: (...args) => actionsService?.copyMessage?.(...args),
      retryFromMessage: (...args) => actionsService?.retryFromMessage?.(...args),
      deleteMessage: (...args) => actionsService?.deleteMessage?.(...args),
      removePendingFileByIndex: (...args) => actionsService?.removePendingFileByIndex?.(...args),
      sendCurrentMessage: (...args) => actionsService?.sendCurrentMessage?.(...args),
      stopStreaming: (...args) => actionsService?.stopStreaming?.(...args),
      openFilePicker: (...args) => actionsService?.openFilePicker?.(...args),
      openSidebar,
      closeSidebar,
      toggleSidebar,
      onResize: handleResize,
    },
    ui: {
      autoResizeInput,
      focusInput,
      openSidebar,
      closeSidebar,
      toggleSidebar,
      handleMessagesScroll,
      scrollToBottom,
    },
  })
}

async function boot(){
  if(hasBooted){
    return
  }
  hasBooted = true

  await initStateService()
  await initCoreServices()
  await initRenderService()
  await initUiService()
  await initActionsService()
  await initEventsService()

  eventsService?.wireDomEvents?.()

  if(window.innerWidth > MOBILE_BREAKPOINT){
    openSidebar()
  }

  autoResizeInput()
  updateComposerState()
  renderAll()

  try{
    await actionsService?.loadChats?.()

    if(state.activeChatId){
      await actionsService?.loadChat?.(state.activeChatId)
    }else{
      renderAll()
      focusInput()
    }
  }catch(error){
    console.error("Nova boot error:", error)
    renderAll()
  }
}

window.NovaChatApp = {
  get state(){
    return state
  },
  elements: el,
  renderAll,
  loadChats: (...args) => actionsService?.loadChats?.(...args),
  loadChat: (...args) => actionsService?.loadChat?.(...args),
  createChat: (...args) => actionsService?.createChat?.(...args),
  deleteChat: (...args) => actionsService?.deleteChat?.(...args),
  startRenameChat: (...args) => actionsService?.startRenameChat?.(...args),
  cancelRenameChat: (...args) => actionsService?.cancelRenameChat?.(...args),
  persistRename: (...args) => actionsService?.persistRename?.(...args),
  sendCurrentMessage: (...args) => actionsService?.sendCurrentMessage?.(...args),
  stopStreaming: (...args) => actionsService?.stopStreaming?.(...args),
  scrollToBottom,
  setPendingFiles: (...args) => actionsService?.setPendingFiles?.(...args),
  openSidebar,
  closeSidebar,
  toggleSidebar,
  syncSidebarForViewport,
}

if(document.readyState === "loading"){
  document.addEventListener("DOMContentLoaded", () => {
    boot().catch((error) => {
      console.error("Nova boot failure:", error)
    })
  }, { once: true })
}else{
  boot().catch((error) => {
    console.error("Nova boot failure:", error)
  })
}

})()