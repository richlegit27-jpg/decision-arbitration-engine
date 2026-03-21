// C:\Users\Owner\nova\static\js\composer.js

(() => {
"use strict"

const chatStateApi = window.NovaChatState
const chatMessages = window.NovaChatMessages
const chatSidebar = window.NovaChatSidebar
const chatStorage = window.NovaChatStorage
const api = window.NovaAPI || {}
const composerInputApi = window.NovaComposerInput
const composerAttachmentsApi = window.NovaComposerAttachments
const composerActionsApi = window.NovaComposerActions

if(!chatStateApi){
  throw new Error("NovaComposer: window.NovaChatState is required")
}

if(!composerInputApi){
  throw new Error("NovaComposer: window.NovaComposerInput is required")
}

if(!composerAttachmentsApi){
  throw new Error("NovaComposer: window.NovaComposerAttachments is required")
}

if(!composerActionsApi){
  throw new Error("NovaComposer: window.NovaComposerActions is required")
}

const { state } = chatStateApi

const el = {
  composer: document.getElementById("composer"),
  input: document.getElementById("input"),
  sendBtn: document.getElementById("sendBtn"),
  stopBtn: document.getElementById("stopBtn"),
  attachBtn: document.getElementById("attachBtn"),
  pendingAttachments: document.getElementById("pendingAttachments"),
  emptySuggestions: document.getElementById("emptySuggestions"),
  messagesScroll: document.getElementById("messagesScroll"),
}

let eventsBound = false

let callbacks = {
  onNeedsCreateChat: null,
  onAfterSend: null,
  onSendError: null,
  onStop: null,
}

let actionsController = null
let attachmentsController = null
let inputController = null

function getAttachmentsService(){
  return window.NovaAttachmentsService || null
}

function getStreamService(){
  return window.NovaStreamService || null
}

function getPendingFiles(){
  if(Array.isArray(state.pendingAttachments)){
    return state.pendingAttachments
  }

  if(Array.isArray(state.pendingFiles)){
    return state.pendingFiles
  }

  return []
}

function syncComposerUiState(){
  const hasText = !!String(el.input?.value || "").trim()
  const pendingFiles = getPendingFiles()
  const hasPendingFiles = pendingFiles.length > 0
  const isStreaming = !!state.isStreaming

  if(el.composer){
    el.composer.classList.toggle("is-busy", isStreaming)
    el.composer.classList.toggle("has-content", hasText || hasPendingFiles)
  }

  if(el.input){
    el.input.setAttribute("aria-busy", isStreaming ? "true" : "false")
    el.input.toggleAttribute("data-has-content", hasText)
  }

  if(el.pendingAttachments){
    el.pendingAttachments.toggleAttribute("data-has-items", hasPendingFiles)
  }

  if(el.sendBtn){
    el.sendBtn.disabled = isStreaming || (!hasText && !hasPendingFiles)
    el.sendBtn.hidden = isStreaming
    el.sendBtn.setAttribute("aria-disabled", el.sendBtn.disabled ? "true" : "false")
  }

  if(el.stopBtn){
    el.stopBtn.hidden = !isStreaming
    el.stopBtn.disabled = !isStreaming
    el.stopBtn.setAttribute("aria-disabled", el.stopBtn.disabled ? "true" : "false")
  }

  if(el.attachBtn){
    el.attachBtn.disabled = isStreaming
    el.attachBtn.setAttribute("aria-disabled", el.attachBtn.disabled ? "true" : "false")
  }
}

function updateComposerState(){
  if(actionsController && typeof actionsController.updateComposerState === "function"){
    actionsController.updateComposerState()
  }

  syncComposerUiState()
}

function ensureControllers(){
  if(attachmentsController && inputController && actionsController){
    return
  }

  attachmentsController = composerAttachmentsApi.create({
    state,
    elements: {
      attachBtn: el.attachBtn,
      pendingAttachments: el.pendingAttachments,
    },
    attachmentsService: getAttachmentsService(),
    onStateChange: updateComposerState,
  })

  inputController = composerInputApi.create({
    elements: {
      input: el.input,
      emptySuggestions: el.emptySuggestions,
    },
    onSubmit: async () => {
      if(actionsController && typeof actionsController.sendCurrentMessage === "function"){
        await actionsController.sendCurrentMessage()
      }
    },
    onStateChange: updateComposerState,
  })

  actionsController = composerActionsApi.create({
    state,
    elements: {
      sendBtn: el.sendBtn,
      stopBtn: el.stopBtn,
      attachBtn: el.attachBtn,
      messagesScroll: el.messagesScroll,
    },
    api,
    chatMessages,
    chatSidebar,
    chatStorage,
    streamService: getStreamService(),
    inputController,
    attachmentsController,
    callbacks,
    onStateChange: updateComposerState,
  })
}

function bindEvents(options = {}){
  callbacks = { ...callbacks, ...options }

  ensureControllers()

  if(actionsController){
    actionsController.callbacks = callbacks
  }

  if(eventsBound){
    updateComposerState()
    return
  }

  inputController.bindEvents()
  attachmentsController.bindEvents()
  actionsController.bindEvents()

  if(el.input){
    el.input.addEventListener("input", () => {
      syncComposerUiState()
    })
  }

  eventsBound = true

  inputController.autoResizeInput()
  actionsController.updateComposerState()
  attachmentsController.renderPendingAttachments()
  syncComposerUiState()
}

ensureControllers()

window.NovaComposer = {
  bindEvents,

  sendCurrentMessage(options = {}){
    ensureControllers()
    return actionsController.sendCurrentMessage(options)
  },

  stopGenerating(){
    ensureControllers()
    return actionsController.stopGenerating()
  },

  autoResizeInput(){
    ensureControllers()
    return inputController.autoResizeInput()
  },

  updateComposerState(){
    ensureControllers()
    updateComposerState()
  },

  focusInput(){
    ensureControllers()
    return inputController.focusInput()
  },

  setInputValue(text){
    ensureControllers()
    const result = inputController.setInputValue(text)
    syncComposerUiState()
    return result
  },

  markStreaming(flag){
    ensureControllers()
    const result = actionsController.markStreaming(flag)
    syncComposerUiState()
    return result
  },

  setPendingFiles(files){
    ensureControllers()
    const result = attachmentsController.setPendingFiles(files)
    syncComposerUiState()
    return result
  },
}

})()