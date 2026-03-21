// C:\Users\Owner\nova\static\js\attachments-service.js

(() => {
"use strict"

const chatStateApi = window.NovaChatState

if(!chatStateApi){
  throw new Error("NovaAttachmentsService: window.NovaChatState is required")
}

const { state } = chatStateApi

function createAttachmentsService(options = {}){
  const {
    state,
    elements = {},
    onChange = null,
  } = options

  if(!state){
    throw new Error("NovaAttachmentsService: state is required")
  }

  const api = window.NovaAPI || {}

  const el = {
    pendingAttachments: elements.pendingAttachments || document.getElementById("pendingAttachments") || null,
    fileInput: elements.fileInput || document.getElementById("fileInput") || null,
    messagesScroll: elements.messagesScroll || document.getElementById("messagesScroll") || null,
    composer: elements.composer || document.getElementById("composer") || null,
    attachBtn: elements.attachBtn || document.getElementById("attachBtn") || null,
  }

  let fallbackFileInput = null
  let changeHandler = typeof onChange === "function" ? onChange : null
  let dragBound = false
  let attachBound = false

  function ensurePendingFiles(){
    if(!Array.isArray(state.pendingFiles)){
      state.pendingFiles = []
    }

    state.pendingAttachments = state.pendingFiles
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

  function generateId(prefix = "att"){
    if(window.crypto?.randomUUID){
      return `${prefix}_${window.crypto.randomUUID()}`
    }
    return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`
  }

  function escapeHtml(value){
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;")
  }

  function getFileName(file = {}){
    return String(file?.filename || file?.name || "file").trim() || "file"
  }

  function getFileSize(file = {}){
    const value = Number(file?.file_size ?? file?.size ?? 0)
    return Number.isFinite(value) ? value : 0
  }

  function formatBytes(bytes){
    const value = Number(bytes || 0)

    if(!Number.isFinite(value) || value <= 0){
      return "0 B"
    }

    const units = ["B", "KB", "MB", "GB", "TB"]
    let size = value
    let unitIndex = 0

    while(size >= 1024 && unitIndex < units.length - 1){
      size /= 1024
      unitIndex += 1
    }

    if(unitIndex === 0){
      return `${Math.round(size)} ${units[unitIndex]}`
    }

    return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[unitIndex]}`
  }

  function getFileType(file = {}){
    return String(file?.mime_type || file?.type || "application/octet-stream").trim() || "application/octet-stream"
  }

  function isImageFile(file = {}){
    const type = getFileType(file).toLowerCase()
    const name = getFileName(file).toLowerCase()

    return (
      type.startsWith("image/") ||
      name.endsWith(".png") ||
      name.endsWith(".jpg") ||
      name.endsWith(".jpeg") ||
      name.endsWith(".gif") ||
      name.endsWith(".webp") ||
      name.endsWith(".bmp") ||
      name.endsWith(".svg")
    )
  }

  function getFileIcon(file = {}){
    const name = getFileName(file).toLowerCase()
    const type = getFileType(file).toLowerCase()

    if(type.startsWith("image/")) return "🖼"
    if(type.startsWith("audio/")) return "🎵"
    if(type.startsWith("video/")) return "🎬"
    if(type.includes("pdf") || name.endsWith(".pdf")) return "📕"
    if(name.endsWith(".zip") || name.endsWith(".rar") || name.endsWith(".7z")) return "🗜"
    if(
      name.endsWith(".js") ||
      name.endsWith(".ts") ||
      name.endsWith(".py") ||
      name.endsWith(".html") ||
      name.endsWith(".css") ||
      name.endsWith(".json") ||
      name.endsWith(".md") ||
      name.endsWith(".sql")
    ){
      return "💻"
    }

    return "📄"
  }

  function createObjectPreview(file){
    try{
      if(file instanceof File && isImageFile(file) && typeof URL !== "undefined" && typeof URL.createObjectURL === "function"){
        return URL.createObjectURL(file)
      }
    }catch(error){
      console.error("NovaAttachmentsService preview create error:", error)
    }

    return ""
  }

  function revokePreviewUrl(item){
    try{
      const previewUrl = String(item?.preview_url || "").trim()
      const isObjectUrl = previewUrl.startsWith("blob:")

      if(isObjectUrl && typeof URL !== "undefined" && typeof URL.revokeObjectURL === "function"){
        URL.revokeObjectURL(previewUrl)
      }
    }catch(error){
      console.error("NovaAttachmentsService preview revoke error:", error)
    }
  }

  function extractUploadedList(payload){
    if(Array.isArray(payload)){
      return payload
    }

    if(payload && typeof payload === "object"){
      if(Array.isArray(payload.files)){
        return payload.files
      }

      if(Array.isArray(payload.attachments)){
        return payload.attachments
      }

      if(Array.isArray(payload.uploaded)){
        return payload.uploaded
      }

      if(Array.isArray(payload.data)){
        return payload.data
      }
    }

    return []
  }

  function normalizeUploadedFile(file = {}){
    const id = String(file.id || file.attachment_id || generateId("att")).trim()
    const attachmentId = String(file.attachment_id || file.id || id).trim()
    const previewUrl = String(
      file.preview_url ||
      file.url ||
      file.storage_path ||
      ""
    ).trim()

    return {
      id,
      attachment_id: attachmentId,
      filename: getFileName(file),
      name: getFileName(file),
      mime_type: getFileType(file),
      type: getFileType(file),
      file_size: getFileSize(file),
      size: getFileSize(file),
      url: String(file.url || "").trim(),
      storage_path: String(file.storage_path || "").trim(),
      preview_url: previewUrl,
      file: null,
      isUploaded: true,
    }
  }

  function normalizePendingItem(item){
    if(!item){
      return null
    }

    if(item instanceof File){
      return {
        id: generateId("local"),
        attachment_id: "",
        filename: item.name || "file",
        name: item.name || "file",
        mime_type: item.type || "application/octet-stream",
        type: item.type || "application/octet-stream",
        file_size: Number(item.size || 0),
        size: Number(item.size || 0),
        url: "",
        storage_path: "",
        preview_url: createObjectPreview(item),
        file: item,
        isUploaded: false,
      }
    }

    if(item.file instanceof File){
      return {
        id: String(item.id || item.attachment_id || generateId("local")).trim(),
        attachment_id: String(item.attachment_id || "").trim(),
        filename: getFileName(item),
        name: getFileName(item),
        mime_type: getFileType(item),
        type: getFileType(item),
        file_size: getFileSize(item),
        size: getFileSize(item),
        url: String(item.url || "").trim(),
        storage_path: String(item.storage_path || "").trim(),
        preview_url: String(item.preview_url || "").trim() || createObjectPreview(item.file),
        file: item.file,
        isUploaded: false,
      }
    }

    return normalizeUploadedFile(item)
  }

  function cleanupPreviewUrls(files = []){
    for(const file of Array.isArray(files) ? files : []){
      revokePreviewUrl(file)
    }
  }

  function getPendingFiles(){
    return ensurePendingFiles()
      .map(normalizePendingItem)
      .filter(Boolean)
  }

  function setPendingFiles(files = []){
    const previous = ensurePendingFiles().slice()
    const normalized = Array.isArray(files)
      ? files.map(normalizePendingItem).filter(Boolean)
      : []

    cleanupPreviewUrls(previous.filter(oldItem => {
      const oldId = String(oldItem?.id || "")
      return !normalized.some(newItem => String(newItem?.id || "") === oldId)
    }))

    state.pendingFiles = normalized
    state.pendingAttachments = normalized
    renderPendingAttachments()
    notifyChange(normalized)
    return normalized
  }

  function addPendingFiles(files = []){
    const nextFiles = [
      ...getPendingFiles(),
      ...(Array.isArray(files) ? files : []),
    ]
    return setPendingFiles(nextFiles)
  }

  function clearPendingFiles(){
    cleanupPreviewUrls(getPendingFiles())

    state.pendingFiles = []
    state.pendingAttachments = []
    renderPendingAttachments()
    notifyChange([])

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

    const removed = nextFiles[fileIndex]
    revokePreviewUrl(removed)

    nextFiles.splice(fileIndex, 1)
    setPendingFiles(nextFiles)
  }

  function bindInput(input){
    if(!input || input.dataset.novaAttachmentsBound === "true"){
      return input
    }

    input.addEventListener("change", () => {
      try{
        const files = Array.from(input.files || [])
        if(!files.length){
          return
        }

        addPendingFiles(files)
      }catch(error){
        console.error("NovaAttachmentsService input change error:", error)
      }finally{
        input.value = ""
      }
    })

    input.dataset.novaAttachmentsBound = "true"
    return input
  }

  function createFallbackInput(){
    if(fallbackFileInput && document.body.contains(fallbackFileInput)){
      return fallbackFileInput
    }

    fallbackFileInput = document.createElement("input")
    fallbackFileInput.type = "file"
    fallbackFileInput.multiple = true
    fallbackFileInput.hidden = true
    fallbackFileInput.id = "fileInput"
    fallbackFileInput.setAttribute("aria-hidden", "true")
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

    el.fileInput = createFallbackInput()
    return el.fileInput
  }

  function openFilePicker(){
    const input = getFileInput()
    if(!input){
      return
    }
    input.click()
  }

  function openPicker(){
    openFilePicker()
  }

  function pickFiles(){
    openFilePicker()
  }

  async function pickAttachments(){
    openFilePicker()
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
    const uploadedList = extractUploadedList(uploaded)

    return uploadedList
      .map(normalizeUploadedFile)
      .filter(Boolean)
  }

  async function uploadPendingFiles(items = []){
    const pendingItems = Array.isArray(items)
      ? items.map(normalizePendingItem).filter(Boolean)
      : []

    const alreadyUploaded = pendingItems
      .filter(item => item && !item.file && (item.isUploaded || item.attachment_id || item.url || item.storage_path))
      .map(normalizeUploadedFile)
      .filter(Boolean)

    const localFiles = pendingItems
      .filter(item => item?.file instanceof File)

    if(!localFiles.length){
      return alreadyUploaded
    }

    const uploadedFresh = await uploadFiles(localFiles.map(item => item.file))

    return [
      ...alreadyUploaded,
      ...uploadedFresh,
    ]
  }

  async function uploadPendingAttachments(){
    const pending = getPendingFiles()
    const uploaded = await uploadPendingFiles(pending)

    const normalizedUploaded = Array.isArray(uploaded)
      ? uploaded.map(normalizeUploadedFile).filter(Boolean)
      : []

    setPendingFiles(normalizedUploaded)
    return normalizedUploaded
  }

  function makeAttachmentPayload(items = []){
    return (Array.isArray(items) ? items : [])
      .map(normalizeUploadedFile)
      .filter(Boolean)
      .map(item => ({
        id: item.id || item.attachment_id || "",
        attachment_id: item.attachment_id || item.id || "",
        filename: item.filename || item.name || "file",
        name: item.filename || item.name || "file",
        mime_type: item.mime_type || item.type || "application/octet-stream",
        type: item.mime_type || item.type || "application/octet-stream",
        file_size: Number(item.file_size || item.size || 0),
        size: Number(item.file_size || item.size || 0),
        url: item.url || "",
        storage_path: item.storage_path || "",
        preview_url: item.preview_url || "",
      }))
  }

  function attachExistingFile(file = {}){
    const normalized = normalizeUploadedFile(file)
    addPendingFiles([normalized])
    return normalized
  }

  function preventDefaults(event){
    event.preventDefault()
    event.stopPropagation()
  }

  function setDragActive(active){
    if(el.messagesScroll){
      el.messagesScroll.classList.toggle("nova-drag-active", !!active)
    }

    if(el.composer){
      el.composer.classList.toggle("nova-drag-active", !!active)
    }

    document.body.classList.toggle("nova-drag-page-active", !!active)
  }

  function injectDragStyles(){
    if(document.getElementById("nova-attachments-drag-styles")){
      return
    }

    const style = document.createElement("style")
    style.id = "nova-attachments-drag-styles"
    style.textContent = `
      .nova-drag-active{
        outline:2px dashed rgba(255,255,255,0.35);
        outline-offset:-4px;
      }

      .nova-drag-page-active{
        cursor:copy;
      }
    `
    document.head.appendChild(style)
  }

  function bindDropArea(area){
    if(!area || area.dataset.novaDropBound === "true"){
      return
    }

    area.dataset.novaDropBound = "true"

    area.addEventListener("dragenter", (event) => {
      preventDefaults(event)
      setDragActive(true)
    })

    area.addEventListener("dragover", (event) => {
      preventDefaults(event)
      setDragActive(true)
    })

    area.addEventListener("dragleave", (event) => {
      preventDefaults(event)

      const currentTarget = event.currentTarget
      const relatedTarget = event.relatedTarget

      if(currentTarget && relatedTarget && currentTarget.contains?.(relatedTarget)){
        return
      }

      setDragActive(false)
    })

    area.addEventListener("drop", (event) => {
      preventDefaults(event)
      setDragActive(false)

      const files = Array.from(event.dataTransfer?.files || [])
      if(!files.length){
        return
      }

      addPendingFiles(files)
    })
  }

  function bindDragAndDrop(){
    if(dragBound){
      return
    }

    injectDragStyles()

    bindDropArea(document.body)
    bindDropArea(el.messagesScroll)
    bindDropArea(el.composer)

    dragBound = true
  }

  function bindAttachButton(){
    if(!el.attachBtn || attachBound || el.attachBtn.dataset.novaAttachBound === "true"){
      return
    }

    el.attachBtn.addEventListener("click", (event) => {
      event.preventDefault()
      openFilePicker()
    })

    el.attachBtn.dataset.novaAttachBound = "true"
    attachBound = true
  }

  function renderPendingAttachments(){
    if(!el.pendingAttachments){
      return
    }

    const files = getPendingFiles()

    if(!files.length){
      el.pendingAttachments.innerHTML = ""
      return
    }

    el.pendingAttachments.innerHTML = `
      <div class="nova-pending-grid">
        ${files.map((file, index) => {
          const name = escapeHtml(getFileName(file))
          const size = formatBytes(getFileSize(file))
          const icon = getFileIcon(file)
          const previewUrl = String(file.preview_url || "").trim()
          const showThumb = isImageFile(file) && !!previewUrl

          return `
            <div class="nova-pending-card ${showThumb ? "has-thumbnail" : ""}">
              <div class="nova-pending-card-main">
                ${
                  showThumb
                    ? `
                      <div class="nova-pending-card-thumb-wrap">
                        <img
                          class="nova-pending-card-thumb"
                          src="${escapeHtml(previewUrl)}"
                          alt="${name}"
                          loading="lazy"
                        >
                      </div>
                    `
                    : `<div class="nova-pending-card-icon">${icon}</div>`
                }
                <div class="nova-pending-card-text">
                  <div class="nova-pending-card-name" title="${name}">${name}</div>
                  <div class="nova-pending-card-meta">${escapeHtml(size)}</div>
                </div>
              </div>
              <button
                type="button"
                class="nova-pending-card-remove"
                data-attachment-index="${index}"
                aria-label="Remove attachment"
                title="Remove"
              >
                ×
              </button>
            </div>
          `
        }).join("")}
      </div>
    `

    const buttons = el.pendingAttachments.querySelectorAll("[data-attachment-index]")

    buttons.forEach(button => {
      if(button.dataset.bound === "true"){
        return
      }

      button.dataset.bound = "true"
      button.addEventListener("click", () => {
        removePendingFileByIndex(button.dataset.attachmentIndex)
      })
    })
  }

  function init(){
    getFileInput()
    bindDragAndDrop()
    bindAttachButton()
    renderPendingAttachments()
  }

  init()

  return {
    getPendingFiles,
    setPendingFiles,
    addPendingFiles,
    setOnChange,
    clearPendingFiles,
    clearPending,
    removePendingFileByIndex,
    openFilePicker,
    openPicker,
    pickFiles,
    pickAttachments,
    uploadFiles,
    uploadPendingFiles,
    uploadPendingAttachments,
    makeAttachmentPayload,
    attachExistingFile,
    renderPendingAttachments,
    bindDragAndDrop,
    bindAttachButton,
    ensurePendingAttachments: getPendingFiles,
  }
}

window.NovaAttachmentsServiceFactory = {
  create: createAttachmentsService,
  createAttachmentsService,
}

window.NovaAttachmentsService = createAttachmentsService({ state })
window.NovaAttachments = window.NovaAttachmentsServiceFactory

})()