// C:\Users\Owner\nova\static\js\attachments.js

(() => {
"use strict"

function createAttachmentsService(options = {}){
  const {
    state,
    elements = {},
    onChange,
  } = options

  if(!state){
    throw new Error("NovaAttachmentsService: state is required")
  }

  const el = {
    fileInput: elements.fileInput || null,
    pendingAttachments: elements.pendingAttachments || null,
    pendingAttachmentsList: elements.pendingAttachmentsList || null,
    composerMeta: elements.composerMeta || null,
  }

  const escapeHtml = window.NovaUtils?.escapeHtml || defaultEscapeHtml
  const formatBytes = window.NovaUtils?.formatBytes || defaultFormatBytes

  ensureAttachmentState()

  function ensureAttachmentState(){
    if(!state.attachments || typeof state.attachments !== "object"){
      state.attachments = {}
    }

    if(!Array.isArray(state.attachments.pendingFiles)){
      state.attachments.pendingFiles = []
    }
  }

  function getPendingFiles(){
    ensureAttachmentState()
    return [...state.attachments.pendingFiles]
  }

  function openPicker(){
    if(!el.fileInput){
      return
    }

    el.fileInput.click()
  }

  function handleFileInput(event){
    const input = event?.target || el.fileInput
    if(!input || !input.files){
      return
    }

    addFiles(Array.from(input.files))

    try{
      input.value = ""
    }catch(_error){
      // ignore reset issues
    }
  }

  function addFiles(files){
    ensureAttachmentState()

    const safeFiles = Array.isArray(files) ? files.filter(Boolean) : []
    if(safeFiles.length === 0){
      render()
      safeCall(onChange)
      return
    }

    const existing = state.attachments.pendingFiles
    const next = [...existing]

    safeFiles.forEach((file) => {
      if(!(file instanceof File)){
        return
      }

      const duplicate = next.some((pending) => isSameFile(pending, file))
      if(duplicate){
        return
      }

      next.push(file)
    })

    state.attachments.pendingFiles = next
    render()
    safeCall(onChange)
  }

  function removeFile(index){
    ensureAttachmentState()

    if(!Number.isInteger(index)){
      return
    }

    if(index < 0 || index >= state.attachments.pendingFiles.length){
      return
    }

    state.attachments.pendingFiles.splice(index, 1)
    render()
    safeCall(onChange)
  }

  function clear(){
    ensureAttachmentState()
    state.attachments.pendingFiles = []

    if(el.fileInput){
      try{
        el.fileInput.value = ""
      }catch(_error){
        // ignore reset issues
      }
    }

    render()
    safeCall(onChange)
  }

  function render(){
    ensureAttachmentState()

    const files = state.attachments.pendingFiles

    if(!el.pendingAttachments || !el.pendingAttachmentsList){
      return
    }

    if(!files.length){
      el.pendingAttachments.hidden = true
      el.pendingAttachmentsList.innerHTML = ""
      return
    }

    el.pendingAttachments.hidden = false

    el.pendingAttachmentsList.innerHTML = files
      .map((file, index) => {
        const name = escapeHtml(file.name || "Attachment")
        const type = escapeHtml(file.type || "application/octet-stream")
        const size = escapeHtml(formatBytes(file.size || 0))

        return `
          <div class="pending-attachment-chip" data-file-index="${index}">
            <div class="pending-attachment-copy">
              <div class="pending-attachment-name">${name}</div>
              <div class="pending-attachment-meta">${type} • ${size}</div>
            </div>

            <button
              type="button"
              class="pending-attachment-remove"
              data-remove-pending-file="${index}"
              aria-label="Remove ${name}"
              title="Remove"
            >
              ✕
            </button>
          </div>
        `
      })
      .join("")

    bindRemoveButtons()
  }

  function bindRemoveButtons(){
    if(!el.pendingAttachmentsList){
      return
    }

    const buttons = el.pendingAttachmentsList.querySelectorAll("[data-remove-pending-file]")

    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        const raw = button.getAttribute("data-remove-pending-file")
        const index = Number(raw)

        if(Number.isInteger(index)){
          removeFile(index)
        }
      })
    })
  }

  function isSameFile(a, b){
    if(!a || !b){
      return false
    }

    return (
      String(a.name || "") === String(b.name || "") &&
      Number(a.size || 0) === Number(b.size || 0) &&
      String(a.type || "") === String(b.type || "") &&
      Number(a.lastModified || 0) === Number(b.lastModified || 0)
    )
  }

  function safeCall(fn){
    if(typeof fn !== "function"){
      return
    }

    try{
      fn()
    }catch(error){
      console.error("NovaAttachmentsService callback failed:", error)
    }
  }

  return {
    openPicker,
    handleFileInput,
    addFiles,
    removeFile,
    clear,
    render,
    getPendingFiles,
  }
}

function defaultEscapeHtml(value){
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;")
}

function defaultFormatBytes(bytes){
  const n = Number(bytes || 0)

  if(!Number.isFinite(n) || n <= 0){
    return "0 B"
  }

  const units = ["B", "KB", "MB", "GB", "TB"]
  let size = n
  let i = 0

  while(size >= 1024 && i < units.length - 1){
    size /= 1024
    i += 1
  }

  return `${size < 10 && i > 0 ? size.toFixed(1) : Math.round(size)} ${units[i]}`
}

window.NovaAttachmentsService = {
  create: createAttachmentsService,
  createAttachmentsService
}})()