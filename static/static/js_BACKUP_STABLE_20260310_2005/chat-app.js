// C:\Users\Owner\nova\static\js\chat-app.js

(() => {
"use strict"

const chatStateApi = window.NovaChatState
const chatStorage = window.NovaChatStorage
const chatSidebar = window.NovaChatSidebar
const chatMessages = window.NovaChatMessages
const composer = window.NovaComposer
const memoryPanel = window.NovaMemoryPanel
const chatOrchestratorApi = window.NovaChatOrchestrator
const chatBootstrapApi = window.NovaChatBootstrap

if(!chatStateApi){
  throw new Error("NovaChatApp: state missing")
}

if(!chatStorage){
  throw new Error("NovaChatApp: storage missing")
}

if(!chatSidebar){
  throw new Error("NovaChatApp: sidebar missing")
}

if(!chatMessages){
  throw new Error("NovaChatApp: messages missing")
}

if(!composer){
  throw new Error("NovaChatApp: composer missing")
}

if(!memoryPanel){
  throw new Error("NovaChatApp: memory panel missing")
}

if(!chatOrchestratorApi){
  throw new Error("NovaChatApp: orchestrator missing")
}

if(!chatBootstrapApi){
  throw new Error("NovaChatApp: bootstrap missing")
}

const { state } = chatStateApi

function getAttachmentsService(){
  return window.NovaAttachmentsService || null
}

function getStreamService(){
  return window.NovaStreamService || null
}

const orchestrator = chatOrchestratorApi.create({
  state,
  chatStorage,
  chatSidebar,
  chatMessages,
  composer,
  memoryPanel,
  getAttachmentsService,
  getStreamService,
})

window.NovaChatApp = {
  state,
  init: orchestrator.init,
  renderAll: orchestrator.renderAll,
  loadActiveChatMessages: orchestrator.loadActiveChatMessages,
  createChatAndLoad: orchestrator.createChatAndLoad,
  retryMessage: orchestrator.retryMessage,
  scrollMessagesToBottom: orchestrator.scrollMessagesToBottom,
  syncSidebarAndLayout: orchestrator.syncSidebarAndLayout,
  openMemoryPanel: orchestrator.openMemoryPanel,
  closeMemoryPanel: orchestrator.closeMemoryPanel,
  refreshMemoryList: orchestrator.refreshMemoryList,
}

chatBootstrapApi.start(orchestrator.init)

})()