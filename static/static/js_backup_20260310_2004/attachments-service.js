// C:\Users\Owner\nova\static\js\attachments-service.js

(() => {
"use strict"

function createAttachmentsService(options = {}){
  const {
    state,
    elements = {},
    onChange = null,
  } = options

  const api = window.NovaAPI || {}

  const el = {
    pendingAttachments: elements.pendingAttachments || null,
    fileInput: elements.fileInput || document.getElementById("fileInput") || null,
  }

  let fallbackFileInput = null
  let changeHandler = typeof onChange === "function" ? onChange : null

  function getPendingFiles(){
    if(!Array.isArray(state.pendingFiles)){
      state.pendingFiles = []
    }
    return state.pendingFiles
  }

  function notifyChange(files){
    if(typeof changeHandler === "function"){
      changeHandler(files)
    }
  }

  function setOnChange(handler){
    changeHandler = typeof handler === "function" ? handler : null
  }

  function setPendingFiles(files = []){
    const normalized = Array.isArray(files) ? files.filter(Boolean) : []
    state.pendingFiles = normalized
    state.pendingAttachments = normalized
    notifyChange(normalized)
  }

  function clearPendingFiles(){
    setPendingFiles([])

    const input = getFileInput()
    if(input){
      input.value = ""
    }
  }

  function clearPending(){
    clearPendingFiles()
  }

  function removePendingFileByIndex(index){
    const nextFiles = [...getPendingFiles()]
    const fileIndex = Number(index)

    if(!Number.isFinite(fileIndex) || fileIndex < 0 || fileIndex >= nextFiles.length){
      return
    }

    nextFiles.splice(fileIndex, 1)
    setPendingFiles(nextFiles)
  }

  function bindInput(input){
    if(!input || input.dataset.novaAttachmentsBound === "true"){
      return input
    }

    input.addEventListener("change", () => {
      const files = Array.from(input.files || [])
      setPendingFiles(files)
      input.value = ""
    })

    input.dataset.novaAttachmentsBound = "true"
    return input
  }

  function createFallbackInput(){
    if(fallbackFileInput){
      return fallbackFileInput
    }

    fallbackFileInput = document.createElement("input")
    fallbackFileInput.type = "file"
    fallbackFileInput.multiple = true
    fallbackFileInput.hidden = true
    document.body.appendChild(fallbackFileInput)

    bindInput(fallbackFileInput)
    return fallbackFileInput
  }

  function getFileInput(){
    if(el.fileInput && document.body.contains(el.fileInput)){
      return bindInput(el.fileInput)
    }

    const existing = document.getElementById("fileInput")
    if(existing){
      el.fileInput = existing
      return bindInput(el.fileInput)
    }

    return createFallbackInput()
  }

  function openFilePicker(){
    const input = getFileInput()
    input?.click?.()
  }

  function openPicker(){
    openFilePicker()
  }

  function pickFiles(){
    openFilePicker()
  }

  function normalizeUploadedFile(file = {}){
    return {
      id: String(file.id || file.attachment_id || `att_${Date.now()}_${Math.random().toString(16).slice(2)}`),
      attachment_id: String(file.attachment_id || file.id || ""),
      filename: String(file.filename || file.name || "file"),
      name: String(file.name || file.filename || "file"),
      mime_type: String(file.mime_type || file.type || "application/octet-stream"),
      type: String(file.type || file.mime_type || "application/octet-stream"),
      file_size: Number(file.file_size || file.size || 0),
      size: Number(file.size || file.file_size || 0),
      url: String(file.url || ""),
      storage_path: String(file.storage_path || ""),
      file: null,
    }
  }

  async function uploadFiles(files = []){
    const list = Array.isArray(files) ? files.filter(Boolean) : []
    if(!list.length){
      return []
    }

    if(typeof api.uploadFiles !== "function"){
      throw new Error("NovaAPI.uploadFiles missing")
    }

    const uploaded = await api.uploadFiles(list)
    return Array.isArray(uploaded)
      ? uploaded.map(normalizeUploadedFile)
      : []
  }

  async function uploadPendingFiles(items = []){
    const pendingItems = Array.isArray(items) ? items.filter(Boolean) : []
    const filesOnly = pendingItems
      .map(item => item?.file || item)
      .filter(Boolean)

    if(!filesOnly.length){
      return []
    }

    return await uploadFiles(filesOnly)
  }

  getFileInput()

  return {
    getPendingFiles,
    setPendingFiles,
    setOnChange,
    clearPendingFiles,
    clearPending,
    removePendingFileByIndex,
    openFilePicker,
    openPicker,
    pickFiles,
    uploadFiles,
    uploadPendingFiles,
  }
}

window.NovaAttachmentsService = {
  create: createAttachmentsService,
  createAttachmentsService,
}

window.NovaAttachments = window.NovaAttachmentsService

})()