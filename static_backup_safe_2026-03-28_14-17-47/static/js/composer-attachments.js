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

  if(!attachmentsService){
    throw new Error("NovaComposerAttachments: attachmentsService is required")
  }

  const el = {
    attachBtn: elements.attachBtn || document.getElementById("attachBtn") || null,
    fileInput: elements.fileInput || document.getElementById("fileInput") || null,
    pendingAttachments: elements.pendingAttachments || document.getElementById("pendingAttachments") || null,
    filesList: elements.filesList || document.getElementById("filesList") || null,
  }

  let eventsBound = false

  function notifyStateChange(){
    if(typeof onStateChange === "function"){
      onStateChange()
    }

    window.dispatchEvent(new CustomEvent("nova:attachments-ui-changed"))
  }

  function formatBytes(bytes){
    const value = Number(bytes || 0)

    if(value < 1024){
      return `${value} B`
    }

    if(value < 1024 * 1024){
      return `${(value / 1024).toFixed(1)} KB`
    }

    if(value < 1024 * 1024 * 1024){
      return `${(value / (1024 * 1024)).toFixed(1)} MB`
    }

    return `${(value / (1024 * 1024 * 1024)).toFixed(1)} GB`
  }

  function escapeHtml(value){
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;")
  }

  function getIconForType(type = "", name = ""){
    const lowerType = String(type || "").toLowerCase()
    const lowerName = String(name || "").toLowerCase()

    if(lowerType.includes("image/")){
      return "🖼️"
    }

    if(lowerType.includes("pdf") || lowerName.endsWith(".pdf")){
      return "📄"
    }

    if(
      lowerType.includes("json") ||
      lowerType.includes("javascript") ||
      lowerType.includes("python") ||
      lowerType.includes("html") ||
      lowerType.includes("css") ||
      lowerType.includes("xml") ||
      lowerName.endsWith(".py") ||
      lowerName.endsWith(".js") ||
      lowerName.endsWith(".ts") ||
      lowerName.endsWith(".html") ||
      lowerName.endsWith(".css") ||
      lowerName.endsWith(".json")
    ){
      return "💻"
    }

    if(
      lowerType.includes("zip") ||
      lowerType.includes("compressed") ||
      lowerName.endsWith(".zip") ||
      lowerName.endsWith(".rar") ||
      lowerName.endsWith(".7z")
    ){
      return "🗜️"
    }

    if(
      lowerType.includes("audio/") ||
      lowerType.includes("video/")
    ){
      return "🎞️"
    }

    return "📎"
  }

  function renderPendingAttachments(){
    if(!el.pendingAttachments){
      return
    }

    const attachments = attachmentsService.getAll()

    if(!attachments.length){
      el.pendingAttachments.innerHTML = ""
      return
    }

    el.pendingAttachments.innerHTML = attachments.map((attachment) => {
      const icon = getIconForType(attachment.type, attachment.name)
      const isImage = String(attachment.type || "").toLowerCase().startsWith("image/")
      const previewUrl = isImage ? attachmentsService.getObjectUrl(attachment.id) : ""

      return `
        <div class="pending-attachment-chip fade-in ${isImage ? "is-image" : ""}" data-attachment-id="${escapeHtml(attachment.id)}">
          <span class="pending-attachment-icon">
            ${
              previewUrl
                ? `<img class="pending-attachment-thumb" src="${escapeHtml(previewUrl)}" alt="${escapeHtml(attachment.name)}">`
                : icon
            }
          </span>
          <div class="pending-attachment-copy">
            <strong class="pending-attachment-name">${escapeHtml(attachment.name)}</strong>
            <small class="pending-attachment-meta">${escapeHtml(formatBytes(attachment.size))}</small>
          </div>
          <button
            class="pending-attachment-remove"
            type="button"
            data-remove-attachment="${escapeHtml(attachment.id)}"
            aria-label="Remove attachment"
            title="Remove attachment"
          >✕</button>
        </div>
      `
    }).join("")
  }

  function renderFilesPanel(){
    if(!el.filesList){
      return
    }

    const attachments = attachmentsService.getAll()

    if(!attachments.length){
      el.filesList.innerHTML = `
        <div class="empty-state-card fade-in panel-empty-card">
          <div class="empty-icon">📎</div>
          <h3>No pending files</h3>
          <p>Attach files from the composer and they will appear here before sending.</p>
        </div>
      `
      return
    }

    el.filesList.innerHTML = `
      <div class="files-panel-list">
        ${attachments.map((attachment) => {
          const icon = getIconForType(attachment.type, attachment.name)
          const isImage = String(attachment.type || "").toLowerCase().startsWith("image/")
          const previewUrl = isImage ? attachmentsService.getObjectUrl(attachment.id) : ""

          return `
            <div class="file-row fade-in" data-file-row-id="${escapeHtml(attachment.id)}">
              <div class="file-row-main">
                <span class="file-row-icon">
                  ${
                    previewUrl
                      ? `<img class="file-row-thumb" src="${escapeHtml(previewUrl)}" alt="${escapeHtml(attachment.name)}">`
                      : icon
                  }
                </span>
                <div class="file-row-copy">
                  <strong class="file-row-name">${escapeHtml(attachment.name)}</strong>
                  <small class="file-row-meta">${escapeHtml(attachment.type || "file")} • ${escapeHtml(formatBytes(attachment.size))}</small>
                </div>
              </div>
              <button
                class="file-row-remove btn btn-secondary"
                type="button"
                data-remove-attachment="${escapeHtml(attachment.id)}"
              >Remove</button>
            </div>
          `
        }).join("")}
      </div>
    `
  }

  function renderAll(){
    renderPendingAttachments()
    renderFilesPanel()
    notifyStateChange()
  }

  function handleFilesSelected(event){
    const files = Array.from(event?.target?.files || [])

    if(!files.length){
      return
    }

    attachmentsService.addFiles(files)
    renderAll()

    if(el.fileInput){
      el.fileInput.value = ""
    }
  }

  function handleRemoveClick(event){
    const target = event.target instanceof Element ? event.target.closest("[data-remove-attachment]") : null

    if(!target){
      return
    }

    const id = target.getAttribute("data-remove-attachment")
    if(!id){
      return
    }

    attachmentsService.removeAttachment(id)
    renderAll()
  }

  function bindEvents(){
    if(eventsBound){
      return
    }

    el.attachBtn?.addEventListener("click", () => {
      el.fileInput?.click()
    })

    el.fileInput?.addEventListener("change", handleFilesSelected)
    el.pendingAttachments?.addEventListener("click", handleRemoveClick)
    el.filesList?.addEventListener("click", handleRemoveClick)

    window.addEventListener("nova:attachments-changed", () => {
      renderPendingAttachments()
      renderFilesPanel()
    })

    eventsBound = true
  }

  function init(){
    bindEvents()
    renderAll()
  }

  return {
    init,
    renderAll,
    renderPendingAttachments,
    renderFilesPanel,
  }
}

window.NovaComposerAttachments = {
  createComposerAttachments,
}

})()