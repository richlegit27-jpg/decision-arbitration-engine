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

let topbarEventsBound = false
let appStarted = false
let orchestrator = null

function getAttachmentsService(){
  return window.NovaAttachmentsService || null
}

function getStreamService(){
  return window.NovaStreamService || null
}

function getWorkspaceFilesApi(){
  return window.NovaWorkspaceFiles || null
}

function ensureOrchestrator(){
  if(orchestrator){
    return orchestrator
  }

  orchestrator = chatOrchestratorApi.create({
    state,
    chatStorage,
    chatSidebar,
    chatMessages,
    composer,
    memoryPanel,
    getAttachmentsService,
    getStreamService,
  })

  return orchestrator
}

function openWorkspaceFilesPanel(){
  const workspaceFilesApi = getWorkspaceFilesApi()

  if(!workspaceFilesApi || typeof workspaceFilesApi.open !== "function"){
    console.warn("NovaChatApp: workspace files panel unavailable")
    return
  }

  workspaceFilesApi.open()
}

function openMemoryPanel(){
  const instance = ensureOrchestrator()

  if(typeof instance.openMemoryPanel === "function"){
    instance.openMemoryPanel()
    return
  }

  if(memoryPanel && typeof memoryPanel.open === "function"){
    memoryPanel.open()
  }
}

function closeMemoryPanel(){
  const instance = ensureOrchestrator()

  if(typeof instance.closeMemoryPanel === "function"){
    instance.closeMemoryPanel()
    return
  }

  if(memoryPanel && typeof memoryPanel.close === "function"){
    memoryPanel.close()
  }
}

function refreshMemoryList(){
  const instance = ensureOrchestrator()

  if(typeof instance.refreshMemoryList === "function"){
    return instance.refreshMemoryList()
  }

  if(memoryPanel && typeof memoryPanel.refresh === "function"){
    return memoryPanel.refresh()
  }

  return undefined
}

function bindTopbarButtons(){
  if(topbarEventsBound){
    return
  }

  const btnWorkspaceFiles = document.getElementById("btnWorkspaceFiles")
  const btnTopbarMemory = document.getElementById("btnTopbarMemory")

  btnWorkspaceFiles?.addEventListener("click", () => {
    openWorkspaceFilesPanel()
  })

  btnTopbarMemory?.addEventListener("click", () => {
    openMemoryPanel()
  })

  topbarEventsBound = true
}

function loadOptionalScript(src){
  return new Promise((resolve) => {
    const existing = document.querySelector(`script[data-optional-src="${src}"]`)

    if(existing){
      if(
        existing.dataset.loaded === "true" ||
        existing.dataset.failed === "true"
      ){
        resolve(existing.dataset.loaded === "true")
        return
      }

      existing.addEventListener("load", () => resolve(true), { once: true })
      existing.addEventListener("error", () => resolve(false), { once: true })
      return
    }

    const script = document.createElement("script")
    script.src = src
    script.async = false
    script.dataset.optionalSrc = src

    script.addEventListener("load", () => {
      script.dataset.loaded = "true"
      resolve(true)
    }, { once: true })

    script.addEventListener("error", () => {
      script.dataset.failed = "true"
      console.info(`NovaChatApp optional script skipped: ${src}`)
      resolve(false)
    }, { once: true })

    document.head.appendChild(script)
  })
}

async function initOptionalFeatures(){
  const imageLightboxLoaded = await loadOptionalScript("/static/js/image-lightbox.js")
  const voiceInputLoaded = await loadOptionalScript("/static/js/voice-input.js")

  if(imageLightboxLoaded && typeof window.NovaImageLightbox?.init === "function"){
    try{
      window.NovaImageLightbox.init()
    }catch(error){
      console.info("NovaChatApp image lightbox init skipped:", error)
    }
  }

  if(voiceInputLoaded && typeof window.NovaVoiceInput?.init === "function"){
    try{
      window.NovaVoiceInput.init()
    }catch(error){
      console.info("NovaChatApp voice input init skipped:", error)
    }
  }
}

async function init(){
  if(appStarted){
    return
  }

  appStarted = true
  bindTopbarButtons()

  try{
    await initOptionalFeatures()
    await ensureOrchestrator().init()
  }catch(error){
    appStarted = false
    console.error("NovaChatApp init failed:", error)
    throw error
  }
}

window.NovaChatApp = {
  state,
  init,

  renderAll(){
    return ensureOrchestrator().renderAll()
  },

  loadActiveChatMessages(){
    return ensureOrchestrator().loadActiveChatMessages()
  },

  createChatAndLoad(){
    return ensureOrchestrator().createChatAndLoad()
  },

  retryMessage(messageId){
    return ensureOrchestrator().retryMessage(messageId)
  },

  editMessage(messageId){
    return ensureOrchestrator().editMessage(messageId)
  },

  scrollMessagesToBottom(force){
    return ensureOrchestrator().scrollMessagesToBottom(force)
  },

  syncSidebarAndLayout(){
    return ensureOrchestrator().syncSidebarAndLayout()
  },

  openMemoryPanel,
  closeMemoryPanel,
  refreshMemoryList,
  openWorkspaceFilesPanel,
}

chatBootstrapApi.start(init)

})()