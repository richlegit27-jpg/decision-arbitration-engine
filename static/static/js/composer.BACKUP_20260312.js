// C:\Users\Owner\nova\static\js\composer.js

(() => {
"use strict"

const chatStateApi = window.NovaChatState
const chatMessages = window.NovaChatMessages || null
const chatSidebar = window.NovaChatSidebar || null
const chatStorage = window.NovaChatStorage || null
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
  voiceBtn: document.getElementById("voiceBtn"),
}

let eventsBound = false
let inputEventsBound = false
let voiceBound = false
let voiceController = null

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

function getVoiceApi(){
  return window.NovaVoiceInput || null
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

function getInputValue(){
  return String(el.input?.value || "")
}

function hasText(){
  return !!getInputValue().trim()
}

function isStreaming(){
  return !!state.isStreaming
}

function hasPendingFiles(){
  return getPendingFiles().length > 0
}

function safeCall(fn, fallback = undefined){
  try{
    if(typeof fn === "function"){
      return fn()
    }
  }catch(error){
    console.error("NovaComposer safeCall error:", error)
  }
  return fallback
}

function syncComposerUiState(){
  const textPresent = hasText()
  const filesPresent = hasPendingFiles()
  const streaming = isStreaming()
  const canSend = !streaming && (textPresent || filesPresent)

  if(el.composer){
    el.composer.classList.toggle("is-busy", streaming)
    el.composer.classList.toggle("has-content", textPresent || filesPresent)
    el.composer.classList.toggle("has-text", textPresent)
    el.composer.classList.toggle("has-files", filesPresent)
  }

  if(el.input){
    el.input.setAttribute("aria-busy", streaming ? "true" : "false")
    el.input.setAttribute("data-has-content", textPresent ? "true" : "false")
    el.input.disabled = false
  }

  if(el.pendingAttachments){
    el.pendingAttachments.setAttribute("data-has-items", filesPresent ? "true" : "false")
  }

  if(el.sendBtn){
    el.sendBtn.disabled = !canSend
    el.sendBtn.hidden = streaming
    el.sendBtn.setAttribute("aria-disabled", el.sendBtn.disabled ? "true" : "false")
  }

  if(el.stopBtn){
    el.stopBtn.hidden = !streaming
    el.stopBtn.disabled = !streaming
    el.stopBtn.setAttribute("aria-disabled", el.stopBtn.disabled ? "true" : "false")
  }

  if(el.attachBtn){
    el.attachBtn.disabled = streaming
    el.attachBtn.setAttribute("aria-disabled", el.attachBtn.disabled ? "true" : "false")
  }

  if(el.voiceBtn){
    el.voiceBtn.disabled = streaming
    el.voiceBtn.setAttribute("aria-disabled", el.voiceBtn.disabled ? "true" : "false")

    if(voiceController && typeof voiceController.getState === "function"){
      const voiceState = voiceController.getState()
      const listening = !!voiceState?.listening
      const supported = !!voiceState?.supported

      el.voiceBtn.hidden = !supported
      el.voiceBtn.classList.toggle("is-listening", listening)
      el.voiceBtn.setAttribute("aria-pressed", listening ? "true" : "false")
    }else{
      el.voiceBtn.classList.remove("is-listening")
      el.voiceBtn.setAttribute("aria-pressed", "false")
    }
  }
}

function updateComposerState(){
  if(actionsController && typeof actionsController.updateComposerState === "function"){
    safeCall(() => actionsController.updateComposerState())
  }

  syncComposerUiState()
}

function buildAttachmentsController(){
  return composerAttachmentsApi.create({
    state,
    elements: {
      attachBtn: el.attachBtn,
      pendingAttachments: el.pendingAttachments,
    },
    attachmentsService: getAttachmentsService(),
    onStateChange: updateComposerState,
  })
}

function buildInputController(){
  return composerInputApi.create({
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
}

function buildActionsController(){
  return composerActionsApi.create({
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

function ensureControllers(){
  if(!attachmentsController){
    attachmentsController = buildAttachmentsController()
  }

  if(!inputController){
    inputController = buildInputController()
  }

  if(!actionsController){
    actionsController = buildActionsController()
  }

  if(actionsController){
    actionsController.callbacks = callbacks
  }
}

function bindInputMirrorEvents(){
  if(inputEventsBound || !el.input){
    return
  }

  const handleInput = () => {
    syncComposerUiState()
  }

  el.input.addEventListener("input", handleInput)
  el.input.addEventListener("change", handleInput)
  el.input.addEventListener("focus", handleInput)
  el.input.addEventListener("blur", handleInput)

  inputEventsBound = true
}

function appendTranscriptToInput(text, isFinal = false){
  const transcript = String(text || "").trim()
  if(!transcript){
    return
  }

  ensureControllers()

  const current = getInputValue()
  const spacer = current.trim() ? " " : ""
  const nextValue = `${current}${spacer}${transcript}`.trimStart()

  if(inputController && typeof inputController.setInputValue === "function"){
    safeCall(() => inputController.setInputValue(nextValue))
  }else if(el.input){
    el.input.value = nextValue
  }

  if(inputController && typeof inputController.autoResizeInput === "function"){
    safeCall(() => inputController.autoResizeInput())
  }

  syncComposerUiState()

  if(isFinal && inputController && typeof inputController.focusInput === "function"){
    safeCall(() => inputController.focusInput())
  }
}

function bindVoice(){
  if(voiceBound){
    return
  }

  voiceBound = true

  const voiceApi = getVoiceApi()
  if(!voiceApi || typeof voiceApi.create !== "function"){
    syncComposerUiState()
    return
  }

  voiceController = safeCall(() => voiceApi.create({
    onTranscript(payload = {}){
      appendTranscriptToInput(payload.text, !!payload.isFinal)
    },
    onStateChange(){
      syncComposerUiState()
    },
  }), null)

  if(el.voiceBtn){
    el.voiceBtn.addEventListener("click", () => {
      if(!voiceController || typeof voiceController.toggle !== "function"){
        return
      }

      if(isStreaming()){
        return
      }

      safeCall(() => voiceController.toggle())
      syncComposerUiState()
    })
  }

  syncComposerUiState()
}

function bindEvents(options = {}){
  callbacks = {
    ...callbacks,
    ...options,
  }

  ensureControllers()

  if(eventsBound){
    if(actionsController){
      actionsController.callbacks = callbacks
    }
    updateComposerState()
    return
  }

  if(inputController && typeof inputController.bindEvents === "function"){
    safeCall(() => inputController.bindEvents())
  }

  if(attachmentsController && typeof attachmentsController.bindEvents === "function"){
    safeCall(() => attachmentsController.bindEvents())
  }

  if(actionsController && typeof actionsController.bindEvents === "function"){
    safeCall(() => actionsController.bindEvents())
  }

  bindInputMirrorEvents()
  bindVoice()

  eventsBound = true

  if(inputController && typeof inputController.autoResizeInput === "function"){
    safeCall(() => inputController.autoResizeInput())
  }

  if(actionsController && typeof actionsController.updateComposerState === "function"){
    safeCall(() => actionsController.updateComposerState())
  }

  if(attachmentsController && typeof attachmentsController.renderPendingAttachments === "function"){
    safeCall(() => attachmentsController.renderPendingAttachments())
  }

  syncComposerUiState()
}

function sendCurrentMessage(options = {}){
  ensureControllers()

  if(!actionsController || typeof actionsController.sendCurrentMessage !== "function"){
    console.error("NovaComposer: sendCurrentMessage unavailable")
    return Promise.resolve(null)
  }

  return safeCall(() => actionsController.sendCurrentMessage(options), Promise.resolve(null))
}

function stopGenerating(){
  ensureControllers()

  if(!actionsController || typeof actionsController.stopGenerating !== "function"){
    return null
  }

  const result = safeCall(() => actionsController.stopGenerating(), null)
  syncComposerUiState()
  return result
}

function autoResizeInput(){
  ensureControllers()

  if(!inputController || typeof inputController.autoResizeInput !== "function"){
    return null
  }

  return safeCall(() => inputController.autoResizeInput(), null)
}

function focusInput(){
  ensureControllers()

  if(inputController && typeof inputController.focusInput === "function"){
    return safeCall(() => inputController.focusInput(), null)
  }

  if(el.input){
    el.input.focus()
  }

  return null
}

function setInputValue(text){
  ensureControllers()

  let result = null

  if(inputController && typeof inputController.setInputValue === "function"){
    result = safeCall(() => inputController.setInputValue(text), null)
  }else if(el.input){
    el.input.value = String(text || "")
  }

  if(inputController && typeof inputController.autoResizeInput === "function"){
    safeCall(() => inputController.autoResizeInput())
  }

  syncComposerUiState()
  return result
}

function markStreaming(flag){
  ensureControllers()

  let result = null

  state.isStreaming = !!flag

  if(actionsController && typeof actionsController.markStreaming === "function"){
    result = safeCall(() => actionsController.markStreaming(flag), null)
  }

  syncComposerUiState()
  return result
}

function setPendingFiles(files){
  ensureControllers()

  let result = null

  if(attachmentsController && typeof attachmentsController.setPendingFiles === "function"){
    result = safeCall(() => attachmentsController.setPendingFiles(files), null)
  }else{
    state.pendingAttachments = Array.isArray(files) ? files.slice() : []
    state.pendingFiles = Array.isArray(files) ? files.slice() : []
  }

  if(attachmentsController && typeof attachmentsController.renderPendingAttachments === "function"){
    safeCall(() => attachmentsController.renderPendingAttachments())
  }

  syncComposerUiState()
  return result
}

function getControllerState(){
  return {
    hasActionsController: !!actionsController,
    hasAttachmentsController: !!attachmentsController,
    hasInputController: !!inputController,
    hasVoiceController: !!voiceController,
    isStreaming: !!state.isStreaming,
    pendingFiles: getPendingFiles().length,
    hasText: hasText(),
  }
}

ensureControllers()

window.NovaComposer = {
  bindEvents,
  sendCurrentMessage,
  stopGenerating,
  autoResizeInput,
  updateComposerState,
  focusInput,
  setInputValue,
  markStreaming,
  setPendingFiles,
  getControllerState,
}

})()