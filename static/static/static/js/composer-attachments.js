// C:\Users\Owner\nova\static\js\composer-attachments.js

(() => {
"use strict"

function createComposerAttachments(options = {}){
  const {
    state,
    elements = {},
    attachmentsService = null,
    onStateChange = null,
  } = options

  if(!state){
    throw new Error("NovaComposerAttachments: state is required")
  }

  const el = {
    attachBtn: elements.attachBtn || document.getElementById("attachBtn") || null,
    pendingAttachments: elements.pendingAttachments || document.getElementById("pendingAttachments") || null,
  }

  let eventsBound = false

  function notifyStateChange(){
    if(typeof onStateChange === "function"){
      onStateChange()
    }
  }

  function generateId(prefix = "pending"){
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

  function ensurePendingAttachments(){
    if(Array.isArray(state.pendingFiles)){
      state.pendingAttachments = state.pendingFiles
      return state.pendingAttachments
    }

    if(!Array.isArray(state.pendingAttachments)){
      state.pendingAttachments = []
    }

    state.pendingFiles = state.pendingAttachments
    return state.pendingAttachments
  }

  function getFileHref(file = {}){
    return String(
      file.preview_url ||
      file.url ||
      file.storage_path ||
      file.path ||
      file.file_path ||
      ""
    ).trim()
  }

  function isImageFile(file = {}){
    const type = String(file.mime_type || file.type || "").toLowerCase()
    const name = String(file.filename || file.name || "").toLowerCase()

    if(file.file instanceof File){
      const fileType = String(file.file.type || "").toLowerCase()
      const fileName = String(file.file.name || "").toLowerCase()

      return (
        fileType.startsWith("image/") ||
        fileName.endsWith(".png") ||
        fileName.endsWith(".jpg") ||
        fileName.endsWith(".jpeg") ||
        fileName.endsWith(".gif") ||
        fileName.endsWith(".webp") ||
        fileName.endsWith(".bmp") ||
        fileName.endsWith(".svg")
      )
    }

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

  function revokePreviewUrl(file = {}){
    const previewUrl = String(file.preview_url || "").trim()

    if(previewUrl.startsWith("blob:")){
      try{
        URL.revokeObjectURL(previewUrl)
      }catch(_error){
      }
    }
  }

  function normalizePendingFile(file){
    if(!file){
      return null
    }

    if(file instanceof File){
      const previewUrl = file.type && file.type.startsWith("image/")
        ? URL.createObjectURL(file)
        : ""

      return {
        id: generateId("pending"),
        file,
        attachment_id: "",
        filename: file.name || "file",
        name: file.name || "file",
        mime_type: file.type || "application/octet-stream",
        type: file.type || "application/octet-stream",
        file_size: Number(file.size || 0),
        size: Number(file.size || 0),
        url: "",
        storage_path: "",
        preview_url: previewUrl,
        isUploaded: false,
      }
    }

    const normalized = {
      id: String(file.id || file.attachment_id || generateId("pending")).trim(),
      file: file.file instanceof File ? file.file : null,
      attachment_id: String(file.attachment_id || "").trim(),
      filename: String(file.filename || file.name || "file").trim() || "file",
      name: String(file.name || file.filename || "file").trim() || "file",
      mime_type: String(file.mime_type || file.type || "application/octet-stream").trim() || "application/octet-stream",
      type: String(file.type || file.mime_type || "application/octet-stream").trim() || "application/octet-stream",
      file_size: Number(file.file_size || file.size || 0),
      size: Number(file.size || file.file_size || 0),
      url: String(file.url || "").trim(),
      storage_path: String(file.storage_path || "").trim(),
      preview_url: String(file.preview_url || "").trim(),
      isUploaded: !!file.isUploaded || !!file.attachment_id,
    }

    if(!normalized.preview_url && normalized.file instanceof File && isImageFile(normalized)){
      normalized.preview_url = URL.createObjectURL(normalized.file)
    }

    return normalized
  }

  function setStatePendingFiles(files = []){
    const previous = ensurePendingAttachments().slice()

    const normalized = Array.isArray(files)
      ? files.map(normalizePendingFile).filter(Boolean)
      : []

    previous.forEach((file) => {
      const exists = normalized.some((nextFile) => nextFile.id === file.id)
      if(!exists){
        revokePreviewUrl(file)
      }
    })

    state.pendingAttachments = normalized
    state.pendingFiles = normalized
    return normalized
  }

  function renderPendingAttachments(){
    if(!el.pendingAttachments){
      return
    }

    const files = ensurePendingAttachments()

    if(!files.length){
      el.pendingAttachments.innerHTML = ""
      return
    }

    el.pendingAttachments.innerHTML = `
      <div class="nova-pending-grid">
        ${files.map((file, index) => renderPendingCard(file, index)).join("")}
      </div>
    `
  }

  function setPendingFiles(files = []){
    const normalized = setStatePendingFiles(files)

    if(attachmentsService && typeof attachmentsService.setPendingFiles === "function"){
      attachmentsService.setPendingFiles(normalized)
    }

    renderPendingAttachments()
    notifyStateChange()
    return normalized
  }

  function addPendingFiles(files = []){
    const current = ensurePendingAttachments()
    return setPendingFiles([
      ...current,
      ...(Array.isArray(files) ? files : []),
    ])
  }

  function removePendingFileAt(index){
    const files = ensurePendingAttachments().slice()
    const fileIndex = Number(index)

    if(!Number.isFinite(fileIndex) || fileIndex < 0 || fileIndex >= files.length){
      return
    }

    const removed = files[fileIndex]
    revokePreviewUrl(removed)
    files.splice(fileIndex, 1)

    if(attachmentsService && typeof attachmentsService.setPendingFiles === "function"){
      attachmentsService.setPendingFiles(files)
      setStatePendingFiles(files)
      renderPendingAttachments()
      notifyStateChange()
      return
    }

    setStatePendingFiles(files)
    renderPendingAttachments()
    notifyStateChange()
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

  function getFileIcon(file = {}){
    const name = String(file.filename || file.name || "").toLowerCase()
    const type = String(file.mime_type || file.type || "").toLowerCase()

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

  function renderPendingCard(file, index){
    const name = escapeHtml(file.filename || file.name || "file")
    const size = escapeHtml(formatBytes(file.file_size || file.size || 0))
    const href = escapeHtml(getFileHref(file))
    const isImage = isImageFile(file)
    const icon = getFileIcon(file)
    const thumb = isImage && href
      ? `
        <div class="nova-pending-card-thumb-wrap">
          <img
            class="nova-pending-card-thumb"
            src="${href}"
            alt="${name}"
            loading="lazy"
          >
        </div>
      `
      : `<div class="nova-pending-card-icon">${icon}</div>`

    return `
      <div class="nova-pending-card ${isImage && href ? "has-thumbnail" : ""}">
        <div class="nova-pending-card-main">
          ${thumb}
          <div class="nova-pending-card-text">
            <div class="nova-pending-card-name" title="${name}">${name}</div>
            <div class="nova-pending-card-meta">${size}</div>
          </div>
        </div>
        <button
          type="button"
          class="nova-pending-card-remove"
          data-remove-pending-index="${index}"
          aria-label="Remove attachment"
          title="Remove"
        >
          ×
        </button>
      </div>
    `
  }

  async function pickAttachments(){
    if(attachmentsService && typeof attachmentsService.pickAttachments === "function"){
      await attachmentsService.pickAttachments()
      syncFromService()
      renderPendingAttachments()
      notifyStateChange()
      return
    }

    if(attachmentsService && typeof attachmentsService.openFilePicker === "function"){
      attachmentsService.openFilePicker()
      return
    }

    if(attachmentsService && typeof attachmentsService.openPicker === "function"){
      attachmentsService.openPicker()
      return
    }

    if(attachmentsService && typeof attachmentsService.pickFiles === "function"){
      attachmentsService.pickFiles()
      return
    }

    const input = document.createElement("input")
    input.type = "file"
    input.multiple = true
    input.hidden = true

    input.addEventListener("change", () => {
      const files = Array.from(input.files || [])
      if(files.length){
        addPendingFiles(files)
      }
      input.remove()
    }, { once: true })

    document.body.appendChild(input)
    input.click()
  }

  async function uploadPendingAttachments(){
    const pending = ensurePendingAttachments()

    if(!pending.length){
      return []
    }

    if(attachmentsService && typeof attachmentsService.uploadPendingAttachments === "function"){
      const uploaded = await attachmentsService.uploadPendingAttachments()
      return Array.isArray(uploaded)
        ? uploaded.map(normalizePendingFile).filter(Boolean)
        : []
    }

    const filesOnly = pending.map(item => item?.file).filter(file => file instanceof File)

    if(filesOnly.length && attachmentsService && typeof attachmentsService.uploadFiles === "function"){
      const uploaded = await attachmentsService.uploadFiles(filesOnly)
      return Array.isArray(uploaded)
        ? uploaded.map(normalizePendingFile).filter(Boolean)
        : []
    }

    if(attachmentsService && typeof attachmentsService.uploadPendingFiles === "function"){
      const uploaded = await attachmentsService.uploadPendingFiles(pending)
      return Array.isArray(uploaded)
        ? uploaded.map(normalizePendingFile).filter(Boolean)
        : []
    }

    return pending.map(normalizePendingFile).filter(Boolean)
  }

  function makeAttachmentPayload(items = []){
    if(attachmentsService && typeof attachmentsService.makeAttachmentPayload === "function"){
      return attachmentsService.makeAttachmentPayload(items)
    }

    return (Array.isArray(items) ? items : [])
      .map(normalizePendingFile)
      .filter(Boolean)
      .map(item => ({
        attachment_id: item.attachment_id || item.id || "",
        id: item.id || item.attachment_id || "",
        filename: item.filename || item.name || "file",
        name: item.filename || item.name || "file",
        mime_type: item.mime_type || item.type || "application/octet-stream",
        type: item.mime_type || item.type || "application/octet-stream",
        file_size: Number(item.file_size || item.size || 0),
        size: Number(item.file_size || item.size || 0),
        storage_path: item.storage_path || "",
        url: item.url || "",
        preview_url: item.preview_url || "",
      }))
  }

  function handlePendingAttachmentClick(event){
    const target = event.target instanceof Element ? event.target : null
    const removeBtn = target ? target.closest("[data-remove-pending-index], [data-attachment-index]") : null
    if(!removeBtn){
      return
    }

    const rawIndex =
      removeBtn.getAttribute("data-remove-pending-index") ??
      removeBtn.getAttribute("data-attachment-index")

    const index = Number(rawIndex)

    if(Number.isFinite(index)){
      removePendingFileAt(index)
    }
  }

  function syncFromService(){
    if(attachmentsService && typeof attachmentsService.getPendingFiles === "function"){
      const files = attachmentsService.getPendingFiles()
      setStatePendingFiles(Array.isArray(files) ? files : [])
      return
    }

    ensurePendingAttachments()
  }

  function bindEvents(){
    if(eventsBound){
      renderPendingAttachments()
      return
    }

    if(attachmentsService && typeof attachmentsService.setOnChange === "function"){
      attachmentsService.setOnChange((files) => {
        setStatePendingFiles(Array.isArray(files) ? files : [])
        renderPendingAttachments()
        notifyStateChange()
      })
    }

    el.attachBtn?.addEventListener("click", async (event) => {
      event.preventDefault()

      try{
        await pickAttachments()
      }catch(error){
        console.error("NovaComposer attachment picker error:", error)
      }
    })

    el.pendingAttachments?.addEventListener("click", handlePendingAttachmentClick)

    if(attachmentsService && typeof attachmentsService.bindDragAndDrop === "function"){
      attachmentsService.bindDragAndDrop()
    }

    syncFromService()
    renderPendingAttachments()
    eventsBound = true
  }

  return {
    bindEvents,
    ensurePendingAttachments,
    normalizePendingFile,
    renderPendingAttachments,
    setPendingFiles,
    addPendingFiles,
    removePendingFileAt,
    pickAttachments,
    uploadPendingAttachments,
    makeAttachmentPayload,
  }
}

window.NovaComposerAttachments = {
  create: createComposerAttachments,
  createComposerAttachments,
}

})()