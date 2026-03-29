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
    attachBtn: elements.attachBtn || null,
    pendingAttachments: elements.pendingAttachments || null,
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
    if(!Array.isArray(state.pendingAttachments)){
      state.pendingAttachments = []
    }
    return state.pendingAttachments
  }

  function normalizePendingFile(file){
    if(!file){
      return null
    }

    if(file instanceof File){
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
      }
    }

    return {
      id: String(file.id || file.attachment_id || generateId("pending")),
      file: file.file || null,
      attachment_id: String(file.attachment_id || ""),
      filename: file.filename || file.name || "file",
      name: file.name || file.filename || "file",
      mime_type: file.mime_type || file.type || "application/octet-stream",
      type: file.type || file.mime_type || "application/octet-stream",
      file_size: Number(file.file_size || file.size || 0),
      size: Number(file.size || file.file_size || 0),
      url: file.url || "",
      storage_path: file.storage_path || "",
    }
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

    el.pendingAttachments.innerHTML = files.map((file, index) => {
      const name = escapeHtml(file.filename || file.name || "file")
      return `
        <div class="pending-attachment-chip">
          <span class="pending-attachment-name">${name}</span>
          <button
            type="button"
            class="pending-attachment-remove"
            data-remove-pending-index="${index}"
            aria-label="Remove attachment"
          >
            ×
          </button>
        </div>
      `
    }).join("")
  }

  function setPendingFiles(files){
    state.pendingAttachments = Array.isArray(files)
      ? files.map(normalizePendingFile).filter(Boolean)
      : []

    renderPendingAttachments()

    if(typeof onStateChange === "function"){
      onStateChange()
    }
  }

  function removePendingFileAt(index){
    const files = ensurePendingAttachments().slice()
    files.splice(index, 1)
    state.pendingAttachments = files
    renderPendingAttachments()

    if(typeof onStateChange === "function"){
      onStateChange()
    }
  }

  async function pickAttachments(){
    if(attachmentsService && typeof attachmentsService.openPicker === "function"){
      const picked = await attachmentsService.openPicker()
      if(Array.isArray(picked) && picked.length){
        setPendingFiles([...ensurePendingAttachments(), ...picked])
      }
      return
    }

    if(attachmentsService && typeof attachmentsService.pickFiles === "function"){
      const picked = await attachmentsService.pickFiles()
      if(Array.isArray(picked) && picked.length){
        setPendingFiles([...ensurePendingAttachments(), ...picked])
      }
      return
    }

    const input = document.createElement("input")
    input.type = "file"
    input.multiple = true
    input.addEventListener("change", () => {
      const files = Array.from(input.files || [])
      if(files.length){
        setPendingFiles([...ensurePendingAttachments(), ...files])
      }
    })
    input.click()
  }

  async function uploadPendingAttachments(){
    const pending = ensurePendingAttachments()
    if(!pending.length){
      return []
    }

    const filesOnly = pending.map((item) => item.file).filter(Boolean)

    if(filesOnly.length && attachmentsService && typeof attachmentsService.uploadFiles === "function"){
      const uploaded = await attachmentsService.uploadFiles(filesOnly)
      return Array.isArray(uploaded) ? uploaded.map(normalizePendingFile).filter(Boolean) : []
    }

    if(attachmentsService && typeof attachmentsService.uploadPendingFiles === "function"){
      const uploaded = await attachmentsService.uploadPendingFiles(pending)
      return Array.isArray(uploaded) ? uploaded.map(normalizePendingFile).filter(Boolean) : []
    }

    return pending
  }

  function makeAttachmentPayload(items = []){
    return items.map((item) => ({
      attachment_id: item.attachment_id || item.id || "",
      id: item.id || item.attachment_id || "",
      filename: item.filename || item.name || "file",
      mime_type: item.mime_type || item.type || "application/octet-stream",
      file_size: Number(item.file_size || item.size || 0),
      storage_path: item.storage_path || item.url || "",
      url: item.url || "",
    }))
  }

  function handlePendingAttachmentClick(event){
    const removeBtn = event.target.closest("[data-remove-pending-index]")
    if(!removeBtn){
      return
    }

    const index = Number(removeBtn.getAttribute("data-remove-pending-index"))
    if(Number.isFinite(index)){
      removePendingFileAt(index)
    }
  }

  function bindEvents(){
    el.attachBtn?.addEventListener("click", async () => {
      try{
        await pickAttachments()
      }catch(error){
        console.error("NovaComposer attachment picker error:", error)
      }
    })

    el.pendingAttachments?.addEventListener("click", handlePendingAttachmentClick)

    renderPendingAttachments()
  }

  return {
    bindEvents,
    ensurePendingAttachments,
    normalizePendingFile,
    renderPendingAttachments,
    setPendingFiles,
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